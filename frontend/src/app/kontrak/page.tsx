"use client";

import Link from "next/link";
import useSWR from "swr";
import { useState } from "react";
import { Plus, RefreshCw, Search } from "lucide-react";

import { swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { ContractStatusBadge } from "@/components/contract/StatusBadge";
import { formatRupiahFull } from "@/lib/format/rupiah";
import { formatTanggalSingkat } from "@/lib/format/tanggal";

type Contract = {
  id: string;
  number: string;
  name: string;
  status: string;
  ppk_name: string;
  contractor_name: string;
  fiscal_year: number;
  original_value: string;
  current_value: string;
  start_date: string;
  end_date: string;
  location_count: number;
};

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

const STATUS_OPTIONS = [
  { value: "DRAFT", label: "Draft" },
  { value: "ACTIVE", label: "Aktif" },
  { value: "ON_HOLD", label: "Pause" },
  { value: "COMPLETED", label: "Selesai" },
  { value: "TERMINATED", label: "Dihentikan" },
];

export default function KontrakListPage() {
  const { hasPerm } = useAuthStore();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [year, setYear] = useState("");

  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (year) params.set("fiscal_year", year);

  const { data, isLoading, mutate } = useSWR<Paginated<Contract>>(
    `/contracts/?${params.toString()}`,
    swrFetcher,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Kontrak</h1>
          <p className="text-sm text-muted-fg">Daftar seluruh kontrak yang Anda akses.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => mutate()} className="btn-ghost" title="Refresh">
            <RefreshCw className="size-4" />
          </button>
          {hasPerm("contract.create") && (
            <Link href="/kontrak/baru" className="btn-primary">
              <Plus className="size-4 mr-1" /> Buat Kontrak
            </Link>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="flex gap-2 flex-wrap mb-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-fg" />
            <input
              className="input pl-9"
              placeholder="Cari nomor / nama kontrak..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select className="input max-w-[180px]" value={status}
                  onChange={(e) => setStatus(e.target.value)}>
            <option value="">Status (semua)</option>
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input className="input max-w-[140px]" type="number" placeholder="Tahun anggaran"
                  value={year} onChange={(e) => setYear(e.target.value)} />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b text-muted-fg">
                <th className="py-2 pr-4">Nomor</th>
                <th className="py-2 pr-4">Nama</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">PPK / Kontraktor</th>
                <th className="py-2 pr-4 text-right">Nilai Saat Ini</th>
                <th className="py-2 pr-4">Periode</th>
                <th className="py-2 pr-4 text-center">Lokasi</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">Memuat...</td></tr>
              )}
              {data?.results?.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">
                  Belum ada kontrak. {hasPerm("contract.create") && (
                    <Link href="/kontrak/baru" className="text-primary hover:underline">
                      Buat kontrak pertama →
                    </Link>
                  )}
                </td></tr>
              )}
              {data?.results?.map((c) => (
                <tr key={c.id} className="border-b hover:bg-muted/30">
                  <td className="py-2 pr-4 font-mono text-xs">
                    <Link href={`/kontrak/${c.id}/ringkasan`} className="hover:text-primary">
                      {c.number}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">
                    <Link href={`/kontrak/${c.id}/ringkasan`} className="hover:text-primary font-medium">
                      {c.name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4"><ContractStatusBadge status={c.status} /></td>
                  <td className="py-2 pr-4">
                    <div>{c.ppk_name}</div>
                    <div className="text-xs text-muted-fg">{c.contractor_name}</div>
                  </td>
                  <td className="py-2 pr-4 text-right font-mono">
                    {formatRupiahFull(c.current_value)}
                  </td>
                  <td className="py-2 pr-4 text-xs">
                    <div>{formatTanggalSingkat(c.start_date)}</div>
                    <div className="text-muted-fg">s.d. {formatTanggalSingkat(c.end_date)}</div>
                  </td>
                  <td className="py-2 pr-4 text-center">{c.location_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && (
          <div className="mt-3 text-xs text-muted-fg">Total: {data.count} kontrak.</div>
        )}
      </div>
    </div>
  );
}
