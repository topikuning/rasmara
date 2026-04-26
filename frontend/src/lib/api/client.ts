/**
 * Fetch wrapper untuk API RASMARA.
 *
 * - Default base path: relatif "/api/v1" (Caddy/Next.js rewrite handle proxy ke backend)
 * - Auto attach Bearer token dari authStore
 * - Auto refresh saat 401 (sekali)
 * - Format error standar { error: { code, message, details } }
 */
import { useAuthStore } from "@/lib/auth/store";

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "") + "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Body bisa berupa:
//   - object (akan di-JSON.stringify),
//   - FormData (untuk upload file, header Content-Type otomatis),
//   - string (kirim apa adanya),
//   - null / undefined (no body).
// Kita pakai Omit<RequestInit, 'body'> supaya TS tidak menahan kita ke
// BodyInit dari fetch native — kita handle serialisasi sendiri di rawFetch.
type FetchOpts = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
};

async function rawFetch(path: string, opts: FetchOpts = {}, token?: string | null): Promise<Response> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers = new Headers(opts.headers as HeadersInit);
  const isFormData = typeof FormData !== "undefined" && opts.body instanceof FormData;
  if (!isFormData && opts.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (token && opts.auth !== false) headers.set("Authorization", `Bearer ${token}`);

  // Pisahkan body custom dari opts sebelum spread ke RequestInit
  const { body, auth: _auth, ...restOpts } = opts;
  let nativeBody: BodyInit | null | undefined;
  if (body === undefined || body === null) {
    nativeBody = undefined;
  } else if (isFormData || typeof body === "string" || body instanceof Blob
              || body instanceof ArrayBuffer || body instanceof URLSearchParams) {
    nativeBody = body as BodyInit;
  } else {
    nativeBody = JSON.stringify(body);
  }

  return fetch(url, {
    ...restOpts,
    headers,
    body: nativeBody,
    cache: "no-store",
    credentials: "include",
  });
}

async function refreshAccess(): Promise<string | null> {
  const { refresh, setTokens, clear } = useAuthStore.getState();
  if (!refresh) return null;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      clear();
      return null;
    }
    const data = await res.json();
    setTokens(data.access, data.refresh ?? refresh);
    return data.access;
  } catch {
    clear();
    return null;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let payload: any = null;
  try {
    payload = await res.json();
  } catch {
    /* noop */
  }
  const err = payload?.error ?? {};
  return new ApiError(
    res.status,
    err.code ?? "ERROR",
    err.message ?? res.statusText ?? "Terjadi kesalahan.",
    err.details,
  );
}

export async function api<T = any>(path: string, opts: FetchOpts = {}): Promise<T> {
  const { access } = useAuthStore.getState();
  let res = await rawFetch(path, opts, access);

  if (res.status === 401 && opts.auth !== false) {
    const newAccess = await refreshAccess();
    if (newAccess) {
      res = await rawFetch(path, opts, newAccess);
    }
  }

  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("Content-Type") ?? "";
  if (ct.includes("application/json")) return res.json() as Promise<T>;
  return res.text() as unknown as Promise<T>;
}

// Helper SWR fetcher
export const swrFetcher = (path: string) => api(path);
