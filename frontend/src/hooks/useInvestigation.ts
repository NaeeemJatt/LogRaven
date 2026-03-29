// LogRaven — useInvestigation Hook
// Fetches a single investigation with file list.
// GET /api/v1/investigations/{id}

import { useQuery } from '@tanstack/react-query'
import { investigationsApi } from '../api/investigations'
import type { Investigation } from '../types/investigation'

export function useInvestigation(id: string | null | undefined) {
  const { data: investigation, isLoading, error } = useQuery<Investigation>({
    queryKey: ['investigation', id],
    queryFn: async () => {
      const res = await investigationsApi.get(id!)
      return res.data
    },
    enabled: !!id,
  })

  return {
    investigation: investigation ?? null,
    isLoading,
    error: error ?? null,
  }
}
