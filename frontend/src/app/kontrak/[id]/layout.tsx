"use client";

import Link from "next/link";
import useSWR from "swr";
import { use } from "react";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { swrFetcher } from "@/lib/api/client";
import { ContractTabs } from "@/components/contract/ContractTabs";
import { ContractStatusBadge } from "@/components/contract/StatusBadge";

export const dynamic = "force-dynamic";

type Summary = {
  id: string;
  number: string;
  name: string;
  status: string;
  status_display: string;
  is_godmode_active: boolean;
  gates_ok: boolean;
  gates_failed_count: number;
};

export default function Layout({
  children, params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data } = useSWR<Summary>(`/contracts/${id}/summary/`, swrFetcher);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/kontrak" className="btn-ghost p-1.5"><ArrowLeft className="size-4" /></Link>
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted-fg font-mono">{data?.number || "..."}</div>
          <h1 className="text-xl font-bold truncate">{data?.name || "Memuat..."}</h1>
        </div>
        {data && <ContractStatusBadge status={data.status} />}
      </div>

      {data?.is_godmode_active && (
        <div className="rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm flex items-start gap-2">
          <AlertTriangle className="size-4 text-danger shrink-0 mt-0.5" />
          <div>
            <strong className="text-danger">God-Mode aktif.</strong> Validasi
            state-machine kontrak ini di-bypass. Semua perubahan ditandai
            <code className="mx-1 text-xs bg-danger/20 px-1 rounded">godmode_bypass</code>
            di audit log.
          </div>
        </div>
      )}

      <ContractTabs contractId={id} />
      <div>{children}</div>
    </div>
  );
}
