// LogRaven — 404 page (replaces the silent redirect-to-dashboard).

import { Link } from 'react-router-dom'
import { SearchX, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="pt-16 min-h-screen flex items-center justify-center p-8 bg-void text-text-primary">
      <div className="text-center max-w-md">
        <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-amber-400/10 border border-amber-400/25 flex items-center justify-center">
          <SearchX className="w-6 h-6 text-amber-400" aria-hidden />
        </div>
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-text-primary mb-3">
          Page not found
        </h1>
        <p className="text-sm text-text-muted leading-relaxed mb-8">
          The address may be incorrect, or the resource may have been relocated or removed.
        </p>
        <Link
          to="/dashboard"
          className="btn-sovereign inline-flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to dashboard</span>
        </Link>
      </div>
    </div>
  )
}
