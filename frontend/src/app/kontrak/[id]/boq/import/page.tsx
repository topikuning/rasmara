"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft, Download, Upload, CheckCircle2, AlertTriangle, Loader2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api/client";
import { downloadFile } from "@/lib/api/download";
import { useAuthStore } from "@/lib/auth/store";

type Preview = {
  detected_format: string;
  sheet_used: string;
  rows_total: number;
  rows_valid: number;
  rows_invalid: number;
  facility_summary: { facility_code: string; facility_name: string;
                       row_count: number; valid_count: number }[];
  unmatched_facility_codes: string[];
  sample_errors: { row: number; code: string; errors: string[] }[];
  warnings: string[];
};

export default function ImportBoqPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: contractId } = use(params);
  const router = useRouter();
  const sp = useSearchParams();
  const revisionId = sp.get("revision") || "";
  const { hasPerm } = useAuthStore();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [navigating, setNavigating] = useState(false);

  if (!hasPerm("boq.import")) {
    return (
      <div className="card p-6">
        <p className="text-sm text-danger">Anda tidak memiliki izin <code>boq.import</code>.</p>
      </div>
    );
  }

  if (!revisionId) {
    return (
      <div className="card p-6">
        <p className="text-sm text-danger">Revisi tidak terpilih. Kembali ke tab BOQ dan klik Import lagi.</p>
        <Link href={`/kontrak/${contractId}/boq`} className="btn-primary mt-3">
          <ArrowLeft className="size-4 mr-1" /> Kembali
        </Link>
      </div>
    );
  }

  async function onPreview() {
    if (!file) {
      toast.error("Pilih file Excel dulu.");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(
        `/api/v1/boq-revisions/${revisionId}/import-preview/`,
        {
          method: "POST", body: fd,
          headers: { Authorization: `Bearer ${useAuthStore.getState().access ?? ""}` },
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || "Parse gagal.");
      }
      const data: Preview = await res.json();
      setPreview(data);
      setStep(2);
    } catch (err: any) {
      toast.error(err.message || "Parse gagal.");
    } finally {
      setBusy(false);
    }
  }

  async function onCommit() {
    if (!file) return;
    if (!confirm(
      `Commit import?\n\nIni akan MENGGANTI semua item BOQ revisi ini dengan ${preview?.rows_valid} baris valid dari Excel.`
    )) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("replace", "1");
      const res = await fetch(
        `/api/v1/boq-revisions/${revisionId}/import-commit/`,
        {
          method: "POST", body: fd,
          headers: { Authorization: `Bearer ${useAuthStore.getState().access ?? ""}` },
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || "Commit gagal.");
      }
      const data = await res.json();
      toast.success(`Import selesai: ${data.rows_imported} baris.`);
      setNavigating(true);
      router.replace(`/kontrak/${contractId}/boq`);
    } catch (err: any) {
      setBusy(false);
      toast.error(err.message || "Commit gagal.");
    }
  }

  return (
    <div className="space-y-4 relative">
      {navigating && (
        <div className="fixed inset-0 z-[70] grid place-items-center bg-background/80 backdrop-blur-sm">
          <div className="card p-6 text-center max-w-sm">
            <Loader2 className="size-10 animate-spin mx-auto mb-3 text-primary" />
            <p className="font-medium">Memuat ulang BOQ...</p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Link href={`/kontrak/${contractId}/boq`} className="btn-ghost p-1.5">
          <ArrowLeft className="size-4" />
        </Link>
        <div>
          <h2 className="text-xl font-semibold">Import BOQ dari Excel</h2>
          <p className="text-sm text-muted-fg">
            Format A — single sheet, kolom: facility_code, code, parent_code, description, dll.
          </p>
        </div>
      </div>

      {/* Stepper */}
      <ol className="flex items-center gap-2 text-sm">
        <Step n={1} active={step === 1} done={step > 1}>Upload</Step>
        <span className="text-muted-fg">→</span>
        <Step n={2} active={step === 2} done={step > 2}>Preview</Step>
        <span className="text-muted-fg">→</span>
        <Step n={3} active={step === 3} done={false}>Selesai</Step>
      </ol>

      {/* Step 1: Upload */}
      {step === 1 && (
        <div className="card p-6 space-y-4">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-sm font-medium mb-1">Belum punya template?</p>
            <p className="text-xs text-muted-fg mb-2">
              Unduh template Format A — sheet &ldquo;BOQ&rdquo; dengan header siap pakai dan baris contoh.
            </p>
            <button
              type="button"
              onClick={() => downloadFile("/boq-revisions/import-template/",
                                            "template-boq.xlsx")
                              .catch((e) => toast.error(e.message))}
              className="btn-secondary"
            >
              <Download className="size-4 mr-1" /> Unduh Template Excel
            </button>
          </div>

          <div>
            <label className="label">File Excel BOQ <span className="text-danger">*</span></label>
            <input type="file" accept=".xlsx,.xls" className="input"
                    onChange={(e) => setFile(e.target.files?.[0] || null)} />
            {file && (
              <p className="text-xs text-muted-fg mt-1">
                Dipilih: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Link href={`/kontrak/${contractId}/boq`} className="btn-secondary flex-1 text-center">
              Batal
            </Link>
            <button onClick={onPreview} disabled={!file || busy} className="btn-primary flex-1">
              {busy ? "Memproses..." : "Lanjut: Preview"}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Preview */}
      {step === 2 && preview && (
        <div className="space-y-4">
          <div className="card p-5">
            <h3 className="font-semibold mb-3">Ringkasan Parse</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <Stat label="Format" value={preview.detected_format} />
              <Stat label="Sheet" value={preview.sheet_used} />
              <Stat label="Baris Total" value={preview.rows_total} />
              <Stat label="Baris Valid" value={preview.rows_valid} ok />
            </div>
            {preview.rows_invalid > 0 && (
              <p className="text-sm text-warning mt-3 flex items-center gap-1">
                <AlertTriangle className="size-4" />
                <strong>{preview.rows_invalid} baris invalid</strong> akan di-skip.
              </p>
            )}
          </div>

          {preview.unmatched_facility_codes.length > 0 && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 p-4">
              <p className="text-sm font-medium text-danger mb-1">
                <AlertTriangle className="size-4 inline mr-1" />
                {preview.unmatched_facility_codes.length} facility_code tidak ditemukan
              </p>
              <p className="text-xs text-muted-fg mb-2">
                Buat fasilitas-nya dulu di tab Lokasi & Fasilitas:
              </p>
              <div className="flex flex-wrap gap-1">
                {preview.unmatched_facility_codes.map((c) => (
                  <code key={c} className="text-xs bg-danger/20 px-1.5 py-0.5 rounded">{c}</code>
                ))}
              </div>
            </div>
          )}

          {preview.facility_summary.length > 0 && (
            <div className="card p-4">
              <h3 className="font-semibold mb-2">Per Fasilitas</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b text-muted-fg text-xs">
                    <th className="py-1.5">Kode</th>
                    <th className="py-1.5">Nama (dari Excel)</th>
                    <th className="py-1.5 text-right">Baris</th>
                    <th className="py-1.5 text-right">Valid</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.facility_summary.map((f) => (
                    <tr key={f.facility_code} className="border-b">
                      <td className="py-1.5 font-mono text-xs">{f.facility_code}</td>
                      <td className="py-1.5">{f.facility_name || "—"}</td>
                      <td className="py-1.5 text-right">{f.row_count}</td>
                      <td className="py-1.5 text-right text-success">{f.valid_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {preview.sample_errors.length > 0 && (
            <div className="card p-4">
              <h3 className="font-semibold mb-2">Contoh Error</h3>
              <ul className="text-xs space-y-1">
                {preview.sample_errors.map((e, i) => (
                  <li key={i} className="text-danger">
                    Baris {e.row} ({e.code}): {e.errors.join("; ")}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => { setStep(1); setPreview(null); }} className="btn-secondary flex-1">
              Kembali
            </button>
            <button onClick={onCommit}
                    disabled={busy || preview.rows_valid === 0 || preview.unmatched_facility_codes.length > 0}
                    className="btn-primary flex-1">
              {busy ? "Mengimpor..." : (
                <span className="inline-flex items-center gap-2">
                  <Upload className="size-4" />
                  Commit Import ({preview.rows_valid} baris)
                </span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Step({ n, active, done, children }: any) {
  return (
    <li className={`flex items-center gap-1.5 ${active ? "text-primary font-semibold"
                                                       : done ? "text-success" : "text-muted-fg"}`}>
      <span className={`size-6 rounded-full grid place-items-center text-xs
        ${active ? "bg-primary text-primary-fg"
                  : done ? "bg-success text-white" : "bg-muted"}`}>
        {done ? <CheckCircle2 className="size-3.5" /> : n}
      </span>
      {children}
    </li>
  );
}

function Stat({ label, value, ok }: { label: string; value: any; ok?: boolean }) {
  return (
    <div>
      <div className="text-xs text-muted-fg">{label}</div>
      <div className={`font-semibold ${ok ? "text-success" : ""}`}>{value}</div>
    </div>
  );
}
