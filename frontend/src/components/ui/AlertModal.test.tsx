import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import AlertModal from './AlertModal'

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={() => setOpen(true)}>Open notice</button>
      <AlertModal
        isOpen={open}
        title="Pipeline notice"
        message="Try again."
        actionLabel="Retry"
        onAction={() => undefined}
        onDismiss={() => setOpen(false)}
      />
    </>
  )
}

describe('AlertModal focus', () => {
  it('traps focus and restores it to the trigger', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const trigger = screen.getByRole('button', { name: 'Open notice' })

    await user.click(trigger)
    const close = screen.getByRole('button', { name: 'Close' })
    await waitFor(() => expect(close).toHaveFocus())

    await user.tab()
    expect(screen.getByRole('button', { name: 'Retry' })).toHaveFocus()
    await user.tab()
    expect(close).toHaveFocus()

    await user.click(close)
    expect(trigger).toHaveFocus()
  })
})
