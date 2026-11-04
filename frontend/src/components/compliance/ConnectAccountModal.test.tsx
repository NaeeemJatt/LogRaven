import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ConnectAccountModal from './ConnectAccountModal'
import * as complianceApi from '../../api/compliance'
import type { CloudAccount } from '../../types/audit'

vi.mock('../../api/compliance', () => ({
  createCloudAccount: vi.fn(),
  verifyCloudAccount: vi.fn(),
}))

const sampleAwsAccount: CloudAccount = {
  id: 'acc-aws-test',
  name: 'Acme AWS Fleet',
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

describe('ConnectAccountModal (3-Step Wizard)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <ConnectAccountModal isOpen={false} onClose={vi.fn()} onAccountConnected={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders Step 1 (Organization info & provider selector) and validates required account name', () => {
    render(<ConnectAccountModal isOpen={true} onClose={vi.fn()} onAccountConnected={vi.fn()} />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Connect Cloud Account')).toBeInTheDocument()
    expect(screen.getByLabelText(/organization \/ company name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/account name \/ alias/i)).toBeInTheDocument()

    // Stepper labels
    expect(screen.getByText('Organization')).toBeInTheDocument()
    expect(screen.getByText('Setup Guide')).toBeInTheDocument()
    expect(screen.getByText('Review & Verify')).toBeInTheDocument()

    // Attempting to advance without account name triggers validation
    fireEvent.click(screen.getByRole('button', { name: /next: setup guide/i }))
    expect(screen.getByText(/please enter an account name or environment alias/i)).toBeInTheDocument()
  })

  it('navigates through 3 pages, runs connectivity test with failure & troubleshooting guide, then succeeds', async () => {
    const onClose = vi.fn()
    const onAccountConnected = vi.fn()
    vi.mocked(complianceApi.createCloudAccount).mockResolvedValueOnce(sampleAwsAccount)
    vi.mocked(complianceApi.verifyCloudAccount).mockResolvedValueOnce(sampleAwsAccount)

    render(
      <ConnectAccountModal
        isOpen={true}
        onClose={onClose}
        onAccountConnected={onAccountConnected}
      />
    )

    // ── PAGE 1: Organization & Alias ──
    fireEvent.change(screen.getByLabelText(/organization \/ company name/i), {
      target: { value: 'Acme Global' },
    })
    fireEvent.change(screen.getByLabelText(/account name \/ alias/i), {
      target: { value: 'Acme AWS Fleet' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: setup guide/i }))

    // ── PAGE 2: Step-by-Step Connection Guide ──
    expect(screen.getByText(/AWS IAM Trust Delegation Steps/i)).toBeInTheDocument()
    expect(screen.getByText(/Copy Policy/i)).toBeInTheDocument()

    const roleInput = screen.getByLabelText(/aws iam role arn/i)
    // Put an invalid role ARN initially
    fireEvent.change(roleInput, { target: { value: 'arn:aws:iam::bad-account:role/Test' } })
    fireEvent.click(screen.getByRole('button', { name: /next: review & verify/i }))

    // ── PAGE 3: Review, Pre-flight Test & Troubleshooting ──
    expect(screen.getByText('Configuration Review')).toBeInTheDocument()
    expect(screen.getByText('Acme Global')).toBeInTheDocument()
    expect(screen.getByText('Acme AWS Fleet')).toBeInTheDocument()

    // Run Pre-flight Connectivity Test (should fail because account ID is not 12 digits)
    const testBtn = screen.getByRole('button', { name: /test connection/i })
    fireEvent.click(testBtn)

    await waitFor(
      () => {
        expect(screen.getByText(/AWS STS AssumeRole Error/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Open Troubleshooting Guide Modal
    const troubleshootBtn = screen.getByRole('button', { name: /view troubleshooting guide/i })
    fireEvent.click(troubleshootBtn)

    expect(screen.getByText('Cloud Connection Troubleshooting')).toBeInTheDocument()
    expect(screen.getByText(/Ensure the IAM Role ARN contains exactly 12 digits/i)).toBeInTheDocument()

    // Close troubleshooting popup
    fireEvent.click(screen.getByRole('button', { name: /close & edit settings/i }))
    await waitFor(() => {
      expect(screen.queryByText('Cloud Connection Troubleshooting')).not.toBeInTheDocument()
    })

    // Click Back to fix the credentials on Page 2
    fireEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByLabelText(/aws iam role arn/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/aws iam role arn/i), {
      target: { value: 'arn:aws:iam::123456789012:role/LogRavenAuditRole' },
    })
    fireEvent.click(screen.getByRole('button', { name: /next: review & verify/i }))

    // Test connectivity again with valid ARN
    fireEvent.click(screen.getByRole('button', { name: /test connection/i }))
    await waitFor(
      () => {
        expect(screen.getByText(/Connection verified! Cloud infrastructure is reachable/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Save & Connect confirmation
    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    await waitFor(() => {
      expect(complianceApi.createCloudAccount).toHaveBeenCalledWith({
        name: 'Acme AWS Fleet',
        provider: 'aws',
        role_arn: 'arn:aws:iam::123456789012:role/LogRavenAuditRole',
        default_frameworks: ['soc2', 'cis_aws'],
        scan_schedule: 'weekly',
      })
      expect(onAccountConnected).toHaveBeenCalledWith(sampleAwsAccount)
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('closes and resets wizard state when Cancel button is clicked', () => {
    const onClose = vi.fn()
    render(<ConnectAccountModal isOpen={true} onClose={onClose} onAccountConnected={vi.fn()} />)

    const cancelBtn = screen.getByRole('button', { name: /^cancel$/i })
    fireEvent.click(cancelBtn)

    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
