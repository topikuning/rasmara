"use client";

import useSWR from "swr";
import { CheckCircle2, AlertCircle, Server, Database, Cpu } from "lucide-react";

import { swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";

type ReadyResp = {
  status: "ok" | "degraded";
  checks: Record<string, string>;
};

export default function DashboardPage() {
  const { me } = useAuthStore();
  const { data: ready } = useSWR<ReadyResp>("/health/ready/", swrFetcher, { refreshInterval: 60000 });
  const { data: version } = useSWR<{ name: string; version: string; module: string }>(
    "/version/",
    swrFetcher,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-fg">
          Selamat datang, {me?.full_name || me?.username}.
        </p>
      </div>

      <div className="card p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Server className="size-4" /> Status Sistem
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatusCard
            icon={<Cpu className="size-4" />}
            label="API"
            value={ready ? (ready.status === "ok" ? "ok" : "degraded") : "..."}
            ok={ready?.status === "ok"}
          />
          <StatusCard
            icon={<Database className="size-4" />}
            label="Database"
            value={ready?.checks?.database ?? "..."}
            ok={ready?.checks?.database === "ok"}
          />
          <StatusCard
            icon={<Server className="size-4" />}
            label="Redis"
            value={ready?.checks?.redis ?? "..."}
            ok={ready?.checks?.redis === "ok"}
          />
        </div>
        {version && (
          <p className="mt-4 text-xs text-muted-fg">
            {version.name} v{version.version} • Modul aktif: {version.module}
          </p>
        )}
      </div>

      <div className="card p-5">
        <h2 className="font-semibold mb-2">Modul Berikutnya</h2>
        <p className="text-sm text-muted-fg">
          Modul fondasi (Auth, RBAC, Audit) sudah aktif. Modul Kontrak, BOQ, VO, Addendum,
          Pelaporan, Termin, dan Dashboard Eksekutif akan dibangun bertahap pada iterasi
          berikutnya.
        </p>
      </div>
    </div>
  );
}

function StatusCard({
  icon, label, value, ok,
}: { icon: React.ReactNode; label: string; value: string; ok?: boolean }) {
  return (
    <div className="border rounded-lg p-4 flex items-start gap-3">
      <div className={`size-9 rounded-md grid place-items-center
        ${ok ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
        {ok ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
      </div>
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-wide text-muted-fg flex items-center gap-1">
          {icon} {label}
        </div>
        <div className="font-medium truncate">{value}</div>
      </div>
    </div>
  );
}
