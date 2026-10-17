import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CloudAccountsManager from './CloudAccountsManager'
import * as complianceApi from '../../api/compliance'
import type { CloudAccount } from '../../types/audit'

vi.mock('../../api/compliance', () => ({
  listCloudAccounts: vi.fn(),
  createCloudAccount: vi.fn(),
  updateCloudAccount: vi.fn(),
  deleteCloudAccount: vi.fn(),
  verifyCloudAccount: vi.fn(),
  triggerAccountScan: vi.fn(),
}))

const sampleAwsAccount: CloudAccount = {
  id: 'acc-aws-1',
  name: 'Production AWS',
  provider: 'aws',
  account_id: '123456789012',
  role_arn: 'arn:aws:iam::123456789012:role/LogRavenAuditRole',
  external_id: 'lr-ext-1234',
  scan_schedule: 'weekly',
  default_frameworks: ['soc2', 'cis_aws'],
  is_active: true,
  health_status: 'connected',
  last_verified_at: '2026-10-16T12:00:00Z',
  next_run_at: '2026-10-23T02:00:00Z',
  latest_score_percent: 88,
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-16T12:00:00Z',
}

const sampleGcpAccount: CloudAccount = {
  id: 'acc-gcp-1',
  name: 'Security Ops GCP',
  provider: 'gcp',
  account_id: 'gcp-project-secops-999',
  gcp_project_id: 'gcp-project-secops-999',
  gcp_service_account_email: 'lograven-auditor@gcp-project-secops-999.iam.gserviceaccount.com',
  scan_schedule: 'daily',
  default_frameworks: ['soc2', 'cis_gcp'],
  is_active: true,
  health_status: 'connected',
  last_verified_at: '2026-10-16T12:00:00Z',
  next_run_at: '2026-10-17T02:00:00Z',
  latest_score_percent: 92,
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-16T12:00:00Z',
}

const sampleAzureAccount: CloudAccount = {
  id: 'acc-azure-1',
  name: 'Core Azure Subscription',
  provider: 'azure',
  account_id: 'sub-1111-2222',
  azure_tenant_id: '00000000-0000-0000-0000-000000000000',
  azure_subscription_id: '11111111-1111-1111-1111-111111111111',
  azure_client_id: '22222222-2222-2222-2222-222222222222',
  scan_schedule: 'weekly',
  default_frameworks: ['soc2', 'cis_azure'],
  is_active: true,
  health_status: 'connected',
  last_verified_at: '2026-10-16T12:00:00Z',
  next_run_at: '2026-10-23T02:00:00Z',
  latest_score_percent: 85,
  created_at: '2026-10-15T00:00:00Z',
  updated_at: '2026-10-16T12:00:00Z',
}

describe('CloudAccountsManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no accounts are returned', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([])

    render(<CloudAccountsManager />)

    expect(screen.getByText(/loading accounts.../i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('No cloud accounts connected')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /connect cloud account/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /connect your first account/i })).toBeInTheDocument()
  })

  it('renders connected accounts list with health status, schedule, and score for multi-cloud fleet', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([
      sampleAwsAccount,
      sampleGcpAccount,
      sampleAzureAccount,
    ])

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('Production AWS')).toBeInTheDocument()
      expect(screen.getByText('Security Ops GCP')).toBeInTheDocument()
      expect(screen.getByText('Core Azure Subscription')).toBeInTheDocument()
    })

    // Badges & details
    expect(screen.getByText('AWS')).toBeInTheDocument()
    expect(screen.getByText('GCP')).toBeInTheDocument()
    expect(screen.getByText('AZURE')).toBeInTheDocument()
    expect(screen.getByText('123456789012')).toBeInTheDocument()
    expect(screen.getByText('gcp-project-secops-999')).toBeInTheDocument()
    expect(screen.getByText('11111111-1111-1111-1111-111111111111')).toBeInTheDocument()
    expect(screen.getByText('Fleet (3)')).toBeInTheDocument()
  })

  it('opens connect modal, validates input, and connects an AWS account', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([])
    const newAccount: CloudAccount = {
      ...sampleAwsAccount,
      id: 'acc-new',
      name: 'Staging AWS',
      role_arn: 'arn:aws:iam::999888777666:role/StagingAuditRole',
    }
    vi.mocked(complianceApi.createCloudAccount).mockResolvedValueOnce(newAccount)

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('No cloud accounts connected')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /connect cloud account/i }))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/Register AWS, GCP, or Azure credentials for automated continuous auditing./i)).toBeInTheDocument()

    const nameInput = screen.getByLabelText(/account name/i)
    const roleInput = screen.getByLabelText(/aws iam role arn/i)

    // Trigger validation with invalid ARN
    fireEvent.change(nameInput, { target: { value: 'Staging AWS' } })
    fireEvent.change(roleInput, { target: { value: 'invalid-arn' } })
    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    expect(screen.getByText(/Valid AWS IAM Role ARN is required/i)).toBeInTheDocument()
    expect(complianceApi.createCloudAccount).not.toHaveBeenCalled()

    // Enter valid ARN and submit
    fireEvent.change(roleInput, { target: { value: 'arn:aws:iam::999888777666:role/StagingAuditRole' } })
    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    await waitFor(() => {
      expect(complianceApi.createCloudAccount).toHaveBeenCalledWith({
        provider: 'aws',
        name: 'Staging AWS',
        role_arn: 'arn:aws:iam::999888777666:role/StagingAuditRole',
        default_frameworks: ['soc2', 'cis_aws'],
        scan_schedule: 'weekly',
      })
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(screen.getByText('Staging AWS')).toBeInTheDocument()
    })
  })

  it('switches to GCP provider tab, validates, and connects a GCP project', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([])
    vi.mocked(complianceApi.createCloudAccount).mockResolvedValueOnce(sampleGcpAccount)

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('No cloud accounts connected')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /connect cloud account/i }))

    // Switch to GCP tab
    fireEvent.click(screen.getByRole('button', { name: /^GCP$/i }))

    // Verify GCP fields appeared and AWS role ARN disappeared
    expect(screen.getByLabelText(/gcp project id/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/service account email/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/aws iam role arn/i)).not.toBeInTheDocument()

    // Fill fields
    fireEvent.change(screen.getByLabelText(/account name/i), { target: { value: 'Security Ops GCP' } })
    fireEvent.change(screen.getByLabelText(/gcp project id/i), { target: { value: 'gcp-project-secops-999' } })
    fireEvent.change(screen.getByLabelText(/service account email/i), {
      target: { value: 'lograven-auditor@gcp-project-secops-999.iam.gserviceaccount.com' },
    })

    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    await waitFor(() => {
      expect(complianceApi.createCloudAccount).toHaveBeenCalledWith({
        provider: 'gcp',
        name: 'Security Ops GCP',
        gcp_project_id: 'gcp-project-secops-999',
        gcp_service_account_email: 'lograven-auditor@gcp-project-secops-999.iam.gserviceaccount.com',
        default_frameworks: ['soc2', 'cis_gcp'],
        scan_schedule: 'weekly',
      })
    })
  })

  it('switches to Azure provider tab, validates, and connects an Azure subscription', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([])
    vi.mocked(complianceApi.createCloudAccount).mockResolvedValueOnce(sampleAzureAccount)

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('No cloud accounts connected')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /connect cloud account/i }))

    // Switch to Azure tab
    fireEvent.click(screen.getByRole('button', { name: /^Azure$/i }))

    // Verify Azure fields appeared
    expect(screen.getByLabelText(/azure directory \(tenant\) id/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/azure subscription id/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/azure application \(client\) id/i)).toBeInTheDocument()

    // Fill fields
    fireEvent.change(screen.getByLabelText(/account name/i), { target: { value: 'Core Azure Subscription' } })
    fireEvent.change(screen.getByLabelText(/azure directory \(tenant\) id/i), {
      target: { value: '00000000-0000-0000-0000-000000000000' },
    })
    fireEvent.change(screen.getByLabelText(/azure subscription id/i), {
      target: { value: '11111111-1111-1111-1111-111111111111' },
    })
    fireEvent.change(screen.getByLabelText(/azure application \(client\) id/i), {
      target: { value: '22222222-2222-2222-2222-222222222222' },
    })

    fireEvent.click(screen.getByRole('button', { name: /save & connect/i }))

    await waitFor(() => {
      expect(complianceApi.createCloudAccount).toHaveBeenCalledWith({
        provider: 'azure',
        name: 'Core Azure Subscription',
        azure_tenant_id: '00000000-0000-0000-0000-000000000000',
        azure_subscription_id: '11111111-1111-1111-1111-111111111111',
        azure_client_id: '22222222-2222-2222-2222-222222222222',
        default_frameworks: ['soc2', 'cis_azure'],
        scan_schedule: 'weekly',
      })
    })
  })

  it('triggers on-demand audit and calls onStartAudit callback', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([sampleAwsAccount])
    vi.mocked(complianceApi.triggerAccountScan).mockResolvedValueOnce({
      status: 'queued',
      audit_id: 'audit-scan-789',
      cloud_account_id: sampleAwsAccount.id,
      company_name: sampleAwsAccount.name,
      frameworks: ['soc2', 'cis_aws'],
    })

    const onStartAudit = vi.fn()
    render(<CloudAccountsManager onStartAudit={onStartAudit} />)

    await waitFor(() => {
      expect(screen.getByText('Production AWS')).toBeInTheDocument()
    })

    const runBtn = screen.getByRole('button', { name: /run audit now/i })
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(complianceApi.triggerAccountScan).toHaveBeenCalledWith(sampleAwsAccount.id)
      expect(onStartAudit).toHaveBeenCalledWith('audit-scan-789', 'Production AWS')
    })
  })

  it('re-verifies connection when Verify button is clicked', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([sampleAwsAccount])
    vi.mocked(complianceApi.verifyCloudAccount).mockResolvedValueOnce({
      ...sampleAwsAccount,
      health_status: 'connected',
      last_verified_at: '2026-10-16T17:00:00Z',
    })

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('Production AWS')).toBeInTheDocument()
    })

    const verifyBtn = screen.getByTitle('Re-verify IAM connection')
    fireEvent.click(verifyBtn)

    await waitFor(() => {
      expect(complianceApi.verifyCloudAccount).toHaveBeenCalledWith(sampleAwsAccount.id)
    })
  })

  it('disconnects cloud account after user confirmation', async () => {
    vi.mocked(complianceApi.listCloudAccounts).mockResolvedValueOnce([sampleAwsAccount])
    vi.mocked(complianceApi.deleteCloudAccount).mockResolvedValueOnce(undefined)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(<CloudAccountsManager />)

    await waitFor(() => {
      expect(screen.getByText('Production AWS')).toBeInTheDocument()
    })

    const deleteBtn = screen.getByTitle('Disconnect account')
    fireEvent.click(deleteBtn)

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining("Disconnect cloud account 'Production AWS'?")
    )

    await waitFor(() => {
      expect(complianceApi.deleteCloudAccount).toHaveBeenCalledWith(sampleAwsAccount.id)
      expect(screen.queryByText('Production AWS')).not.toBeInTheDocument()
    })

    confirmSpy.mockRestore()
  })
})
