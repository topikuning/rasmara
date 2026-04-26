/**
 * Helper download file via fetch (auto-attach Bearer JWT).
 * Tag <a href="/api/..."> tidak otomatis kirim Authorization header,
 * jadi pakai fetch + Blob lalu trigger download programmatic.
 */
import { useAuthStore } from "@/lib/auth/store";

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "") + "/api/v1";

export async function downloadFile(
  path: string,
  fallbackFilename = "download",
): Promise<void> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const access = useAuthStore.getState().access;
  const res = await fetch(url, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
    credentials: "include",
  });
  if (!res.ok) {
    let msg = "Download gagal.";
    try {
      const j = await res.json();
      msg = j?.error?.message || msg;
    } catch {
      // not JSON
    }
    throw new Error(msg);
  }

  // Filename dari Content-Disposition jika ada
  const cd = res.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename="?([^"]+)"?/i);
  const filename = match ? match[1] : fallbackFilename;

  const blob = await res.blob();
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
}
