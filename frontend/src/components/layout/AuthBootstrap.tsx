// LogRaven — Restore session from httpOnly cookies via GET /auth/me
import { useEffect, useState } from 'react'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'

export default function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const me = await authApi.me()
        if (!cancelled) setUser(me.data)
      } catch {
        if (!cancelled) logout()
      } finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setUser, logout])

  if (!ready) {
    return (
      <div className="min-h-screen bg-raven-950 flex items-center justify-center">
        <div
          className="h-10 w-10 rounded-full border-2 border-raven-700 border-t-electric-500 animate-spin"
          aria-hidden
        />
      </div>
    )
  }
  return <>{children}</>
}
