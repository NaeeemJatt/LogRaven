// LogRaven — Axios HTTP client (httpOnly cookies; use empty VITE_API_URL + Vite proxy in dev)
import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { normalizeApiBase } from './normalizeApiBase'

const baseURL = normalizeApiBase(import.meta.env.VITE_API_URL)
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
  (response) => {
    // If an API request expecting JSON received HTML (e.g. from a misconfigured proxy or SPA fallback)
    const contentType = String(response.headers?.['content-type'] ?? '')
    const url = String(response.config?.url ?? '')
    if (
      (url.startsWith('/api') || url.startsWith('/auth') || url === '/health') &&
      typeof response.data === 'string' &&
      (contentType.includes('text/html') ||
        response.data.trim().startsWith('<!doctype') ||
        response.data.trim().startsWith('<html'))
    ) {
      return Promise.reject(
        new Error(`Expected JSON from ${url} but received HTML document (status ${response.status})`),
      )
    }
    return response
  },
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

    const requestUrl = String(originalRequest.url ?? '')
    const isSessionProbe =
      String(originalRequest.method ?? '').toLowerCase() === 'get' &&
      (requestUrl === '/auth/me' || requestUrl.endsWith('/auth/me'))
    originalRequest._retry = true
    try {
      await refreshSession()
      return client(originalRequest)
    } catch {
      if (!isSessionProbe) redirectToLogin()
      return Promise.reject(error)
    }
  },
)

export default client
