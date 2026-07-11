import { describe, expect, it } from 'vitest'
import { dateKey, formatDateTime, recentCalendarDays } from './dateTime'

describe('saved-timezone date helpers', () => {
  it('treats offsetless API timestamps as UTC', () => {
    expect(
      formatDateTime('2026-01-15T12:00:00', 'America/New_York', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
    ).toBe('07:00')
  })

  it('falls back to UTC for missing or invalid IANA timezones', () => {
    const options: Intl.DateTimeFormatOptions = {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }
    expect(formatDateTime('2026-07-10T23:30:00Z', undefined, options)).toBe(
      formatDateTime('2026-07-10T23:30:00Z', 'UTC', options),
    )
    expect(formatDateTime('2026-07-10T23:30:00Z', 'Not/AZone', options)).toBe(
      formatDateTime('2026-07-10T23:30:00Z', 'UTC', options),
    )
  })

  it('creates local date keys correctly across DST boundaries', () => {
    expect(dateKey('2026-03-08T06:30:00Z', 'America/New_York')).toBe('2026-03-08')
    expect(dateKey('2026-03-08T04:30:00Z', 'America/New_York')).toBe('2026-03-07')
    expect(dateKey('not-a-date', 'America/New_York')).toBe('')
  })

  it('generates consecutive local calendar days across DST changes', () => {
    expect(
      recentCalendarDays(3, 'America/New_York', new Date('2026-03-09T01:00:00Z')).map(
        (day) => day.key,
      ),
    ).toEqual(['2026-03-06', '2026-03-07', '2026-03-08'])
  })
})
