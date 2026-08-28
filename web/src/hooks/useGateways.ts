import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gatewayService } from "../services/channel.service";

export const useGateways = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["gateways"],
    queryFn: gatewayService.list,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      gatewayService.toggle(id, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gateways"] }),
  });

  return {
    gateways: query.data || [],
    isLoading: query.isLoading,
    toggleGateway: toggleMutation.mutateAsync,
    refetch: query.refetch,
  };
};
