// LogRaven — useReport Hook
// Fetches full report with all findings from GET /api/v1/reports/{id}
// TODO Month 4 Week 1: Implement.

export function useReport(_reportId: string) {
  return { report: null, isLoading: true, error: null }
}
