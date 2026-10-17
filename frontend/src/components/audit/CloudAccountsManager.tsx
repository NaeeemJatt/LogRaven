// LogRaven — Multi-Cloud Fleet Management & Autonomous Scheduling
//
// Allows customers to connect their AWS, GCP, and Azure infrastructure, configure
// continuous audit schedules (daily/weekly/monthly), verify cloud identity connectivity,
// and trigger 1-click on-demand compliance assessments across SOC 2, ISO 27001,
// and native CIS benchmarks.

import { useEffect, useState } from 'react'
import {
  Cloud, Plus, Loader2, Play, Trash2, AlertTriangle,
  Clock, ShieldCheck, RefreshCw, Copy, Check, X,
} from 'lucide-react'
import type { CloudAccount, CreateCloudAccountBody } from '../../types/audit'
import {
  listCloudAccounts, createCloudAccount,
  deleteCloudAccount, verifyCloudAccount, triggerAccountScan,
} from '../../api/compliance'

interface CloudAccountsManagerProps {
  onStartAudit?: (auditId: string, companyName: string) => void
}

export default function CloudAccountsManager({ onStartAudit }: CloudAccountsManagerProps) {
  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [provider, setProvider] = useState<'aws' | 'gcp' | 'azure'>('aws')
  const [name, setName] = useState('')
  const [roleArn, setRoleArn] = useState('')
  const [gcpProjectId, setGcpProjectId] = useState('')
  const [gcpServiceAccountEmail, setGcpServiceAccountEmail] = useState('')
  const [gcpWorkloadPool, setGcpWorkloadPool] = useState('')
  const [azureTenantId, setAzureTenantId] = useState('')
  const [azureSubscriptionId, setAzureSubscriptionId] = useState('')
  const [azureClientId, setAzureClientId] = useState('')
  const [scanSchedule, setScanSchedule] = useState<'none' | 'daily' | 'weekly' | 'monthly'>('weekly')
  const [frameworks, setFrameworks] = useState<string[]>(['soc2', 'cis_aws'])
  const [submitting, setSubmitting] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)

  // Active action spinners
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const fetchAccounts = async () => {
    try {
      setLoading(true)
      const data = await listCloudAccounts()
      setAccounts(data)
      setError(null)
    } catch {
      setError('Failed to load connected cloud accounts.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAccounts()
  }, [])

  const handleProviderSwitch = (newProvider: 'aws' | 'gcp' | 'azure') => {
    setProvider(newProvider)
    setModalError(null)
    if (newProvider === 'aws') {
      setFrameworks(['soc2', 'cis_aws'])
    } else if (newProvider === 'gcp') {
      setFrameworks(['soc2', 'cis_gcp'])
    } else if (newProvider === 'azure') {
      setFrameworks(['soc2', 'cis_azure'])
    }
  }

  const handleCopy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      // ignore clipboard error
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setModalError('Account name is required.')
      return
    }

    const payload: CreateCloudAccountBody = {
      provider,
      name: name.trim(),
      default_frameworks: frameworks,
      scan_schedule: scanSchedule,
    }

    if (provider === 'aws') {
      if (!roleArn.trim() || !roleArn.startsWith('arn:aws:iam::')) {
        setModalError('Valid AWS IAM Role ARN is required (arn:aws:iam::12-digit-id:role/...).')
        return
      }
      payload.role_arn = roleArn.trim()
    } else if (provider === 'gcp') {
      if (!gcpProjectId.trim()) {
        setModalError('GCP Project ID is required.')
        return
      }
      if (!gcpServiceAccountEmail.trim() || !gcpServiceAccountEmail.includes('@')) {
        setModalError('Valid GCP Service Account Email is required.')
        return
      }
      payload.gcp_project_id = gcpProjectId.trim()
      payload.gcp_service_account_email = gcpServiceAccountEmail.trim()
      if (gcpWorkloadPool.trim()) {
        payload.gcp_workload_identity_pool = gcpWorkloadPool.trim()
      }
    } else if (provider === 'azure') {
      if (!azureTenantId.trim()) {
        setModalError('Azure Tenant ID is required.')
        return
      }
      if (!azureSubscriptionId.trim()) {
        setModalError('Azure Subscription ID is required.')
        return
      }
      if (!azureClientId.trim()) {
        setModalError('Azure Application (Client) ID is required.')
        return
      }
      payload.azure_tenant_id = azureTenantId.trim()
      payload.azure_subscription_id = azureSubscriptionId.trim()
      payload.azure_client_id = azureClientId.trim()
    }

    setSubmitting(true)
    setModalError(null)
    try {
      const newAcc = await createCloudAccount(payload)
      setAccounts((prev) => [newAcc, ...prev])
      setIsModalOpen(false)
      setName('')
      setRoleArn('')
      setGcpProjectId('')
      setGcpServiceAccountEmail('')
      setGcpWorkloadPool('')
      setAzureTenantId('')
      setAzureSubscriptionId('')
      setAzureClientId('')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setModalError(detail || 'Failed to connect cloud account.')
    } finally {
      setSubmitting(false)
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
    } catch {
      setError(`Failed to trigger scan for ${account.name}.`)
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleVerify = async (accountId: string) => {
    setActionLoadingId(accountId)
    try {
      const updated = await verifyCloudAccount(accountId)
      setAccounts((prev) => prev.map((a) => (a.id === accountId ? updated : a)))
    } catch {
      setError('Verification failed.')
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
    } catch {
      setError(`Failed to delete account ${accName}.`)
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

  const availableFrameworks = provider === 'gcp'
    ? ['soc2', 'iso27001', 'cis_gcp']
    : provider === 'azure'
    ? ['soc2', 'iso27001', 'cis_azure']
    : ['soc2', 'iso27001', 'cis_aws']

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Cloud className="w-5 h-5 text-indigo-400" /> Connected Cloud Accounts
            </h2>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
              Fleet ({accounts.length})
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1 max-w-xl">
            Register your AWS, GCP, or Azure infrastructure once. LogRaven maintains verified identity credentials and autonomously runs continuous compliance assessments on your chosen schedule.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all flex-shrink-0"
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
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mr-2" /> Loading accounts...
        </div>
      ) : accounts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 p-12 text-center space-y-3">
          <Cloud className="w-10 h-10 text-text-muted mx-auto stroke-[1.2]" />
          <h3 className="text-sm font-semibold text-text-primary">No cloud accounts connected</h3>
          <p className="text-xs text-text-secondary max-w-md mx-auto">
            Connect your AWS organization, GCP project, or Azure subscription to automate continuous audits across SOC 2, ISO 27001, and CIS benchmarks.
          </p>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Connect your first account
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {accounts.map((acc) => {
            const isLoading = actionLoadingId === acc.id
            const isConnected = acc.health_status === 'connected'
            const isError = acc.health_status === 'permission_error'
            const idInfo = getProviderIdentifier(acc)

            return (
              <div
                key={acc.id}
                className="rounded-xl border border-white/[0.08] bg-[#0d121d] p-5 space-y-4 hover:border-white/[0.14] transition-colors relative"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getProviderBadgeStyle(acc.provider)}`}>
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
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Connected
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
                    <span className="text-[10px] font-mono uppercase text-text-muted block">Scan Schedule</span>
                    <span className="font-medium text-text-primary flex items-center gap-1 mt-0.5 capitalize">
                      <Clock className="w-3 h-3 text-indigo-400" /> {acc.scan_schedule}
                    </span>
                    {acc.next_run_at && (
                      <span className="text-[10px] text-text-muted block mt-0.5">
                        Next: {acc.next_run_at.split('T')[0]}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase text-text-muted block">Posture Score</span>
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
                  <span className="text-[10px] font-mono uppercase text-text-muted mr-1">Frameworks:</span>
                  {(acc.default_frameworks || ['soc2']).map((fw) => (
                    <span
                      key={fw}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/[0.04] border border-white/[0.08] text-text-secondary uppercase"
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
                    <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
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
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
                    >
                      {isLoading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
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

      {/* Connect Account Modal */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
          role="presentation"
        >
          <div
            className="w-full max-w-lg p-6 relative border border-white/[0.12] bg-[#0E131F] shadow-2xl rounded-xl space-y-5"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-text-muted hover:text-text-primary p-1 rounded-lg"
              aria-label="Close modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 text-indigo-400">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-text-primary">Connect Cloud Account</h3>
                <p className="text-xs text-text-muted">Register AWS, GCP, or Azure credentials for automated continuous auditing.</p>
              </div>
            </div>

            {/* Provider Selector Tabs */}
            <div className="grid grid-cols-3 gap-2 p-1 rounded-lg bg-black/40 border border-white/[0.08]">
              <button
                type="button"
                onClick={() => handleProviderSwitch('aws')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  provider === 'aws'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                    : 'text-text-muted hover:text-text-secondary hover:bg-white/5'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                AWS
              </button>
              <button
                type="button"
                onClick={() => handleProviderSwitch('gcp')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  provider === 'gcp'
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm'
                    : 'text-text-muted hover:text-text-secondary hover:bg-white/5'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                GCP
              </button>
              <button
                type="button"
                onClick={() => handleProviderSwitch('azure')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold transition-all ${
                  provider === 'azure'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-text-muted hover:text-text-secondary hover:bg-white/5'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Azure
              </button>
            </div>

            {modalError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="account-name" className="block text-xs font-semibold text-text-primary mb-1">
                  Account Name <span className="text-red-400">*</span>
                </label>
                <input
                  id="account-name"
                  type="text"
                  required
                  placeholder={
                    provider === 'gcp'
                      ? 'e.g. Production GCP Project'
                      : provider === 'azure'
                      ? 'e.g. Production Azure Subscription'
                      : 'e.g. Production AWS'
                  }
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full text-xs rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                />
              </div>

              {/* Provider-Specific Credential Inputs */}
              {provider === 'aws' && (
                <div>
                  <label htmlFor="role-arn" className="block text-xs font-semibold text-text-primary mb-1">
                    AWS IAM Role ARN <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="role-arn"
                    type="text"
                    required
                    placeholder="arn:aws:iam::123456789012:role/LogRavenAuditRole"
                    value={roleArn}
                    onChange={(e) => setRoleArn(e.target.value)}
                    className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                  />
                  <span className="text-[10px] text-text-muted mt-1 block">
                    Must be configured with SecurityAudit managed policy and an AssumeRole trust policy for LogRaven.
                  </span>
                </div>
              )}

              {provider === 'gcp' && (
                <div className="space-y-3">
                  <div>
                    <label htmlFor="gcp-project-id" className="block text-xs font-semibold text-text-primary mb-1">
                      GCP Project ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="gcp-project-id"
                      type="text"
                      required
                      placeholder="my-company-prod-123456"
                      value={gcpProjectId}
                      onChange={(e) => setGcpProjectId(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="gcp-service-account" className="block text-xs font-semibold text-text-primary mb-1">
                      Service Account Email <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="gcp-service-account"
                      type="email"
                      required
                      placeholder="lograven-auditor@my-company-prod-123456.iam.gserviceaccount.com"
                      value={gcpServiceAccountEmail}
                      onChange={(e) => setGcpServiceAccountEmail(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                    <span className="text-[10px] text-text-muted mt-1 block">
                      Requires Viewer and Security Reviewer IAM roles on the target GCP Project.
                    </span>
                  </div>
                  <div>
                    <label htmlFor="gcp-workload-pool" className="block text-xs font-semibold text-text-primary mb-1">
                      Workload Identity Pool <span className="text-text-muted">(Optional)</span>
                    </label>
                    <input
                      id="gcp-workload-pool"
                      type="text"
                      placeholder="projects/123456/locations/global/workloadIdentityPools/lograven-pool"
                      value={gcpWorkloadPool}
                      onChange={(e) => setGcpWorkloadPool(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                </div>
              )}

              {provider === 'azure' && (
                <div className="space-y-3">
                  <div>
                    <label htmlFor="azure-tenant-id" className="block text-xs font-semibold text-text-primary mb-1">
                      Azure Directory (Tenant) ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="azure-tenant-id"
                      type="text"
                      required
                      placeholder="00000000-0000-0000-0000-000000000000"
                      value={azureTenantId}
                      onChange={(e) => setAzureTenantId(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="azure-subscription-id" className="block text-xs font-semibold text-text-primary mb-1">
                      Azure Subscription ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="azure-subscription-id"
                      type="text"
                      required
                      placeholder="11111111-1111-1111-1111-111111111111"
                      value={azureSubscriptionId}
                      onChange={(e) => setAzureSubscriptionId(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label htmlFor="azure-client-id" className="block text-xs font-semibold text-text-primary mb-1">
                      Azure Application (Client) ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="azure-client-id"
                      type="text"
                      required
                      placeholder="22222222-2222-2222-2222-222222222222"
                      value={azureClientId}
                      onChange={(e) => setAzureClientId(e.target.value)}
                      className="w-full text-xs font-mono rounded-lg border border-white/10 bg-black/40 text-text-primary px-3 py-2 placeholder:text-text-muted/60 focus:border-indigo-400 focus:outline-none"
                    />
                    <span className="text-[10px] text-text-muted mt-1 block">
                      Register an App in Microsoft Entra ID with Reader RBAC role on the target Subscription.
                    </span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="scan-schedule" className="block text-xs font-semibold text-text-primary mb-1">
                    Autonomous Schedule
                  </label>
                  <select
                    id="scan-schedule"
                    value={scanSchedule}
                    onChange={(e) => setScanSchedule(e.target.value as 'none' | 'daily' | 'weekly' | 'monthly')}
                    className="w-full text-xs rounded-lg border border-white/10 bg-[#161B26] text-text-primary px-3 py-2 focus:border-indigo-400 focus:outline-none"
                  >
                    <option value="weekly">Weekly (Recommended)</option>
                    <option value="daily">Daily Continuous</option>
                    <option value="monthly">Monthly Periodic</option>
                    <option value="none">Manual On-Demand Only</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text-primary mb-1">
                    Default Frameworks
                  </label>
                  <div className="flex items-center gap-2 pt-1.5 flex-wrap">
                    {availableFrameworks.map((fw) => {
                      const selected = frameworks.includes(fw)
                      return (
                        <button
                          key={fw}
                          type="button"
                          onClick={() => {
                            setFrameworks((prev) =>
                              prev.includes(fw) ? prev.filter((f) => f !== fw) : [...prev, fw],
                            )
                          }}
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase transition-colors ${
                            selected
                              ? 'border-indigo-500/50 bg-indigo-500/20 text-indigo-200'
                              : 'border-white/10 bg-white/5 text-text-muted'
                          }`}
                        >
                          {fw}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-2 text-xs text-text-muted hover:text-text-primary rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                >
                  {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                  <span>Save & Connect</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
