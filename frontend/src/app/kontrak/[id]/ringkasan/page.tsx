"use client";

import { use, useState } from "react";
import useSWR from "swr";
import { CheckCircle2, XCircle, Play, Square, PauseCircle, AlertTriangle, Trophy } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { PpnBreakdown } from "@/components/contract/PpnBreakdown";
import { ContractStatusBadge } from "@/components/contract/StatusBadge";
import { formatRupiahFull } from "@/lib/format/rupiah";
import { formatTanggalID } from "@/lib/format/tanggal";

type Detail = {
  id: string;
  number: string;
  name: string;
  status: string;
  status_display: string;
  ppk_name: string;
  ppk_nip: string;
  contractor_name: string;
  contractor_code: string;
  fiscal_year: number;
  original_value: string;
  current_value: string;
  ppn_pct: string;
  boq_pre_ppn_value: string;
  ppn_amount: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  unlock_until: string | null;
  unlock_reason: string;
  is_godmode_active: boolean;
  notes: string;
};

type Gate = { code: string; label: string; ok: boolean; detail: string };
type GateResult = { ok: boolean; checks: Gate[] };

export default function RingkasanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { hasPerm, me } = useAuthStore();
  const { data, mutate } = useSWR<Detail>(`/contracts/${id}/`, swrFetcher);
  const { data: gates, mutate: mutateGates } = useSWR<GateResult>(
    `/contracts/${id}/evaluate-gates/`, swrFetcher,
  );

  const [busy, setBusy] = useState(false);

  async function callAction(path: string, label: string, body: any = {}) {
    if (!confirm(`Yakin ingin ${label.toLowerCase()}?`)) return;
    setBusy(true);
    try {
      await api(`/contracts/${id}/${path}/`, { method: "POST", body });
      toast.success(`${label} berhasil.`);
      mutate(); mutateGates();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <div className="text-sm text-muted-fg">Memuat...</div>;

  const isDraft = data.status === "DRAFT";
  const isActive = data.status === "ACTIVE";
  const isOnHold = data.status === "ON_HOLD";
  const isTerminal = data.status === "COMPLETED" || data.status === "TERMINATED";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Kolom kiri 2/3: header info + nilai + actions */}
      <div className="lg:col-span-2 space-y-4">
        {/* Header info */}
        <div className="card p-5">
          <h2 className="font-semibold mb-4">Informasi Kontrak</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Field label="Nomor Kontrak" value={data.number} />
            <Field label="Tahun Anggaran" value={String(data.fiscal_year)} />
            <Field label="PPK" value={`${data.ppk_name} (NIP ${data.ppk_nip})`} />
            <Field label="Kontraktor" value={`${data.contractor_code} - ${data.contractor_name}`} />
            <Field label="Tanggal Mulai" value={formatTanggalID(data.start_date)} />
            <Field label="Tanggal Selesai" value={formatTanggalID(data.end_date)} />
            <Field label="Durasi" value={`${data.duration_days} hari`} />
            <Field label="PPN" value={`${parseFloat(data.ppn_pct)}%`} />
          </div>
          {data.notes && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">Catatan</div>
              <p className="text-sm whitespace-pre-wrap">{data.notes}</p>
            </div>
          )}
        </div>

        {/* Breakdown nilai */}
        <div className="card p-5 space-y-3">
          <h2 className="font-semibold">Nilai Kontrak</h2>
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="text-xs uppercase tracking-wide text-muted-fg mb-1.5">Nilai Saat Ini</div>
            <PpnBreakdown
              boqValue={data.boq_pre_ppn_value}
              ppnPct={data.ppn_pct}
              contractValue={data.current_value}
            />
          </div>
          {data.original_value !== data.current_value && (
            <div className="rounded-lg border bg-muted/30 p-3">
              <div className="text-xs uppercase tracking-wide text-muted-fg mb-1.5">
                Nilai Awal Kontrak (sebelum addendum)
              </div>
              <div className="font-mono text-sm">{formatRupiahFull(data.original_value)}</div>
            </div>
          )}
          {parseFloat(data.boq_pre_ppn_value) === 0 && (
            <p className="text-xs text-warning flex items-center gap-1">
              <AlertTriangle className="size-3" /> BOQ belum diisi. Buka tab BOQ untuk mengisi.
            </p>
          )}
        </div>

        {/* Actions */}
        {hasPerm("contract.update") && !isTerminal && (
          <div className="card p-5">
            <h2 className="font-semibold mb-3">Aksi Kontrak</h2>
            <div className="flex flex-wrap gap-2">
              {isDraft && hasPerm("contract.activate") && (
                <button
                  onClick={() => callAction("activate", "Aktivasi kontrak")}
                  disabled={busy || !gates?.ok}
                  className="btn-primary"
                  title={gates?.ok ? "" : "Lengkapi gate aktivasi dulu"}
                >
                  <Play className="size-4 mr-1" /> Aktivasi
                </button>
              )}
              {isDraft && me?.is_superuser && (
                <button
                  onClick={() => callAction("activate", "Aktivasi paksa (bypass gate)", { bypass_gate: true })}
                  disabled={busy}
                  className="btn-secondary"
                  title="Bypass gate aktivasi (hanya superadmin)"
                >
                  <Play className="size-4 mr-1" /> Aktivasi Paksa
                </button>
              )}
              {isActive && hasPerm("contract.hold") && (
                <button
                  onClick={() => callAction("hold", "Pause kontrak")}
                  disabled={busy}
                  className="btn-secondary"
                >
                  <PauseCircle className="size-4 mr-1" /> Pause
                </button>
              )}
              {isOnHold && hasPerm("contract.hold") && (
                <button
                  onClick={() => callAction("unhold", "Lanjutkan kontrak")}
                  disabled={busy}
                  className="btn-primary"
                >
                  <Play className="size-4 mr-1" /> Lanjutkan
                </button>
              )}
              {isActive && hasPerm("contract.complete") && (
                <button
                  onClick={() => callAction("complete", "Selesaikan kontrak (BAST final)")}
                  disabled={busy}
                  className="btn-primary"
                >
                  <Trophy className="size-4 mr-1" /> Selesaikan
                </button>
              )}
              {(isDraft || isActive || isOnHold) && hasPerm("contract.terminate") && (
                <button
                  onClick={() => callAction("terminate", "HENTIKAN kontrak (TERMINAL)")}
                  disabled={busy}
                  className="btn-danger"
                >
                  <Square className="size-4 mr-1" /> Hentikan
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Kolom kanan 1/3: Gate aktivasi */}
      <div className="space-y-4">
        <div className="card p-5">
          <h2 className="font-semibold mb-3">Gate Aktivasi</h2>
          {gates?.ok ? (
            <div className="text-sm text-success flex items-center gap-2 mb-3">
              <CheckCircle2 className="size-4" /> Semua syarat terpenuhi.
            </div>
          ) : (
            <div className="text-sm text-warning flex items-center gap-2 mb-3">
              <AlertTriangle className="size-4" /> Beberapa syarat belum terpenuhi.
            </div>
          )}
          <ul className="space-y-2.5 text-sm">
            {gates?.checks.map((g) => (
              <li key={g.code} className="flex items-start gap-2">
                {g.ok
                  ? <CheckCircle2 className="size-4 text-success mt-0.5 shrink-0" />
                  : <XCircle className="size-4 text-danger mt-0.5 shrink-0" />}
                <div className="min-w-0">
                  <div className="font-medium">{g.label}</div>
                  {g.detail && <div className="text-xs text-muted-fg">{g.detail}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-fg mb-0.5">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}
