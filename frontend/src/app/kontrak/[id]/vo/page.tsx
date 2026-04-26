"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { VOStatusBadge } from "@/components/contract/VOStatusBadge";
import { formatTanggalSingkat } from "@/lib/format/tanggal";

type VO = {
  id: string;
  contract: string;
  number: string;
  title: string;
  status: string;
  status_display: string;
  item_count: number;
  created_at: string;
};

type Paginated<T> = { count: number; results: T[] };

export default function VOListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const { hasPerm } = useAuthStore();
  const [showCreate, setShowCreate] = useState(false);

  const { data, mutate } = useSWR<Paginated<VO>>(
    `/vos/?contract=${contractId}&page_size=200`, swrFetcher,
  );

  async function onDelete(vo: VO) {
    if (!confirm(`Hapus VO "${vo.number} - ${vo.title}"?`)) return;
    try {
      await api(`/vos/${vo.id}/`, { method: "DELETE" });
      toast.success("VO dihapus.");
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold">Variation Order (VO)</h2>
          <p className="text-sm text-muted-fg">Usulan perubahan teknis pra-Addendum.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => mutate()} className="btn-ghost"><RefreshCw className="size-4" /></button>
          {hasPerm("vo.create") && (
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus className="size-4 mr-1" /> Buat VO
            </button>
          )}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b text-xs uppercase text-muted-fg bg-muted/30">
              <th className="py-2 px-3">No.</th>
              <th className="py-2 px-3">Judul</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3 text-center">Items</th>
              <th className="py-2 px-3">Dibuat</th>
              {hasPerm("vo.delete") && <th className="py-2 px-3 w-20">Aksi</th>}
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).length === 0 && (
              <tr><td colSpan={6} className="py-6 text-center text-muted-fg">Belum ada VO.</td></tr>
            )}
            {data?.results?.map((v) => (
              <tr key={v.id} className="border-b hover:bg-muted/20">
                <td className="py-1.5 px-3 font-mono text-xs">
                  <Link href={`/kontrak/${contractId}/vo/${v.id}`} className="hover:text-primary">
                    {v.number}
                  </Link>
                </td>
                <td className="py-1.5 px-3">
                  <Link href={`/kontrak/${contractId}/vo/${v.id}`} className="hover:text-primary">
                    {v.title}
                  </Link>
                </td>
                <td className="py-1.5 px-3"><VOStatusBadge status={v.status} /></td>
                <td className="py-1.5 px-3 text-center">{v.item_count}</td>
                <td className="py-1.5 px-3 text-xs text-muted-fg">
                  {formatTanggalSingkat(v.created_at)}
                </td>
                {hasPerm("vo.delete") && (
                  <td className="py-1.5 px-3">
                    {v.status === "DRAFT" && (
                      <button onClick={() => onDelete(v)} className="btn-ghost p-1 text-danger" title="Hapus">
                        <Trash2 className="size-3.5" />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateVOModal
          contractId={contractId}
          onClose={() => setShowCreate(false)}
          onCreated={(vo) => {
            setShowCreate(false); mutate();
            window.location.href = `/kontrak/${contractId}/vo/${vo.id}`;
          }}
        />
      )}
    </div>
  );
}

function CreateVOModal({
  contractId, onClose, onCreated,
}: { contractId: string; onClose: () => void; onCreated: (v: VO) => void }) {
  const [form, setForm] = useState({ number: "", title: "", justification: "" });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api<VO>("/vos/", {
        method: "POST",
        body: { ...form, contract: contractId },
      });
      toast.success("VO dibuat. Tambahkan item perubahan.");
      onCreated(res);
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
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Buat VO Baru</h2>
        <div>
          <label className="label">Nomor VO <span className="text-danger">*</span></label>
          <input className="input font-mono" required value={form.number}
                  onChange={(e) => setForm({ ...form, number: e.target.value })}
                  placeholder="VO-001/2026" />
        </div>
        <div>
          <label className="label">Judul <span className="text-danger">*</span></label>
          <input className="input" required value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="label">Justifikasi Teknis</label>
          <textarea className="input" rows={4} value={form.justification}
                    onChange={(e) => setForm({ ...form, justification: e.target.value })} />
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
