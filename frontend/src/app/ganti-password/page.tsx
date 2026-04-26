"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { changePassword, fetchMe } from "@/lib/auth/actions";
import { useAuthStore } from "@/lib/auth/store";
import { ApiError } from "@/lib/api/client";

export default function GantiPasswordPage() {
  const router = useRouter();
  const { me, hydrated } = useAuthStore();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    if (!useAuthStore.getState().access) {
      router.replace("/login");
    }
  }, [hydrated, router]);

  const isForce = !!me?.must_change_password;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== confirm) {
      toast.error("Password baru dan konfirmasi tidak sama.");
      return;
    }
    if (next.length < 8) {
      toast.error("Password minimal 8 karakter.");
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(isForce ? null : current, next);
      await fetchMe();
      toast.success("Password berhasil diganti.");
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) toast.error(err.message);
      else toast.error("Gagal mengganti password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center px-6 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Ganti Password</h1>
          {isForce && (
            <p className="text-sm text-warning mt-2">
              Anda diwajibkan mengganti password sebelum melanjutkan.
            </p>
          )}
        </div>

        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          {!isForce && (
            <div>
              <label className="label">Password saat ini</label>
              <input
                className="input"
                type="password"
                required
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                disabled={submitting}
              />
            </div>
          )}
          <div>
            <label className="label">Password baru</label>
            <input
              className="input"
              type="password"
              required
              minLength={8}
              value={next}
              onChange={(e) => setNext(e.target.value)}
              disabled={submitting}
            />
            <p className="text-xs text-muted-fg mt-1">Minimal 8 karakter.</p>
          </div>
          <div>
            <label className="label">Konfirmasi password baru</label>
            <input
              className="input"
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={submitting}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? "Memproses..." : "Simpan Password"}
          </button>
        </form>
      </div>
    </main>
  );
}
