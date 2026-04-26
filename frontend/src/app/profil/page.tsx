"use client";

import Link from "next/link";
import { useAuthStore } from "@/lib/auth/store";

export default function ProfilPage() {
  const { me } = useAuthStore();
  if (!me) return null;
  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-2xl font-bold">Profil Saya</h1>
      <div className="card p-5 space-y-2 text-sm">
        <Row label="Username" value={me.username} />
        <Row label="Nama Lengkap" value={me.full_name} />
        <Row label="Email" value={me.email || "—"} />
        <Row label="No. WhatsApp" value={me.phone || "—"} />
        <Row label="Role" value={me.role_name || "—"} />
        <Row label="Superadmin" value={me.is_superuser ? "Ya" : "Tidak"} />
        <Row label="Wajib Ganti Password" value={me.must_change_password ? "Ya" : "Tidak"} />
        <Row label="Scope Kontrak"
              value={me.assigned_contract_ids === null ? "Semua kontrak" : `${me.assigned_contract_ids.length} kontrak`} />
      </div>
      <Link href="/ganti-password" className="btn-primary inline-block">Ganti Password</Link>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-3 gap-3 py-1 border-b last:border-0">
      <div className="text-muted-fg">{label}</div>
      <div className="col-span-2 font-medium">{value}</div>
    </div>
  );
}
