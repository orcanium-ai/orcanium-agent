import { API_BASE } from "./api";

export interface AuthStatus {
  setup_complete: boolean;
  authenticated: boolean;
  user?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

const AUTH_BASE = API_BASE;

export const authService = {
  /** GET /api/v1/auth/setup — check if admin password is configured */
  checkSetup: async (): Promise<AuthStatus | null> => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/setup`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  /** POST /api/v1/auth/setup — set initial admin password */
  setup: async (password: string): Promise<TokenResponse | null> => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  /** POST /api/v1/auth/login — authenticate with password */
  login: async (password: string): Promise<TokenResponse | null> => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  /** POST /api/v1/auth/logout — invalidate session token */
  logout: async (token: string): Promise<boolean> => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok;
    } catch {
      return false;
    }
  },

  /** GET /api/v1/auth/status — check current auth state */
  status: async (token: string | null): Promise<AuthStatus | null> => {
    try {
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const res = await fetch(`${AUTH_BASE}/auth/status`, { headers });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  /** GET /api/v1/auth/check — verify token is still valid */
  checkAuth: async (token: string): Promise<boolean> => {
    try {
      const res = await fetch(`${AUTH_BASE}/auth/check`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok;
    } catch {
      return false;
    }
  },
};
