export interface GatewayChannel {
  id: string;
  platform: string;
  enabled: boolean;
  config: Record<string, any>;
}
