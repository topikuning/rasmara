"use client";

import useSWR from "swr";
import { useState } from "react";
import { RefreshCw, Search } from "lucide-react";

import { swrFetcher } from "@/lib/api/client";
import { formatTanggalJam } from "@/lib/format/tanggal";

type AuditLog = {
  id: string;
  user_username: string | null;
  user_full_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  entity_repr: string;
  changes: Record<string, { before: any; after: any }>;
  ip_address: string | null;
  godmode_bypass: boolean;
  unlock_reason: string;
  ts: string;
};

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export default function AuditPage() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (action) params.set("action", action);
  if (entityType) params.set("entity_type", entityType);

  const { data, isLoading, mutate } = useSWR<Paginated<AuditLog>>(
    `/audit-logs/?${params.toString()}`,
    swrFetcher,
  );

  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <button onClick={() => mutate()} className="btn-ghost"><RefreshCw className="size-4" /></button>
      </div>

      <div className="card p-4">
        <div className="flex gap-2 flex-wrap mb-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-fg" />
            <input
              className="input pl-9"
              placeholder="Cari entity..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select className="input max-w-[180px]" value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">Semua Action</option>
            <option value="CREATE">Create</option>
            <option value="UPDATE">Update</option>
            <option value="DELETE">Delete</option>
            <option value="LOGIN">Login</option>
            <option value="LOGOUT">Logout</option>
            <option value="LOGIN_FAILED">Login Failed</option>
            <option value="GODMODE_BYPASS">Godmode Bypass</option>
          </select>
          <input
            className="input max-w-[180px]"
            placeholder="Entity type..."
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b text-muted-fg">
                <th className="py-2 pr-4">Waktu</th>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Action</th>
                <th className="py-2 pr-4">Entity</th>
                <th className="py-2 pr-4">Repr</th>
                <th className="py-2 pr-4">IP</th>
                <th className="py-2 pr-4">Diff</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">Memuat...</td></tr>
              )}
              {data?.results?.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">Tidak ada log.</td></tr>
              )}
              {data?.results?.map((l) => (
                <>
                  <tr key={l.id} className="border-b hover:bg-muted/30">
                    <td className="py-2 pr-4 whitespace-nowrap">{formatTanggalJam(l.ts)}</td>
                    <td className="py-2 pr-4">{l.user_username ?? "—"}</td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs px-2 py-0.5 rounded
                        ${l.action === "DELETE" || l.action === "LOGIN_FAILED" || l.action === "GODMODE_BYPASS"
                          ? "bg-danger/10 text-danger"
                          : l.action === "CREATE" ? "bg-success/10 text-success"
                          : "bg-muted"}`}>
                        {l.action}
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">{l.entity_type}</td>
                    <td className="py-2 pr-4 truncate max-w-[200px]">{l.entity_repr || "—"}</td>
                    <td className="py-2 pr-4 text-xs font-mono">{l.ip_address ?? "—"}</td>
                    <td className="py-2 pr-4">
                      {Object.keys(l.changes ?? {}).length > 0 ? (
                        <button
                          onClick={() => setOpenId(openId === l.id ? null : l.id)}
                          className="text-primary text-xs hover:underline">
                          {openId === l.id ? "Tutup" : "Lihat"}
                        </button>
                      ) : "—"}
                    </td>
                  </tr>
                  {openId === l.id && (
                    <tr key={l.id + "-d"}>
                      <td colSpan={7} className="bg-muted/30 p-4">
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(l.changes, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
