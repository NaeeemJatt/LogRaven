// LogRaven — Auth state (no tokens in JS; httpOnly cookies hold JWTs)
import { create } from 'zustand'
import { queryClient } from '../queryClient'

export interface AuthUser {
  id: string
  email: string
  tier: string
  email_verified?: boolean
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

  setUser: (user) =>
    set((state) => {
      if (state.user?.id !== user?.id) {
        void queryClient.cancelQueries()
        queryClient.clear()
      }
      return { user, isAuthenticated: !!user }
    }),

  logout: () => {
    void queryClient.cancelQueries()
    queryClient.clear()
    set({
      user: null,
      isAuthenticated: false,
    })
  },
}))
