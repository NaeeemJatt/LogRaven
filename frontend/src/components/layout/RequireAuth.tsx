// LogRaven — Server-verified route guard
//
// Client-side route state (the auth store boolean) can be flipped from browser
// devtools, so it is NOT trusted as a security boundary on its own. This guard
// re-verifies the session against the backend (`GET /auth/me`, which requires a
// valid httpOnly session cookie the browser cannot forge). If the server does
// not recognise the session, the user is sent to /login regardless of any
// locally-manipulated store value.
//
// The real security boundary is always the API: every data endpoint requires
// the signed cookie. This guard just keeps the UI honest with that truth.

import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '../../api/auth'
import { useAuthStore, isValidUser } from '../../store/authStore'
import type { AuthUser } from '../../store/authStore'

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const currentUserId = useAuthStore((s) => s.user?.id)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ['auth-session', currentUserId ?? 'anonymous'],
    queryFn: async () => {
      const res = await authApi.me()
      if (!isValidUser(res.data)) {
        throw new Error('Invalid user session')
      }
      return res.data as AuthUser
    },
    retry: false,
    staleTime: 0,
    refetchOnMount: 'always',
  })

  useEffect(() => {
    if (isValidUser(data)) setUser(data)
  }, [data, setUser])

  useEffect(() => {
    if (isError) logout()
  }, [isError, logout])

  if (isLoading || isFetching) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <div
          className="h-10 w-10 rounded-full border-2 border-white/[0.08] border-t-indigo-500 animate-spin"
          aria-hidden
        />
      </div>
    )
  }

  if (isError || !isValidUser(data)) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
