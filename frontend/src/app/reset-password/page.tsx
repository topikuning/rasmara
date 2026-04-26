"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api/client";

function ResetForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const uid = sp.get("uid") || "";
  const token = sp.get("token") || "";
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== confirm) {
      toast.error("Password tidak sama.");
      return;
    }
    setSubmitting(true);
    try {
      await api("/auth/reset-password", {
        method: "POST",
        body: { uid, token, new_password: next },
        auth: false,
      });
      toast.success("Password berhasil di-reset.");
      router.replace("/login");
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
      else toast.error("Tidak bisa terhubung ke server.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!uid || !token) {
    return (
      <div className="card p-6">
        <p className="text-sm text-danger">Tautan tidak valid.</p>
        <Link href="/login" className="btn-primary w-full mt-4">Kembali ke Login</Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="card p-6 space-y-4">
      <div>
        <label className="label">Password baru</label>
        <input
          className="input" type="password" required minLength={8}
          value={next} onChange={(e) => setNext(e.target.value)}
          disabled={submitting}
        />
      </div>
      <div>
        <label className="label">Konfirmasi password baru</label>
        <input
          className="input" type="password" required minLength={8}
          value={confirm} onChange={(e) => setConfirm(e.target.value)}
          disabled={submitting}
        />
      </div>
      <button className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Memproses..." : "Reset Password"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="min-h-screen grid place-items-center px-6 py-10">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6">Reset Password</h1>
        <Suspense fallback={<div className="card p-6">Memuat...</div>}>
          <ResetForm />
        </Suspense>
      </div>
    </main>
  );
}
