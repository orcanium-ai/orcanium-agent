export interface Agent {
  name: string;
  status: "running" | "paused" | "stopped" | "archived" | string;
  active_sessions: number;
  health: string;
  model_provider: string;
  model_name: string;
}

export interface AgentConfig {
  model_provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  auto_memory: boolean;
  auto_skill: string;
}

export interface Message {
  id?: string;
  session_id: string;
  sender: "user" | "agent" | "system" | string;
  content: string;
  timestamp?: string;
}
