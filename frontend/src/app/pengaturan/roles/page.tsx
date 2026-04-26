"use client";

import useSWR from "swr";
import { useState } from "react";
import { toast } from "sonner";

import { api, ApiError, swrFetcher } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth/store";

type Role = {
  id: string;
  code: string;
  name: string;
  description: string;
  is_system: boolean;
  permission_codes: string[];
  menu_codes: string[];
  user_count: number;
};

type Permission = { id: string; code: string; name: string; module: string; action: string };

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export default function RolesPage() {
  const { hasPerm } = useAuthStore();
  const { data: rolesData, mutate } = useSWR<Paginated<Role>>("/roles/", swrFetcher);
  const { data: perms } = useSWR<Permission[]>("/permissions/", swrFetcher);

  const roles = rolesData?.results ?? [];
  const [selected, setSelected] = useState<Role | null>(null);
  const canUpdate = hasPerm("role.update");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Role & Permission</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 lg:col-span-1">
          <h2 className="font-semibold mb-3">Daftar Role</h2>
          <ul className="space-y-1">
            {roles.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => setSelected(r)}
                  className={`w-full text-left px-3 py-2 rounded-lg border
                    ${selected?.id === r.id ? "bg-primary/10 border-primary" : "hover:bg-muted"}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{r.name}</span>
                    {r.is_system && (
                      <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded">SYSTEM</span>
                    )}
                  </div>
                  <div className="text-xs text-muted-fg">
                    {r.permission_codes.length} izin · {r.user_count} user
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="card p-4 lg:col-span-2">
          {!selected && (
            <div className="text-sm text-muted-fg">Pilih role di sebelah kiri untuk melihat / mengubah izin.</div>
          )}
          {selected && (
            <RolePermissionEditor
              role={selected}
              perms={perms ?? []}
              canUpdate={canUpdate}
              onSaved={() => { mutate(); }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function RolePermissionEditor({
  role, perms, canUpdate, onSaved,
}: { role: Role; perms: Permission[]; canUpdate: boolean; onSaved: () => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set(role.permission_codes));
  const [saving, setSaving] = useState(false);

  // Re-init when role berubah
  if ((role.permission_codes.length !== selected.size
       || role.permission_codes.some((c) => !selected.has(c)))
      && JSON.stringify([...selected].sort()) !== JSON.stringify([...role.permission_codes].sort())) {
    // hanya reset kalau memang beda set (ringan)
  }

  function toggle(code: string) {
    if (!canUpdate) return;
    setSelected((s) => {
      const n = new Set(s);
      n.has(code) ? n.delete(code) : n.add(code);
      return n;
    });
  }

  function toggleModule(module: string, allCodes: string[]) {
    if (!canUpdate) return;
    setSelected((s) => {
      const n = new Set(s);
      const allSelected = allCodes.every((c) => n.has(c));
      allCodes.forEach((c) => allSelected ? n.delete(c) : n.add(c));
      return n;
    });
  }

  async function save() {
    setSaving(true);
    try {
      await api(`/roles/${role.id}/permissions/`, {
        method: "PUT",
        body: { permission_codes: [...selected] },
      });
      toast.success("Permission role disimpan.");
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Group by module
  const byModule = perms.reduce<Record<string, Permission[]>>((acc, p) => {
    (acc[p.module] ??= []).push(p);
    return acc;
  }, {});
  const modules = Object.keys(byModule).sort();

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold">{role.name}</h2>
          <p className="text-xs text-muted-fg">{role.description}</p>
        </div>
        {canUpdate && (
          <button onClick={save} className="btn-primary" disabled={saving}>
            {saving ? "Menyimpan..." : "Simpan Perubahan"}
          </button>
        )}
      </div>

      <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
        {modules.map((m) => {
          const items = byModule[m];
          const codes = items.map((p) => p.code);
          const allSelected = codes.every((c) => selected.has(c));
          const someSelected = codes.some((c) => selected.has(c));
          return (
            <div key={m} className="border rounded-lg p-3">
              <label className="flex items-center gap-2 font-medium text-sm mb-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => { if (el) el.indeterminate = !allSelected && someSelected; }}
                  onChange={() => toggleModule(m, codes)}
                  disabled={!canUpdate}
                />
                <span className="capitalize">{m}</span>
                <span className="text-xs text-muted-fg ml-auto">
                  {codes.filter((c) => selected.has(c)).length}/{codes.length}
                </span>
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
                {items.map((p) => (
                  <label key={p.code} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selected.has(p.code)}
                      onChange={() => toggle(p.code)}
                      disabled={!canUpdate}
                    />
                    <span className="font-mono text-xs">{p.action}</span>
                    <span className="text-muted-fg text-xs hidden md:inline truncate">— {p.name}</span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
