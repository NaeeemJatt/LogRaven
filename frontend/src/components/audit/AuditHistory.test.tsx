import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { listAudits } from '../../api/compliance'
import AuditHistory from './AuditHistory'

vi.mock('../../api/compliance', () => ({
  listAudits: vi.fn(),
}))

describe('AuditHistory retry', () => {
  it('offers retry only for failed audits and disables it while pending', async () => {
    const user = userEvent.setup()
    vi.mocked(listAudits).mockResolvedValue({
      items: [
        {
          audit_id: 'failed-audit',
          company_name: 'Example',
          frameworks: ['soc2'],
          status: 'failed',
          created_at: '2026-07-10T12:00:00Z',
          recurrence: 'weekly',
        },
      ],
      page: 1,
      total: 1,
      totalPages: 1,
    })
    const onRetry = vi.fn()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { rerender } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AuditHistory
            onOpen={vi.fn()}
            onShare={vi.fn()}
            onRetry={onRetry}
            retryingAuditId={null}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const retry = await screen.findByRole('button', { name: 'Retry' })
    await user.click(retry)
    expect(onRetry).toHaveBeenCalledWith(expect.objectContaining({ audit_id: 'failed-audit' }))

    rerender(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AuditHistory
            onOpen={vi.fn()}
            onShare={vi.fn()}
            onRetry={onRetry}
            retryingAuditId="failed-audit"
          />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('button', { name: 'Retry' })).toBeDisabled()
  })
})
