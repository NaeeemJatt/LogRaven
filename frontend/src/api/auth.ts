// LogRaven — Auth API Functions
// register(email, password) -> TokenResponse
// login(email, password) -> TokenResponse
// refresh(refresh_token) -> {access_token}
// TODO Month 1 Week 1: Implement.

import client from './client'

export const authApi = {
  register: (email: string, password: string) =>
    client.post('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),
  refresh: (refreshToken: string) =>
    client.post('/auth/refresh', { refresh_token: refreshToken }),
}
