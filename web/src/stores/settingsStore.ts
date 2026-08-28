import { create } from "zustand";

interface SettingsState {
  apiBase: string;
  theme: "slate" | "violet" | "emerald" | "amber";
  setApiBase: (url: string) => void;
  setTheme: (theme: "slate" | "violet" | "emerald" | "amber") => void;
}

const DEFAULT_API_BASE = "http://localhost:8000/api/v1";

export const useSettingsStore = create<SettingsState>((set) => ({
  apiBase: localStorage.getItem("orcanium_api_base") || DEFAULT_API_BASE,
  theme: (localStorage.getItem("orcanium_theme") as any) || "slate",
  setApiBase: (url) => {
    localStorage.setItem("orcanium_api_base", url);
    set({ apiBase: url });
  },
  setTheme: (theme) => {
    localStorage.setItem("orcanium_theme", theme);
    set({ theme });
  },
}));
