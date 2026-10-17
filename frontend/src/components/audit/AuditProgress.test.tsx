import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { getAuditStatus } from '../../api/compliance'
import AuditProgress from './AuditProgress'

vi.mock('../../api/compliance', () => ({
  getAuditStatus: vi.fn(),
}))

describe('AuditProgress failed retry', () => {
  it('keeps the current failure visible and starts a disabled retry', async () => {
    const user = userEvent.setup()
    vi.mocked(getAuditStatus).mockResolvedValue({
      audit_id: 'audit-1',
      status: 'failed',
      error: 'AWS role could not be assumed',
    })
    const onRetry = vi.fn().mockResolvedValue(undefined)
    const { rerender } = render(
      <AuditProgress
        auditId="audit-1"
        companyName="Example"
        onComplete={vi.fn()}
        onLeave={vi.fn()}
        onRetry={onRetry}
        isRetrying={false}
      />,
    )

    expect(await screen.findByText('AWS role could not be assumed')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Retry as new audit' }))
    expect(onRetry).toHaveBeenCalledOnce()

    rerender(
      <AuditProgress
        auditId="audit-1"
        companyName="Example"
        onComplete={vi.fn()}
        onLeave={vi.fn()}
        onRetry={onRetry}
        isRetrying
      />,
    )
    expect(screen.getByRole('button', { name: 'Starting retry…' })).toBeDisabled()
  })
})
