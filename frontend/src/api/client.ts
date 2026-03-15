// LogRaven — Axios HTTP Client
//
// PURPOSE:
//   Single Axios instance used by ALL LogRaven API call files.
//   Never create another Axios instance elsewhere.
//
// CONFIGURATION:
//   baseURL: from VITE_API_URL env var (default: http://localhost:8000)
//
// REQUEST INTERCEPTOR:
//   Reads JWT access token from Zustand authStore.
//   Adds: Authorization: Bearer {access_token} to every request.
//
// RESPONSE INTERCEPTOR:
//   On 401 response:
//     1. Attempt silent token refresh via POST /auth/refresh
//     2. If refresh succeeds: retry original request with new token
//     3. If refresh fails: clear authStore, redirect to /login
//   Users are never unexpectedly logged out during an active session.
//
// TODO Month 1 Week 1: Implement this file.

import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// TODO: Add request interceptor (JWT injection)
// TODO: Add response interceptor (token refresh on 401)

export default client
