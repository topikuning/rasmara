"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { AddendumStatusBadge } from "@/components/contract/VOStatusBadge";
import { formatRupiahFull } from "@/lib/format/rupiah";
import { formatTanggalSingkat } from "@/lib/format/tanggal";

type Addendum = {
  id: string;
  contract: string;
  number: string;
  addendum_type: string;
  addendum_type_display: string;
  status: string;
  status_display: string;
  value_delta: string;
  days_delta: number;
  signed_at: string | null;
  vo_count: number;
  created_at: string;
};

type Paginated<T> = { count: number; results: T[] };

const TYPES = [
  { value: "CCO", label: "Contract Change Order (Lingkup)" },
  { value: "EXTENSION", label: "Perpanjangan Durasi" },
  { value: "VALUE_CHANGE", label: "Perubahan Nilai" },
  { value: "COMBINED", label: "Gabungan" },
];

export default function AddendumListPage({
  params,
}: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const { hasPerm } = useAuthStore();
  const [showCreate, setShowCreate] = useState(false);

  const { data, mutate } = useSWR<Paginated<Addendum>>(
    `/addenda/?contract=${contractId}&page_size=200`, swrFetcher,
  );

  async function onDelete(ad: Addendum) {
    if (!confirm(`Hapus addendum DRAFT "${ad.number}"?`)) return;
    try {
      await api(`/addenda/${ad.id}/`, { method: "DELETE" });
      toast.success("Addendum dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">Addendum</h2>
          <p className="text-sm text-muted-fg">
            Dokumen legal perubahan kontrak. Saat di-sign akan auto-spawn revisi BOQ baru.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => mutate()} className="btn-ghost"><RefreshCw className="size-4" /></button>
          {hasPerm("addendum.create") && (
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus className="size-4 mr-1" /> Buat Addendum
            </button>
          )}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b text-xs uppercase text-muted-fg bg-muted/30">
              <th className="py-2 px-3">No.</th>
              <th className="py-2 px-3">Tipe</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3 text-right">Nilai Delta</th>
              <th className="py-2 px-3 text-center">Durasi (hari)</th>
              <th className="py-2 px-3 text-center">VO</th>
              <th className="py-2 px-3">Tanggal TTD</th>
              {hasPerm("addendum.delete") && <th className="py-2 px-3 w-16">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).length === 0 && (
              <tr><td colSpan={8} className="py-6 text-center text-muted-fg">Belum ada addendum.</td></tr>
            )}
            {data?.results?.map((a) => {
              const delta = parseFloat(a.value_delta);
              return (
                <tr key={a.id} className="border-b hover:bg-muted/20">
                  <td className="py-1.5 px-3 font-mono text-xs">
                    <Link href={`/kontrak/${contractId}/addendum/${a.id}`} className="hover:text-primary">
                      {a.number}
                    </Link>
                  </td>
                  <td className="py-1.5 px-3">{a.addendum_type_display}</td>
                  <td className="py-1.5 px-3"><AddendumStatusBadge status={a.status} /></td>
                  <td className={`py-1.5 px-3 text-right font-mono ${delta > 0 ? "text-success"
                                                                                    : delta < 0 ? "text-danger" : ""}`}>
                    {delta !== 0 ? formatRupiahFull(a.value_delta) : "—"}
                  </td>
                  <td className="py-1.5 px-3 text-center">{a.days_delta || "—"}</td>
                  <td className="py-1.5 px-3 text-center">{a.vo_count}</td>
                  <td className="py-1.5 px-3 text-xs text-muted-fg">
                    {a.signed_at ? formatTanggalSingkat(a.signed_at) : "—"}
                  </td>
                  {hasPerm("addendum.delete") && (
                    <td className="py-1.5 px-3">
                      {a.status === "DRAFT" && (
                        <button onClick={() => onDelete(a)} className="btn-ghost p-1 text-danger">
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateAddendumModal
          contractId={contractId}
          onClose={() => setShowCreate(false)}
          onCreated={(a) => {
            setShowCreate(false); mutate();
            window.location.href = `/kontrak/${contractId}/addendum/${a.id}`;
          }}
        />
      )}
    </div>
  );
}

function CreateAddendumModal({
  contractId, onClose, onCreated,
}: { contractId: string; onClose: () => void; onCreated: (a: Addendum) => void }) {
  const [form, setForm] = useState({
    number: "", addendum_type: "CCO", reason: "",
    value_delta: "0", days_delta: 0, new_end_date: "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: any = {
        contract: contractId,
        number: form.number,
        addendum_type: form.addendum_type,
        reason: form.reason,
        value_delta: form.value_delta || "0",
        days_delta: form.days_delta || 0,
        new_end_date: form.new_end_date || null,
      };
      const res = await api<Addendum>("/addenda/", { method: "POST", body });
      toast.success("Addendum dibuat (DRAFT).");
      onCreated(res);
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
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Buat Addendum Baru</h2>
        <div>
          <label className="label">Nomor Addendum <span className="text-danger">*</span></label>
          <input className="input font-mono" required value={form.number}
                  onChange={(e) => setForm({ ...form, number: e.target.value })}
                  placeholder="001/ADD/IV/2026" />
        </div>
        <div>
          <label className="label">Tipe <span className="text-danger">*</span></label>
          <select className="input" value={form.addendum_type}
                  onChange={(e) => setForm({ ...form, addendum_type: e.target.value })}>
            {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Alasan / Deskripsi Singkat</label>
          <textarea className="input" rows={3} value={form.reason}
                    onChange={(e) => setForm({ ...form, reason: e.target.value })} />
        </div>
        {(form.addendum_type === "VALUE_CHANGE" || form.addendum_type === "COMBINED" || form.addendum_type === "CCO") && (
          <div>
            <label className="label">Selisih Nilai (POST-PPN, signed)</label>
            <input className="input font-mono" type="number" step="0.01" value={form.value_delta}
                    onChange={(e) => setForm({ ...form, value_delta: e.target.value })}
                    placeholder="100000000.00 atau -50000000.00" />
            <p className="text-xs text-muted-fg mt-1">Positif = naik, negatif = turun.</p>
          </div>
        )}
        {(form.addendum_type === "EXTENSION" || form.addendum_type === "COMBINED") && (
          <>
            <div>
              <label className="label">Tambahan Durasi (hari)</label>
              <input className="input" type="number" value={form.days_delta}
                      onChange={(e) => setForm({ ...form, days_delta: parseInt(e.target.value || "0") })} />
            </div>
            <div>
              <label className="label">ATAU Tanggal Selesai Baru</label>
              <input className="input" type="date" value={form.new_end_date}
                      onChange={(e) => setForm({ ...form, new_end_date: e.target.value })} />
            </div>
          </>
        )}
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
