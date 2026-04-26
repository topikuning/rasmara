"use client";

import MasterCrudPage from "@/components/master/MasterCrudPage";

type Facility = {
  id: string;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
};

export default function FacilitiesPage() {
  return (
    <MasterCrudPage<Facility>
      title="Master Fasilitas"
      resourceUrl="/master-facilities/"
      permRead="master.read"
      permCreate="master.update"
      permUpdate="master.update"
      permDelete="master.update"
      searchPlaceholder="Cari kode atau nama fasilitas..."
      filters={[
        { key: "is_active", label: "Status",
          options: [{ value: "true", label: "Aktif" }, { value: "false", label: "Nonaktif" }] },
      ]}
      columns={[
        { key: "code", header: "Kode", width: "120px" },
        { key: "name", header: "Nama" },
        { key: "description", header: "Deskripsi", render: (r) => r.description || "—" },
        { key: "is_active", header: "Status", render: (r) =>
          r.is_active
            ? <span className="text-xs px-2 py-0.5 rounded bg-success/10 text-success">Aktif</span>
            : <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-fg">Nonaktif</span>
        },
      ]}
      initialForm={{ code: "", name: "", description: "", is_active: true }}
      renderForm={({ form, setForm }) => (
        <>
          <div>
            <label className="label">Kode <span className="text-danger">*</span></label>
            <input className="input" required value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    placeholder="GB, PE, CB" />
          </div>
          <div>
            <label className="label">Nama <span className="text-danger">*</span></label>
            <input className="input" required value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Gudang Beku, Pabrik Es, Cool Box" />
          </div>
          <div>
            <label className="label">Deskripsi</label>
            <textarea className="input" rows={3} value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            <span>Aktif (tampil di pemilihan saat membuat fasilitas baru)</span>
          </label>
        </>
      )}
    />
  );
}
