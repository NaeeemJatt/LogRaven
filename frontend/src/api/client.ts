// LogRaven — Axios HTTP client (httpOnly cookies; use empty VITE_API_URL + Vite proxy in dev)
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const baseURL = import.meta.env.VITE_API_URL ?? ''
let refreshPromise: Promise<void> | null = null

const client = axios.create({
  baseURL,
  withCredentials: true,
})

function redirectToLogin() {
  useAuthStore.getState().logout()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

function refreshSession(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh`, {}, { withCredentials: true })
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as (typeof error.config & { _retry?: boolean }) | undefined
    if (!originalRequest || error.response?.status !== 401) {
      return Promise.reject(error)
    }

    if (originalRequest._retry) {
      return Promise.reject(error)
    }

    if (String(originalRequest.url ?? '').includes('/auth/refresh')) {
      redirectToLogin()
      return Promise.reject(error)
    }

    if (String(originalRequest.url ?? '').includes('/auth/login')) {
      return Promise.reject(error)
    }

    originalRequest._retry = true
    try {
      await refreshSession()
      return client(originalRequest)
    } catch {
      redirectToLogin()
      return Promise.reject(error)
    }
  },
)

export default client
