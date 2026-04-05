// LogRaven — useFileUpload Hook
// Handles file upload mutation.
// POST /api/v1/investigations/{id}/files (multipart + source_type)

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { investigationsApi } from '../api/investigations'
import type { InvestigationFile } from '../types/investigation'

interface UploadArgs {
  file: File
  sourceType: string
  ingestionMode?: 'parsers' | 'decoders'
}

export function useFileUpload(investigationId: string) {
  const queryClient = useQueryClient()

  const mutation = useMutation<InvestigationFile, Error, UploadArgs>({
    mutationFn: async ({ file, sourceType, ingestionMode = 'parsers' }) => {
      const res = await investigationsApi.uploadFile(investigationId, file, sourceType, ingestionMode)
      return res.data
    },
    onSuccess: () => {
      // Refresh investigation so the file list updates immediately
      queryClient.invalidateQueries({ queryKey: ['investigation', investigationId] })
    },
  })

  return {
    upload: (file: File, sourceType: string, ingestionMode: 'parsers' | 'decoders' = 'parsers') =>
      mutation.mutateAsync({ file, sourceType, ingestionMode }),
    isUploading: mutation.isPending,
    uploadError: mutation.error,
    reset: mutation.reset,
  }
}
