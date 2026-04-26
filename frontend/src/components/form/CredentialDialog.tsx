"use client";

/**
 * CredentialDialog — modal untuk menampilkan kredensial user yang baru dibuat
 * (auto-provisioned dari Company / PPK, reset password, dll.).
 *
 * UX requirements:
 *  - Field selectable + tombol Copy per-field
 *  - Tombol "Salin Semua" untuk salin format multi-baris
 *  - Tombol "Unduh .txt" sebagai backup
 *  - Banner peringatan bahwa password tidak akan ditampilkan ulang
 *  - Confirm checkbox + tombol "Saya sudah catat" untuk tutup
 *  - Tampil sampai user tutup secara sadar (tidak auto-dismiss)
 */
import { useState } from "react";
import { Check, Copy, Download, AlertTriangle, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

export type CredentialItem = {
  label: string;
  value: string;
  /** true = nilai default tersembunyi (mata coret), bisa di-toggle; biasanya untuk password */
  secret?: boolean;
  /** ekstra info di bawah field */
  hint?: string;
};

type Props = {
  open: boolean;
  title?: string;
  description?: string;
  items: CredentialItem[];
  /** filename utk download .txt (tanpa ekstensi) */
  filenameBase?: string;
  /** dipanggil saat user klik tutup. Hanya bisa setelah user check konfirmasi (default: required). */
  onClose: () => void;
  /** Kalau true, abaikan checkbox konfirmasi (mis. saat dipakai utk view non-sensitif) */
  skipConfirm?: boolean;
};

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fallthrough ke fallback */
  }
  // Fallback untuk HTTP (akses via IP) yang tidak punya clipboard API.
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    ta.style.pointerEvents = "none";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

function formatAll(items: CredentialItem[], title?: string): string {
  const head = title ? `${title}\n${"-".repeat(title.length)}\n` : "";
  const body = items.map((i) => `${i.label}: ${i.value}`).join("\n");
  const ts = `\n\nDicetak: ${new Date().toLocaleString("id-ID")}`;
  return head + body + ts + "\n";
}

export default function CredentialDialog({
  open, title = "Kredensial Akun", description,
  items, filenameBase = "kredensial", onClose, skipConfirm = false,
}: Props) {
  const [confirmed, setConfirmed] = useState(false);
  if (!open) return null;
  const canClose = skipConfirm || confirmed;

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cred-title"
    >
      <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b">
          <div className="flex items-start gap-3">
            <div className="size-10 rounded-full bg-warning/15 text-warning grid place-items-center shrink-0">
              <AlertTriangle className="size-5" />
            </div>
            <div className="min-w-0">
              <h2 id="cred-title" className="text-lg font-semibold">{title}</h2>
              {description && (
                <p className="text-sm text-muted-fg mt-1">{description}</p>
              )}
            </div>
          </div>
          {!skipConfirm && (
            <div className="mt-4 rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs">
              <strong>Catat sekarang.</strong> Password tidak akan ditampilkan ulang.
              Setelah dialog ini ditutup, satu-satunya cara mendapat password baru
              adalah <em>reset password</em> oleh admin.
            </div>
          )}
        </div>

        <div className="p-5 space-y-3">
          {items.map((it, idx) => (
            <CredField key={idx} item={it} />
          ))}
        </div>

        <div className="p-5 pt-0 space-y-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={async () => {
                const ok = await copyToClipboard(formatAll(items, title));
                ok ? toast.success("Semua kredensial disalin.") : toast.error("Gagal menyalin.");
              }}
              className="btn-secondary"
            >
              <Copy className="size-4 mr-1.5" /> Salin Semua
            </button>
            <button
              type="button"
              onClick={() => {
                const text = formatAll(items, title);
                const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
                const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${filenameBase}-${ts}.txt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }}
              className="btn-secondary"
            >
              <Download className="size-4 mr-1.5" /> Unduh .txt
            </button>
          </div>

          {!skipConfirm && (
            <label className="flex items-start gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              <span>Saya sudah mencatat / menyalin / mengunduh kredensial di atas.</span>
            </label>
          )}

          <button
            type="button"
            disabled={!canClose}
            onClick={onClose}
            className={cn(
              "btn-primary w-full",
              !canClose && "opacity-50 cursor-not-allowed",
            )}
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}

function CredField({ item }: { item: CredentialItem }) {
  const [revealed, setRevealed] = useState(!item.secret);
  const [justCopied, setJustCopied] = useState(false);

  const display = revealed ? item.value : "•".repeat(Math.max(8, item.value.length));

  async function onCopy() {
    const ok = await copyToClipboard(item.value);
    if (ok) {
      setJustCopied(true);
      setTimeout(() => setJustCopied(false), 1500);
    } else {
      toast.error("Gagal menyalin.");
    }
  }

  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-fg mb-1">
        {item.label}
      </div>
      <div className="flex items-stretch gap-1.5">
        <input
          readOnly
          value={display}
          onFocus={(e) => e.currentTarget.select()}
          className="input font-mono text-sm flex-1 cursor-text"
        />
        {item.secret && (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            className="btn-secondary px-2.5"
            aria-label={revealed ? "Sembunyikan" : "Tampilkan"}
            title={revealed ? "Sembunyikan" : "Tampilkan"}
          >
            {revealed ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        )}
        <button
          type="button"
          onClick={onCopy}
          className="btn-secondary px-2.5"
          aria-label={`Salin ${item.label}`}
          title={`Salin ${item.label}`}
        >
          {justCopied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
        </button>
      </div>
      {item.hint && <p className="text-xs text-muted-fg mt-1">{item.hint}</p>}
    </div>
  );
}
