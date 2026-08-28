import { create } from "zustand";

interface UIState {
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Modals
  isCreateAgentOpen: boolean;
  setIsCreateAgentOpen: (open: boolean) => void;
  newAgentName: string;
  setNewAgentName: (name: string) => void;
  newAgentModel: string;
  setNewAgentModel: (model: string) => void;
  newAgentProvider: string;
  setNewAgentProvider: (provider: string) => void;

  isCreateTaskOpen: boolean;
  setIsCreateTaskOpen: (open: boolean) => void;
  taskCron: string;
  setTaskCron: (cron: string) => void;
  taskJobType: string;
  setTaskJobType: (jobType: string) => void;

  // Keys Provider sub-tab and editing state
  keysActiveSubTab: string;
  setKeysActiveSubTab: (subTab: string) => void;
  editingProviderId: string | null;
  setEditingProviderId: (id: string | null) => void;
  editingProviderValue: string;
  setEditingProviderValue: (val: string) => void;
  validatingProviderId: string | null;
  setValidatingProviderId: (id: string | null) => void;

  // Knowledge uploads
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  searchingKB: boolean;
  setSearchingKB: (searching: boolean) => void;
  kbUploadFile: File | null;
  setKbUploadFile: (file: File | null) => void;
  kbUploadType: string;
  setKbUploadType: (type: string) => void;
  uploadStatus: string | null;
  setUploadStatus: (status: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: "agents",
  setActiveTab: (activeTab) => set({ activeTab }),

  isCreateAgentOpen: false,
  setIsCreateAgentOpen: (isCreateAgentOpen) => set({ isCreateAgentOpen }),
  newAgentName: "",
  setNewAgentName: (newAgentName) => set({ newAgentName }),
  newAgentModel: "gpt-4-turbo",
  setNewAgentModel: (newAgentModel) => set({ newAgentModel }),
  newAgentProvider: "openai",
  setNewAgentProvider: (newAgentProvider) => set({ newAgentProvider }),

  isCreateTaskOpen: false,
  setIsCreateTaskOpen: (isCreateTaskOpen) => set({ isCreateTaskOpen }),
  taskCron: "0 * * * *",
  setTaskCron: (taskCron) => set({ taskCron }),
  taskJobType: "run_agent",
  setTaskJobType: (taskJobType) => set({ taskJobType }),

  keysActiveSubTab: "providers",
  setKeysActiveSubTab: (keysActiveSubTab) => set({ keysActiveSubTab }),
  editingProviderId: null,
  setEditingProviderId: (editingProviderId) => set({ editingProviderId }),
  editingProviderValue: "",
  setEditingProviderValue: (editingProviderValue) => set({ editingProviderValue }),
  validatingProviderId: null,
  setValidatingProviderId: (validatingProviderId) => set({ validatingProviderId }),

  searchQuery: "",
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  searchingKB: false,
  setSearchingKB: (searchingKB) => set({ searchingKB }),
  kbUploadFile: null,
  setKbUploadFile: (kbUploadFile) => set({ kbUploadFile }),
  kbUploadType: "md",
  setKbUploadType: (kbUploadType) => set({ kbUploadType }),
  uploadStatus: null,
  setUploadStatus: (uploadStatus) => set({ uploadStatus }),
}));
