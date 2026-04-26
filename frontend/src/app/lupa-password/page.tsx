"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api/client";

export default function LupaPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api("/auth/forgot-password", {
        method: "POST",
        body: { email },
        auth: false,
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
      else toast.error("Tidak bisa terhubung ke server.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center px-6 py-10">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-bold mb-1">Lupa Password</h1>
        <p className="text-sm text-muted-fg mb-6">
          Masukkan email yang terdaftar. Kami akan kirim tautan reset (berlaku 30 menit).
        </p>

        {done ? (
          <div className="card p-6 space-y-4">
            <p className="text-sm">
              Jika email Anda terdaftar, tautan reset akan segera dikirim. Periksa kotak masuk
              (atau folder spam).
            </p>
            <Link href="/login" className="btn-primary w-full">
              Kembali ke Login
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="card p-6 space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={submitting}>
              {submitting ? "Memproses..." : "Kirim Tautan Reset"}
            </button>
            <div className="text-center text-sm">
              <Link href="/login" className="text-primary hover:underline">Kembali ke login</Link>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
