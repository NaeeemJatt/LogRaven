// LogRaven — Auth API Functions
import client from './client'
import type { AuthUser } from '../store/authStore'

export interface AuthSessionResponse {
  token_type: string
  access_token?: string
  refresh_token?: string
  user?: AuthUser
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post<AuthSessionResponse>('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    client.post<AuthSessionResponse>('/auth/login', { email, password }),

  // Session refresh lives in api/client.ts (raw axios interceptor, avoids recursion).
  me: () => client.get('/auth/me'),

  logout: () => client.post('/auth/logout'),

  /** Send a password-reset email (always 202 — no user enumeration). */
  forgotPassword: (email: string) =>
    client.post('/auth/password/forgot', { email }),

  /** Set a new password using the token from the reset email. */
  resetPassword: (token: string, new_password: string) =>
    client.post('/auth/password/reset', { token, new_password }),

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
