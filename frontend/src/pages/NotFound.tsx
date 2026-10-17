// LogRaven — 404 page (replaces the silent redirect-to-dashboard).

import { Link } from 'react-router-dom'
import { SearchX } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="pt-16 min-h-screen flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center">
          <SearchX className="w-6 h-6 text-indigo-300" aria-hidden />
        </div>
        <p className="font-mono text-[11px] text-indigo-400 tracking-[0.22em] uppercase mb-2">404 — Not found</p>
        <h1 className="font-display text-2xl font-bold text-text-primary mb-3">This page doesn't exist</h1>
        <p className="text-sm text-text-muted leading-relaxed mb-8">
          The address may be wrong, or the resource may have been deleted.
        </p>
        <Link
          to="/dashboard"
          className="btn-sovereign inline-block px-6 py-2.5 rounded-lg text-sm font-semibold cursor-pointer"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
