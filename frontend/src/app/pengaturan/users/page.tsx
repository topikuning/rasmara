"use client";

import useSWR from "swr";
import { useState } from "react";
import { Plus, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";
import { formatTanggalJam } from "@/lib/format/tanggal";

type User = {
  id: string;
  username: string;
  full_name: string;
  email: string;
  role_name: string | null;
  role_code: string | null;
  is_active: boolean;
  must_change_password: boolean;
  auto_provisioned: boolean;
  last_login: string | null;
  role_id?: string | null;
};

type Role = { id: string; code: string; name: string };

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export default function UsersPage() {
  const { hasPerm } = useAuthStore();
  const [search, setSearch] = useState("");

  const { data, isLoading, mutate } = useSWR<Paginated<User>>(
    `/users/?search=${encodeURIComponent(search)}`,
    swrFetcher,
  );
  const { data: rolesData } = useSWR<Paginated<Role>>("/roles/", swrFetcher);
  const roles = rolesData?.results ?? [];

  const [showCreate, setShowCreate] = useState(false);

  const canCreate = hasPerm("user.create");
  const canUpdate = hasPerm("user.update");

  async function onResetPassword(u: User) {
    if (!confirm(`Reset password user "${u.username}"?`)) return;
    try {
      const res = await api<{ initial_password: string }>(
        `/users/${u.id}/reset-password/`,
        { method: "POST", body: {} },
      );
      toast.success(`Password baru: ${res.initial_password}`, { duration: 15000 });
      mutate();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h1 className="text-2xl font-bold">User</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => mutate()} className="btn-ghost" title="Refresh">
            <RefreshCw className="size-4" />
          </button>
          {canCreate && (
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus className="size-4 mr-1" /> Tambah User
            </button>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="relative max-w-md mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-fg" />
          <input
            className="input pl-9"
            placeholder="Cari username, nama, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b text-muted-fg">
                <th className="py-2 pr-4">Username</th>
                <th className="py-2 pr-4">Nama Lengkap</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Login Terakhir</th>
                <th className="py-2 pr-4">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">Memuat...</td></tr>
              )}
              {data?.results?.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-muted-fg">Tidak ada data.</td></tr>
              )}
              {data?.results?.map((u) => (
                <tr key={u.id} className="border-b hover:bg-muted/30">
                  <td className="py-2 pr-4 font-mono">{u.username}</td>
                  <td className="py-2 pr-4">{u.full_name}</td>
                  <td className="py-2 pr-4">{u.email || "-"}</td>
                  <td className="py-2 pr-4">{u.role_name || "-"}</td>
                  <td className="py-2 pr-4">
                    {u.is_active ? (
                      <span className="inline-block px-2 py-0.5 rounded bg-success/10 text-success text-xs">Aktif</span>
                    ) : (
                      <span className="inline-block px-2 py-0.5 rounded bg-muted text-muted-fg text-xs">Nonaktif</span>
                    )}
                    {u.must_change_password && (
                      <span className="ml-1 inline-block px-2 py-0.5 rounded bg-warning/10 text-warning text-xs">
                        Wajib ganti password
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-muted-fg">
                    {u.last_login ? formatTanggalJam(u.last_login) : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {canUpdate && (
                      <button onClick={() => onResetPassword(u)} className="text-primary hover:underline text-xs">
                        Reset password
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <CreateUserModal
          roles={roles}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); mutate(); }}
        />
      )}
    </div>
  );
}

function CreateUserModal({
  roles, onClose, onCreated,
}: { roles: Role[]; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    username: "", full_name: "", email: "", phone: "",
    role_id: "" as string, password: "",
  });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api<any>("/users/", {
        method: "POST",
        body: {
          username: form.username,
          full_name: form.full_name,
          email: form.email,
          phone: form.phone,
          role_id: form.role_id || null,
          password: form.password || undefined,
          is_active: true,
        },
      });
      if (res.initial_password) {
        toast.success(`User dibuat. Password awal: ${res.initial_password}`, { duration: 15000 });
      } else {
        toast.success("User berhasil dibuat.");
      }
      onCreated();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(`${err.message}${err.details ? "\n" + JSON.stringify(err.details) : ""}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-md space-y-3">
        <h2 className="text-lg font-semibold">Tambah User Baru</h2>
        <div>
          <label className="label">Username</label>
          <input className="input" required value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </div>
        <div>
          <label className="label">Nama Lengkap</label>
          <input className="input" required value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <label className="label">No. WhatsApp (mis. 6281234567890)</label>
          <input className="input" value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </div>
        <div>
          <label className="label">Role</label>
          <select className="input" value={form.role_id}
                  onChange={(e) => setForm({ ...form, role_id: e.target.value })}>
            <option value="">— pilih —</option>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Password (kosongkan untuk auto-generate)</label>
          <input className="input" type="text" value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <div className="flex gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={submitting}>
            Batal
          </button>
          <button type="submit" className="btn-primary flex-1" disabled={submitting}>
            {submitting ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </form>
    </div>
  );
}
