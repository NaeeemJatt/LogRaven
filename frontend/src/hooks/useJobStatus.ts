// LogRaven — useJobStatus Polling Hook
//
// PURPOSE:
//   Polls investigation status every 3 seconds until analysis is complete.
//   The most technically critical frontend hook.
//
// POLLING LOGIC:
//   React Query refetchInterval: 3000ms when status is NOT terminal
//   Terminal states: complete | failed -> refetchInterval becomes false (stops polling)
//
// RETURNS:
//   status: string (queued/parsing/rule_engine/correlation/ai_analysis/complete/failed)
//   progress_stage: string (for progress bar display)
//   report_id: string | null (available when complete)
//   files: InvestigationFile[] (with per-file status)
//   isLoading: boolean
//   error: Error | null
//
// TODO Month 1 Week 3: Implement.

export function useJobStatus(investigationId: string) {
  // TODO: implement with React Query, refetchInterval for polling
  return { status: 'queued', progress_stage: null, report_id: null, isLoading: true }
}
