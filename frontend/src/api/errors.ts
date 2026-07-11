interface ApiErrorResult {
  message: string
  isPlanLimit: boolean
}

function detailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return null
  const messages = detail.map((item) => {
    if (item && typeof item === 'object' && 'msg' in item) {
      const error = item as { loc?: unknown[]; msg: string }
      const location = Array.isArray(error.loc) ? error.loc.join('.') : ''
      return location ? `${location}: ${error.msg}` : error.msg
    }
    return String(item)
  })
  return messages.length ? messages.join('; ') : null
}

export function normalizeApiError(
  error: unknown,
  fallback = 'Request failed.',
): ApiErrorResult {
  const response =
    error && typeof error === 'object' && 'response' in error
      ? (error as {
          response?: {
            status?: number
            data?: { detail?: unknown; error?: unknown; code?: unknown }
          }
        })
          .response
      : undefined
  const message =
    detailMessage(response?.data?.detail) ||
    (typeof response?.data?.error === 'string' ? response.data.error : null) ||
    fallback
  const lower = message.toLowerCase()
  const code = typeof response?.data?.code === 'string' ? response.data.code : ''
  const isPlanLimit =
    code === 'FILE_TOO_LARGE' ||
    response?.status === 413 ||
    ((response?.status === 403 || response?.status === 429) &&
      /(plan|tier|subscription|daily analysis).*(limit|quota|requires)|requires.*(plan|tier|subscription)/i.test(
        lower,
      ))
  return { message, isPlanLimit }
}
