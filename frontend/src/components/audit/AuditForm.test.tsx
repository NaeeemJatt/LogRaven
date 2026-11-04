import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listFrameworks, listCloudAccounts } from '../../api/compliance'
import AuditForm from './AuditForm'

vi.mock('../../api/compliance', () => ({
  listFrameworks: vi.fn(),
  listCloudAccounts: vi.fn(),
}))

function renderForm(ui: React.ReactElement, initialEntry = '/compliance?tab=audit') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      {ui}
    </MemoryRouter>
  )
}

describe('AuditForm (Multi-Step Assessment Wizard)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    vi.mocked(listCloudAccounts).mockResolvedValue([])
    vi.mocked(listFrameworks).mockResolvedValue([
      {
        id: 'soc2',
        name: 'SOC 2 Type II',
        version: '2017',
        description: 'Trust Services Criteria',
        control_count: 11,
        automatable_count: 11,
      },
    ])
  })

  it('navigates through Step 1, Step 2, and Step 3 and submits validated scope', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    renderForm(<AuditForm onSubmit={onSubmit} isLoading={false} />)

    // ── STEP 1: Frameworks Scope (SOC 2 pre-selected) ──
    expect(screen.getByText('Select Compliance Frameworks')).toBeInTheDocument()
    expect(screen.getByText('Selected Frameworks (1)')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Next: Target Environment/i }))

    // ── STEP 2: Target Environment ──
    expect(screen.getByText('Target Organization & Cloud Role')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Company \/ Organization Name/i), {
      target: { value: 'Acme Security' },
    })
    fireEvent.change(screen.getByLabelText(/AWS IAM Role ARN/i), {
      target: { value: 'arn:aws:iam::123456789012:role/LogRavenAudit' },
    })

    await user.click(screen.getByRole('button', { name: /Next: Period & Review/i }))

    // ── STEP 3: Evidence Window & Cadence ──
    expect(screen.getByText('Evidence Window & Cadence')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Start Date/i), { target: { value: '2024-01-01' } })
    fireEvent.change(screen.getByLabelText(/End Date/i), { target: { value: '2024-02-01' } })

    await user.selectOptions(screen.getByLabelText(/Assessment Cadence/i), 'weekly')
    await user.click(screen.getByRole('button', { name: /Run compliance audit \(1\)/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      companyName: 'Acme Security',
      roleArn: 'arn:aws:iam::123456789012:role/LogRavenAudit',
      auditStartDate: '2024-01-01',
      auditEndDate: '2024-02-01',
      frameworks: ['soc2'],
      recurrence: 'weekly',
    })
  })

  it('shows field validation errors on Step 2 and Step 3', async () => {
    const user = userEvent.setup()
    renderForm(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    // Advance to Step 2
    await user.click(screen.getByRole('button', { name: /Next: Target Environment/i }))

    // Step 2 blur validations
    fireEvent.blur(screen.getByLabelText(/Company \/ Organization Name/i))
    fireEvent.change(screen.getByLabelText(/AWS IAM Role ARN/i), { target: { value: 'not-an-arn' } })
    fireEvent.blur(screen.getByLabelText(/AWS IAM Role ARN/i))

    expect(screen.getByText('Company name is required')).toBeVisible()
    expect(screen.getByText(/Invalid ARN format/)).toBeVisible()

    // Fix Step 2 inputs to advance to Step 3
    fireEvent.change(screen.getByLabelText(/Company \/ Organization Name/i), { target: { value: 'Acme Corp' } })
    fireEvent.change(screen.getByLabelText(/AWS IAM Role ARN/i), { target: { value: 'arn:aws:iam::123456789012:role/AuditRole' } })
    await user.click(screen.getByRole('button', { name: /Next: Period & Review/i }))

    // Step 3 blur validations
    fireEvent.change(screen.getByLabelText(/Start Date/i), { target: { value: '2099-01-01' } })
    fireEvent.blur(screen.getByLabelText(/Start Date/i))
    fireEvent.change(screen.getByLabelText(/End Date/i), { target: { value: '2023-01-01' } })
    fireEvent.blur(screen.getByLabelText(/End Date/i))

    expect(screen.getByText('Start date cannot be in the future')).toBeVisible()
    expect(screen.getByText('End date must be after start date')).toBeVisible()
  })

  it('adds and removes frameworks in Step 1', async () => {
    vi.mocked(listFrameworks).mockResolvedValueOnce([
      {
        id: 'soc2',
        name: 'SOC 2 Type II',
        version: '2017',
        description: 'Trust Services Criteria',
        control_count: 11,
        automatable_count: 11,
      },
      {
        id: 'iso27001',
        name: 'ISO 27001',
        version: '2022',
        description: 'Information security management',
        control_count: 93,
        automatable_count: 30,
      },
    ])
    const user = userEvent.setup()
    renderForm(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    await user.click(await screen.findByRole('button', { name: /ISO 27001/ }))
    expect(screen.getByText(/2 frameworks selected/i)).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Remove SOC 2 Type II' }))
    expect(screen.getByText(/1 framework selected/i)).toBeVisible()
  })

  it('reveals and copies the IAM policy in Step 2', async () => {
    const user = userEvent.setup()
    renderForm(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    // Go to Step 2
    await user.click(screen.getByRole('button', { name: /Next: Target Environment/i }))

    await user.click(screen.getByRole('button', { name: /View IAM trust policy JSON/i }))
    expect(screen.getByText(/sts:AssumeRole/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^Copy$/i }))
    expect(screen.getByRole('button', { name: /Copy|Copied/ })).toBeInTheDocument()
  })

  it('supports quick lookback presets on Step 3', async () => {
    const user = userEvent.setup()
    renderForm(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    // Advance to Step 2
    await user.click(screen.getByRole('button', { name: /Next: Target Environment/i }))
    fireEvent.change(screen.getByLabelText(/Company \/ Organization Name/i), { target: { value: 'Acme Security' } })
    fireEvent.change(screen.getByLabelText(/AWS IAM Role ARN/i), { target: { value: 'arn:aws:iam::123456789012:role/AuditRole' } })

    // Advance to Step 3
    await user.click(screen.getByRole('button', { name: /Next: Period & Review/i }))

    // Click 90 days preset
    await user.click(screen.getByRole('button', { name: /Last 90 Days \(Recommended\)/i }))
    await waitFor(() => {
      expect(screen.getByText(/90-day verified evidence window/i)).toBeInTheDocument()
    })
  })
})
