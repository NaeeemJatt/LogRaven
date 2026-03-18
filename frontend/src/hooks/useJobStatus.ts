// LogRaven — useJobStatus Polling Hook
import { useQuery } from '@tanstack/react-query'
import { investigationsApi } from '../api/investigations'
import type { InvestigationStatus } from '../types/investigation'

const TERMINAL = ['complete', 'failed']

export function useJobStatus(investigationId: string | null) {
  const query = useQuery<InvestigationStatus>({
    queryKey: ['status', investigationId],
    queryFn: async () => {
      const res = await investigationsApi.getStatus(investigationId!)
      return res.data
    },
    enabled: investigationId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status && TERMINAL.includes(status)) return false
      return 3000
    },
  })

  const status = query.data?.status ?? 'queued'
  const files  = query.data?.files  ?? []

  return {
    status,
    files,
    isLoading:  query.isLoading,
    isComplete: status === 'complete',
    isFailed:   status === 'failed',
  }
}
