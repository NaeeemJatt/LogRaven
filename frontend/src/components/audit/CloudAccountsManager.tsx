// LogRaven — Multi-Cloud Fleet Management & Autonomous Scheduling
//
// Allows customers to connect their AWS, GCP, and Azure infrastructure, configure
// continuous audit schedules (daily/weekly/monthly), verify cloud identity connectivity,
// and trigger 1-click on-demand compliance assessments across SOC 2, ISO 27001,
// and native CIS benchmarks.

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Cloud, Plus, Loader2, Play, Trash2, AlertTriangle,
  Clock, RefreshCw, Copy, Check,
} from 'lucide-react'
import type { CloudAccount } from '../../types/audit'
import {
  listCloudAccounts,
  deleteCloudAccount, verifyCloudAccount, triggerAccountScan,
} from '../../api/compliance'
import { normalizeApiError } from '../../api/errors'

interface CloudAccountsManagerProps {
  onStartAudit?: (auditId: string, companyName: string) => void
}

export default function CloudAccountsManager({ onStartAudit }: CloudAccountsManagerProps) {
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Active action spinners
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const fetchAccounts = async () => {
    try {
      setLoading(true)
      const data = await listCloudAccounts()
      if (Array.isArray(data)) {
        setAccounts(data)
      }
      setError(null)
    } catch {
      setError('Failed to load connected cloud accounts.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchAccounts()
  }, [])

  const handleCopy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      // ignore clipboard error
    }
  }

  const handleScanNow = async (account: CloudAccount) => {
    setActionLoadingId(account.id)
    try {
      const res = await triggerAccountScan(account.id)
      if (onStartAudit) {
        onStartAudit(res.audit_id, account.name)
      } else {
        await fetchAccounts()
      }
    } catch (err: unknown) {
      setError(normalizeApiError(err, `Failed to trigger scan for ${account.name}.`).message)
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleVerify = async (accountId: string) => {
    setActionLoadingId(accountId)
    try {
      const updated = await verifyCloudAccount(accountId)
      setAccounts((prev) => prev.map((a) => (a.id === accountId ? updated : a)))
    } catch (err: unknown) {
      setError(normalizeApiError(err, 'Verification failed.').message)
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleDelete = async (accountId: string, accName: string) => {
    if (!window.confirm(`Disconnect cloud account '${accName}'? Historical audits will be preserved.`)) {
      return
    }
    setActionLoadingId(accountId)
    try {
      await deleteCloudAccount(accountId)
      setAccounts((prev) => prev.filter((a) => a.id !== accountId))
    } catch (err: unknown) {
      setError(normalizeApiError(err, `Failed to delete account ${accName}.`).message)
    } finally {
      setActionLoadingId(null)
    }
  }

  const getProviderBadgeStyle = (prov: string) => {
    switch (prov.toLowerCase()) {
      case 'gcp':
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30'
      case 'azure':
        return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
      case 'aws':
      default:
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30'
    }
  }

  const getProviderIdentifier = (acc: CloudAccount) => {
    const prov = (acc.provider || 'aws').toLowerCase()
    if (prov === 'gcp') {
      return {
        label: 'GCP Project ID',
        value: acc.gcp_project_id || acc.account_id || '—',
        stripValue: acc.gcp_service_account_email || acc.role_arn || 'Configured via Service Account',
      }
    }
    if (prov === 'azure') {
      return {
        label: 'Azure Subscription',
        value: acc.azure_subscription_id || acc.account_id || '—',
        stripValue: `Tenant: ${acc.azure_tenant_id || '—'} | Client: ${acc.azure_client_id || '—'}`,
      }
    }
    return {
      label: 'AWS Account ID',
      value: acc.account_id || '—',
      stripValue: acc.role_arn || '—',
    }
  }

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 p-4 sm:p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Cloud className="w-5 h-5 text-amber-400" /> Connected Cloud Accounts
            </h2>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/30">
              Fleet ({accounts?.length ?? 0})
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1 max-w-xl">
            Register your AWS, GCP, or Azure infrastructure once. LogRaven maintains verified identity credentials and autonomously runs continuous compliance assessments on your chosen schedule.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/compliance/connect/step-1')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-400 hover:bg-amber-300 text-stone-950 font-semibold text-xs shadow-sm transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] flex-shrink-0"
        >
          <Plus className="w-4 h-4" /> Connect Cloud Account
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Account Cards Grid */}
      {loading ? (
        <div className="flex items-center justify-center p-12 text-text-muted">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-amber-400 mr-2" /> Loading accounts…
        </div>
      ) : accounts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 py-7 px-6 text-center space-y-2.5">
          <Cloud className="w-10 h-10 text-text-muted mx-auto stroke-[1.2]" />
          <h3 className="text-sm font-semibold text-text-primary">No cloud accounts connected</h3>
          <p className="text-xs text-text-secondary max-w-md mx-auto">
            Connect your AWS organization, GCP project, or Azure subscription to automate continuous audits across SOC 2, ISO 27001, and CIS benchmarks.
          </p>
          <button
            type="button"
            onClick={() => navigate('/compliance/connect/step-1')}
            className="mt-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 border border-amber-400/30 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" /> Connect your first account
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {(accounts || []).filter(Boolean).map((acc) => {
            const isLoading = actionLoadingId === acc.id
            const isConnected = acc.health_status === 'connected'
            const isError = acc.health_status === 'permission_error'
            const idInfo = getProviderIdentifier(acc)

            return (
              <div
                key={acc.id}
                className="rounded-xl border border-white/[0.08] bg-surface/60 p-5 space-y-4 hover:border-white/[0.14] transition-colors relative"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getProviderBadgeStyle(acc.provider)}`}>
                        {acc.provider.toUpperCase()}
                      </span>
                      <h3 className="text-sm font-semibold text-text-primary leading-snug">
                        {acc.name}
                      </h3>
                    </div>
                    {idInfo.value && (
                      <div className="text-[11px] font-mono text-text-muted mt-1">
                        {idInfo.label}: <strong className="text-text-secondary">{idInfo.value}</strong>
                      </div>
                    )}
                  </div>

                  {/* Health status pill */}
                  <div className="flex items-center gap-1.5">
                    {isConnected ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 motion-safe:animate-pulse" /> Connected
                      </span>
                    ) : isError ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-red-400 bg-red-500/10 border border-red-500/30 px-2 py-0.5 rounded-full">
                        <AlertTriangle className="w-3 h-3 text-red-400" /> Permission Error
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 px-2 py-0.5 rounded-full">
                        Unverified
                      </span>
                    )}
                  </div>
                </div>

                {/* Identity / Credential strip */}
                <div className="flex items-center justify-between p-2 rounded-lg bg-black/40 border border-white/[0.06] text-[11px] font-mono text-text-muted">
                  <span className="truncate max-w-[260px] sm:max-w-[340px]">{idInfo.stripValue}</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(idInfo.stripValue, acc.id)}
                    className="p-1 text-text-muted hover:text-text-primary transition-colors flex-shrink-0"
                    title="Copy Credentials"
                  >
                    {copiedKey === acc.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                {/* Metadata details */}
                <div className="grid grid-cols-2 gap-3 pt-1 text-xs">
                  <div>
                    <span className="text-xs text-text-muted block">Scan schedule</span>
                    <span className="font-medium text-text-primary flex items-center gap-1 mt-0.5 capitalize">
                      <Clock className="w-3 h-3 text-amber-400" /> {acc.scan_schedule}
                    </span>
                    {acc.next_run_at && (
                      <span className="text-[10px] text-text-muted block mt-0.5">
                        Next: {acc.next_run_at.split('T')[0]}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-xs text-text-muted block">Posture score</span>
                    {acc.latest_score_percent !== null && acc.latest_score_percent !== undefined ? (
                      <span className="font-semibold text-emerald-400 text-sm mt-0.5 block">
                        {acc.latest_score_percent}%
                      </span>
                    ) : (
                      <span className="text-[11px] text-text-muted mt-0.5 block">No audit run yet</span>
                    )}
                  </div>
                </div>

                {/* Default frameworks */}
                <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-white/[0.06]">
                  <span className="text-xs text-text-muted mr-1">Frameworks:</span>
                  {(acc.default_frameworks || ['soc2']).map((fw) => (
                    <span
                      key={fw}
                      className="px-2 py-0.5 rounded text-xs bg-white/[0.04] border border-white/[0.08] text-text-secondary"
                    >
                      {fw}
                    </span>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => handleVerify(acc.id)}
                    disabled={isLoading}
                    className="p-1.5 text-text-muted hover:text-text-primary rounded hover:bg-white/5 transition-colors text-xs flex items-center gap-1 disabled:opacity-50"
                    title="Re-verify IAM connection"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'motion-safe:animate-spin' : ''}`} />
                    <span>Verify</span>
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleDelete(acc.id, acc.name)}
                      disabled={isLoading}
                      className="p-1.5 text-text-muted hover:text-red-400 rounded hover:bg-red-500/10 transition-colors disabled:opacity-50"
                      title="Disconnect account"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleScanNow(acc)}
                      disabled={isLoading}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-stone-950 text-xs font-semibold shadow-sm transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50"
                    >
                      {isLoading ? (
                        <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5 fill-current" />
                      )}
                      <span>Run Audit Now</span>
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
