import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { taskService } from "../services/task.service";

export const useTasks = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["tasks"],
    queryFn: taskService.list,
  });

  const createMutation = useMutation({
    mutationFn: taskService.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({
      taskId,
      status,
    }: {
      taskId: string;
      status: "active" | "paused";
    }) => taskService.toggle(taskId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: taskService.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  return {
    tasks: query.data || [],
    isLoading: query.isLoading,
    createTask: createMutation.mutateAsync,
    toggleTask: toggleMutation.mutateAsync,
    deleteTask: deleteMutation.mutateAsync,
    refetch: query.refetch,
  };
};
