// LogRaven — useReport Hook
// Fetches a full report by its report UUID from GET /api/v1/reports/{id}
// Use this when you have the report's own ID (not the investigation ID).
// For investigation-scoped report access, use investigationsApi.getReport(investigationId).

import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '../api/reports'
import type { Report } from '../types/report'

export function useReport(reportId: string | null | undefined) {
  const { data: report, isLoading, error } = useQuery<Report>({
    queryKey: ['report', reportId],
    queryFn: async () => {
      const res = await reportsApi.get(reportId!)
      return res.data
    },
    enabled: !!reportId,
  })

  return {
    report: report ?? null,
    isLoading,
    error: error ?? null,
  }
}
