import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ConnectAccountPage from './ConnectAccountPage'
import * as complianceApi from '../api/compliance'
import type { CloudAccount } from '../types/audit'

vi.mock('../api/compliance', () => ({
  createCloudAccount: vi.fn(),
  verifyCloudAccount: vi.fn(),
}))

const sampleAwsAccount: CloudAccount = {
  id: 'acc-aws-page-test',
  name: 'Acme Prod AWS',
  provider: 'aws',
  account_id: '123456789012',
  role_arn: 'arn:aws:iam::123456789012:role/LogRavenAuditRole',
  external_id: 'lr-ext-1234',
  scan_schedule: 'weekly',
  default_frameworks: ['soc2', 'cis_aws'],
  is_active: true,
  health_status: 'connected',
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-16T12:00:00Z',
}

function renderWithRouter(initialEntry = '/compliance/connect/step-1') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/compliance/connect" element={<ConnectAccountPage />} />
        <Route path="/compliance/connect/:step" element={<ConnectAccountPage />} />
        <Route path="/compliance" element={<div>Compliance Control Room Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ConnectAccountPage (Full Page Multi-Step Wizard)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('renders Step 1 with organization & provider selection and validates account name', async () => {
    renderWithRouter('/compliance/connect/step-1')

    expect(screen.getByRole('heading', { name: /connect cloud account/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/organization \/ company name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/account name \/ alias/i)).toBeInTheDocument()

    // Step navigator items
    const nav = screen.getByRole('navigation', { name: /connection steps/i })
    expect(within(nav).getByText('Organization')).toBeInTheDocument()
    expect(within(nav).getByText('Setup Guide')).toBeInTheDocument()
    expect(within(nav).getByText('Review & Verify')).toBeInTheDocument()

    // Try submitting without account name
    fireEvent.click(screen.getByRole('button', { name: /next: setup guide/i }))
    expect(screen.getByText(/please enter an account name or environment alias/i)).toBeInTheDocument()
  })

  it('navigates through step-1, step-2, and step-3 URLs while preserving state', async () => {
    vi.mocked(complianceApi.createCloudAccount).mockResolvedValueOnce(sampleAwsAccount)
    vi.mocked(complianceApi.verifyCloudAccount).mockResolvedValueOnce(sampleAwsAccount)

    renderWithRouter('/compliance/connect/step-1')

    // ── STEP 1: Input details and advance ──
    fireEvent.change(screen.getByLabelText(/organization \/ company name/i), {
      target: { value: 'Acme International' },
    })
    fireEvent.change(screen.getByLabelText(/account name \/ alias/i), {
      target: { value: 'Acme Prod AWS' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: setup guide/i }))

    // ── STEP 2: Instructions and Role ARN ──
    await waitFor(() => {
      expect(screen.getByText(/AWS IAM Trust Delegation Steps/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Copy Policy/i)).toBeInTheDocument()

    const roleInput = screen.getByLabelText(/aws iam role arn/i)
    fireEvent.change(roleInput, {
      target: { value: 'arn:aws:iam::123456789012:role/LogRavenAuditRole' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: review & verify/i }))

    // ── STEP 3: Review, Pre-flight Test & Confirmation ──
    await waitFor(() => {
      expect(screen.getByText('Configuration Summary')).toBeInTheDocument()
      expect(screen.getByText('Acme International')).toBeInTheDocument()
      expect(screen.getByText('Acme Prod AWS')).toBeInTheDocument()
    })

    // Run Pre-flight test
    fireEvent.click(screen.getByRole('button', { name: /test connection/i }))
    await waitFor(
      () => {
        expect(screen.getByText(/Connection verified! Cloud infrastructure is reachable/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Save & Connect
    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    await waitFor(() => {
      expect(complianceApi.createCloudAccount).toHaveBeenCalledWith({
        name: 'Acme Prod AWS',
        provider: 'aws',
        role_arn: 'arn:aws:iam::123456789012:role/LogRavenAuditRole',
        default_frameworks: ['soc2', 'cis_aws'],
        scan_schedule: 'weekly',
      })
      expect(screen.getByText('Compliance Control Room Page')).toBeInTheDocument()
    })
  })

  it('triggers connectivity failure on invalid credentials and opens troubleshooting dialog', async () => {
    renderWithRouter('/compliance/connect/step-1')

    fireEvent.change(screen.getByLabelText(/account name \/ alias/i), {
      target: { value: 'Bad Account Fleet' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: setup guide/i }))

    await waitFor(() => {
      expect(screen.getByLabelText(/aws iam role arn/i)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText(/aws iam role arn/i), {
      target: { value: 'arn:aws:iam::not-12-digits:role/BadRole' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: review & verify/i }))

    await waitFor(() => {
      expect(screen.getByText('Configuration Summary')).toBeInTheDocument()
    })

    // Test Connection
    fireEvent.click(screen.getByRole('button', { name: /test connection/i }))

    await waitFor(
      () => {
        expect(screen.getByText(/AWS STS AssumeRole Error/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Open Troubleshooting Guide
    fireEvent.click(screen.getByRole('button', { name: /view troubleshooting guide/i }))
    expect(screen.getByText('Cloud Connection Troubleshooting')).toBeInTheDocument()
    expect(screen.getByText(/Ensure the IAM Role ARN contains exactly 12 digits/i)).toBeInTheDocument()

    // Close troubleshooting
    fireEvent.click(screen.getByRole('button', { name: /close & edit settings/i }))
    await waitFor(() => {
      expect(screen.queryByText('Cloud Connection Troubleshooting')).not.toBeInTheDocument()
    })
  })

  it('redirects directly visited step-2 to step-1 when step 1 details are missing', async () => {
    renderWithRouter('/compliance/connect/step-2')

    await waitFor(() => {
      expect(screen.getByText(/Please enter an account name or alias on Step 1 before proceeding to the setup guide/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/account name \/ alias/i)).toBeInTheDocument()
    })
  })

  it('redirects directly visited step-3 to step-2 when credentials are missing', async () => {
    // Populate session with step 1 valid, but step 2 credentials empty
    sessionStorage.setItem(
      'lograven_cloud_connect_wizard_v1',
      JSON.stringify({
        orgName: 'Acme Test Corp',
        name: 'Acme AWS Production',
        provider: 'aws',
        roleArn: '',
      })
    )

    renderWithRouter('/compliance/connect/step-3')

    await waitFor(() => {
      expect(screen.getByText(/Please provide valid cloud credentials on Step 2 before proceeding to review/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/aws iam role arn/i)).toBeInTheDocument()
    })
  })

  it('navigates back to compliance accounts list when Cancel is clicked', async () => {
    renderWithRouter('/compliance/connect/step-1')

    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))

    await waitFor(() => {
      expect(screen.getByText('Compliance Control Room Page')).toBeInTheDocument()
    })
  })
})
