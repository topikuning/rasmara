"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  Plus, RefreshCw, ChevronDown, ChevronRight, Edit2, Trash2,
  CheckCircle2, AlertTriangle, Calculator, ShieldCheck,
  FileSpreadsheet, FileText, Upload, GitCompareArrows,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { downloadFile } from "@/lib/api/download";
import { useAuthStore } from "@/lib/auth/store";
import { formatRupiahFull, formatNumber, formatPercent } from "@/lib/format/rupiah";
import FilterableSelect from "@/components/form/FilterableSelect";
import { PpnBreakdown } from "@/components/contract/PpnBreakdown";

type Revision = {
  id: string;
  contract: string;
  version: number;
  status: "DRAFT" | "APPROVED" | "SUPERSEDED";
  status_display: string;
  is_active: boolean;
  approved_at: string | null;
  approved_by_username: string | null;
  notes: string;
  item_count: number;
  leaf_count: number;
  total_pre_ppn: string;
};

type Item = {
  id: string;
  boq_revision: string;
  facility: string;
  facility_code: string;
  facility_name: string;
  code: string;
  full_code: string;
  description: string;
  unit: string;
  volume: string;
  unit_price: string;
  total_price: string;
  weight_pct: string;
  parent: string | null;
  level: number;
  display_order: number;
  is_leaf: boolean;
  change_type: string;
  planned_start_week: number | null;
  planned_duration_weeks: number | null;
  notes: string;
};

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

type Budget = {
  boq_pre_ppn: string;
  ppn_pct: string;
  ppn_amount: string;
  boq_post_ppn: string;
  nilai_kontrak: string;
  gap: string;
  ok: boolean;
  tolerance: string;
};

export default function BoqPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const { hasPerm } = useAuthStore();

  const { data: revs } = useSWR<Paginated<Revision>>(
    `/boq-revisions/?contract=${contractId}&page_size=50&ordering=version`,
    swrFetcher,
  );
  const revisions = revs?.results ?? [];
  const activeRev = revisions.find((r) => r.is_active) || revisions[revisions.length - 1];
  const [selectedRevId, setSelectedRevId] = useState<string | null>(null);
  const currentRev = selectedRevId
    ? revisions.find((r) => r.id === selectedRevId)
    : activeRev;

  const { data: itemsResp, mutate: mutateItems } = useSWR<Paginated<Item>>(
    currentRev ? `/boq-items/?boq_revision=${currentRev.id}&page_size=2000` : null,
    swrFetcher,
  );
  const items = itemsResp?.results ?? [];

  const [showItemForm, setShowItemForm] = useState(false);
  const [editItem, setEditItem] = useState<Item | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [busy, setBusy] = useState(false);

  const isLocked = currentRev && (currentRev.status !== "DRAFT");
  const canEdit = hasPerm("boq.update") && !isLocked;

  async function onRecompute() {
    if (!currentRev) return;
    setBusy(true);
    try {
      await api(`/boq-revisions/${currentRev.id}/recompute/`, { method: "POST", body: {} });
      toast.success("Recompute selesai.");
      mutateItems();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onValidateBudget() {
    if (!currentRev) return;
    setBusy(true);
    try {
      const res = await api<Budget>(`/boq-revisions/${currentRev.id}/validate-budget/`,
                                      { method: "POST", body: {} });
      setBudget(res);
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onApprove() {
    if (!currentRev) return;
    if (!confirm(`Approve revisi V${currentRev.version}? Setelah ini, BOQ tidak bisa diedit langsung.`)) return;
    setBusy(true);
    try {
      await api(`/boq-revisions/${currentRev.id}/approve/`, { method: "POST", body: {} });
      toast.success(`Revisi V${currentRev.version} di-approve.`);
      // refresh both
      mutateItems();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteItem(item: Item) {
    if (!confirm(`Hapus "${item.full_code} - ${item.description.slice(0, 40)}"?\n\nChild item akan dipindah ke parent atas.`)) return;
    try {
      await api(`/boq-items/${item.id}/`, { method: "DELETE" });
      toast.success("Item dihapus.");
      mutateItems();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  // Build tree structure
  const tree = buildTree(items);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">BOQ (Bill of Quantity)</h2>
          {currentRev && (
            <p className="text-sm text-muted-fg">
              {revisions.length} revisi · Saat ini: <strong>V{currentRev.version}</strong> ({currentRev.status_display})
              {currentRev.is_active && <span className="ml-1 text-success">• aktif</span>}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            className="input max-w-[200px]"
            value={currentRev?.id || ""}
            onChange={(e) => setSelectedRevId(e.target.value)}
          >
            {revisions.map((r) => (
              <option key={r.id} value={r.id}>
                V{r.version} - {r.status_display}{r.is_active ? " (aktif)" : ""}
              </option>
            ))}
          </select>
          <button onClick={() => mutateItems()} className="btn-ghost" title="Refresh">
            <RefreshCw className="size-4" />
          </button>
          {canEdit && (
            <button onClick={() => { setEditItem(null); setShowItemForm(true); }} className="btn-primary">
              <Plus className="size-4 mr-1" /> Tambah Item
            </button>
          )}
        </div>
      </div>

      {/* Status / locking banner */}
      {isLocked && (
        <div className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm flex items-start gap-2">
          <ShieldCheck className="size-4 text-warning shrink-0 mt-0.5" />
          <div>
            Revisi <strong>V{currentRev?.version}</strong> ber-status <strong>{currentRev?.status_display}</strong>.
            Edit langsung dikunci. Perubahan harus melalui Addendum baru.
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {canEdit && (
          <button onClick={onRecompute} className="btn-secondary" disabled={busy}>
            <Calculator className="size-4 mr-1" /> Recompute Total & Bobot
          </button>
        )}
        <button onClick={onValidateBudget} className="btn-secondary" disabled={busy}>
          <CheckCircle2 className="size-4 mr-1" /> Cek Anggaran
        </button>
        {canEdit && hasPerm("boq.import") && (
          <Link href={`/kontrak/${contractId}/boq/import?revision=${currentRev?.id}`}
                className="btn-secondary">
            <Upload className="size-4 mr-1" /> Import Excel
          </Link>
        )}
        {currentRev && (
          <button
            onClick={() => downloadFile(`/boq-revisions/${currentRev.id}/export-xlsx/`,
                                          `BOQ-V${currentRev.version}.xlsx`)
                            .catch((e) => toast.error(e.message))}
            className="btn-secondary"
          >
            <FileSpreadsheet className="size-4 mr-1" /> Unduh Excel
          </button>
        )}
        {currentRev && (
          <button
            onClick={() => downloadFile(`/boq-revisions/${currentRev.id}/export-pdf/`,
                                          `BOQ-V${currentRev.version}.pdf`)
                            .catch((e) => toast.error(e.message))}
            className="btn-secondary"
          >
            <FileText className="size-4 mr-1" /> Unduh PDF
          </button>
        )}
        {revisions.length >= 2 && (
          <Link href={`/kontrak/${contractId}/boq/komparasi`} className="btn-secondary">
            <GitCompareArrows className="size-4 mr-1" /> Komparasi Revisi
          </Link>
        )}
        {canEdit && hasPerm("boq.approve") && currentRev?.status === "DRAFT" && (
          <button onClick={onApprove} className="btn-primary" disabled={busy}>
            <ShieldCheck className="size-4 mr-1" /> Approve V{currentRev.version}
          </button>
        )}
      </div>

      {/* Budget result */}
      {budget && (
        <div className={`rounded-lg border p-4 ${budget.ok ? "border-success/40 bg-success/5" : "border-danger/40 bg-danger/5"}`}>
          <div className="flex items-center gap-2 mb-2">
            {budget.ok ? <CheckCircle2 className="size-4 text-success" />
                        : <AlertTriangle className="size-4 text-danger" />}
            <strong>{budget.ok ? "Anggaran OK" : "Anggaran melebihi"}</strong>
          </div>
          <PpnBreakdown
            boqValue={budget.boq_pre_ppn}
            ppnPct={budget.ppn_pct}
            contractValue={budget.boq_post_ppn}
          />
          <div className="text-xs text-muted-fg mt-2">
            Nilai Kontrak: <strong>{formatRupiahFull(budget.nilai_kontrak)}</strong>
            {" — "}
            Selisih: <strong className={budget.ok ? "text-success" : "text-danger"}>
              {formatRupiahFull(budget.gap)}
            </strong>
          </div>
        </div>
      )}

      {/* Items tree */}
      <div className="card overflow-hidden">
        {items.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-fg mb-3">Belum ada item BOQ.</p>
            {canEdit && (
              <button onClick={() => { setEditItem(null); setShowItemForm(true); }} className="btn-primary">
                <Plus className="size-4 mr-1" /> Tambah Item Pertama
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b text-xs uppercase tracking-wide text-muted-fg bg-muted/30">
                  <th className="py-2 px-3">Kode</th>
                  <th className="py-2 px-3">Uraian Pekerjaan</th>
                  <th className="py-2 px-3 w-20">Sat.</th>
                  <th className="py-2 px-3 text-right w-28">Volume</th>
                  <th className="py-2 px-3 text-right w-32">Harga (PRE-PPN)</th>
                  <th className="py-2 px-3 text-right w-36">Total</th>
                  <th className="py-2 px-3 text-right w-20">Bobot %</th>
                  {canEdit && <th className="py-2 px-3 w-24">Aksi</th>}
                </tr>
              </thead>
              <tbody>
                {tree.map((node) => (
                  <BoqRow
                    key={node.id}
                    node={node}
                    canEdit={canEdit}
                    onEdit={(it) => { setEditItem(it); setShowItemForm(true); }}
                    onDelete={onDeleteItem}
                  />
                ))}
                {/* Footer total */}
                <tr className="border-t bg-muted/30 font-semibold">
                  <td colSpan={5} className="py-2 px-3 text-right">
                    Total Leaf (PRE-PPN):
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {formatRupiahFull(currentRev?.total_pre_ppn ?? "0")}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {currentRev?.leaf_count} leaf · {(currentRev?.item_count ?? 0) - (currentRev?.leaf_count ?? 0)} parent
                  </td>
                  {canEdit && <td />}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showItemForm && currentRev && (
        <ItemFormModal
          revision={currentRev}
          contractId={contractId}
          editing={editItem}
          allItems={items}
          onClose={() => { setShowItemForm(false); setEditItem(null); }}
          onSaved={() => { setShowItemForm(false); setEditItem(null); mutateItems(); }}
        />
      )}
    </div>
  );
}

// ---------- Tree builder ----------
type Node = Item & { children: Node[]; expanded?: boolean };

function buildTree(items: Item[]): Node[] {
  const byId = new Map<string, Node>();
  items.forEach((i) => byId.set(i.id, { ...i, children: [] }));
  const roots: Node[] = [];
  byId.forEach((n) => {
    if (n.parent && byId.has(n.parent)) {
      byId.get(n.parent)!.children.push(n);
    } else {
      roots.push(n);
    }
  });
  // Sort children: first by display_order, then by code
  const sortFn = (a: Node, b: Node) =>
    a.display_order - b.display_order || a.code.localeCompare(b.code, undefined, { numeric: true });
  function rec(arr: Node[]) {
    arr.sort(sortFn);
    arr.forEach((c) => rec(c.children));
  }
  rec(roots);
  return roots;
}

// ---------- Row ----------
function BoqRow({
  node, canEdit, onEdit, onDelete, depth = 0,
}: {
  node: Node;
  canEdit: boolean;
  onEdit: (i: Item) => void;
  onDelete: (i: Item) => void;
  depth?: number;
}) {
  const [open, setOpen] = useState(true);
  const hasChildren = node.children.length > 0;

  return (
    <>
      <tr className={`border-b hover:bg-muted/20 ${!node.is_leaf ? "bg-muted/10" : ""}`}>
        <td className="py-1.5 px-3 font-mono text-xs">
          <div className="flex items-center" style={{ paddingLeft: `${depth * 16}px` }}>
            {hasChildren ? (
              <button onClick={() => setOpen(!open)} className="btn-ghost p-0.5 mr-1">
                {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              </button>
            ) : (
              <span className="inline-block w-5" />
            )}
            <span className={!node.is_leaf ? "font-semibold" : ""}>{node.full_code || node.code}</span>
          </div>
        </td>
        <td className="py-1.5 px-3">
          <span className={!node.is_leaf ? "font-semibold" : ""}>{node.description}</span>
          <div className="text-xs text-muted-fg">{node.facility_code} · {node.facility_name}</div>
        </td>
        <td className="py-1.5 px-3 text-xs">{node.unit}</td>
        <td className="py-1.5 px-3 text-right font-mono">
          {node.is_leaf ? formatNumber(node.volume, 4) : "—"}
        </td>
        <td className="py-1.5 px-3 text-right font-mono">
          {node.is_leaf ? formatRupiahFull(node.unit_price) : "—"}
        </td>
        <td className="py-1.5 px-3 text-right font-mono">
          {formatRupiahFull(node.total_price)}
        </td>
        <td className="py-1.5 px-3 text-right text-xs">
          {parseFloat(node.weight_pct) > 0 ? formatPercent(node.weight_pct, 2) : "—"}
        </td>
        {canEdit && (
          <td className="py-1.5 px-3">
            <div className="flex gap-1">
              <button onClick={() => onEdit(node)} className="btn-ghost p-1" title="Edit">
                <Edit2 className="size-3" />
              </button>
              <button onClick={() => onDelete(node)} className="btn-ghost p-1 text-danger" title="Hapus">
                <Trash2 className="size-3" />
              </button>
            </div>
          </td>
        )}
      </tr>
      {open && hasChildren && node.children.map((c) => (
        <BoqRow key={c.id} node={c} canEdit={canEdit} onEdit={onEdit} onDelete={onDelete} depth={depth + 1} />
      ))}
    </>
  );
}

// ---------- Item form modal ----------
function ItemFormModal({
  revision, contractId, editing, allItems, onClose, onSaved,
}: {
  revision: Revision;
  contractId: string;
  editing: Item | null;
  allItems: Item[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    facility: editing?.facility ?? "",
    code: editing?.code ?? "",
    description: editing?.description ?? "",
    unit: editing?.unit ?? "",
    volume: editing?.volume ?? "0",
    unit_price: editing?.unit_price ?? "0",
    parent: editing?.parent ?? "",
    display_order: editing?.display_order ?? 0,
    planned_start_week: editing?.planned_start_week ?? "",
    planned_duration_weeks: editing?.planned_duration_weeks ?? "",
    notes: editing?.notes ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  // Filter parents: harus dari fasilitas yang sama (atau global utk root)
  const parentCandidates = allItems.filter((i) =>
    i.id !== editing?.id &&  // tidak bisa pilih diri sendiri
    (form.facility ? i.facility === form.facility : true) &&
    i.level < 3,  // max depth 3 (sehingga child level <= 3, total 4 level 0-3)
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = {
        boq_revision: revision.id,
        facility: form.facility,
        code: form.code,
        description: form.description,
        unit: form.unit,
        volume: form.volume || "0",
        unit_price: form.unit_price || "0",
        parent: form.parent || null,
        display_order: form.display_order || 0,
        planned_start_week: form.planned_start_week || null,
        planned_duration_weeks: form.planned_duration_weeks || null,
        notes: form.notes,
      };
      if (editing) {
        await api(`/boq-items/${editing.id}/`, { method: "PATCH", body });
        toast.success("Item disimpan.");
      } else {
        await api(`/boq-items/`, { method: "POST", body });
        toast.success("Item dibuat.");
      }
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.details ? "\n" + JSON.stringify(err.details) : "";
        toast.error(`${err.message}${detail}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{editing ? "Edit Item BOQ" : "Tambah Item BOQ"}</h2>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Fasilitas <span className="text-danger">*</span></label>
            <FilterableSelect
              value={form.facility}
              onChange={(id) => setForm({ ...form, facility: id || "" })}
              fetchUrl={`/facilities/?location__contract=${contractId}&page_size=200`}
              getLabel={(f: any) => `${f.code} - ${f.name}`}
              getSubLabel={(f: any) => f.location_code ? `Lokasi ${f.location_code}` : null}
              placeholder="Pilih fasilitas..."
              required
              initialItem={editing ? {
                id: form.facility, code: editing.facility_code, name: editing.facility_name,
              } as any : null}
            />
          </div>
          <div>
            <label className="label">Kode <span className="text-danger">*</span></label>
            <input className="input font-mono" required value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    placeholder="4, A, 1, a, dst." />
          </div>
        </div>

        <div>
          <label className="label">Uraian Pekerjaan <span className="text-danger">*</span></label>
          <textarea className="input" rows={2} required value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Satuan</label>
            <input className="input" value={form.unit}
                    onChange={(e) => setForm({ ...form, unit: e.target.value })}
                    placeholder="m2, m3, ls, unit" />
          </div>
          <div>
            <label className="label">Volume</label>
            <input className="input font-mono" type="number" step="0.0001" min="0"
                    value={form.volume}
                    onChange={(e) => setForm({ ...form, volume: e.target.value })} />
          </div>
          <div>
            <label className="label">Harga Satuan (PRE-PPN)</label>
            <input className="input font-mono" type="number" step="0.01" min="0"
                    value={form.unit_price}
                    onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
          </div>
        </div>

        <div>
          <label className="label">Parent (jika item ini sub-pekerjaan)</label>
          <select className="input" value={form.parent || ""}
                  onChange={(e) => setForm({ ...form, parent: e.target.value })}>
            <option value="">— tidak ada (root) —</option>
            {parentCandidates.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_code} — {p.description.slice(0, 60)}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-fg mt-1">
            Pilih parent untuk membuat hirarki. Maksimum 4 level (0-3).
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Urutan</label>
            <input className="input" type="number" min="0" value={form.display_order}
                    onChange={(e) => setForm({ ...form, display_order: parseInt(e.target.value || "0") })} />
          </div>
          <div>
            <label className="label">Mulai Minggu</label>
            <input className="input" type="number" min="1"
                    value={form.planned_start_week as any}
                    onChange={(e) => setForm({ ...form, planned_start_week: e.target.value as any })} />
          </div>
          <div>
            <label className="label">Durasi (minggu)</label>
            <input className="input" type="number" min="1"
                    value={form.planned_duration_weeks as any}
                    onChange={(e) => setForm({ ...form, planned_duration_weeks: e.target.value as any })} />
          </div>
        </div>

        <div>
          <label className="label">Catatan</label>
          <textarea className="input" rows={2} value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>

        <div className="flex gap-2 pt-2 border-t">
          <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={submitting}>Batal</button>
          <button type="submit" className="btn-primary flex-1" disabled={submitting}>
            {submitting ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </form>
    </div>
  );
}
