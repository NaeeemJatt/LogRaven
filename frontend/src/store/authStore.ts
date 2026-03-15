// LogRaven — Auth State Store (Zustand)
//
// PURPOSE:
//   Global authentication state for LogRaven frontend.
//   Stores JWT tokens and current user info.
//
// STATE:
//   user: { id, email, tier } | null
//   accessToken: string | null
//   refreshToken: string | null
//   isAuthenticated: boolean
//
// ACTIONS:
//   setTokens(access, refresh) — called after login/register/refresh
//   setUser(user) — called after fetching /user/me
//   logout() — clears all auth state, redirects to /login
//
// NOTE: Tokens stored in memory (Zustand state), NOT localStorage.
//       localStorage is insecure for tokens (XSS risk).
//       Tokens are lost on page refresh — handled by refresh token flow.
//
// TODO Month 1 Week 1: Implement this file.

import { create } from 'zustand'

interface AuthState {
  user: { id: string; email: string; tier: string } | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  setTokens: (access, refresh) =>
    set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),
  logout: () =>
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
}))
