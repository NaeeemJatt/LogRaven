import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuditorPortalPage from './AuditorPortalPage'
import * as complianceApi from '../api/compliance'
import type { AuditorPortalOverview, AuditorPortalException } from '../types/audit'

vi.mock('../api/compliance', () => ({
  getAuditorPortalOverview: vi.fn(),
  getAuditorPortalExceptions: vi.fn(),
  getEvidenceVaultDownloadUrl: vi.fn(
    (token, _passcode) => `/api/v1/compliance/auditor/portal/${token}/evidence-vault`,
  ),
}))

const sampleOverview: AuditorPortalOverview = {
  company_name: 'Acme SaaS Corp',
  recipient_name: 'Sarah Jenkins',
  expires_at: '2026-11-20T00:00:00Z',
  allowed_frameworks: ['soc2', 'iso27001'],
  can_download_raw_evidence: true,
  latest_audit: {
    audit_id: 'audit-999',
    score_percent: 94,
    raw_score_percent: 88,
    frameworks: ['soc2'],
    completed_at: '2026-10-16T12:00:00Z',
    controls_passed: 18,
    controls_failed: 2,
    controls_partial: 1,
    controls_suppressed: 1,
    total_controls: 21,
  },
  recent_audits: [
    {
      audit_id: 'audit-999',
      score_percent: 94,
      raw_score_percent: 88,
      frameworks: ['soc2'],
      completed_at: '2026-10-16T12:00:00Z',
    },
  ],
  active_exceptions_count: 1,
}

const sampleExceptions: AuditorPortalException[] = [
  {
    id: 'exc-1',
    control_id: 'CC6.6',
    framework: 'soc2',
    status: 'ACTIVE',
    justification: 'Corporate VPN gateway with MFA is required for bastion SSH.',
    compensating_controls: 'WireGuard VPN with Cisco Duo 2FA.',
    authorized_by: 'CISO Bob',
    expires_at: '2026-12-31T00:00:00Z',
    created_at: '2026-10-15T00:00:00Z',
  },
]

describe('AuditorPortalPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders verified evidence vault details and score metrics', async () => {
    vi.mocked(complianceApi.getAuditorPortalOverview).mockResolvedValueOnce(sampleOverview)
    vi.mocked(complianceApi.getAuditorPortalExceptions).mockResolvedValueOnce(sampleExceptions)

    render(
      <MemoryRouter initialEntries={['/auditor/portal/test-token-123']}>
        <Routes>
          <Route path="/auditor/portal/:token" element={<AuditorPortalPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(/verifying cryptographic auditor token/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/Acme SaaS Corp — Compliance Evidence Vault/i)).toBeInTheDocument()
    })

    expect(screen.getAllByText('94%').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('88%').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Download Evidence Vault \(\.ZIP\)/i)).toBeInTheDocument()
    expect(screen.getByText(/18 Passed · 2 Failed/i)).toBeInTheDocument()
  })

  it('prompts for passcode when server returns 401, then unlocks on correct passcode', async () => {
    const error401 = { response: { status: 401, data: { detail: 'Passcode required' } } }
    vi.mocked(complianceApi.getAuditorPortalOverview)
      .mockRejectedValueOnce(error401)
      .mockResolvedValueOnce(sampleOverview)
    vi.mocked(complianceApi.getAuditorPortalExceptions).mockResolvedValueOnce(sampleExceptions)

    render(
      <MemoryRouter initialEntries={['/auditor/portal/test-token-123']}>
        <Routes>
          <Route path="/auditor/portal/:token" element={<AuditorPortalPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Passcode Protected Vault')).toBeInTheDocument()
    })

    // Enter passcode and submit
    fireEvent.change(screen.getByPlaceholderText(/enter access passcode/i), {
      target: { value: 'Secret2026!' },
    })
    fireEvent.click(screen.getByRole('button', { name: /verify & access evidence vault/i }))

    await waitFor(() => {
      expect(complianceApi.getAuditorPortalOverview).toHaveBeenCalledWith(
        'test-token-123',
        'Secret2026!',
      )
      expect(screen.getByText(/Acme SaaS Corp — Compliance Evidence Vault/i)).toBeInTheDocument()
    })
  })

  it('switches to Compensating Controls & Exceptions tab', async () => {
    vi.mocked(complianceApi.getAuditorPortalOverview).mockResolvedValueOnce(sampleOverview)
    vi.mocked(complianceApi.getAuditorPortalExceptions).mockResolvedValueOnce(sampleExceptions)

    render(
      <MemoryRouter initialEntries={['/auditor/portal/test-token-123']}>
        <Routes>
          <Route path="/auditor/portal/:token" element={<AuditorPortalPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/Acme SaaS Corp — Compliance Evidence Vault/i)).toBeInTheDocument()
    })

    // Click tab
    const tabBtn = screen.getByRole('button', {
      name: /compensating controls & exceptions/i,
    })
    fireEvent.click(tabBtn)

    await waitFor(() => {
      expect(screen.getByText('CC6.6')).toBeInTheDocument()
      expect(screen.getByText(/WireGuard VPN with Cisco Duo 2FA/i)).toBeInTheDocument()
      expect(screen.getByText('CISO Bob')).toBeInTheDocument()
    })
  })
})
