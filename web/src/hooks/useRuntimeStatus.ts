import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { systemService } from "../services/system.service";
import { useRuntimeStore } from "../stores/runtimeStore";

export function useRuntimeStatus(lines = 100) {
  const { logs, setLogs } = useRuntimeStore();

  // Query for system logs — polls every 10s
  const { data: logsData } = useQuery({
    queryKey: ["logs", lines],
    queryFn: () => systemService.getLogs(lines),
    refetchInterval: 10000,
  });

  // Sync logs to store
  useEffect(() => {
    if (logsData) {
      setLogs(logsData.logs);
    }
  }, [logsData, setLogs]);

  return { logs };
}
