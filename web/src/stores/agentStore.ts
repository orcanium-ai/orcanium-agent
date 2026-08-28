import { create } from "zustand";
import { Agent, AgentConfig, Message } from "../types/agent";

interface AgentState {
  selectedAgent: Agent | null;
  agentTab:
    | "identity"
    | "skills"
    | "memory"
    | "knowledge"
    | "tasks"
    | "channels"
    | "chat";
  agentSoul: string;
  agentSkill: string;
  agentMemory: string;
  agentConfig: AgentConfig | null;
  chatMessages: Message[];
  inputMessage: string;
  chatLoading: boolean;

  setSelectedAgent: (agent: Agent | null) => void;
  setAgentTab: (
    tab:
      | "identity"
      | "skills"
      | "memory"
      | "knowledge"
      | "tasks"
      | "channels"
      | "chat",
  ) => void;
  setAgentSoul: (soul: string) => void;
  setAgentSkill: (skill: string) => void;
  setAgentMemory: (memory: string) => void;
  setAgentConfig: (config: AgentConfig | null) => void;
  setChatMessages: (messages: Message[]) => void;
  setInputMessage: (msg: string) => void;
  setChatLoading: (loading: boolean) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  selectedAgent: null,
  agentTab: "identity",
  agentSoul: "",
  agentSkill: "",
  agentMemory: "",
  agentConfig: null,
  chatMessages: [],
  inputMessage: "",
  chatLoading: false,

  setSelectedAgent: (selectedAgent) => set({ selectedAgent }),
  setAgentTab: (agentTab) => set({ agentTab }),
  setAgentSoul: (agentSoul) => set({ agentSoul }),
  setAgentSkill: (agentSkill) => set({ agentSkill }),
  setAgentMemory: (agentMemory) => set({ agentMemory }),
  setAgentConfig: (agentConfig) => set({ agentConfig }),
  setChatMessages: (chatMessages) => set({ chatMessages }),
  setInputMessage: (inputMessage) => set({ inputMessage }),
  setChatLoading: (chatLoading) => set({ chatLoading }),
}));
