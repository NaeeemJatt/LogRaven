import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../../api/auth'
import * as cryptoUtils from '../../utils/crypto'
import ForgotPassword from './ForgotPassword'

vi.mock('../../api/auth', () => ({
  authApi: {
    forgotPassword: vi.fn(),
  },
}))

vi.mock('../../utils/crypto', () => ({
  encryptPayload: vi.fn(),
}))

describe('ForgotPassword', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cryptoUtils.encryptPayload).mockResolvedValue({
      key_id: 'test-key',
      encrypted_key: 'enc-key',
      iv: 'iv-bytes',
      ciphertext: 'cipher-bytes',
      tag: 'tag-bytes',
    })
    vi.mocked(authApi.forgotPassword).mockResolvedValue({} as never)
  })

  it('renders initial form with clean title and description', () => {
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /reset your password/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument()
  })

  it('rejects multiple recipients / comma-separated input', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    )

    const emailInput = screen.getByLabelText(/email/i)
    await user.type(emailInput, 'alice@test.com,hacker@evil.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect(
      screen.getByText(/please enter exactly one email address without commas/i)
    ).toBeInTheDocument()
    expect(cryptoUtils.encryptPayload).not.toHaveBeenCalled()
  })

  it('encrypts email and shows neutral confirmation message on submit', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    )

    const emailInput = screen.getByLabelText(/email/i)
    await user.type(emailInput, 'operator@lograven.io')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    await waitFor(() => {
      expect(cryptoUtils.encryptPayload).toHaveBeenCalledWith({
        email: 'operator@lograven.io',
      })
      expect(authApi.forgotPassword).toHaveBeenCalledWith({
        envelope: expect.objectContaining({
          key_id: 'test-key',
          ciphertext: 'cipher-bytes',
        }),
      })
    })

    expect(screen.getByTestId('forgot-password-success')).toBeInTheDocument()
    expect(screen.getByText(/check your inbox/i)).toBeInTheDocument()
    expect(screen.getByText(/15 minutes/i)).toBeInTheDocument()
    expect(screen.getByText(/zero-knowledge dispatch parity verified/i)).toBeInTheDocument()
  })
})
