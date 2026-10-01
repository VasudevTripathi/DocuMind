import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/documentService';

export const useDocuments = () => {
  const queryClient = useQueryClient();

  const {
    data: documents = [],
    isLoading,
    isError,
    error,
    refetch
  } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentService.getDocuments(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Keep all components synchronized when document storage changes
  useEffect(() => {
    const unsubscribe = documentService.subscribe(() => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    });
    return unsubscribe;
  }, [queryClient]);

  const saveMutation = useMutation({
    mutationFn: (document) => documentService.saveDocument(document),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => documentService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  const clearMutation = useMutation({
    mutationFn: () => documentService.clearDocuments(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  const resetMutation = useMutation({
    mutationFn: () => documentService.resetToInitial(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  return {
    documents,
    isLoading,
    isError,
    error,
    refetch,
    saveDocument: saveMutation.mutateAsync,
    deleteDocument: deleteMutation.mutateAsync,
    clearDocuments: clearMutation.mutateAsync,
    resetToInitial: resetMutation.mutateAsync,
    isSaving: saveMutation.isPending,
    isDeleting: deleteMutation.isPending
  };
};
