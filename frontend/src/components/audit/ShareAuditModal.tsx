// LogRaven — Share audit modal
//
// Creates a scoped, expiring read-only share link (POST /audit/{id}/share) and
// presents a browser-openable URL to the public /shared/audit/:token page for
// external auditors. The backend returns an API path; we wrap the token in a
// frontend route so recipients get a rendered report, not raw JSON.

import { useState } from 'react'
import { Share2, Copy, Check, Loader2 } from 'lucide-react'
import { createShareLink } from '../../api/compliance'
import { useModalFocus } from '../../hooks/useModalFocus'

interface ShareAuditModalProps {
  auditId: string
  companyName?: string
  onClose: () => void
}

const EXPIRY_OPTIONS = [1, 7, 14, 30]

export default function ShareAuditModal({ auditId, companyName, onClose }: ShareAuditModalProps) {
  const [expiresDays, setExpiresDays] = useState(7)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const dialogRef = useModalFocus<HTMLDivElement>(true, onClose)

  const generate = async () => {
    setLoading(true)
    setError(null)
    setCopied(false)
    try {
      const res = await createShareLink(auditId, expiresDays)
      setShareUrl(`${window.location.origin}/shared/audit/${res.token}`)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Could not create share link.')
    } finally {
      setLoading(false)
    }
  }

  const copy = async () => {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Copy failed — select and copy the link manually.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-white/[0.08] bg-surface shadow-2xl shadow-black/60"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-modal-title"
      >
        <div className="border-b border-white/[0.06] bg-void/60 px-5 py-4 flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300">
            <Share2 className="h-5 w-5" strokeWidth={2} aria-hidden />
          </span>
          <div>
            <p id="share-modal-title" className="text-base font-semibold tracking-tight text-text-primary">
              Share audit
            </p>
            {companyName && <p className="text-xs text-text-muted">{companyName}</p>}
          </div>
        </div>

        <div className="px-5 py-5 space-y-4">
          <p className="text-sm text-text-secondary leading-relaxed">
            Generates a read-only link for external auditors. It shows results only — no
            account access — and expires automatically.
          </p>

          <div>
            <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">
              Link expires after
            </label>
            <div className="flex flex-wrap gap-2">
              {EXPIRY_OPTIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => { setExpiresDays(d); setShareUrl(null) }}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                    expiresDays === d
                      ? 'border-indigo-500/50 bg-indigo-500/12 text-indigo-300'
                      : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                  }`}
                >
                  {d} day{d > 1 ? 's' : ''}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p role="alert" className="text-xs px-3 py-2.5 rounded-lg border border-rose-500/25 bg-rose-500/[0.06] text-rose-400">
              {error}
            </p>
          )}

          {shareUrl ? (
            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-text-muted mb-2">
                Shareable link
              </label>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={shareUrl}
                  onFocus={(e) => e.currentTarget.select()}
                  className="sovereign-input flex-1 px-3 py-2.5 rounded-lg text-xs font-mono"
                />
                <button
                  type="button"
                  onClick={() => { void copy() }}
                  className="btn-sovereign px-3 py-2.5 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1.5 flex-shrink-0"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className="mt-2 font-mono text-[10px] text-text-muted">
                Expires in {expiresDays} day{expiresDays > 1 ? 's' : ''}. Anyone with this link can view the results.
              </p>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => { void generate() }}
              disabled={loading}
              className="btn-sovereign w-full py-2.5 rounded-lg text-sm font-semibold text-white inline-flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
              {loading ? 'Generating…' : 'Generate link'}
            </button>
          )}
        </div>

        <div className="flex items-center justify-end border-t border-white/[0.06] bg-void/40 px-5 py-4">
          <button
            data-autofocus
            type="button"
            onClick={onClose}
            className="btn-ghost rounded-lg px-4 py-2.5 text-sm font-medium text-text-secondary"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
