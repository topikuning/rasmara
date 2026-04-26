/**
 * Zustand store: auth state (access, refresh, user profile).
 * Persist ke localStorage supaya reload tidak logout.
 */
"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type MenuNode = {
  id: string;
  code: string;
  label: string;
  icon?: string;
  route?: string;
  order: number;
  children?: MenuNode[];
};

export type Me = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  phone: string;
  role_code: string | null;
  role_name: string | null;
  assigned_contract_ids: string[] | null;
  must_change_password: boolean;
  is_superuser: boolean;
  is_active: boolean;
  permission_codes: string[];
  menu_tree: MenuNode[];
};

type AuthState = {
  access: string | null;
  refresh: string | null;
  me: Me | null;
  hydrated: boolean;
  setTokens: (access: string | null, refresh: string | null) => void;
  setMe: (me: Me | null) => void;
  clear: () => void;
  hasPerm: (code: string) => boolean;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      access: null,
      refresh: null,
      me: null,
      hydrated: false,
      setTokens: (access, refresh) => set({ access, refresh }),
      setMe: (me) => set({ me }),
      clear: () => set({ access: null, refresh: null, me: null }),
      hasPerm: (code) => {
        const me = get().me;
        if (!me) return false;
        if (me.is_superuser) return true;
        return me.permission_codes.includes(code);
      },
    }),
    {
      name: "rasmara-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ access: s.access, refresh: s.refresh, me: s.me }),
      onRehydrateStorage: () => (state) => {
        if (state) state.hydrated = true;
      },
    },
  ),
);
