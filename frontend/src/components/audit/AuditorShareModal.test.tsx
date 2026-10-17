import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuditorShareModal from './AuditorShareModal'
import * as complianceApi from '../../api/compliance'

vi.mock('../../api/compliance', () => ({
  createAuditorToken: vi.fn(),
  listAuditorTokens: vi.fn(),
  revokeAuditorToken: vi.fn(),
}))

describe('AuditorShareModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <AuditorShareModal isOpen={false} companyName="Acme Corp" onClose={vi.fn()} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders form and creates an auditor invite link', async () => {
    vi.mocked(complianceApi.createAuditorToken).mockResolvedValueOnce({
      id: 'token-uuid-1',
      token: 'sample_secret_token_123',
      company_name: 'Acme Corp',
      recipient_name: 'Sarah Jenkins',
      recipient_email: 'sarah@firm.com',
      allowed_frameworks: ['soc2', 'iso27001'],
      can_download_raw_evidence: true,
      expires_at: '2026-11-16T12:00:00Z',
      created_at: '2026-10-16T12:00:00Z',
    })

    render(<AuditorShareModal isOpen={true} companyName="Acme Corp" onClose={vi.fn()} />)

    expect(screen.getByText('External Auditor Portal')).toBeInTheDocument()

    // Fill form
    fireEvent.change(screen.getByPlaceholderText(/sarah jenkins/i), {
      target: { value: 'Sarah Jenkins' },
    })
    fireEvent.change(screen.getByPlaceholderText(/auditor@firm.com/i), {
      target: { value: 'sarah@firm.com' },
    })

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /generate auditor link/i }))

    await waitFor(() => {
      expect(complianceApi.createAuditorToken).toHaveBeenCalledWith({
        company_name: 'Acme Corp',
        recipient_name: 'Sarah Jenkins',
        recipient_email: 'sarah@firm.com',
        passcode: undefined,
        duration_days: 30,
        allowed_frameworks: ['soc2', 'iso27001'],
        can_download_raw_evidence: true,
      })
    })

    // Shows generated link view
    expect(screen.getByText('Auditor Access Link Generated')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
  })

  it('switches to manage active links tab and revokes a link', async () => {
    vi.mocked(complianceApi.listAuditorTokens).mockResolvedValueOnce([
      {
        id: 'tok-1',
        company_name: 'Acme Corp',
        recipient_name: 'John Auditor',
        recipient_email: 'john@firm.com',
        allowed_frameworks: ['soc2'],
        can_download_raw_evidence: true,
        expires_at: '2026-11-01T00:00:00Z',
        is_expired: false,
        is_revoked: false,
        access_count: 3,
        last_accessed_at: '2026-10-16T10:00:00Z',
        created_at: '2026-10-15T00:00:00Z',
      },
    ])
    vi.mocked(complianceApi.revokeAuditorToken).mockResolvedValueOnce(undefined)

    render(<AuditorShareModal isOpen={true} companyName="Acme Corp" onClose={vi.fn()} />)

    // Switch to manage tab
    fireEvent.click(screen.getByRole('button', { name: /manage active links/i }))

    await waitFor(() => {
      expect(screen.getByText('John Auditor')).toBeInTheDocument()
    })
    expect(screen.getByText('Views: 3')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()

    // Click revoke button
    const revokeBtn = screen.getByTitle('Revoke link')
    fireEvent.click(revokeBtn)

    await waitFor(() => {
      expect(complianceApi.revokeAuditorToken).toHaveBeenCalledWith('tok-1')
      expect(screen.getByText('Revoked')).toBeInTheDocument()
    })
  })
})
