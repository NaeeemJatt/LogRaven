// LogRaven — Suppress Finding & Business Logic Exception Modal
//
// Allows compliance officers and security leads to document business justifications,
// compensating controls, and risk acceptance dates for a failing or partial control.

import { useState } from 'react'
import { ShieldAlert, X, Loader2, Calendar, CheckCircle2 } from 'lucide-react'
import { useModalFocus } from '../../hooks/useModalFocus'
import type { SuppressControlBody } from '../../api/compliance'

interface SuppressFindingModalProps {
  isOpen: boolean
  onClose: () => void
  controlId: string
  controlName: string
  frameworkId: string
  onConfirm: (data: SuppressControlBody) => Promise<void>
}

export default function SuppressFindingModal({
  isOpen,
  onClose,
  controlId,
  controlName,
  frameworkId,
  onConfirm,
}: SuppressFindingModalProps) {
  const dialogRef = useModalFocus<HTMLDivElement>(isOpen, onClose)
  const [justification, setJustification] = useState('')
  const [compensatingControls, setCompensatingControls] = useState('')
  const [riskLevel, setRiskLevel] = useState<'low' | 'medium' | 'high' | 'critical'>('medium')
  const [expiresAt, setExpiresAt] = useState(() => {
    const nextYear = new Date()
    nextYear.setFullYear(nextYear.getFullYear() + 1)
    return nextYear.toISOString().split('T')[0]
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!justification.trim() || justification.trim().length < 5) {
      setError('Business justification must be at least 5 characters.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await onConfirm({
        business_justification: justification.trim(),
        compensating_controls: compensatingControls.trim() || undefined,
        risk_level: riskLevel,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
      })
      onClose()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Failed to suppress finding.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="suppress-modal-title"
        className="ops-panel w-full max-w-lg p-6 relative border border-white/[0.12] bg-[#0E131F] shadow-2xl rounded-xl space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-text-muted hover:text-text-primary p-1 rounded-lg transition-colors"
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center flex-shrink-0 text-purple-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-purple-300">
              Business Logic Exception · {frameworkId.toUpperCase()}
            </div>
            <h2 id="suppress-modal-title" className="text-lg font-bold text-text-primary leading-tight mt-0.5">
              Suppress {controlId}
            </h2>
            <p className="text-xs text-text-muted mt-1 leading-snug line-clamp-2">
              {controlName}
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="business-justification" className="block text-xs font-semibold text-text-primary mb-1.5">
              Business Justification <span className="text-red-400">*</span>
            </label>
            <textarea
              id="business-justification"
              required
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="e.g. S3 bucket 'marketing-static-cdn' is intentionally public for hosting public corporate website assets."
              className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400/40"
            />
            <span className="text-[10px] text-text-muted mt-1 block">
              Explain why this architecture or configuration is required for business operations.
            </span>
          </div>

          <div>
            <label htmlFor="compensating-controls" className="block text-xs font-semibold text-text-primary mb-1.5 flex items-center justify-between">
              <span>Compensating Controls (Optional)</span>
              <span className="font-mono text-[10px] text-text-muted">Recommended for SOC 2</span>
            </label>
            <textarea
              id="compensating-controls"
              rows={2}
              value={compensatingControls}
              onChange={(e) => setCompensatingControls(e.target.value)}
              placeholder="e.g. Origin Access Control (OAC) limits bucket reads to CloudFront; AWS WAF rate-limits anomalous traffic."
              className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-purple-400 focus:outline-none focus:ring-1 focus:ring-purple-400/40"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="risk-level" className="block text-xs font-semibold text-text-primary mb-1.5">
                Risk Level
              </label>
              <select
                id="risk-level"
                value={riskLevel}
                onChange={(e) => setRiskLevel(e.target.value as any)}
                className="w-full text-xs rounded-lg border border-white/10 bg-[#161B26] text-text-primary px-3 py-2 focus:border-purple-400 focus:outline-none"
              >
                <option value="low">Low Risk</option>
                <option value="medium">Medium Risk</option>
                <option value="high">High Risk</option>
                <option value="critical">Critical Risk</option>
              </select>
            </div>

            <div>
              <label htmlFor="exception-expiry" className="block text-xs font-semibold text-text-primary mb-1.5 flex items-center gap-1">
                <Calendar className="w-3 h-3 text-purple-300" /> Review By Date
              </label>
              <input
                id="exception-expiry"
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full text-xs rounded-lg border border-white/10 bg-[#161B26] text-text-primary px-3 py-2 focus:border-purple-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] text-[11px] text-text-muted flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
            <span>
              This will update the control status to <strong>SUPPRESSED</strong>. It will be excluded from the gap count, 
              documented in the dedicated auditor report section, and will not penalize your adjusted score.
            </span>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3.5 py-2 text-xs font-semibold text-text-muted hover:text-text-primary rounded-lg transition-colors border border-transparent hover:border-white/10"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/20 flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Authorizing…
                </>
              ) : (
                'Authorize & Suppress'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
