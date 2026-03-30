// LogRaven — Top navigation (matches dashboard chrome)
import { Link } from 'react-router-dom'
import { LayoutDashboard, LogOut, Shield } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAuth } from '../../hooks/useAuth'

export default function Navbar() {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { logout } = useAuth()

  const homeTo = isAuthenticated ? '/dashboard' : '/'

  return (
    <header className="sticky top-0 z-40 border-b border-raven-800/90 bg-raven-950/95 backdrop-blur-md supports-[backdrop-filter]:bg-raven-950/80">
      <nav className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6" aria-label="Main">
        <Link
          to={homeTo}
          className="group flex items-center gap-2.5 rounded-lg outline-none ring-offset-2 ring-offset-raven-950 focus-visible:ring-2 focus-visible:ring-electric-500"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-electric-500/35 bg-electric-500/10 text-electric-400 transition-colors group-hover:border-electric-500/55 group-hover:bg-electric-500/15">
            <Shield className="h-4 w-4" strokeWidth={2} aria-hidden />
          </span>
          <span className="text-base font-bold tracking-tight text-white">LogRaven</span>
        </Link>

        {isAuthenticated && (
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/dashboard"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-raven-400 transition-colors hover:bg-white/5 hover:text-electric-400"
            >
              <LayoutDashboard className="h-4 w-4 opacity-70" aria-hidden />
              Dashboard
            </Link>
            <span
              className="hidden md:inline max-w-[200px] truncate text-xs font-mono text-raven-500"
              title={user?.email}
            >
              {user?.email}
            </span>
            <button
              type="button"
              onClick={() => void logout()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-transparent px-3 py-2 text-xs font-semibold uppercase tracking-wide text-raven-300 transition-colors hover:border-white/20 hover:bg-white/5 hover:text-white"
            >
              <LogOut className="h-3.5 w-3.5 opacity-80" aria-hidden />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        )}
      </nav>
    </header>
  )
}
