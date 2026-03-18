// LogRaven — Axios HTTP Client
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Inject JWT on every request
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401; redirect to /login if refresh also fails
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const { refreshToken, setTokens, logout } = useAuthStore.getState()

      if (refreshToken) {
        try {
          const res = await axios.post(
            `${client.defaults.baseURL}/auth/refresh`,
            { refresh_token: refreshToken },
          )
          const newAccess: string = res.data.access_token
          setTokens(newAccess, refreshToken)
          originalRequest.headers.Authorization = `Bearer ${newAccess}`
          return client(originalRequest)
        } catch {
          // refresh failed — fall through to logout
        }
      }

      logout()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  },
)

export default client
