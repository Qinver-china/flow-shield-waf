import { defineStore } from "pinia";
import { api, clearSession, setTokens } from "@/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem("waf_access_token") || "",
    username: localStorage.getItem("waf_username") || "",
  }),
  getters: {
    isLoggedIn: (s) => !!s.accessToken,
  },
  actions: {
    async login(username: string, password: string) {
      const resp = await api.post<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/login",
        { username, password },
      );
      this.setSession(username, resp.data.access_token, resp.data.refresh_token);
    },
    setSession(username: string, accessToken: string, refreshToken?: string) {
      this.accessToken = accessToken;
      this.username = username;
      setTokens(accessToken, refreshToken);
      localStorage.setItem("waf_username", username);
    },
    async refreshSession() {
      const { refreshAccessToken } = await import("@/api");
      const accessToken = await refreshAccessToken();
      this.accessToken = accessToken;
      return accessToken;
    },
    async fetchProfile() {
      const resp = await api.get<{ username: string }>("/api/v1/auth/me");
      this.username = resp.data.username;
      localStorage.setItem("waf_username", resp.data.username);
      return resp.data;
    },
    async changeUsername(currentPassword: string, newUsername: string) {
      const resp = await api.put<{
        username: string;
        access_token: string;
        refresh_token: string;
      }>("/api/v1/auth/username", {
        current_password: currentPassword,
        new_username: newUsername,
      });
      this.setSession(resp.data.username, resp.data.access_token, resp.data.refresh_token);
      return resp.data;
    },
    async changePassword(currentPassword: string, newPassword: string) {
      await api.put("/api/v1/auth/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
    },
    logout() {
      this.accessToken = "";
      this.username = "";
      clearSession();
    },
  },
});
