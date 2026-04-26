"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api/client";
import FilterableSelect from "@/components/form/FilterableSelect";
import { PpnBreakdown } from "@/components/contract/PpnBreakdown";

export default function BuatKontrakPage() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    number: "",
    name: "",
    ppk: "",
    contractor: "",
    fiscal_year: new Date().getFullYear(),
    original_value: "",
    ppn_pct: "11.00",
    start_date: today,
    end_date: today,
    notes: "",
  });

  const orig = parseFloat(form.original_value || "0");
  const ppnPct = parseFloat(form.ppn_pct || "0");
  const boqEstimate = ppnPct > 0 ? orig / (1 + ppnPct / 100) : orig;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api<any>("/contracts/", {
        method: "POST",
        body: form,
      });
      toast.success("Kontrak dibuat. Status: DRAFT.");
      router.replace(`/kontrak/${res.id}/ringkasan`);
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.details ? "\n" + JSON.stringify(err.details) : "";
        toast.error(`${err.message}${detail}`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/kontrak" className="btn-ghost p-1.5"><ArrowLeft className="size-4" /></Link>
        <h1 className="text-2xl font-bold">Buat Kontrak Baru</h1>
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Nomor Kontrak <span className="text-danger">*</span></label>
            <input className="input" required value={form.number}
                    onChange={(e) => setForm({ ...form, number: e.target.value })}
                    placeholder="001/KONTRAK/IV/2026" />
          </div>
          <div>
            <label className="label">Tahun Anggaran <span className="text-danger">*</span></label>
            <input className="input" type="number" required min="2000" max="2100"
                    value={form.fiscal_year}
                    onChange={(e) => setForm({ ...form, fiscal_year: parseInt(e.target.value || "0") })} />
          </div>
        </div>

        <div>
          <label className="label">Nama Kontrak <span className="text-danger">*</span></label>
          <input className="input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Pembangunan Gudang Beku Wilayah Timur" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">PPK Pemilik <span className="text-danger">*</span></label>
            <FilterableSelect
              value={form.ppk}
              onChange={(id) => setForm({ ...form, ppk: id || "" })}
              fetchUrl="/ppks/lookup/"
              getLabel={(p: any) => p.full_name}
              getSubLabel={(p: any) => `NIP ${p.nip}${p.jabatan ? " — " + p.jabatan : ""}`}
              placeholder="Pilih PPK..."
              required
            />
          </div>
          <div>
            <label className="label">Kontraktor <span className="text-danger">*</span></label>
            <FilterableSelect
              value={form.contractor}
              onChange={(id) => setForm({ ...form, contractor: id || "" })}
              fetchUrl="/companies/lookup/?type=KONTRAKTOR"
              getLabel={(c: any) => `${c.code} - ${c.name}`}
              placeholder="Pilih kontraktor..."
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Nilai Kontrak (POST-PPN) <span className="text-danger">*</span></label>
            <input className="input font-mono" type="number" step="0.01" required min="0"
                    value={form.original_value}
                    onChange={(e) => setForm({ ...form, original_value: e.target.value })}
                    placeholder="1000000000.00" />
            <p className="text-xs text-muted-fg mt-1">
              Total nilai kontrak sudah termasuk PPN (sesuai dokumen kontrak).
            </p>
          </div>
          <div>
            <label className="label">PPN (%)</label>
            <input className="input font-mono" type="number" step="0.01" min="0" max="100"
                    value={form.ppn_pct}
                    onChange={(e) => setForm({ ...form, ppn_pct: e.target.value })} />
          </div>
        </div>

        {orig > 0 && (
          <div className="rounded-lg border bg-muted/30 p-3">
            <div className="text-xs text-muted-fg mb-1.5">Estimasi breakdown:</div>
            <PpnBreakdown boqValue={boqEstimate} ppnPct={ppnPct} contractValue={orig} />
            <p className="text-xs text-muted-fg mt-2">
              Nilai BOQ aktual akan dihitung dari item-item BOQ yang Anda input nanti
              (PRE-PPN). Total BOQ × (1+PPN%) tidak boleh melebihi nilai kontrak.
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Tanggal Mulai <span className="text-danger">*</span></label>
            <input className="input" type="date" required value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div>
            <label className="label">Tanggal Selesai <span className="text-danger">*</span></label>
            <input className="input" type="date" required value={form.end_date}
                    onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          </div>
        </div>

        <div>
          <label className="label">Catatan</label>
          <textarea className="input" rows={3} value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>

        <div className="flex gap-2 pt-2 border-t">
          <Link href="/kontrak" className="btn-secondary flex-1 text-center">Batal</Link>
          <button type="submit" className="btn-primary flex-1" disabled={submitting}>
            {submitting ? "Menyimpan..." : "Simpan Kontrak"}
          </button>
        </div>
      </form>
    </div>
  );
}
