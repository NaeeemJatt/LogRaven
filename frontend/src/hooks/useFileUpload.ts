// LogRaven — useFileUpload Hook
// Handles file upload mutation.
// POST /api/v1/investigations/{id}/files (multipart + source_type)
// Returns: { upload, isUploading, error }
// TODO Month 1 Week 3: Implement.

export function useFileUpload(_investigationId: string) {
  // TODO: implement with React Query useMutation
  return { upload: async () => {}, isUploading: false, error: null }
}
