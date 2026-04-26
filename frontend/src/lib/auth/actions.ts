"use client";

import { api, ApiError } from "@/lib/api/client";
import { useAuthStore, type Me } from "@/lib/auth/store";

export async function login(username: string, password: string) {
  const data = await api<{
    access: string;
    refresh: string;
    user: Me;
    must_change_password: boolean;
  }>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  useAuthStore.getState().setTokens(data.access, data.refresh);
  useAuthStore.getState().setMe(data.user);
  return data;
}

export async function fetchMe(): Promise<Me> {
  const me = await api<Me>("/auth/me");
  useAuthStore.getState().setMe(me);
  return me;
}

export async function logout() {
  const { refresh } = useAuthStore.getState();
  try {
    if (refresh) {
      await api("/auth/logout", { method: "POST", body: { refresh } });
    }
  } catch (e) {
    // tetap clear lokal walau backend error
    if (!(e instanceof ApiError)) console.error(e);
  } finally {
    useAuthStore.getState().clear();
  }
}

export async function changePassword(currentPassword: string | null, newPassword: string) {
  return api("/auth/change-password", {
    method: "POST",
    body: {
      current_password: currentPassword ?? "",
      new_password: newPassword,
    },
  });
}
