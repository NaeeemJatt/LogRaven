// LogRaven — External CPA Auditor Portal
//
// Specialized read-only evidence room for external auditors (SOC 2, ISO 27001).
// Provides verified audit histories, the business exceptions ledger, and
// one-click download of the cryptographically hashed Evidence Vault ZIP.

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  ShieldCheck, Download, Lock, CheckCircle2,
  ShieldAlert, KeyRound, Loader2,
} from 'lucide-react'
import type { AuditorPortalException, AuditorPortalOverview } from '../types/audit'
import {
  getAuditorPortalExceptions,
  getAuditorPortalOverview,
  getEvidenceVaultDownloadUrl,
} from '../api/compliance'

export default function AuditorPortalPage() {
  const { token } = useParams<{ token: string }>()
  const [overview, setOverview] = useState<AuditorPortalOverview | null>(null)
  const [exceptions, setExceptions] = useState<AuditorPortalException[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'exceptions'>('overview')

  const [loading, setLoading] = useState(true)
  const [passcodeRequired, setPasscodeRequired] = useState(false)
  const [passcodeInput, setPasscodeInput] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isVerifying, setIsVerifying] = useState(false)

  const loadPortalData = async (enteredPasscode?: string) => {
    if (!token) return
    setLoading(true)
    setErrorMessage(null)

    try {
      const data = await getAuditorPortalOverview(token, enteredPasscode)
      setOverview(data)
      setPasscodeRequired(false)

      // Also fetch exceptions
      try {
        const excs = await getAuditorPortalExceptions(token, enteredPasscode)
        setExceptions(excs)
      } catch {
        // non-blocking
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (status === 401) {
        setPasscodeRequired(true)
      } else {
        setErrorMessage(detail || 'Invalid or expired auditor link.')
      }
    } finally {
      setLoading(false)
      setIsVerifying(false)
    }
  }

  useEffect(() => {
    void loadPortalData()
  }, [token])

  const handlePasscodeSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!passcodeInput.trim()) return
    setIsVerifying(true)
    void loadPortalData(passcodeInput.trim())
  }

  // ── Passcode Entry Screen ──────────────────────────────────────────────────
  if (passcodeRequired) {
    return (
      <div className="min-h-screen bg-[#070A11] text-text-primary flex items-center justify-center p-4">
        <div className="w-full max-w-md p-8 rounded-2xl border border-white/10 bg-[#0E131F] shadow-2xl space-y-6 text-center">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-400">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Passcode Protected Vault</h1>
            <p className="text-xs text-text-secondary mt-1">
              This auditor room requires a passcode provided by the account administrator.
            </p>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
              {errorMessage}
            </div>
          )}

          <form onSubmit={handlePasscodeSubmit} className="space-y-4">
            <input
              type="password"
              required
              autoFocus
              placeholder="Enter Access Passcode"
              value={passcodeInput}
              onChange={(e) => setPasscodeInput(e.target.value)}
              className="w-full text-center tracking-widest text-sm rounded-lg border border-white/15 bg-black/50 text-text-primary px-4 py-3 focus:border-indigo-400 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isVerifying}
              className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-2"
            >
              {isVerifying ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
              <span>Verify & Access Evidence Vault</span>
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ── Loading Screen ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#070A11] text-text-primary flex items-center justify-center p-4">
        <div className="flex items-center gap-3 text-text-muted text-sm">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
          <span>Verifying cryptographic auditor token...</span>
        </div>
      </div>
    )
  }

  // ── Error Screen ───────────────────────────────────────────────────────────
  if (errorMessage || !overview) {
    return (
      <div className="min-h-screen bg-[#070A11] text-text-primary flex items-center justify-center p-4">
        <div className="max-w-md p-6 rounded-xl border border-red-500/30 bg-red-500/10 text-center space-y-3">
          <ShieldAlert className="w-10 h-10 text-red-400 mx-auto" />
          <h2 className="text-base font-bold text-red-300">Access Denied</h2>
          <p className="text-xs text-red-200/80">
            {errorMessage || 'This auditor access link is invalid, expired, or has been revoked.'}
          </p>
        </div>
      </div>
    )
  }

  const latest = overview.latest_audit
  const downloadUrl = getEvidenceVaultDownloadUrl(token!, passcodeInput || undefined)

  return (
    <div className="min-h-screen bg-[#070A11] text-text-primary p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Top Branding Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-emerald-400 uppercase tracking-wider font-semibold">
                  Verified Audit Room
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-text-muted font-mono">
                  Read-Only Non-Repudiation
                </span>
              </div>
              <h1 className="text-lg font-bold text-text-primary mt-0.5">
                {overview.company_name} — Compliance Evidence Vault
              </h1>
            </div>
          </div>

          <div className="text-right text-xs">
            <span className="text-text-muted block">Valid Until:</span>
            <span className="font-mono text-text-secondary font-medium">
              {overview.expires_at.split('T')[0]}
            </span>
          </div>
        </div>

        {/* Evidence Vault Download Hero Card */}
        {overview.can_download_raw_evidence && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.05] p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
            <div className="space-y-1.5 max-w-xl">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                <CheckCircle2 className="w-4 h-4" /> Official SOC 2 &amp; ISO 27001 Evidence Archive
              </div>
              <h2 className="text-base font-bold text-text-primary">
                Download Cryptographic Evidence Vault (.ZIP)
              </h2>
              <p className="text-xs text-text-secondary leading-relaxed">
                Contains verified cloud configuration telemetry organized by AICPA Trust Services Criteria (CC6/CC7), the business exception ledger, executive summary report, and <code className="font-mono text-emerald-300">SHA256_INTEGRITY_MANIFEST.txt</code> to mathematically prove evidence has not been tampered with.
              </p>
            </div>

            <a
              href={downloadUrl}
              download
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/25 transition-all flex-shrink-0"
            >
              <Download className="w-4 h-4" />
              <span>Download Evidence Vault (.ZIP)</span>
            </a>
          </div>
        )}

        {/* Score & Summary Metrics */}
        {latest && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#0E131F]">
              <span className="text-[10px] font-mono uppercase text-text-muted">Adjusted Score</span>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                {latest.score_percent}%
              </div>
              <span className="text-[10px] text-text-muted mt-0.5 block">With Approved Exceptions</span>
            </div>

            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#0E131F]">
              <span className="text-[10px] font-mono uppercase text-text-muted">Raw Baseline Score</span>
              <div className="text-2xl font-bold text-text-primary mt-1">
                {latest.raw_score_percent}%
              </div>
              <span className="text-[10px] text-text-muted mt-0.5 block">Unadjusted Cloud Status</span>
            </div>

            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#0E131F]">
              <span className="text-[10px] font-mono uppercase text-text-muted">Controls Assessed</span>
              <div className="text-2xl font-bold text-indigo-300 mt-1">
                {latest.total_controls}
              </div>
              <div className="text-[10px] text-emerald-400 mt-0.5">
                {latest.controls_passed} Passed · {latest.controls_failed} Failed
              </div>
            </div>

            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#0E131F]">
              <span className="text-[10px] font-mono uppercase text-text-muted">Business Exceptions</span>
              <div className="text-2xl font-bold text-amber-300 mt-1">
                {overview.active_exceptions_count}
              </div>
              <span className="text-[10px] text-text-muted mt-0.5 block">Compensating Controls</span>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-white/[0.08] pb-3 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'overview'
                ? 'bg-indigo-500/12 text-indigo-300 border border-indigo-500/40'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Audit History &amp; Cadence ({overview.recent_audits.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('exceptions')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'exceptions'
                ? 'bg-indigo-500/12 text-indigo-300 border border-indigo-500/40'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Compensating Controls &amp; Exceptions ({exceptions.length})
          </button>
        </div>

        {/* Tab 1: Audit Cadence */}
        {activeTab === 'overview' && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider font-mono">
              Continuous Assessment Timeline
            </h3>
            <div className="rounded-xl border border-white/[0.08] overflow-hidden bg-[#0E131F]">
              <table className="w-full text-xs text-left">
                <thead className="bg-white/[0.03] text-text-muted font-mono uppercase text-[10px] border-b border-white/[0.08]">
                  <tr>
                    <th className="p-3">Audit Date</th>
                    <th className="p-3">Frameworks</th>
                    <th className="p-3">Adjusted Score</th>
                    <th className="p-3">Raw Score</th>
                    <th className="p-3">Audit ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {overview.recent_audits.map((audit) => (
                    <tr key={audit.audit_id} className="hover:bg-white/[0.02]">
                      <td className="p-3 font-medium text-text-primary">
                        {audit.completed_at ? audit.completed_at.split('T')[0] : 'N/A'}
                      </td>
                      <td className="p-3 uppercase font-mono text-[11px] text-text-secondary">
                        {(audit.frameworks || []).join(' · ')}
                      </td>
                      <td className="p-3 font-semibold text-emerald-400">
                        {audit.score_percent}%
                      </td>
                      <td className="p-3 text-text-secondary">
                        {audit.raw_score_percent}%
                      </td>
                      <td className="p-3 font-mono text-[10px] text-text-muted truncate max-w-[120px]">
                        {audit.audit_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Exceptions & Compensating Controls */}
        {activeTab === 'exceptions' && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider font-mono">
              Authorized Risk Acceptances &amp; Compensating Controls
            </h3>
            {exceptions.length === 0 ? (
              <div className="rounded-xl border border-white/[0.08] p-8 text-center text-xs text-text-muted bg-[#0E131F]">
                No business exceptions have been granted for this organization.
              </div>
            ) : (
              <div className="rounded-xl border border-white/[0.08] overflow-hidden bg-[#0E131F]">
                <table className="w-full text-xs text-left">
                  <thead className="bg-white/[0.03] text-text-muted font-mono uppercase text-[10px] border-b border-white/[0.08]">
                    <tr>
                      <th className="p-3">Control ID</th>
                      <th className="p-3">Business Justification</th>
                      <th className="p-3">Compensating Controls</th>
                      <th className="p-3">Authorized By</th>
                      <th className="p-3">Expires</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.06]">
                    {exceptions.map((exc) => (
                      <tr key={exc.id} className="hover:bg-white/[0.02]">
                        <td className="p-3 font-mono font-bold text-amber-300">
                          {exc.control_id}
                        </td>
                        <td className="p-3 text-text-secondary max-w-xs">
                          {exc.justification}
                        </td>
                        <td className="p-3 text-text-secondary max-w-xs">
                          {exc.compensating_controls || 'None documented'}
                        </td>
                        <td className="p-3 font-medium text-text-primary">
                          {exc.authorized_by || 'Executive Sign-off'}
                        </td>
                        <td className="p-3 text-text-muted font-mono text-[11px]">
                          {exc.expires_at ? exc.expires_at.split('T')[0] : 'Indefinite'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
