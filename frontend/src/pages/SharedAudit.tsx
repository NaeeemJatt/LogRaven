// LogRaven — Public shared audit view (/shared/audit/:token)
//
// Read-only compliance results for external auditors, gated only by the
// scoped, expiring share token. No account or session required, so this route
// lives outside RequireAuth and hides every authenticated-only action.

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldCheck, Loader2, Link2, Lock } from 'lucide-react'
import AuditResults from '../components/audit/AuditResults'
import { getSharedAudit } from '../api/compliance'
import type { AuditStatusResponse } from '../types/audit'
import LegalLinks from '../components/layout/LegalLinks'

export default function SharedAudit() {
  const { token } = useParams<{ token: string }>()
  const [results, setResults] = useState<AuditStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) { setError('Invalid share link.'); return }
    let cancelled = false
    getSharedAudit(token)
      .then((data) => { if (!cancelled) setResults(data) })
      .catch((err) => {
        if (cancelled) return
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setError(detail ?? 'This share link is invalid or has expired.')
      })
    return () => { cancelled = true }
  }, [token])

  return (
    <div className="min-h-screen bg-void grid-bg">
      {/* Minimal public header */}
      <header className="border-b border-white/[0.06] bg-deep/40 backdrop-blur">
        <div className="px-4 sm:px-6 lg:px-8 py-4 max-w-[1200px] mx-auto flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-indigo-300" />
            </span>
            <span className="font-display font-bold text-text-primary">LogRaven</span>
          </Link>
          <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">
            <Lock className="w-3 h-3" /> Read-only shared report
          </span>
        </div>
      </header>

      <main className="px-4 sm:px-6 lg:px-8 py-8 max-w-[1200px] mx-auto">
        {error ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="ops-panel p-12 flex flex-col items-center text-center gap-3 max-w-lg mx-auto mt-12"
          >
            <Link2 className="w-8 h-8 text-text-ghost" strokeWidth={1.25} />
            <p className="text-base font-semibold text-text-primary">Link unavailable</p>
            <p className="text-sm text-text-muted leading-relaxed">{error}</p>
            <p className="text-xs text-text-muted">
              Ask the report owner to generate a new share link.
            </p>
          </motion.div>
        ) : !results ? (
          <div className="flex items-center justify-center py-24 text-sm text-text-muted">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading shared report…
          </div>
        ) : (
          <>
            <div className="mb-5">
              {results.company_name && (
                <h1 className="font-display font-bold text-text-primary text-2xl">
                  {results.company_name}
                </h1>
              )}
              <p className="text-sm text-text-muted mt-1">
                Compliance audit results shared via a scoped, expiring link.
              </p>
            </div>
            <AuditResults results={results} auditId={results.audit_id} readOnly />
          </>
        )}
      </main>
      <LegalLinks className="px-4 pb-8" />
    </div>
  )
}
