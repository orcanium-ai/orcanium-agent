import { useQuery, useMutation } from "@tanstack/react-query";
import { agentService } from "../services/agent.service";

export const useAgents = () => {
  const query = useQuery({
    queryKey: ["agents"],
    queryFn: agentService.list,
  });

  const createMutation = useMutation({
    mutationFn: (data: {
      name: string;
      soul?: string;
      provider?: string;
      model?: string;
    }) =>
      agentService.create({
        name: data.name,
        soul: data.soul,
        model_provider: data.provider,
        model_name: data.model,
      }),
    onSuccess: () => query.refetch(),
  });

  const statusMutation = useMutation({
    mutationFn: ({ name, action }: { name: string; action: string }) =>
      agentService.updateStatus(name, action),
    onSuccess: () => query.refetch(),
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => agentService.delete(name),
    onSuccess: () => query.refetch(),
  });

  return {
    agents: query.data || [],
    isLoading: query.isLoading,
    createAgent: createMutation.mutateAsync,
    updateStatus: statusMutation.mutateAsync,
    deleteAgent: deleteMutation.mutateAsync,
    refetch: query.refetch,
  };
};
