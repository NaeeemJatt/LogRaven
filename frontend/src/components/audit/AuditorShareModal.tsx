// LogRaven — Auditor Share Modal
//
// Allows compliance managers to create time-bound, read-only magic links
// for external CPAs and SOC 2 / ISO 27001 auditors to inspect evidence
// and download the cryptographic Evidence Vault ZIP.

import { useEffect, useState } from 'react'
import {
  ShieldCheck, X, Copy, Check, Loader2,
  Key, Trash2,
} from 'lucide-react'
import type { AuditorAccessToken } from '../../types/audit'
import { createAuditorToken, listAuditorTokens, revokeAuditorToken } from '../../api/compliance'

interface AuditorShareModalProps {
  isOpen: boolean
  companyName: string
  onClose: () => void
}

export default function AuditorShareModal({
  isOpen,
  companyName,
  onClose,
}: AuditorShareModalProps) {
  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create')
  const [recipientName, setRecipientName] = useState('')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [passcode, setPasscode] = useState('')
  const [durationDays, setDurationDays] = useState(30)
  const [canDownloadRaw, setCanDownloadRaw] = useState(true)
  const [frameworks] = useState<string[]>(['soc2', 'iso27001'])

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [createdShareUrl, setCreatedShareUrl] = useState<string | null>(null)
  const [isCopied, setIsCopied] = useState(false)

  const [tokensList, setTokensList] = useState<AuditorAccessToken[]>([])
  const [isLoadingTokens, setIsLoadingTokens] = useState(false)
  const [revokingId, setRevokingId] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && activeTab === 'manage') {
      void fetchTokens()
    }
  }, [isOpen, activeTab])

  const fetchTokens = async () => {
    setIsLoadingTokens(true)
    try {
      const data = await listAuditorTokens()
      setTokensList(data)
    } catch {
      // ignore list error
    } finally {
      setIsLoadingTokens(false)
    }
  }

  if (!isOpen) return null

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setErrorMessage(null)
    setCreatedShareUrl(null)

    try {
      const res = await createAuditorToken({
        company_name: companyName || 'Company',
        recipient_name: recipientName.trim() || undefined,
        recipient_email: recipientEmail.trim() || undefined,
        passcode: passcode.trim() || undefined,
        duration_days: durationDays,
        allowed_frameworks: frameworks,
        can_download_raw_evidence: canDownloadRaw,
      })

      const shareUrl = `${window.location.origin}/auditor/portal/${res.token}`
      setCreatedShareUrl(shareUrl)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail || 'Failed to generate auditor link.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCopyLink = async () => {
    if (!createdShareUrl) return
    try {
      await navigator.clipboard.writeText(createdShareUrl)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch {
      // clipboard fallback
    }
  }

  const handleRevoke = async (tokenId: string) => {
    setRevokingId(tokenId)
    try {
      await revokeAuditorToken(tokenId)
      setTokensList((prev) =>
        prev.map((t) => (t.id === tokenId ? { ...t, is_revoked: true } : t)),
      )
    } catch {
      // ignore
    } finally {
      setRevokingId(null)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
      role="presentation"
    >
      <div
        className="w-full max-w-xl p-6 relative border border-white/[0.12] bg-[#0E131F] shadow-2xl rounded-xl space-y-5"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auditor-modal-title"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-text-muted hover:text-text-primary p-1 rounded-lg"
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center flex-shrink-0 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 id="auditor-modal-title" className="text-base font-bold text-text-primary">
              External Auditor Portal
            </h3>
            <p className="text-xs text-text-muted">
              Generate a time-bound, read-only link for external CPAs to inspect evidence and download the Evidence Vault.
            </p>
          </div>
        </div>

        {/* View Tabs */}
        <div className="flex items-center gap-2 border-b border-white/[0.08] pb-2 text-xs">
          <button
            type="button"
            onClick={() => { setActiveTab('create'); setCreatedShareUrl(null); }}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'create'
                ? 'bg-indigo-500/12 text-indigo-300 border border-indigo-500/40'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Create Auditor Link
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('manage')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              activeTab === 'manage'
                ? 'bg-indigo-500/12 text-indigo-300 border border-indigo-500/40'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Manage Active Links
          </button>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
            {errorMessage}
          </div>
        )}

        {/* Tab 1: Create Link */}
        {activeTab === 'create' && (
          <div>
            {createdShareUrl ? (
              <div className="space-y-4 p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/[0.06]">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                  <Check className="w-4 h-4" /> Auditor Access Link Generated
                </div>
                <p className="text-xs text-text-secondary">
                  Share this secure link with your auditor. It grants read-only access to verify compliance snapshots and download the cryptographic Evidence Vault.
                </p>

                <div className="flex items-center gap-2 p-2 rounded-lg bg-black/60 border border-white/10">
                  <input
                    type="text"
                    readOnly
                    value={createdShareUrl}
                    className="w-full text-xs font-mono bg-transparent text-text-primary focus:outline-none select-all"
                  />
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 flex-shrink-0 transition-colors"
                  >
                    {isCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{isCopied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <div className="text-[11px] text-text-muted flex items-center justify-between">
                  <span>Expires in {durationDays} days</span>
                  <button
                    type="button"
                    onClick={() => setCreatedShareUrl(null)}
                    className="text-indigo-400 hover:underline"
                  >
                    Create another link
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-text-primary mb-1">
                      Auditor / Recipient Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Sarah Jenkins (Schellman)"
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                      className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-text-primary mb-1">
                      Recipient Email (Optional)
                    </label>
                    <input
                      type="email"
                      placeholder="e.g. auditor@firm.com"
                      value={recipientEmail}
                      onChange={(e) => setRecipientEmail(e.target.value)}
                      className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-text-primary mb-1">
                      Link Duration
                    </label>
                    <select
                      value={durationDays}
                      onChange={(e) => setDurationDays(Number(e.target.value))}
                      className="w-full text-xs rounded-lg border border-white/10 bg-[#161B26] text-text-primary px-3 py-2 focus:border-indigo-400 focus:outline-none"
                    >
                      <option value={7}>7 Days (Quick Inspection)</option>
                      <option value={14}>14 Days</option>
                      <option value={30}>30 Days (Standard Audit)</option>
                      <option value={90}>90 Days (Type II Audit Window)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-text-primary mb-1">
                      Passcode Protection (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. AuditPass2026!"
                      value={passcode}
                      onChange={(e) => setPasscode(e.target.value)}
                      className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 focus:border-indigo-400 focus:outline-none font-mono"
                    />
                  </div>
                </div>

                {/* Evidence download toggle */}
                <div className="flex items-center gap-2 p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                  <input
                    id="allow-vault"
                    type="checkbox"
                    checked={canDownloadRaw}
                    onChange={(e) => setCanDownloadRaw(e.target.checked)}
                    className="rounded border-white/20 bg-black/40 text-indigo-500 focus:ring-0"
                  />
                  <label htmlFor="allow-vault" className="text-xs text-text-secondary cursor-pointer">
                    <strong className="text-text-primary">Allow Cryptographic Evidence Vault (.ZIP) download</strong>
                    <span className="block text-[11px] text-text-muted mt-0.5">
                      Includes raw evidence snapshots and SHA256 integrity manifest for non-repudiation.
                    </span>
                  </label>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.08]">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-3 py-2 text-xs text-text-muted hover:text-text-primary rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                  >
                    {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Key className="w-3.5 h-3.5" />}
                    <span>Generate Auditor Link</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Tab 2: Manage Active Links */}
        {activeTab === 'manage' && (
          <div className="space-y-3">
            {isLoadingTokens ? (
              <div className="flex items-center justify-center p-8 text-text-muted text-xs">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400 mr-2" /> Loading auditor links...
              </div>
            ) : tokensList.length === 0 ? (
              <div className="text-center p-8 text-xs text-text-muted">
                No active auditor links created yet.
              </div>
            ) : (
              <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                {tokensList.map((token) => (
                  <div
                    key={token.id}
                    className="p-3 rounded-lg border border-white/[0.06] bg-black/30 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-primary">
                          {token.recipient_name || 'Unnamed Auditor'}
                        </span>
                        {token.is_revoked ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-500/10 text-red-400 border border-red-500/30">
                            Revoked
                          </span>
                        ) : token.is_expired ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
                            Expired
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-text-muted mt-0.5 flex items-center gap-3">
                        <span>Expires: {token.expires_at.split('T')[0]}</span>
                        <span>Views: {token.access_count}</span>
                      </div>
                    </div>

                    {!token.is_revoked && !token.is_expired && (
                      <button
                        type="button"
                        onClick={() => handleRevoke(token.id)}
                        disabled={revokingId === token.id}
                        className="p-1.5 text-text-muted hover:text-red-400 rounded hover:bg-red-500/10 transition-colors"
                        title="Revoke link"
                      >
                        {revokingId === token.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
