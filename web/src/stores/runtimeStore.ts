import { create } from "zustand";

interface RuntimeState {
  logs: string;
  setLogs: (logs: string) => void;
  appendLog: (line: string) => void;
}

export const useRuntimeStore = create<RuntimeState>((set) => ({
  logs: "Loading system logs...",
  setLogs: (logs) => set({ logs }),
  appendLog: (line) => set((state) => ({ logs: `${state.logs}\n${line}` })),
}));
