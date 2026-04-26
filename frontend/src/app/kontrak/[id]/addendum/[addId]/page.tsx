"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  ArrowLeft, AlertTriangle, ShieldCheck, FileSignature,
  Eye, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { AddendumStatusBadge, VOStatusBadge } from "@/components/contract/VOStatusBadge";
import { formatRupiahFull } from "@/lib/format/rupiah";
import { formatTanggalID, formatTanggalSingkat } from "@/lib/format/tanggal";
import FilterableSelect from "@/components/form/FilterableSelect";

type VO = {
  id: string;
  number: string;
  title: string;
  status: string;
  status_display: string;
};

type AddendumDetail = {
  id: string;
  contract: string;
  number: string;
  addendum_type: string;
  addendum_type_display: string;
  reason: string;
  status: string;
  status_display: string;
  value_delta: string;
  days_delta: number;
  new_end_date: string | null;
  signed_at: string | null;
  signed_by_username: string | null;
  document: string | null;
  kpa_approval: any;
  needs_kpa: boolean;
  has_kpa: boolean;
  vos: VO[];
  notes: string;
};

type Preview = {
  vo_count: number;
  vo_item_count: number;
  value_delta: string;
  days_delta: number;
  current_value_before: string;
  current_value_after: string;
  end_date_before: string;
  end_date_after: string;
  needs_kpa: boolean;
  has_kpa: boolean;
  kpa_threshold_amount: string;
  vo_status_invalid: string[];
};

export default function AddendumDetailPage({
  params,
}: { params: Promise<{ id: string; addId: string }> }) {
  const { id: contractId, addId } = use(params);
  const { hasPerm } = useAuthStore();

  const { data, mutate } = useSWR<AddendumDetail>(`/addenda/${addId}/`, swrFetcher);
  const { data: preview } = useSWR<Preview>(`/addenda/${addId}/preview/`, swrFetcher);

  const [showBundle, setShowBundle] = useState(false);
  const [showKPA, setShowKPA] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!data) return <div className="text-sm text-muted-fg">Memuat...</div>;

  const isDraft = data.status === "DRAFT";
  const canEdit = hasPerm("addendum.update") && isDraft;

  async function onUnbundle(voId: string) {
    if (!confirm("Lepas VO ini dari addendum?")) return;
    try {
      await api(`/addenda/${addId}/unbundle-vo/`, {
        method: "POST", body: { vo_ids: [voId] },
      });
      toast.success("VO dilepas.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  async function onSign() {
    if (!confirm(
      `TANDA TANGAN addendum ${data?.number}?\n\n` +
      `Aksi ini akan:\n` +
      `1. Set VO bundled jadi BUNDLED\n` +
      `2. Spawn revisi BOQ baru (kalau ada VO BOQ)\n` +
      `3. Update nilai & durasi kontrak\n\n` +
      `Tidak bisa di-undo.`
    )) return;
    setBusy(true);
    try {
      await api(`/addenda/${addId}/sign/`, { method: "POST", body: {} });
      toast.success("Addendum SIGNED. Revisi BOQ baru dibuat.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href={`/kontrak/${contractId}/addendum`} className="btn-ghost p-1.5">
          <ArrowLeft className="size-4" />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted-fg font-mono">{data.number}</div>
          <h2 className="text-xl font-semibold">{data.addendum_type_display}</h2>
        </div>
        <AddendumStatusBadge status={data.status} />
      </div>

      {data.reason && (
        <div className="card p-4">
          <div className="text-xs uppercase text-muted-fg mb-1">Alasan</div>
          <p className="text-sm whitespace-pre-wrap">{data.reason}</p>
        </div>
      )}

      {/* Preview impact */}
      {preview && (
        <div className="card p-5">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Eye className="size-4" /> Preview Dampak
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <Stat label="VO di-bundle" value={`${preview.vo_count} VO · ${preview.vo_item_count} item perubahan`} />
            <Stat label="Nilai Delta"
                  value={formatRupiahFull(preview.value_delta)}
                  emphasize={parseFloat(preview.value_delta) !== 0} />
            <Stat label="Nilai sebelum → sesudah"
                  value={`${formatRupiahFull(preview.current_value_before)} → ${formatRupiahFull(preview.current_value_after)}`} />
            <Stat label="Durasi delta" value={preview.days_delta ? `${preview.days_delta} hari` : "—"} />
            <Stat label="Tanggal selesai"
                  value={`${formatTanggalSingkat(preview.end_date_before)} → ${formatTanggalSingkat(preview.end_date_after)}`} />
          </div>
          {preview.needs_kpa && (
            <div className={`mt-3 rounded-lg border p-3 text-sm ${preview.has_kpa
              ? "border-success/40 bg-success/10" : "border-danger/40 bg-danger/10"}`}>
              {preview.has_kpa ? (
                <>
                  <CheckCircle2 className="size-4 inline text-success mr-1" />
                  <strong>KPA approval sudah ada.</strong> Addendum siap di-sign.
                </>
              ) : (
                <>
                  <AlertTriangle className="size-4 inline text-danger mr-1" />
                  <strong>KPA approval WAJIB.</strong> |Δ| {formatRupiahFull(preview.value_delta)} melebihi
                  10% nilai original (threshold: {formatRupiahFull(preview.kpa_threshold_amount)}).
                  Upload approval KPA dulu sebelum sign.
                </>
              )}
            </div>
          )}
          {preview.vo_status_invalid.length > 0 && (
            <div className="mt-3 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm">
              <AlertTriangle className="size-4 inline text-danger mr-1" />
              VO berikut belum APPROVED: {preview.vo_status_invalid.join(", ")}
            </div>
          )}
        </div>
      )}

      {/* VO bundled */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">VO yang Di-bundle ({data.vos.length})</h3>
          {canEdit && (
            <button onClick={() => setShowBundle(true)} className="btn-secondary">
              Tambah VO
            </button>
          )}
        </div>
        {data.vos.length === 0 ? (
          <div className="p-6 text-center text-muted-fg text-sm">
            Belum ada VO di-bundle. Tambah VO APPROVED untuk addendum BOQ-affecting.
          </div>
        ) : (
          <ul>
            {data.vos.map((v) => (
              <li key={v.id} className="flex items-center gap-3 px-4 py-2 border-b">
                <Link href={`/kontrak/${contractId}/vo/${v.id}`}
                      className="font-mono text-xs hover:text-primary">
                  {v.number}
                </Link>
                <span className="flex-1 text-sm">{v.title}</span>
                <VOStatusBadge status={v.status} />
                {canEdit && (
                  <button onClick={() => onUnbundle(v.id)} className="text-xs text-danger hover:underline">
                    Lepas
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* KPA approval */}
      {data.needs_kpa && (
        <div className={`card p-5 ${data.has_kpa ? "border-success/40" : "border-warning/40"}`}>
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <ShieldCheck className="size-4" /> KPA Approval
          </h3>
          {data.has_kpa ? (
            <div className="text-sm">
              <CheckCircle2 className="size-4 inline text-success mr-1" />
              Disetujui oleh: <strong>{data.kpa_approval?.signed_by_name}</strong>
              {data.kpa_approval?.signed_by_nip && ` (NIP ${data.kpa_approval.signed_by_nip})`}
              {" pada "}
              {formatTanggalID(data.kpa_approval?.signed_at)}.
              {canEdit && (
                <button onClick={() => setShowKPA(true)} className="ml-2 text-xs text-primary hover:underline">
                  Edit
                </button>
              )}
            </div>
          ) : (
            <>
              <p className="text-sm text-muted-fg mb-3">
                |Δ| nilai melebihi 10% nilai original. Wajib upload approval KPA sebelum sign.
              </p>
              {canEdit && (
                <button onClick={() => setShowKPA(true)} className="btn-secondary">
                  Upload KPA Approval
                </button>
              )}
            </>
          )}
        </div>
      )}

      {/* Sign action */}
      {canEdit && hasPerm("addendum.sign") && (
        <div className="card p-5">
          <button onClick={onSign}
                  disabled={busy || (data.needs_kpa && !data.has_kpa)
                            || preview?.vo_status_invalid?.length! > 0}
                  className="btn-danger w-full">
            <FileSignature className="size-4 mr-1" />
            {busy ? "Memproses..." : "TANDA TANGAN ADDENDUM (LEGAL ACTION)"}
          </button>
          <p className="text-xs text-muted-fg mt-2 text-center">
            Aksi tidak bisa di-undo. Akan auto-spawn revisi BOQ baru.
          </p>
        </div>
      )}

      {data.signed_at && (
        <div className="card p-4 text-sm">
          <CheckCircle2 className="size-4 inline text-success mr-1" />
          <strong>Addendum SIGNED</strong> oleh {data.signed_by_username} pada {formatTanggalID(data.signed_at)}.
        </div>
      )}

      {showBundle && (
        <BundleVOModal
          contractId={contractId}
          addId={addId}
          onClose={() => setShowBundle(false)}
          onSaved={() => { setShowBundle(false); mutate(); }}
        />
      )}
      {showKPA && (
        <KPAModal
          addId={addId}
          existing={data.kpa_approval}
          onClose={() => setShowKPA(false)}
          onSaved={() => { setShowKPA(false); mutate(); }}
        />
      )}
    </div>
  );
}

function Stat({ label, value, emphasize }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div>
      <div className="text-xs text-muted-fg">{label}</div>
      <div className={`font-medium ${emphasize ? "text-primary" : ""}`}>{value}</div>
    </div>
  );
}

function BundleVOModal({
  contractId, addId, onClose, onSaved,
}: { contractId: string; addId: string; onClose: () => void; onSaved: () => void }) {
  const [voId, setVoId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api(`/addenda/${addId}/bundle-vo/`, {
        method: "POST",
        body: { vo_ids: [voId] },
      });
      toast.success("VO ditambahkan.");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Tambah VO ke Addendum</h2>
        <div>
          <label className="label">VO (status APPROVED) <span className="text-danger">*</span></label>
          <FilterableSelect
            value={voId}
            onChange={(id) => setVoId(id || "")}
            fetchUrl={`/vos/?contract=${contractId}&status=APPROVED&page_size=200`}
            getLabel={(v: any) => `${v.number} — ${v.title}`}
            placeholder="Pilih VO..."
            required
          />
          <p className="text-xs text-muted-fg mt-1">
            Hanya VO APPROVED yang bisa di-bundle. 1 VO max 1 addendum.
          </p>
        </div>
        <div className="flex gap-2 pt-2 border-t">
          <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={submitting}>Batal</button>
          <button type="submit" className="btn-primary flex-1" disabled={submitting || !voId}>
            {submitting ? "Menyimpan..." : "Tambah"}
          </button>
        </div>
      </form>
    </div>
  );
}

function KPAModal({
  addId, existing, onClose, onSaved,
}: { addId: string; existing: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    signed_by_name: existing?.signed_by_name ?? "",
    signed_by_nip: existing?.signed_by_nip ?? "",
    signed_at: existing?.signed_at ?? new Date().toISOString().slice(0, 10),
    document_url: existing?.document_url ?? "",
    notes: existing?.notes ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api(`/addenda/${addId}/upload-kpa-approval/`, {
        method: "POST",
        body: form,
      });
      toast.success("KPA approval disimpan.");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">KPA Approval</h2>
        <div>
          <label className="label">Nama KPA <span className="text-danger">*</span></label>
          <input className="input" required value={form.signed_by_name}
                  onChange={(e) => setForm({ ...form, signed_by_name: e.target.value })} />
        </div>
        <div>
          <label className="label">NIP KPA</label>
          <input className="input font-mono" value={form.signed_by_nip}
                  onChange={(e) => setForm({ ...form, signed_by_nip: e.target.value })} />
        </div>
        <div>
          <label className="label">Tanggal TTD <span className="text-danger">*</span></label>
          <input className="input" type="date" required value={form.signed_at}
                  onChange={(e) => setForm({ ...form, signed_at: e.target.value })} />
        </div>
        <div>
          <label className="label">URL Dokumen Approval</label>
          <input className="input" type="url" value={form.document_url}
                  onChange={(e) => setForm({ ...form, document_url: e.target.value })}
                  placeholder="https://..." />
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
