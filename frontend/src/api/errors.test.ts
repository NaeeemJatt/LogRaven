import { describe, expect, it } from 'vitest'
import { normalizeApiError } from './errors'

describe('normalizeApiError', () => {
  it('classifies upload tier limits with the accurate server message', () => {
    const result = normalizeApiError({
      response: {
        status: 413,
        data: { detail: 'File exceeds size limit for your tier. Max: 5 MB' },
      },
    })

    expect(result).toEqual({
      message: 'File exceeds size limit for your tier. Max: 5 MB',
      isPlanLimit: true,
    })
  })

  it('recognizes the real FILE_TOO_LARGE response contract', () => {
    expect(
      normalizeApiError({
        response: {
          status: 400,
          data: {
            error: 'File exceeds size limit for your tier. Max: 5 MB',
            code: 'FILE_TOO_LARGE',
          },
        },
      }),
    ).toEqual({
      message: 'File exceeds size limit for your tier. Max: 5 MB',
      isPlanLimit: true,
    })
  })

  it('classifies daily analysis quotas but not generic rate limits', () => {
    expect(
      normalizeApiError({
        response: {
          status: 429,
          data: { detail: 'Daily analysis limit reached for your plan.' },
        },
      }).isPlanLimit,
    ).toBe(true)
    expect(
      normalizeApiError({
        response: { status: 429, data: { detail: 'Too many requests.' } },
      }).isPlanLimit,
    ).toBe(false)
  })

  it('normalizes FastAPI validation arrays and safe fallbacks', () => {
    expect(
      normalizeApiError({
        response: {
          status: 422,
          data: { detail: [{ loc: ['body', 'name'], msg: 'Field required' }] },
        },
      }).message,
    ).toBe('body.name: Field required')
    expect(normalizeApiError(null, 'Upload failed.').message).toBe('Upload failed.')
  })
})
