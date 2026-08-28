export interface ScheduledTask {
  id: string;
  agent_name: string;
  cron_expr: string;
  job_type: string;
  payload: Record<string, any>;
  next_run: string | null;
  status: string;
}
