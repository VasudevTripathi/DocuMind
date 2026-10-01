import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentService } from '../services/documentService';

export const useDocuments = (params) => {
  const queryClient = useQueryClient();

  const {
    data: documents = [],
    isLoading,
    isError,
    error,
    refetch
  } = useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentService.getDocuments(params),
    staleTime: 1000 * 15,
    retry: 1,
    // Dynamically poll every 2s while any document is pending or processing
    refetchInterval: (query) => {
      const docs = query.state.data;
      if (Array.isArray(docs)) {
        const hasActiveJobs = docs.some(d => {
          const st = (d.status || '').toLowerCase();
          return st === 'pending' || st === 'processing';
        });
        if (hasActiveJobs) {
          return 2000;
        }
      }
      return false;
    }
  });

  // Keep all components synchronized when document storage changes
  useEffect(() => {
    const unsubscribe = documentService.subscribe(() => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    });
    return unsubscribe;
  }, [queryClient]);

  const uploadMutation = useMutation({
    mutationFn: ({ file, category }) => documentService.uploadDocument(file, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  });

  const saveMutation = useMutation({
    mutationFn: (param) => {
      if (param instanceof File) {
        return documentService.uploadDocument(param);
      }
      if (param?.file instanceof File) {
        return documentService.uploadDocument(param.file, param.category);
      }
      return documentService.saveDocument(param);
    },
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

  const processMutation = useMutation({
    mutationFn: (id) => documentService.processDocument(id),
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

  return {
    documents,
    isLoading,
    isError,
    error,
    refetch,
    uploadDocument: (file, category) => uploadMutation.mutateAsync({ file, category }),
    saveDocument: saveMutation.mutateAsync,
    deleteDocument: deleteMutation.mutateAsync,
    processDocument: processMutation.mutateAsync,
    clearDocuments: clearMutation.mutateAsync,
    isSaving: saveMutation.isPending || uploadMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isProcessing: processMutation.isPending
  };
};

export const useDocumentAnalysis = (documentId) => {
  return useQuery({
    queryKey: ['document-analysis', documentId],
    queryFn: () => documentService.getDocumentAnalysis(documentId),
    enabled: Boolean(documentId),
    retry: 1
  });
};
