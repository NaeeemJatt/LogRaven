const OFFSET_SUFFIX = /(?:Z|[+-]\d{2}:\d{2})$/i

function parseTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null
  const normalized =
    /T|\s/.test(value) && !OFFSET_SUFFIX.test(value) ? `${value}Z` : value
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function validTimeZone(timeZone?: string | null): string {
  if (!timeZone) return 'UTC'
  try {
    new Intl.DateTimeFormat('en-US', { timeZone }).format()
    return timeZone
  } catch {
    return 'UTC'
  }
}

export function formatDateTime(
  value: string | null | undefined,
  timeZone: string | null | undefined,
  options: Intl.DateTimeFormatOptions,
): string {
  const date = parseTimestamp(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat('en-US', {
    ...options,
    timeZone: validTimeZone(timeZone),
  }).format(date)
}

export function dateKey(
  value: string | Date | null | undefined,
  timeZone?: string | null,
): string {
  const date = value instanceof Date ? value : parseTimestamp(value)
  if (!date || Number.isNaN(date.getTime())) return ''
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: validTimeZone(timeZone),
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

export function recentCalendarDays(
  count: number,
  timeZone?: string | null,
  now = new Date(),
): { key: string; label: string }[] {
  const today = dateKey(now, timeZone)
  if (!today || count <= 0) return []
  const [year, month, day] = today.split('-').map(Number)
  const anchor = new Date(Date.UTC(year, month - 1, day, 12))
  return Array.from({ length: count }, (_, index) => {
    const calendarDate = new Date(anchor)
    calendarDate.setUTCDate(anchor.getUTCDate() - (count - 1 - index))
    return {
      key: calendarDate.toISOString().slice(0, 10),
      label: new Intl.DateTimeFormat('en-US', {
        timeZone: 'UTC',
        weekday: 'short',
      }).format(calendarDate),
    }
  })
}
