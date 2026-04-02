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

  /** Uses httpOnly refresh cookie when body omitted. */
  refresh: () => client.post<AuthSessionResponse>('/auth/refresh', {}),

  me: () => client.get('/auth/me'),

  logout: () => client.post('/auth/logout'),
}
