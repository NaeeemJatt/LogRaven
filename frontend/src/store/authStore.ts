// LogRaven — Auth state (no tokens in JS; httpOnly cookies hold JWTs)
import { create } from 'zustand'

export interface AuthUser {
  id: string
  email: string
  tier: string
  name?: string | null
  timezone?: string | null
  created_at?: string
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  setUser: (user: AuthUser | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isAuthenticated: false,

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  logout: () =>
    set({
      user: null,
      isAuthenticated: false,
    }),
}))
