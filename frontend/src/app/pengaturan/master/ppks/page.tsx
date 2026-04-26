"use client";

import { toast } from "sonner";

import MasterCrudPage from "@/components/master/MasterCrudPage";

type PPK = {
  id: string;
  nip: string;
  full_name: string;
  jabatan: string;
  satker: string;
  whatsapp: string;
  email: string;
  user_username: string | null;
  user_full_name: string | null;
};

export default function PpksPage() {
  return (
    <MasterCrudPage<PPK>
      title="Master PPK (Pejabat Pembuat Komitmen)"
      resourceUrl="/ppks/"
      permRead="ppk.read"
      permCreate="ppk.create"
      permUpdate="ppk.update"
      permDelete="ppk.delete"
      searchPlaceholder="Cari NIP, nama, jabatan, satker..."
      columns={[
        { key: "nip", header: "NIP" },
        { key: "full_name", header: "Nama Lengkap" },
        { key: "jabatan", header: "Jabatan", render: (r) => r.jabatan || "—" },
        { key: "satker", header: "Satker", render: (r) => r.satker || "—" },
        { key: "whatsapp", header: "WhatsApp", render: (r) => r.whatsapp || "—" },
        { key: "user_username", header: "Akun User", render: (r) =>
          r.user_username || <span className="text-muted-fg">—</span>
        },
      ]}
      initialForm={{
        nip: "", full_name: "", jabatan: "", satker: "",
        whatsapp: "", email: "",
      }}
      renderForm={({ form, setForm }) => (
        <>
          <div>
            <label className="label">NIP <span className="text-danger">*</span></label>
            <input className="input" required value={form.nip}
                    onChange={(e) => setForm({ ...form, nip: e.target.value })}
                    placeholder="18 digit angka" />
          </div>
          <div>
            <label className="label">Nama Lengkap <span className="text-danger">*</span></label>
            <input className="input" required value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="label">Jabatan</label>
            <input className="input" value={form.jabatan}
                    onChange={(e) => setForm({ ...form, jabatan: e.target.value })}
                    placeholder="PPK Direktorat XYZ" />
          </div>
          <div>
            <label className="label">Satuan Kerja (Satker)</label>
            <input className="input" value={form.satker}
                    onChange={(e) => setForm({ ...form, satker: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">No. WhatsApp</label>
              <input className="input" value={form.whatsapp}
                      onChange={(e) => setForm({ ...form, whatsapp: e.target.value })}
                      placeholder="6281234567890" />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
          </div>
          <p className="text-xs text-muted-fg pt-1">
            User akun PPK akan dibuat otomatis. Password awal akan ditampilkan sekali — catat
            dan berikan ke PPK terkait.
          </p>
        </>
      )}
      onCreated={(created) => {
        if (created.initial_user) {
          const { username, initial_password } = created.initial_user;
          toast.success(
            `Akun PPK dibuat: ${username} | Password awal: ${initial_password}`,
            { duration: 30000, description: "Catat password ini sekarang." },
          );
        }
      }}
    />
  );
}
