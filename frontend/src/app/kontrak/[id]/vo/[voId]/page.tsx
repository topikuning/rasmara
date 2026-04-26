"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  ArrowLeft, Plus, Trash2, Edit2, Send, CheckCircle2, XCircle, Undo2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { VOStatusBadge } from "@/components/contract/VOStatusBadge";
import FilterableSelect from "@/components/form/FilterableSelect";
import { formatNumber, formatRupiahFull } from "@/lib/format/rupiah";

type VOItem = {
  id: string;
  vo: string;
  action: string;
  action_display: string;
  source_boq_item: string | null;
  source_full_code: string | null;
  source_description: string | null;
  facility: string | null;
  facility_code: string | null;
  parent_boq_item: string | null;
  code: string;
  description: string;
  unit: string;
  new_description: string;
  new_unit: string;
  volume_delta: string;
  unit_price: string;
  notes: string;
};

type VODetail = {
  id: string;
  contract: string;
  number: string;
  title: string;
  justification: string;
  status: string;
  status_display: string;
  rejection_reason: string;
  notes: string;
  items: VOItem[];
};

const ACTIONS = [
  { value: "ADD", label: "Tambah Item Baru" },
  { value: "INCREASE", label: "Tambah Volume" },
  { value: "DECREASE", label: "Kurangi Volume" },
  { value: "MODIFY_SPEC", label: "Ubah Spesifikasi" },
  { value: "REMOVE", label: "Hapus Item" },
  { value: "REMOVE_FACILITY", label: "Hapus Fasilitas" },
];

export default function VODetailPage({
  params,
}: { params: Promise<{ id: string; voId: string }> }) {
  const { id: contractId, voId } = use(params);
  const { hasPerm } = useAuthStore();

  const { data, mutate } = useSWR<VODetail>(`/vos/${voId}/`, swrFetcher);
  const [showItemForm, setShowItemForm] = useState(false);
  const [editItem, setEditItem] = useState<VOItem | null>(null);
  const [busy, setBusy] = useState(false);

  if (!data) return <div className="text-sm text-muted-fg">Memuat...</div>;

  const isDraft = data.status === "DRAFT";
  const canEdit = hasPerm("vo.update") && isDraft;

  async function callAction(path: string, label: string, body: any = {}) {
    if (!confirm(`${label}?`)) return;
    setBusy(true);
    try {
      await api(`/vos/${voId}/${path}/`, { method: "POST", body });
      toast.success(`${label} berhasil.`);
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteItem(item: VOItem) {
    if (!confirm(`Hapus VO item ${item.action_display}?`)) return;
    try {
      await api(`/vo-items/${item.id}/`, { method: "DELETE" });
      toast.success("Item dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href={`/kontrak/${contractId}/vo`} className="btn-ghost p-1.5">
          <ArrowLeft className="size-4" />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted-fg font-mono">{data.number}</div>
          <h2 className="text-xl font-semibold">{data.title}</h2>
        </div>
        <VOStatusBadge status={data.status} />
      </div>

      {data.justification && (
        <div className="card p-4">
          <div className="text-xs uppercase text-muted-fg mb-1">Justifikasi Teknis</div>
          <p className="text-sm whitespace-pre-wrap">{data.justification}</p>
        </div>
      )}

      {data.status === "REJECTED" && data.rejection_reason && (
        <div className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm">
          <strong>Alasan Penolakan:</strong> {data.rejection_reason}
        </div>
      )}

      {/* State actions */}
      <div className="flex flex-wrap gap-2">
        {isDraft && hasPerm("vo.submit") && (
          <button onClick={() => callAction("submit", "Submit VO untuk review")}
                  className="btn-primary" disabled={busy || data.items.length === 0}>
            <Send className="size-4 mr-1" /> Submit untuk Review
          </button>
        )}
        {data.status === "UNDER_REVIEW" && hasPerm("vo.approve") && (
          <>
            <button onClick={() => callAction("approve", "Approve VO ini")}
                    className="btn-primary" disabled={busy}>
              <CheckCircle2 className="size-4 mr-1" /> Approve
            </button>
            <button onClick={() => callAction("return-to-draft", "Kembalikan ke Draft")}
                    className="btn-secondary" disabled={busy}>
              <Undo2 className="size-4 mr-1" /> Kembali ke Draft
            </button>
          </>
        )}
        {(data.status === "DRAFT" || data.status === "UNDER_REVIEW" || data.status === "APPROVED")
          && hasPerm("vo.reject") && (
          <button
            onClick={async () => {
              const reason = prompt("Alasan penolakan:");
              if (reason === null) return;
              await callAction("reject", "Reject VO", { reason });
            }}
            className="btn-danger" disabled={busy}>
            <XCircle className="size-4 mr-1" /> Reject
          </button>
        )}
      </div>

      {/* Items */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">Item Perubahan ({data.items.length})</h3>
          {canEdit && (
            <button onClick={() => { setEditItem(null); setShowItemForm(true); }} className="btn-primary">
              <Plus className="size-4 mr-1" /> Tambah Item
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b text-xs uppercase text-muted-fg bg-muted/30">
                <th className="py-2 px-3 w-32">Aksi</th>
                <th className="py-2 px-3">Source / Detail</th>
                <th className="py-2 px-3 text-right w-32">Volume Delta</th>
                <th className="py-2 px-3 text-right w-32">Harga</th>
                {canEdit && <th className="py-2 px-3 w-16">Aksi</th>}
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-muted-fg">Belum ada item.</td></tr>
              )}
              {data.items.map((it) => (
                <tr key={it.id} className="border-b hover:bg-muted/20">
                  <td className="py-2 px-3">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted">{it.action_display}</span>
                  </td>
                  <td className="py-2 px-3">
                    {it.action === "ADD" ? (
                      <div>
                        <div className="font-medium">{it.code} — {it.description}</div>
                        <div className="text-xs text-muted-fg">
                          Fasilitas: {it.facility_code} · Satuan: {it.unit}
                        </div>
                      </div>
                    ) : it.action === "REMOVE_FACILITY" ? (
                      <div className="text-sm">
                        Hapus seluruh fasilitas: <strong>{it.facility_code}</strong>
                      </div>
                    ) : (
                      <div>
                        <div className="font-mono text-xs">{it.source_full_code}</div>
                        <div className="text-sm">{it.source_description}</div>
                        {it.action === "MODIFY_SPEC" && (
                          <div className="text-xs text-muted-fg mt-1">
                            → {it.new_description || "(deskripsi tetap)"} {it.new_unit && `[${it.new_unit}]`}
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {it.action === "INCREASE" || it.action === "DECREASE" || it.action === "ADD"
                      ? formatNumber(it.volume_delta, 4)
                      : "—"}
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {it.action === "ADD" || it.action === "MODIFY_SPEC"
                      ? formatRupiahFull(it.unit_price)
                      : "—"}
                  </td>
                  {canEdit && (
                    <td className="py-2 px-3">
                      <button onClick={() => onDeleteItem(it)} className="btn-ghost p-1 text-danger">
                        <Trash2 className="size-3.5" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showItemForm && (
        <VOItemFormModal
          voId={voId}
          contractId={contractId}
          editing={editItem}
          onClose={() => { setShowItemForm(false); setEditItem(null); }}
          onSaved={() => { setShowItemForm(false); setEditItem(null); mutate(); }}
        />
      )}
    </div>
  );
}

function VOItemFormModal({
  voId, contractId, editing, onClose, onSaved,
}: {
  voId: string; contractId: string; editing: VOItem | null;
  onClose: () => void; onSaved: () => void;
}) {
  const [form, setForm] = useState({
    action: editing?.action ?? "ADD",
    source_boq_item: editing?.source_boq_item ?? "",
    facility: editing?.facility ?? "",
    parent_boq_item: editing?.parent_boq_item ?? "",
    code: editing?.code ?? "",
    description: editing?.description ?? "",
    unit: editing?.unit ?? "",
    new_description: editing?.new_description ?? "",
    new_unit: editing?.new_unit ?? "",
    volume_delta: editing?.volume_delta ?? "0",
    unit_price: editing?.unit_price ?? "0",
    notes: editing?.notes ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  const needsFacility = form.action === "ADD" || form.action === "REMOVE_FACILITY";
  const needsSource = ["INCREASE", "DECREASE", "MODIFY_SPEC", "REMOVE"].includes(form.action);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = {
        vo: voId, action: form.action,
        source_boq_item: form.source_boq_item || null,
        facility: form.facility || null,
        parent_boq_item: form.parent_boq_item || null,
        code: form.code,
        description: form.description,
        unit: form.unit,
        new_description: form.new_description,
        new_unit: form.new_unit,
        volume_delta: form.volume_delta || "0",
        unit_price: form.unit_price || "0",
        notes: form.notes,
      };
      if (editing) {
        await api(`/vo-items/${editing.id}/`, { method: "PATCH", body });
      } else {
        await api(`/vo-items/`, { method: "POST", body });
      }
      toast.success("Item disimpan.");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message + (err.details ? "\n" + JSON.stringify(err.details) : ""));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-3">
        <h2 className="text-lg font-semibold">{editing ? "Edit" : "Tambah"} VO Item</h2>

        <div>
          <label className="label">Aksi <span className="text-danger">*</span></label>
          <select className="input" value={form.action}
                  onChange={(e) => setForm({ ...form, action: e.target.value })}>
            {ACTIONS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>

        {needsSource && (
          <div>
            <label className="label">Item BOQ Existing <span className="text-danger">*</span></label>
            <FilterableSelect
              value={form.source_boq_item}
              onChange={(id) => setForm({ ...form, source_boq_item: id || "" })}
              fetchUrl={`/boq-items/?boq_revision__contract=${contractId}&boq_revision__is_active=true&page_size=200`}
              getLabel={(it: any) => `${it.full_code} — ${it.description}`}
              getSubLabel={(it: any) => `${it.facility_code} · ${formatNumber(it.volume, 2)} ${it.unit}`}
              placeholder="Pilih item BOQ..."
              required
            />
          </div>
        )}

        {needsFacility && (
          <div>
            <label className="label">Fasilitas <span className="text-danger">*</span></label>
            <FilterableSelect
              value={form.facility}
              onChange={(id) => setForm({ ...form, facility: id || "" })}
              fetchUrl={`/facilities/?location__contract=${contractId}&page_size=200`}
              getLabel={(f: any) => `${f.code} — ${f.name}`}
              placeholder="Pilih fasilitas..."
              required
            />
          </div>
        )}

        {form.action === "ADD" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Kode</label>
                <input className="input font-mono" value={form.code}
                        onChange={(e) => setForm({ ...form, code: e.target.value })}
                        placeholder="VO-001" />
              </div>
              <div>
                <label className="label">Satuan</label>
                <input className="input" value={form.unit}
                        onChange={(e) => setForm({ ...form, unit: e.target.value })}
                        placeholder="m2, m3, ls" />
              </div>
            </div>
            <div>
              <label className="label">Uraian <span className="text-danger">*</span></label>
              <textarea className="input" rows={2} required value={form.description}
                        onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
          </>
        )}

        {form.action === "MODIFY_SPEC" && (
          <>
            <div>
              <label className="label">Deskripsi Baru</label>
              <textarea className="input" rows={2} value={form.new_description}
                        onChange={(e) => setForm({ ...form, new_description: e.target.value })} />
            </div>
            <div>
              <label className="label">Satuan Baru</label>
              <input className="input" value={form.new_unit}
                      onChange={(e) => setForm({ ...form, new_unit: e.target.value })} />
            </div>
          </>
        )}

        {(form.action === "INCREASE" || form.action === "DECREASE" || form.action === "ADD") && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">
                {form.action === "ADD" ? "Volume Awal" : "Volume Delta"}
                {form.action === "INCREASE" && <span className="text-success ml-1">(+)</span>}
                {form.action === "DECREASE" && <span className="text-danger ml-1">(-)</span>}
              </label>
              <input className="input font-mono" type="number" step="0.0001"
                      value={form.volume_delta}
                      onChange={(e) => setForm({ ...form, volume_delta: e.target.value })} />
            </div>
            {(form.action === "ADD" || form.action === "MODIFY_SPEC") && (
              <div>
                <label className="label">Harga Satuan (PRE-PPN)</label>
                <input className="input font-mono" type="number" step="0.01" min="0"
                        value={form.unit_price}
                        onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
              </div>
            )}
          </div>
        )}

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
