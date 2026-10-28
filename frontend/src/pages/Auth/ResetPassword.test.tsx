import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../../api/auth'
import * as cryptoUtils from '../../utils/crypto'
import ResetPassword from './ResetPassword'

vi.mock('../../api/auth', () => ({
  authApi: {
    verifyResetToken: vi.fn(),
    resetPassword: vi.fn(),
  },
}))

vi.mock('../../utils/crypto', () => ({
  encryptPayload: vi.fn(),
}))

function renderResetPassword(initialUrl = '/reset-password?token=valid-token-123') {
  return render(
    <MemoryRouter initialEntries={[initialUrl]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/forgot-password" element={<div>Forgot Password Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ResetPassword', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cryptoUtils.encryptPayload).mockResolvedValue({
      key_id: 'test-key',
      encrypted_key: 'enc-key',
      iv: 'iv-bytes',
      ciphertext: 'cipher-bytes',
      tag: 'tag-bytes',
    })
    vi.mocked(authApi.verifyResetToken).mockResolvedValue({
      data: { valid: true, email_masked: 'o***r@lograven.io' },
    } as never)
    vi.mocked(authApi.resetPassword).mockResolvedValue({} as never)
  })

  it('displays invalid state when link has no token', async () => {
    renderResetPassword('/reset-password')

    await waitFor(() => {
      expect(screen.getByTestId('reset-password-invalid')).toBeInTheDocument()
      expect(screen.getByText(/missing its authentication token/i)).toBeInTheDocument()
    })
  })

  it('performs pre-flight check and displays masked email on valid token', async () => {
    renderResetPassword('/reset-password?token=valid-token-123')

    await waitFor(() => {
      expect(authApi.verifyResetToken).toHaveBeenCalledWith('valid-token-123')
      expect(screen.getByText('o***r@lograven.io')).toBeInTheDocument()
      expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument()
    })
  })

  it('enforces live password complexity checklist before allowing submit', async () => {
    const user = userEvent.setup()
    renderResetPassword('/reset-password?token=valid-token-123')

    await waitFor(() => {
      expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument()
    })

    const passwordInput = screen.getByLabelText(/^new password$/i)
    const confirmInput = screen.getByLabelText(/confirm new password/i)

    // Type a weak password (<12 chars)
    await user.type(passwordInput, 'Short1!')
    await user.type(confirmInput, 'Short1!')
    await user.click(screen.getByRole('button', { name: /update password/i }))

    expect(screen.getByText(/please satisfy all password complexity requirements/i)).toBeInTheDocument()
    expect(authApi.resetPassword).not.toHaveBeenCalled()
  })

  it('encrypts credentials and submits reset password successfully', async () => {
    const user = userEvent.setup()
    renderResetPassword('/reset-password?token=valid-token-123')

    await waitFor(() => {
      expect(screen.getByLabelText(/^new password$/i)).toBeInTheDocument()
    })

    const passwordInput = screen.getByLabelText(/^new password$/i)
    const confirmInput = screen.getByLabelText(/confirm new password/i)

    await user.type(passwordInput, 'ComplexSecureP@ss2026!')
    await user.type(confirmInput, 'ComplexSecureP@ss2026!')
    await user.click(screen.getByRole('button', { name: /update password/i }))

    await waitFor(() => {
      expect(cryptoUtils.encryptPayload).toHaveBeenCalledWith({
        token: 'valid-token-123',
        new_password: 'ComplexSecureP@ss2026!',
      })
      expect(authApi.resetPassword).toHaveBeenCalledWith({
        envelope: expect.objectContaining({
          key_id: 'test-key',
          ciphertext: 'cipher-bytes',
        }),
      })
      expect(screen.getByTestId('reset-password-success')).toBeInTheDocument()
      expect(screen.getByText(/password updated/i)).toBeInTheDocument()
    })
  })
})
