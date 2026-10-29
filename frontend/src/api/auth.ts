// LogRaven — Auth API Functions
import client from './client'
import type { AuthUser } from '../store/authStore'
import type { EncryptedEnvelope } from '../utils/crypto'

export interface AuthSessionResponse {
  token_type: string
  access_token?: string
  refresh_token?: string
  user?: AuthUser
}

export interface ResetVerifyResponse {
  valid: boolean
  email_masked?: string
  code?: string
  message?: string
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post<AuthSessionResponse>('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    client.post<AuthSessionResponse>('/auth/login', { email, password }),

  // Session refresh lives in api/client.ts (raw axios interceptor, avoids recursion).
  me: () => client.get('/auth/me'),

  logout: () => client.post('/auth/logout'),

  /** Pre-flight check validating reset token without consuming it */
  verifyResetToken: (token: string) =>
    client.get<ResetVerifyResponse>('/auth/password/reset/verify', { params: { token } }),

  /** Send a password-reset email (supports plain email or encrypted envelope). */
  forgotPassword: (data: string | { envelope: EncryptedEnvelope }) => {
    if (typeof data === 'string') {
      return client.post('/auth/password/forgot', { email: data })
    }
    return client.post('/auth/password/forgot', data)
  },

  /** Set a new password using token and new password (or encrypted envelope). */
  resetPassword: (
    data:
      | { token: string; new_password: string }
      | { envelope: EncryptedEnvelope }
  ) => client.post('/auth/password/reset', data),

  /** Confirm email ownership using the token from the verification email. */
  verifyEmail: (token: string) =>
    client.post('/auth/verify-email', { token }),

  /** Re-send the verification email for the logged-in user. */
  requestVerification: () =>
    client.post('/auth/verify-email/request'),

  /** Permanently delete the account (requires password confirmation). */
  deleteAccount: (password: string) =>
    client.delete('/auth/me', { data: { password } }),
}
