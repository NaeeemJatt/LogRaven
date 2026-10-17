import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { investigationsApi } from '../api/investigations'
import type { InvestigationStatus } from '../types/investigation'
import { useJobStatus } from './useJobStatus'

const { useQueryMock } = vi.hoisted(() => ({
  useQueryMock: vi.fn(),
}))

vi.mock('@tanstack/react-query', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@tanstack/react-query')>()),
  useQuery: useQueryMock,
}))

vi.mock('../api/investigations', () => ({
  investigationsApi: {
    getStatus: vi.fn(),
  },
}))

const processing: InvestigationStatus = {
  id: 'investigation-1',
  status: 'processing',
  progress_stage: 'parsing',
  error_message: null,
  files: [],
}

describe('useJobStatus', () => {
  beforeEach(() => {
    useQueryMock.mockReset()
    vi.mocked(investigationsApi.getStatus).mockReset()
    useQueryMock.mockReturnValue({
      data: processing,
      isLoading: false,
      isError: false,
    })
  })

  it('polls active jobs every two seconds and stops at terminal states', async () => {
    vi.mocked(investigationsApi.getStatus).mockResolvedValue({ data: processing } as Awaited<
      ReturnType<typeof investigationsApi.getStatus>
    >)

    const { result } = renderHook(() => useJobStatus('investigation-1'))
    const options = useQueryMock.mock.calls[0][0]

    expect(options.enabled).toBe(true)
    expect(options.refetchInterval({ state: { data: processing } })).toBe(2000)
    expect(
      options.refetchInterval({ state: { data: { ...processing, status: 'complete' } } }),
    ).toBe(false)
    expect(options.refetchInterval({ state: { data: { ...processing, status: 'failed' } } })).toBe(
      false,
    )
    expect(options.refetchInterval({ state: { data: { ...processing, status: 'draft' } } })).toBe(
      false,
    )
    await expect(options.queryFn()).resolves.toEqual(processing)
    expect(investigationsApi.getStatus).toHaveBeenCalledWith('investigation-1')
    expect(result.current).toMatchObject({
      status: 'processing',
      progressStage: 'parsing',
      isComplete: false,
      isFailed: false,
    })
  })

  it('does not request status without an investigation id', () => {
    renderHook(() => useJobStatus(null))

    expect(useQueryMock.mock.calls[0][0].enabled).toBe(false)
  })
})
