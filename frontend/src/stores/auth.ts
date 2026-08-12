import { create } from "zustand";

import { fetchCurrentUser, login as loginRequest, type CurrentUser } from "@/api/auth";
import { getToken, setToken } from "@/api/client";

type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  user: CurrentUser | null;
  status: AuthStatus;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  // 应用启动时用已存令牌换取当前用户；令牌失效则清理，避免"看似登录实则 401"。
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",

  login: async (username, password) => {
    const token = await loginRequest(username, password);
    setToken(token.access_token);
    const user = await fetchCurrentUser();
    set({ user, status: "authenticated" });
  },

  logout: () => {
    setToken(null);
    set({ user: null, status: "unauthenticated" });
  },

  hydrate: async () => {
    if (!getToken()) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await fetchCurrentUser();
      set({ user, status: "authenticated" });
    } catch {
      setToken(null);
      set({ user: null, status: "unauthenticated" });
    }
  },
}));
