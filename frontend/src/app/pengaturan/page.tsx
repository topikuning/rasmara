"use client";

import Link from "next/link";
import { Users, Shield, ListTree, History, AlertTriangle, Building, UserCog, Package, Tag } from "lucide-react";

import { useAuthStore } from "@/lib/auth/store";

const ITEMS = [
  { href: "/pengaturan/users", icon: Users, label: "User", desc: "Kelola pengguna sistem.", perm: "user.read" },
  { href: "/pengaturan/roles", icon: Shield, label: "Role & Permission", desc: "Atur role dan izin akses.", perm: "role.read" },
  { href: "/pengaturan/menus", icon: ListTree, label: "Menu", desc: "Konfigurasi menu navigasi per role.", perm: "menu.read" },
  { href: "/pengaturan/master/companies", icon: Building, label: "Perusahaan", desc: "Master perusahaan kontraktor & konsultan.", perm: "company.read" },
  { href: "/pengaturan/master/ppks", icon: UserCog, label: "PPK", desc: "Master Pejabat Pembuat Komitmen.", perm: "ppk.read" },
  { href: "/pengaturan/master/facilities", icon: Package, label: "Master Fasilitas", desc: "Katalog tipe fasilitas.", perm: "master.read" },
  { href: "/pengaturan/master/work-codes", icon: Tag, label: "Master Kode Pekerjaan", desc: "Katalog kode pekerjaan.", perm: "master.read" },
  { href: "/pengaturan/audit", icon: History, label: "Audit Log", desc: "Lihat catatan semua perubahan.", perm: "audit.read" },
  { href: "/pengaturan/godmode", icon: AlertTriangle, label: "God Mode", desc: "Bypass validasi state (Superadmin).", perm: null, superonly: true },
];

export default function PengaturanHub() {
  const { hasPerm, me } = useAuthStore();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Pengaturan</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {ITEMS.map((it) => {
          const allowed = it.superonly ? me?.is_superuser : (it.perm ? hasPerm(it.perm) : true);
          if (!allowed) return null;
          const Icon = it.icon;
          return (
            <Link key={it.href} href={it.href}
                  className="card p-4 hover:shadow-md transition-shadow flex items-start gap-3">
              <div className="size-10 rounded-lg bg-primary/10 text-primary grid place-items-center shrink-0">
                <Icon className="size-5" />
              </div>
              <div>
                <div className="font-medium">{it.label}</div>
                <div className="text-sm text-muted-fg">{it.desc}</div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
