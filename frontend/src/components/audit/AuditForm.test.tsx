import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listFrameworks } from '../../api/compliance'
import AuditForm from './AuditForm'

vi.mock('../../api/compliance', () => ({
  listFrameworks: vi.fn(),
}))

describe('AuditForm', () => {
  beforeEach(() => {
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

  it('submits validated compliance scope without contacting AWS', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<AuditForm onSubmit={onSubmit} isLoading={false} />)

    fireEvent.change(screen.getByLabelText('Company name'), { target: { value: 'Acme Security' } })
    fireEvent.change(screen.getByLabelText('IAM role ARN'), {
      target: { value: 'arn:aws:iam::123456789012:role/LogRavenAudit' },
    })
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2024-01-01' } })
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2024-02-01' } })
    await user.click(screen.getByRole('button', { name: /Continuous monitoring/ }))
    await user.selectOptions(screen.getByLabelText('Cadence'), 'weekly')
    await user.click(screen.getByRole('button', { name: 'Run compliance audit (1)' }))

    expect(onSubmit).toHaveBeenCalledWith({
      companyName: 'Acme Security',
      roleArn: 'arn:aws:iam::123456789012:role/LogRavenAudit',
      auditStartDate: '2024-01-01',
      auditEndDate: '2024-02-01',
      frameworks: ['soc2'],
      recurrence: 'weekly',
    })
  })

  it('shows field errors after invalid values lose focus', () => {
    render(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    fireEvent.blur(screen.getByLabelText('Company name'))
    fireEvent.change(screen.getByLabelText('IAM role ARN'), { target: { value: 'not-an-arn' } })
    fireEvent.blur(screen.getByLabelText('IAM role ARN'))
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2099-01-01' } })
    fireEvent.blur(screen.getByLabelText('Start date'))
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2023-01-01' } })
    fireEvent.blur(screen.getByLabelText('End date'))

    expect(screen.getByText('Company name is required')).toBeVisible()
    expect(screen.getByText(/Invalid ARN format/)).toBeVisible()
    expect(screen.getByText('Start date cannot be in the future')).toBeVisible()
    expect(screen.getByText('End date must be after start date')).toBeVisible()
  })

  it('adds and removes frameworks from the loaded catalog', async () => {
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
    render(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    await user.click(await screen.findByRole('button', { name: /ISO 27001/ }))
    expect(screen.getByText('2 frameworks')).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Remove SOC 2 Type II' }))
    expect(screen.getByText('1 framework')).toBeVisible()
  })

  it('reveals and copies the IAM policy', async () => {
    const user = userEvent.setup()
    render(<AuditForm onSubmit={vi.fn()} isLoading={false} />)

    await user.click(screen.getByRole('button', { name: 'View IAM policy JSON' }))
    expect(screen.getByText(/cloudtrail:LookupEvents/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Copy' }))
    expect(screen.getByRole('button', { name: /Copy|Copied/ })).toBeInTheDocument()
  })
})
