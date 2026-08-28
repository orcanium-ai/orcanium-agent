import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authService, type AuthStatus } from "../services/auth.service";

interface AuthContextValue {
  /** True while the auth status check is in flight */
  loading: boolean;
  /** Current auth status, or null if not yet determined */
  status: AuthStatus | null;
  /** The stored Bearer token, or null */
  token: string | null;
  /** Try to log in with a password.  Returns true on success. */
  login: (password: string) => Promise<boolean>;
  /** Perform first-time setup.  Returns true on success. */
  setup: (password: string) => Promise<boolean>;
  /** Log out and clear stored token. */
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_STORAGE_KEY = "orcanium_auth_token";

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string | null) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // localStorage may be unavailable
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());

  // On mount, check if we have a stored token and if it's valid
  useEffect(() => {
    (async () => {
      try {
        const stored = getStoredToken();
        // Use the stored token (if any) to check auth status
        const s = await authService.status(stored);
        if (s) {
          setStatus(s);
          if (!s.authenticated) {
            // Token is invalid/expired — clear it
            storeToken(null);
            setToken(null);
          }
        } else {
          // Backend unreachable — allow access (dev mode fallback)
          setStatus({ setup_complete: false, authenticated: false });
        }
      } catch {
        setStatus({ setup_complete: false, authenticated: false });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (password: string): Promise<boolean> => {
    const res = await authService.login(password);
    if (res) {
      storeToken(res.access_token);
      setToken(res.access_token);
      setStatus({ setup_complete: true, authenticated: true, user: "admin" });
      return true;
    }
    return false;
  }, []);

  const setup = useCallback(async (password: string): Promise<boolean> => {
    const res = await authService.setup(password);
    if (res) {
      storeToken(res.access_token);
      setToken(res.access_token);
      setStatus({ setup_complete: true, authenticated: true, user: "admin" });
      return true;
    }
    return false;
  }, []);

  const logout = useCallback(async () => {
    if (token) {
      await authService.logout(token);
    }
    storeToken(null);
    setToken(null);
    setStatus({ setup_complete: true, authenticated: false });
  }, [token]);

  return (
    <AuthContext.Provider value={{ loading, status, token, login, setup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
