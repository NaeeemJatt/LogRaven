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

export function isValidUser(user: unknown): user is AuthUser {
  return (
    typeof user === 'object' &&
    user !== null &&
    typeof (user as AuthUser).id === 'string' &&
    typeof (user as AuthUser).email === 'string' &&
    (user as AuthUser).id.trim().length > 0 &&
    (user as AuthUser).email.trim().length > 0
  )
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
      const validUser = isValidUser(user) ? user : null
      if (state.user?.id !== validUser?.id) {
        void queryClient.cancelQueries()
        queryClient.clear()
      }
      return { user: validUser, isAuthenticated: !!validUser }
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
