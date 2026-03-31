// LogRaven — useJobStatus polling (uses backend progress_stage for live pipeline)
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
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st && TERMINAL.includes(st)) return false
      return 2000
    },
  })

  const status = query.data?.status ?? 'queued'
  const progressStage = query.data?.progress_stage ?? null
  const files = query.data?.files ?? []
  const errorMessage = query.data?.error_message ?? null

  return {
    status,
    progressStage,
    errorMessage,
    files,
    isLoading: query.isLoading,
    isComplete: status === 'complete',
    isFailed: status === 'failed',
  }
}
