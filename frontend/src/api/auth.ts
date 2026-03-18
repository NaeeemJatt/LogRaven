// LogRaven — Auth API Functions
import client from './client'

export const authApi = {
  register: (email: string, password: string) =>
    client.post('/auth/register', { email, password }),

  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),

  refresh: (refreshToken: string) =>
    client.post('/auth/refresh', { refresh_token: refreshToken }),

  me: () => client.get('/auth/me'),
}
