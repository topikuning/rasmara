"use client";

import MasterCrudPage from "@/components/master/MasterCrudPage";

const CATEGORY_OPTIONS = [
  { value: "PERSIAPAN", label: "Persiapan" },
  { value: "STRUKTURAL", label: "Struktural" },
  { value: "ARSITEKTURAL", label: "Arsitektural" },
  { value: "MEP", label: "Mekanikal/Elektrikal/Plumbing" },
  { value: "FINISHING", label: "Finishing" },
  { value: "FURNITURE", label: "Furniture & Equipment" },
  { value: "LANSEKAP", label: "Lansekap & Sitework" },
  { value: "LAINNYA", label: "Lainnya" },
];
const CAT_LABEL: Record<string, string> = Object.fromEntries(CATEGORY_OPTIONS.map((o) => [o.value, o.label]));

type WorkCode = {
  id: string;
  code: string;
  name: string;
  category: string;
  category_display: string;
  default_unit: string;
  description: string;
  is_active: boolean;
};

export default function WorkCodesPage() {
  return (
    <MasterCrudPage<WorkCode>
      title="Master Kode Pekerjaan"
      resourceUrl="/master-work-codes/"
      permRead="master.read"
      permCreate="master.update"
      permUpdate="master.update"
      permDelete="master.update"
      searchPlaceholder="Cari kode, nama, satuan..."
      filters={[
        { key: "category", label: "Kategori", options: CATEGORY_OPTIONS },
        { key: "is_active", label: "Status",
          options: [{ value: "true", label: "Aktif" }, { value: "false", label: "Nonaktif" }] },
      ]}
      columns={[
        { key: "code", header: "Kode", width: "140px" },
        { key: "name", header: "Nama" },
        { key: "category", header: "Kategori", render: (r) =>
          <span className="text-xs px-2 py-0.5 rounded bg-muted">{CAT_LABEL[r.category] || r.category}</span>
        },
        { key: "default_unit", header: "Satuan", render: (r) => r.default_unit || "—" },
        { key: "is_active", header: "Status", render: (r) =>
          r.is_active
            ? <span className="text-xs px-2 py-0.5 rounded bg-success/10 text-success">Aktif</span>
            : <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-fg">Nonaktif</span>
        },
      ]}
      initialForm={{
        code: "", name: "", category: "STRUKTURAL",
        default_unit: "", description: "", is_active: true,
      }}
      renderForm={({ form, setForm }) => (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Kode <span className="text-danger">*</span></label>
              <input className="input" required value={form.code}
                      onChange={(e) => setForm({ ...form, code: e.target.value })}
                      placeholder="STR-001" />
            </div>
            <div>
              <label className="label">Kategori <span className="text-danger">*</span></label>
              <select className="input" value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {CATEGORY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Nama <span className="text-danger">*</span></label>
            <input className="input" required value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Satuan Default</label>
            <input className="input" value={form.default_unit}
                    onChange={(e) => setForm({ ...form, default_unit: e.target.value })}
                    placeholder="m2, m3, ls, unit, kg" />
          </div>
          <div>
            <label className="label">Deskripsi</label>
            <textarea className="input" rows={3} value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            <span>Aktif</span>
          </label>
        </>
      )}
    />
  );
}
