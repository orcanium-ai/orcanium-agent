export interface ModelProvider {
  provider_id: string;
  provider_name: string;
  type: string;
  env_var: string;
  configured: boolean;
  masked_value: string;
  enabled: boolean;
  status: string;
  last_checked: string | null;
}
