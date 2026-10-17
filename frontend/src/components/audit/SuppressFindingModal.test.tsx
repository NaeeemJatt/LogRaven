import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import SuppressFindingModal from './SuppressFindingModal'

describe('SuppressFindingModal', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <SuppressFindingModal
        isOpen={false}
        onClose={vi.fn()}
        controlId="CC6.1"
        controlName="Logical Access Controls"
        frameworkId="soc2"
        onConfirm={vi.fn()}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders modal details and submits valid business justification', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    const onClose = vi.fn()

    render(
      <SuppressFindingModal
        isOpen={true}
        onClose={onClose}
        controlId="CC6.1"
        controlName="Logical Access Controls"
        frameworkId="soc2"
        onConfirm={onConfirm}
      />,
    )

    expect(screen.getByRole('heading', { name: /suppress cc6\.1/i })).toBeInTheDocument()
    expect(screen.getByText('Logical Access Controls')).toBeInTheDocument()

    // Fill in justification
    const justificationInput = screen.getByLabelText(/business justification/i)
    await user.type(justificationInput, 'Break-glass root account with physical YubiKey stored in bank safe.')

    // Fill in compensating controls
    const compensatingInput = screen.getByLabelText(/compensating controls/i)
    await user.type(compensatingInput, 'Quarterly audit log review and real-time SNS alerts on root login.')

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /authorize & suppress/i })
    await user.click(submitBtn)

    expect(onConfirm).toHaveBeenCalledOnce()
    const callArg = onConfirm.mock.calls[0][0]
    expect(callArg.business_justification).toBe('Break-glass root account with physical YubiKey stored in bank safe.')
    expect(callArg.compensating_controls).toBe('Quarterly audit log review and real-time SNS alerts on root login.')
    expect(callArg.risk_level).toBe('medium')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('displays validation error if justification is too short', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined)

    render(
      <SuppressFindingModal
        isOpen={true}
        onClose={vi.fn()}
        controlId="CC6.1"
        controlName="Logical Access Controls"
        frameworkId="soc2"
        onConfirm={onConfirm}
      />,
    )

    const justificationInput = screen.getByLabelText(/business justification/i)
    fireEvent.change(justificationInput, { target: { value: 'abc' } })

    const submitBtn = screen.getByRole('button', { name: /authorize & suppress/i })
    fireEvent.click(submitBtn)

    expect(await screen.findByText('Business justification must be at least 5 characters.')).toBeInTheDocument()
    expect(onConfirm).not.toHaveBeenCalled()
  })
})
