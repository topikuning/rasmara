"use client";

import { use, useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { ArrowLeft, FileSpreadsheet } from "lucide-react";

import { toast } from "sonner";

import { swrFetcher } from "@/lib/api/client";
import { downloadFile } from "@/lib/api/download";
import { formatRupiahFull, formatNumber } from "@/lib/format/rupiah";

type Revision = { id: string; version: number; status_display: string; is_active: boolean };

type Line = {
  full_code: string;
  description: string;
  facility_code: string;
  unit: string;
  unit_price_a: string;
  unit_price_b: string;
  volume_a: string;
  volume_b: string;
  total_a: string;
  total_b: string;
  diff_volume: string;
  diff_total: string;
  note: string;
};

type CompareData = {
  revision_a: { id: string; version: number; status: string };
  revision_b: { id: string; version: number; status: string };
  lines: Line[];
  total_a: string;
  total_b: string;
  total_tambah: string;
  total_kurang: string;
};

const NOTE_STYLE: Record<string, string> = {
  BARU: "bg-success/10 text-success",
  DIHAPUS: "bg-danger/10 text-danger",
  BERTAMBAH: "bg-warning/10 text-warning",
  BERKURANG: "bg-warning/10 text-warning",
  SAMA: "text-muted-fg",
};

export default function KomparasiBoqPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);

  const { data: revs } = useSWR<{ results: Revision[] }>(
    `/boq-revisions/?contract=${contractId}&page_size=50&ordering=version`, swrFetcher,
  );
  const revisions = revs?.results ?? [];

  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");

  // Auto-set default: from=V0 (jika ada), to=aktif
  if (!from && revisions.length > 0) {
    const v0 = revisions.find((r) => r.version === 0);
    if (v0) setFrom(v0.id);
  }
  if (!to && revisions.length > 1) {
    const active = revisions.find((r) => r.is_active) || revisions[revisions.length - 1];
    setTo(active.id);
  }

  const { data, isLoading } = useSWR<CompareData>(
    from && to && from !== to
      ? `/contracts/${contractId}/boq-compare/?from=${from}&to=${to}`
      : null,
    swrFetcher,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href={`/kontrak/${contractId}/boq`} className="btn-ghost p-1.5">
          <ArrowLeft className="size-4" />
        </Link>
        <div>
          <h2 className="text-xl font-semibold">Komparasi BOQ Antar Revisi</h2>
          <p className="text-sm text-muted-fg">Bandingkan dua revisi untuk lihat tambah/kurang.</p>
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="min-w-[180px]">
            <label className="label">Revisi A (referensi)</label>
            <select className="input" value={from} onChange={(e) => setFrom(e.target.value)}>
              <option value="">— pilih —</option>
              {revisions.map((r) => (
                <option key={r.id} value={r.id}>
                  V{r.version} — {r.status_display}{r.is_active ? " (aktif)" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="text-muted-fg text-2xl pb-2">vs</div>
          <div className="min-w-[180px]">
            <label className="label">Revisi B (target)</label>
            <select className="input" value={to} onChange={(e) => setTo(e.target.value)}>
              <option value="">— pilih —</option>
              {revisions.map((r) => (
                <option key={r.id} value={r.id}>
                  V{r.version} — {r.status_display}{r.is_active ? " (aktif)" : ""}
                </option>
              ))}
            </select>
          </div>
          {from && to && from !== to && (
            <button
              onClick={() => downloadFile(
                `/contracts/${contractId}/boq-compare/export-xlsx/?from=${from}&to=${to}`,
                "Komparasi-BOQ.xlsx",
              ).catch((e) => toast.error(e.message))}
              className="btn-secondary"
            >
              <FileSpreadsheet className="size-4 mr-1" /> Unduh Excel
            </button>
          )}
        </div>
      </div>

      {!from || !to ? (
        <div className="card p-8 text-center text-muted-fg">Pilih dua revisi untuk membandingkan.</div>
      ) : from === to ? (
        <div className="card p-8 text-center text-warning">Pilih revisi yang berbeda.</div>
      ) : isLoading ? (
        <div className="card p-8 text-center text-muted-fg">Memuat...</div>
      ) : !data ? null : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card label={`Total V${data.revision_a.version}`} value={formatRupiahFull(data.total_a)} />
            <Card label={`Total V${data.revision_b.version}`} value={formatRupiahFull(data.total_b)} />
            <Card label="Total Tambah" value={formatRupiahFull(data.total_tambah)} ok />
            <Card label="Total Kurang" value={formatRupiahFull(data.total_kurang)} danger />
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b text-xs uppercase text-muted-fg bg-muted/30">
                  <th className="py-2 px-3">Kode</th>
                  <th className="py-2 px-3">Uraian</th>
                  <th className="py-2 px-3">Sat.</th>
                  <th className="py-2 px-3 text-right">Harga Satuan</th>
                  <th className="py-2 px-3 text-right">Vol A</th>
                  <th className="py-2 px-3 text-right">Jumlah A</th>
                  <th className="py-2 px-3 text-right">Vol B</th>
                  <th className="py-2 px-3 text-right">Jumlah B</th>
                  <th className="py-2 px-3 text-right">Selisih Vol</th>
                  <th className="py-2 px-3 text-right">Selisih Jumlah</th>
                  <th className="py-2 px-3">Ket.</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((ln, i) => {
                  const diff = parseFloat(ln.diff_total);
                  return (
                    <tr key={i} className="border-b hover:bg-muted/20">
                      <td className="py-1.5 px-3 font-mono text-xs">{ln.full_code}</td>
                      <td className="py-1.5 px-3">
                        {ln.description}
                        <div className="text-xs text-muted-fg">{ln.facility_code}</div>
                      </td>
                      <td className="py-1.5 px-3 text-xs">{ln.unit}</td>
                      <td className="py-1.5 px-3 text-right font-mono">
                        {formatRupiahFull(ln.unit_price_b || ln.unit_price_a)}
                      </td>
                      <td className="py-1.5 px-3 text-right font-mono">{formatNumber(ln.volume_a, 4)}</td>
                      <td className="py-1.5 px-3 text-right font-mono">{formatRupiahFull(ln.total_a)}</td>
                      <td className="py-1.5 px-3 text-right font-mono">{formatNumber(ln.volume_b, 4)}</td>
                      <td className="py-1.5 px-3 text-right font-mono">{formatRupiahFull(ln.total_b)}</td>
                      <td className="py-1.5 px-3 text-right font-mono">
                        {parseFloat(ln.diff_volume) !== 0 ? formatNumber(ln.diff_volume, 4) : "—"}
                      </td>
                      <td className={`py-1.5 px-3 text-right font-mono ${diff > 0 ? "text-success"
                                                                                       : diff < 0 ? "text-danger" : ""}`}>
                        {diff !== 0 ? formatRupiahFull(ln.diff_total) : "—"}
                      </td>
                      <td className="py-1.5 px-3">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${NOTE_STYLE[ln.note] || ""}`}>
                          {ln.note}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Card({ label, value, ok, danger }: { label: string; value: string; ok?: boolean; danger?: boolean }) {
  return (
    <div className={`card p-4 ${ok ? "border-success/30 bg-success/5" : danger ? "border-danger/30 bg-danger/5" : ""}`}>
      <div className="text-xs text-muted-fg">{label}</div>
      <div className="font-semibold font-mono mt-1">{value}</div>
    </div>
  );
}
