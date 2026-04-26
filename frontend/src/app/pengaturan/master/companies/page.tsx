"use client";

import { toast } from "sonner";

import MasterCrudPage from "@/components/master/MasterCrudPage";

const TYPE_OPTIONS = [
  { value: "KONTRAKTOR", label: "Kontraktor" },
  { value: "KONSULTAN", label: "Konsultan MK" },
  { value: "SUPPLIER", label: "Supplier" },
  { value: "OTHER", label: "Lainnya" },
];

const TYPE_LABEL: Record<string, string> = Object.fromEntries(
  TYPE_OPTIONS.map((o) => [o.value, o.label]),
);

type Company = {
  id: string;
  code: string;
  name: string;
  npwp: string;
  type: string;
  type_display: string;
  address: string;
  phone: string;
  email: string;
  pic_name: string;
  pic_phone: string;
  default_user_username: string | null;
};

export default function CompaniesPage() {
  return (
    <MasterCrudPage<Company>
      title="Master Perusahaan"
      resourceUrl="/companies/"
      permRead="company.read"
      permCreate="company.create"
      permUpdate="company.update"
      permDelete="company.delete"
      searchPlaceholder="Cari kode, nama, NPWP, PIC..."
      filters={[
        { key: "type", label: "Tipe", options: TYPE_OPTIONS },
      ]}
      columns={[
        { key: "code", header: "Kode" },
        { key: "name", header: "Nama" },
        { key: "type", header: "Tipe", render: (r) => (
          <span className="text-xs px-2 py-0.5 rounded bg-muted">{TYPE_LABEL[r.type] || r.type}</span>
        )},
        { key: "npwp", header: "NPWP", render: (r) => r.npwp || "—" },
        { key: "pic_name", header: "PIC", render: (r) => r.pic_name || "—" },
        { key: "default_user_username", header: "User Default", render: (r) =>
          r.default_user_username || <span className="text-muted-fg">—</span>
        },
      ]}
      initialForm={{
        code: "", name: "", npwp: "", type: "KONTRAKTOR",
        address: "", phone: "", email: "",
        pic_name: "", pic_phone: "",
      }}
      renderForm={({ form, setForm }) => (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Kode <span className="text-danger">*</span></label>
              <input className="input" required value={form.code}
                      onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </div>
            <div>
              <label className="label">Tipe <span className="text-danger">*</span></label>
              <select className="input" value={form.type}
                      onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Nama Perusahaan <span className="text-danger">*</span></label>
            <input className="input" required value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">NPWP</label>
            <input className="input" value={form.npwp}
                    onChange={(e) => setForm({ ...form, npwp: e.target.value })}
                    placeholder="12.345.678.9-012.345" />
          </div>
          <div>
            <label className="label">Alamat</label>
            <textarea className="input" rows={2} value={form.address}
                      onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Telepon</label>
              <input className="input" value={form.phone}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-2 border-t">
            <div>
              <label className="label">Nama PIC</label>
              <input className="input" value={form.pic_name}
                      onChange={(e) => setForm({ ...form, pic_name: e.target.value })} />
            </div>
            <div>
              <label className="label">No. WhatsApp PIC</label>
              <input className="input" value={form.pic_phone}
                      onChange={(e) => setForm({ ...form, pic_phone: e.target.value })}
                      placeholder="6281234567890" />
            </div>
          </div>
          <p className="text-xs text-muted-fg pt-1">
            User default akan dibuat otomatis saat perusahaan baru dibuat. Password awal akan
            ditampilkan sekali — catat dan berikan ke perusahaan terkait.
          </p>
        </>
      )}
      onCreated={(created) => {
        if (created.initial_user) {
          const { username, initial_password } = created.initial_user;
          toast.success(
            `User otomatis dibuat: ${username} | Password awal: ${initial_password}`,
            { duration: 30000, description: "Catat password ini sekarang. Tidak akan ditampilkan ulang." },
          );
        }
      }}
    />
  );
}
