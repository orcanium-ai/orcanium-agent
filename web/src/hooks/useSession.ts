import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sessionService } from "../services/session.service";

export const useSessions = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["sessions"],
    queryFn: () => sessionService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => sessionService.delete(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });

  return {
    sessions: query.data || [],
    isLoading: query.isLoading,
    deleteSession: deleteMutation.mutateAsync,
    refetch: query.refetch,
  };
};

export const useSession = (sessionId?: string) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: () => (sessionId ? sessionService.getMessages(sessionId) : []),
    enabled: !!sessionId,
  });

  const sendMutation = useMutation({
    mutationFn: ({
      sessionId,
      agentName,
      message,
    }: {
      sessionId: string;
      agentName: string;
      message: string;
    }) => sessionService.sendMessage(sessionId, agentName, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  const createMutation = useMutation({
    mutationFn: ({ agentName, title }: { agentName: string; title?: string }) =>
      sessionService.create(agentName, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  return {
    messages: query.data || [],
    isLoading: query.isLoading,
    sendMessage: sendMutation.mutateAsync,
    createSession: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    refetch: query.refetch,
  };
};
