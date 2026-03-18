// LogRaven — Navigation Bar
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'

export default function Navbar() {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { logout } = useAuth()

  return (
    <nav className="bg-raven-950 border-b border-raven-700 px-6 py-3 flex items-center justify-between">
      <span className="font-mono font-bold tracking-widest text-electric-500 text-sm uppercase select-none">
        LOGRAVEN
      </span>

      {isAuthenticated && (
        <div className="flex items-center gap-4">
          <span className="text-raven-400 text-xs font-mono truncate max-w-48">
            {user?.email}
          </span>
          <button
            onClick={logout}
            className="text-raven-400 text-xs hover:text-electric-500 transition-colors"
          >
            logout
          </button>
        </div>
      )}
    </nav>
  )
}
