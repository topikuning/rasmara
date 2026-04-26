"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { LogIn, Eye, EyeOff } from "lucide-react";

import { login } from "@/lib/auth/actions";
import { ApiError } from "@/lib/api/client";

// Disable prerender — halaman ini client-only (pakai useSearchParams + auth state).
export const dynamic = "force-dynamic";

function LoginForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const next = sp.get("next") || "/dashboard";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await login(username.trim(), password);
      if (res.must_change_password) {
        toast.info("Anda wajib mengganti password sebelum melanjutkan.");
        router.replace("/ganti-password");
      } else {
        toast.success(`Selamat datang, ${res.user.full_name || res.user.username}.`);
        router.replace(next);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message || "Login gagal.");
      } else {
        toast.error("Tidak bisa terhubung ke server.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card p-6 space-y-4">
      <div>
        <label className="label" htmlFor="username">Username</label>
        <input
          id="username"
          className="input"
          autoComplete="username"
          autoFocus
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={submitting}
        />
      </div>
      <div>
        <label className="label" htmlFor="password">Password</label>
        <div className="relative">
          <input
            id="password"
            className="input pr-10"
            type={showPwd ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={submitting}
          />
          <button
            type="button"
            onClick={() => setShowPwd((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-muted-fg hover:text-fg"
            aria-label={showPwd ? "Sembunyikan password" : "Tampilkan password"}
          >
            {showPwd ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      </div>

      <button type="submit" className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Memproses..." : (
          <span className="inline-flex items-center gap-2">
            <LogIn className="size-4" /> Masuk
          </span>
        )}
      </button>

      <div className="text-sm text-center">
        <Link href="/lupa-password" className="text-primary hover:underline">
          Lupa password?
        </Link>
      </div>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-screen grid place-items-center px-6 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">RASMARA</h1>
          <p className="text-sm text-muted-fg mt-1">Masuk ke sistem monitoring kontrak.</p>
        </div>
        <Suspense fallback={<div className="card p-6 text-center text-muted-fg">Memuat...</div>}>
          <LoginForm />
        </Suspense>
        <p className="mt-6 text-center text-xs text-muted-fg">
          <Link href="/" className="hover:underline">Kembali ke beranda</Link>
        </p>
      </div>
    </main>
  );
}
