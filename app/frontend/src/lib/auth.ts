import { create } from "zustand";
import { authApi } from "./api";
import { api } from "./api";

interface User {
  id: string;
  email: string;
  full_name: string;
  workspace_id: string;
  is_active: boolean;
}

interface AuthStore {
  user: User | null;
  token: string | null;
  _hasHydrated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  hydrate: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  // Initialize as null always — never read localStorage here.
  // localStorage is only available in the browser, but this store initializer
  // runs on the server during SSR too. Reading it here causes React #418
  // because server (null) and client (stored token) produce different HTML.
  token: null,
  _hasHydrated: false,
  isLoading: false,

  hydrate: () => {
    if (typeof window === "undefined") {
      set({ _hasHydrated: true });
      return;
    }
    const token = localStorage.getItem("access_token");
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }
    set({ token: token ?? null, _hasHydrated: true });
  },

  login: async (email, password) => {
    set({ isLoading: true });
    const res = await authApi.login(email, password);
    const { access_token } = res.data;
    localStorage.setItem("access_token", access_token);
    api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    const meRes = await authApi.me();
    set({ token: access_token, user: meRes.data, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    delete api.defaults.headers.common["Authorization"];
    set({ user: null, token: null });
  },

  loadUser: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    try {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      const res = await authApi.me();
      set({ user: res.data, token });
    } catch {
      localStorage.removeItem("access_token");
      set({ user: null, token: null });
    }
  },
}));
