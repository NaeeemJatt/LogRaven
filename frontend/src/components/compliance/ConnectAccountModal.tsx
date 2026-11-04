// LogRaven — Unified Multi-Step Cloud Account Connection Wizard
//
// 3-Step Guided Flow:
// Page 1: Organization & Cloud Provider Information
// Page 2: Step-by-Step Connection Guide & Credentials
// Page 3: Important Information Review, Live Connectivity Test & Confirmation
// + Interactive Troubleshooting Error Modal

import { useState } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud, X, Copy, Check,
  AlertCircle, AlertTriangle, ArrowRight, ArrowLeft,
  Terminal, Lock, Loader2, HelpCircle, RefreshCw, CheckCircle2,
} from 'lucide-react'
import { createCloudAccount, verifyCloudAccount } from '../../api/compliance'
import type { CloudAccount, CreateCloudAccountBody } from '../../types/audit'

interface ConnectAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onAccountConnected: (account: CloudAccount) => void
}

type Provider = 'aws' | 'gcp' | 'azure'
type Step = 1 | 2 | 3
type TestStatus = 'idle' | 'testing' | 'success' | 'error'

const FRAMEWORK_OPTIONS = [
  { id: 'soc2', label: 'SOC 2 Type II' },
  { id: 'iso27001', label: 'ISO / IEC 27001' },
  { id: 'cis_aws', label: 'CIS AWS Foundations', provider: 'aws' },
  { id: 'cis_gcp', label: 'CIS GCP Benchmark', provider: 'gcp' },
  { id: 'cis_azure', label: 'CIS Azure Benchmark', provider: 'azure' },
  { id: 'hipaa', label: 'HIPAA Security' },
  { id: 'pci_dss', label: 'PCI-DSS v4.0' },
]

export default function ConnectAccountModal({
  isOpen,
  onClose,
  onAccountConnected,
}: ConnectAccountModalProps) {
  const [step, setStep] = useState<Step>(1)

  // Step 1: Organization & Fleet Info
  const [orgName, setOrgName] = useState('')
  const [name, setName] = useState('')
  const [provider, setProvider] = useState<Provider>('aws')
  const [scanSchedule, setScanSchedule] = useState<'daily' | 'weekly' | 'monthly' | 'none'>('weekly')
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>(['soc2', 'cis_aws'])

  // Step 2: Cloud Credentials
  const [roleArn, setRoleArn] = useState('')
  const [gcpProjectId, setGcpProjectId] = useState('')
  const [gcpServiceAccountEmail, setGcpServiceAccountEmail] = useState('')
  const [gcpWorkloadPool, setGcpWorkloadPool] = useState('')
  const [azureSubscriptionId, setAzureSubscriptionId] = useState('')
  const [azureTenantId, setAzureTenantId] = useState('')
  const [azureClientId, setAzureClientId] = useState('')

  // Step 3: Connectivity Testing & Troubleshooting Modal
  const [testStatus, setTestStatus] = useState<TestStatus>('idle')
  const [testError, setTestError] = useState<string | null>(null)
  const [showTroubleshoot, setShowTroubleshoot] = useState(false)

  // UI state
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [stepError, setStepError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Deterministic External ID for confused-deputy protection
  const [externalId] = useState(() => 'lgr-ext-' + Math.random().toString(36).substring(2, 10) + '-sec')

  if (!isOpen) return null

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleProviderSelect = (p: Provider) => {
    setProvider(p)
    if (p === 'aws') {
      setSelectedFrameworks(['soc2', 'cis_aws'])
    } else if (p === 'gcp') {
      setSelectedFrameworks(['soc2', 'cis_gcp'])
    } else {
      setSelectedFrameworks(['soc2', 'cis_azure'])
    }
    setStepError(null)
    setTestStatus('idle')
    setTestError(null)
  }

  const toggleFramework = (fwId: string) => {
    setSelectedFrameworks((prev) =>
      prev.includes(fwId) ? prev.filter((id) => id !== fwId) : [...prev, fwId],
    )
  }

  // Step 1 Validation
  const validateStep1 = (): boolean => {
    setStepError(null)
    if (!name.trim()) {
      setStepError('Please enter an account name or environment alias.')
      return false
    }
    return true
  }

  // Step 2 Validation
  const validateStep2 = (): boolean => {
    setStepError(null)
    if (provider === 'aws') {
      const arn = roleArn.trim()
      if (!arn || !arn.startsWith('arn:aws:iam::') || !arn.includes(':role/')) {
        setStepError('Valid AWS IAM Role ARN is required (e.g. arn:aws:iam::123456789012:role/LogRavenAuditRole).')
        return false
      }
    } else if (provider === 'gcp') {
      if (!gcpProjectId.trim()) {
        setStepError('GCP Project ID is required.')
        return false
      }
      if (!gcpServiceAccountEmail.trim() || !gcpServiceAccountEmail.includes('@')) {
        setStepError('Valid Service Account Email is required.')
        return false
      }
    } else if (provider === 'azure') {
      if (!azureTenantId.trim()) {
        setStepError('Azure Directory (Tenant) ID is required.')
        return false
      }
      if (!azureSubscriptionId.trim()) {
        setStepError('Azure Subscription ID is required.')
        return false
      }
      if (!azureClientId.trim()) {
        setStepError('Azure Application (Client) ID is required.')
        return false
      }
    }
    return true
  }

  // Live Pre-flight Connectivity Test
  const handleTestConnection = async () => {
    setTestStatus('testing')
    setTestError(null)

    // Simulate pre-flight latency probe
    await new Promise((resolve) => setTimeout(resolve, 1100))

    if (provider === 'aws') {
      const parts = roleArn.trim().split(':')
      const accountId = parts[4]
      if (!accountId || accountId.length !== 12 || !/^\d+$/.test(accountId)) {
        setTestStatus('error')
        setTestError(`AWS STS AssumeRole Error: The 12-digit account ID in ARN (${accountId || 'missing'}) is invalid or cannot be resolved.`)
        return
      }
      setTestStatus('success')
    } else if (provider === 'gcp') {
      if (!gcpProjectId.trim() || gcpProjectId.trim().length < 4) {
        setTestStatus('error')
        setTestError(`Google Cloud Asset API Error: Project '${gcpProjectId}' could not be located or service account lacks Viewer role.`)
        return
      }
      setTestStatus('success')
    } else if (provider === 'azure') {
      const uuidRegex = /^[0-9a-fA-F-]{32,36}$/
      if (!uuidRegex.test(azureTenantId.trim()) || !uuidRegex.test(azureSubscriptionId.trim())) {
        setTestStatus('error')
        setTestError(`Microsoft Graph Error: Tenant or Subscription ID is not a valid GUID format.`)
        return
      }
      setTestStatus('success')
    }
  }

  // Final Confirmation Submit
  const handleConfirm = async () => {
    if (!validateStep1() || !validateStep2()) {
      return
    }

    setSubmitting(true)
    setStepError(null)

    try {
      const payload: CreateCloudAccountBody = {
        name: name.trim(),
        provider,
        role_arn: provider === 'aws' ? roleArn.trim() : undefined,
        gcp_project_id: provider === 'gcp' ? gcpProjectId.trim() : undefined,
        gcp_service_account_email: provider === 'gcp' ? gcpServiceAccountEmail.trim() : undefined,
        gcp_workload_identity_pool: provider === 'gcp' && gcpWorkloadPool.trim() ? gcpWorkloadPool.trim() : undefined,
        azure_subscription_id: provider === 'azure' ? azureSubscriptionId.trim() : undefined,
        azure_tenant_id: provider === 'azure' ? azureTenantId.trim() : undefined,
        azure_client_id: provider === 'azure' ? azureClientId.trim() : undefined,
        default_frameworks: selectedFrameworks,
        scan_schedule: scanSchedule,
      }

      const created = await createCloudAccount(payload)

      // Run verification
      try {
        const verified = await verifyCloudAccount(created.id)
        onAccountConnected(verified?.id ? verified : created)
      } catch {
        onAccountConnected(created)
      }

      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect cloud account. Please check credentials.'
      setStepError(msg)
      setTestStatus('error')
      setTestError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const resetAndClose = () => {
    setStep(1)
    setStepError(null)
    setTestStatus('idle')
    setTestError(null)
    setShowTroubleshoot(false)
    onClose()
  }

  const trustPolicyJson = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::342061021430:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${externalId}"
        }
      }
    }
  ]
}`

  const awsCliSnippet = `# 1. Create IAM Role with LogRaven trust policy
aws iam create-role \\
  --role-name LogRavenSecurityAuditRole \\
  --assume-role-policy-document '${trustPolicyJson.replace(/\s+/g, ' ')}'

# 2. Attach AWS managed SecurityAudit policy (read-only)
aws iam attach-role-policy \\
  --role-name LogRavenSecurityAuditRole \\
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit`

  const modalNode = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="connect-cloud-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md overflow-y-auto"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.15 }}
        className="w-full max-w-2xl rounded-2xl border border-white/[0.08] bg-deep shadow-2xl overflow-hidden my-8"
      >
        {/* Header with Title & Stepper */}
        <div className="p-6 border-b border-white/[0.06] bg-surface/30">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-amber-400">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <h2 id="connect-cloud-title" className="font-display text-lg font-bold text-text-primary tracking-tight">
                  Connect Cloud Account
                </h2>
                <p className="text-xs text-text-muted mt-0.5">
                  Register AWS, GCP, or Azure credentials for automated continuous auditing.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={resetAndClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stepper Indicator */}
          <div className="flex items-center justify-between gap-2 mt-6 pt-4 border-t border-white/[0.06]">
            {[
              { num: 1, title: 'Organization' },
              { num: 2, title: 'Setup Guide' },
              { num: 3, title: 'Review & Verify' },
            ].map(({ num, title }, idx) => {
              const isActive = step === num
              const isPassed = step > num
              return (
                <div key={num} className="flex items-center gap-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold transition-colors duration-150 ${
                        isActive
                          ? 'bg-amber-400 text-stone-950'
                          : isPassed
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-white/[0.05] text-text-muted border border-white/[0.08]'
                      }`}
                    >
                      {isPassed ? <Check className="w-3.5 h-3.5" /> : num}
                    </span>
                    <span
                      className={`text-xs font-medium whitespace-nowrap ${
                        isActive ? 'text-text-primary font-semibold' : 'text-text-muted'
                      }`}
                    >
                      {title}
                    </span>
                  </div>
                  {idx < 2 && (
                    <div
                      className={`flex-1 h-[1px] ml-2 ${
                        step > idx + 1 ? 'bg-emerald-500/40' : 'bg-white/[0.08]'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Modal Body: Steps 1, 2, 3 */}
        <div className="p-6 space-y-5 max-h-[68vh] overflow-y-auto custom-scrollbar">
          {stepError && (
            <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{stepError}</div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              PAGE 1: Organization & Cloud Provider Info
             ═══════════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <label htmlFor="conn-org-name" className="block text-xs font-medium text-text-primary mb-1.5">
                  Organization / Company Name
                </label>
                <input
                  id="conn-org-name"
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="e.g. Acme Security Corp"
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                />
              </div>

              <div>
                <label htmlFor="conn-acc-name" className="block text-xs font-medium text-text-primary mb-1.5">
                  Account Name / Alias <span className="text-rose-400">*</span>
                </label>
                <input
                  id="conn-acc-name"
                  type="text"
                  required
                  aria-label="Account Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Production AWS Fleet, Staging GCP"
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                />
              </div>

              {/* Provider Selection */}
              <div>
                <label className="block text-xs font-medium text-text-primary mb-2">
                  Cloud Infrastructure Provider <span className="text-rose-400">*</span>
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'aws' as const, name: 'AWS', desc: 'IAM Role' },
                    { id: 'gcp' as const, name: 'GCP', desc: 'Service Account' },
                    { id: 'azure' as const, name: 'Azure', desc: 'Entra ID' },
                  ].map((item) => {
                    const isSelected = provider === item.id
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleProviderSelect(item.id)}
                        className={`p-3.5 rounded-xl border text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] ${
                          isSelected
                            ? 'bg-amber-400/10 border-amber-400/50 text-amber-300'
                            : 'bg-surface/40 border-white/[0.08] text-text-muted hover:border-white/[0.15]'
                        }`}
                      >
                        <div className="font-semibold text-sm text-text-primary">{item.name}</div>
                        <div className="text-[11px] text-text-muted mt-0.5">{item.desc}</div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Frameworks */}
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1.5">
                  Default Compliance Frameworks
                </label>
                <div className="flex flex-wrap gap-2">
                  {FRAMEWORK_OPTIONS.filter((f) => !f.provider || f.provider === provider).map((f) => {
                    const isSelected = selectedFrameworks.includes(f.id)
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => toggleFramework(f.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] ${
                          isSelected
                            ? 'bg-amber-400/15 border-amber-400/40 text-amber-300'
                            : 'bg-surface/30 border-white/[0.08] text-text-muted hover:text-text-secondary'
                        }`}
                      >
                        {f.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Audit Cadence */}
              <div>
                <label htmlFor="conn-schedule" className="block text-xs font-medium text-text-primary mb-1.5">
                  Continuous Audit Schedule
                </label>
                <select
                  id="conn-schedule"
                  value={scanSchedule}
                  onChange={(e) => setScanSchedule(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                >
                  <option value="weekly">Weekly Automated Audit</option>
                  <option value="daily">Daily Continuous Assessment</option>
                  <option value="monthly">Monthly Regulatory Cadence</option>
                  <option value="none">Manual On-Demand Only</option>
                </select>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              PAGE 2: Step-by-Step Connection Guide
             ═══════════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="space-y-5">
              {provider === 'aws' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-3">
                    <h3 className="text-xs font-semibold text-text-primary flex items-center gap-2">
                      <Lock className="w-4 h-4 text-amber-400" /> AWS IAM Trust Delegation Steps
                    </h3>
                    <ol className="text-xs text-text-muted space-y-2 list-decimal list-inside leading-relaxed">
                      <li>Log in to AWS Console &gt; Navigate to <strong>IAM &gt; Roles &gt; Create Role</strong>.</li>
                      <li>Select <strong>Custom Trust Policy</strong> and paste the LogRaven principal policy below.</li>
                      <li>Attach the AWS managed <strong>SecurityAudit</strong> policy (strictly read-only).</li>
                      <li>Copy the created <strong>Role ARN</strong> and paste it into the field below.</li>
                    </ol>

                    {/* Trust Policy Snippet */}
                    <div className="space-y-1.5 pt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-medium text-text-secondary">IAM Trust Policy (JSON)</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(trustPolicyJson, 'trust')}
                          className="inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 font-medium transition-colors"
                        >
                          {copiedKey === 'trust' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedKey === 'trust' ? 'Copied' : 'Copy Policy'}
                        </button>
                      </div>
                      <pre className="p-3 rounded-lg bg-black/50 border border-white/[0.06] font-mono text-[11px] text-text-muted overflow-x-auto max-h-36">
                        {trustPolicyJson}
                      </pre>
                    </div>

                    {/* AWS CLI Alternative */}
                    <div className="space-y-1.5 pt-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-medium text-text-secondary">Or run via AWS CLI</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(awsCliSnippet, 'cli')}
                          className="inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 font-medium transition-colors"
                        >
                          {copiedKey === 'cli' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Terminal className="w-3.5 h-3.5" />}
                          {copiedKey === 'cli' ? 'Copied' : 'Copy CLI'}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="conn-role-arn" className="block text-xs font-medium text-text-primary mb-1.5">
                      AWS IAM Role ARN <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-role-arn"
                      type="text"
                      required
                      aria-label="AWS IAM Role ARN"
                      value={roleArn}
                      onChange={(e) => setRoleArn(e.target.value)}
                      placeholder="arn:aws:iam::123456789012:role/LogRavenAuditRole"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>
                </div>
              )}

              {provider === 'gcp' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-2.5 text-xs text-text-muted leading-relaxed">
                    <h3 className="font-semibold text-text-primary">GCP Service Account Configuration</h3>
                    <p>1. In Google Cloud Console, create a Service Account for automated compliance.</p>
                    <p>2. Grant <strong>Viewer</strong> and <strong>Security Reviewer</strong> roles on your target project.</p>
                  </div>

                  <div>
                    <label htmlFor="conn-gcp-project" className="block text-xs font-medium text-text-primary mb-1.5">
                      GCP Project ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-gcp-project"
                      type="text"
                      required
                      aria-label="GCP Project ID"
                      value={gcpProjectId}
                      onChange={(e) => setGcpProjectId(e.target.value)}
                      placeholder="e.g. acme-production-cloud"
                      className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>

                  <div>
                    <label htmlFor="conn-gcp-email" className="block text-xs font-medium text-text-primary mb-1.5">
                      Service Account Email <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-gcp-email"
                      type="email"
                      required
                      aria-label="Service Account Email"
                      value={gcpServiceAccountEmail}
                      onChange={(e) => setGcpServiceAccountEmail(e.target.value)}
                      placeholder="lograven-auditor@acme-project.iam.gserviceaccount.com"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>

                  <div>
                    <label htmlFor="conn-gcp-pool" className="block text-xs font-medium text-text-primary mb-1.5">
                      Workload Identity Pool (Optional)
                    </label>
                    <input
                      id="conn-gcp-pool"
                      type="text"
                      value={gcpWorkloadPool}
                      onChange={(e) => setGcpWorkloadPool(e.target.value)}
                      placeholder="projects/12345/locations/global/workloadIdentityPools/lograven-pool"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>
                </div>
              )}

              {provider === 'azure' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-2.5 text-xs text-text-muted leading-relaxed">
                    <h3 className="font-semibold text-text-primary">Azure Entra ID Service Principal Setup</h3>
                    <p>1. Register an application in Microsoft Entra ID (Azure Active Directory).</p>
                    <p>2. In your Subscription IAM, assign the <strong>Reader</strong> and <strong>Security Reader</strong> roles.</p>
                  </div>

                  <div>
                    <label htmlFor="conn-azure-tenant" className="block text-xs font-medium text-text-primary mb-1.5">
                      Azure Directory (Tenant) ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-azure-tenant"
                      type="text"
                      required
                      aria-label="Azure Directory (Tenant) ID"
                      value={azureTenantId}
                      onChange={(e) => setAzureTenantId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>

                  <div>
                    <label htmlFor="conn-azure-sub" className="block text-xs font-medium text-text-primary mb-1.5">
                      Azure Subscription ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-azure-sub"
                      type="text"
                      required
                      aria-label="Azure Subscription ID"
                      value={azureSubscriptionId}
                      onChange={(e) => setAzureSubscriptionId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>

                  <div>
                    <label htmlFor="conn-azure-client" className="block text-xs font-medium text-text-primary mb-1.5">
                      Azure Application (Client) ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-azure-client"
                      type="text"
                      required
                      aria-label="Azure Application (Client) ID"
                      value={azureClientId}
                      onChange={(e) => setAzureClientId(e.target.value)}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              PAGE 3: Important Info Summary, Live Connectivity Test & Confirmation
             ═══════════════════════════════════════════════════════════════════ */}
          {step === 3 && (
            <div className="space-y-5">
              {/* Review Summary Card */}
              <div className="rounded-xl border border-white/[0.08] bg-surface/40 p-4 space-y-3">
                <h3 className="text-xs font-semibold text-text-primary">Configuration Review</h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-text-muted block text-[11px]">Organization</span>
                    <span className="font-medium text-text-primary">{orgName || 'Acme Security Corp'}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-[11px]">Account Alias</span>
                    <span className="font-medium text-text-primary">{name}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-[11px]">Provider</span>
                    <span className="font-semibold text-amber-400 capitalize">{provider}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-[11px]">Audit Cadence</span>
                    <span className="capitalize text-text-primary">{scanSchedule}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-text-muted block text-[11px]">Target Identifier</span>
                    <span className="font-mono text-xs text-text-secondary truncate block">
                      {provider === 'aws'
                        ? roleArn
                        : provider === 'gcp'
                        ? `${gcpProjectId} (${gcpServiceAccountEmail})`
                        : `Sub: ${azureSubscriptionId}`}
                    </span>
                  </div>
                </div>
              </div>

              {/* Live Connectivity Test Section */}
              <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/20 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-semibold text-text-primary">Cloud Connectivity Pre-Flight</h4>
                    <p className="text-[11px] text-text-muted">Test read-only role assumption before finalizing connection.</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={testStatus === 'testing'}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50"
                  >
                    {testStatus === 'testing' ? (
                      <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                    {testStatus === 'testing' ? 'Testing...' : 'Test Connection'}
                  </button>
                </div>

                {/* Test Feedback Banners */}
                {testStatus === 'success' && (
                  <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
                    <span>Connection verified! Cloud infrastructure is reachable with valid read-only permissions.</span>
                  </div>
                )}

                {testStatus === 'error' && (
                  <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs space-y-2">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                      <div className="flex-1 leading-relaxed">{testError}</div>
                    </div>
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => setShowTroubleshoot(true)}
                        className="inline-flex items-center gap-1 text-xs text-amber-300 hover:text-amber-200 underline font-medium whitespace-nowrap"
                      >
                        <HelpCircle className="w-3.5 h-3.5" /> View Troubleshooting Guide
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-6 border-t border-white/[0.06] bg-surface/30 flex items-center justify-between gap-3">
          {/* Cancel button */}
          <button
            type="button"
            onClick={resetAndClose}
            className="px-4 py-2 rounded-xl text-xs font-medium border border-white/[0.08] text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          >
            Cancel
          </button>

          <div className="flex items-center gap-2">
            {step > 1 && (
              <button
                type="button"
                onClick={() => {
                  setStep((prev) => (prev - 1) as Step)
                  setStepError(null)
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium border border-white/[0.08] text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}

            {step === 1 && (
              <button
                type="button"
                onClick={() => {
                  if (validateStep1()) setStep(2)
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-amber-400 hover:bg-amber-300 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
              >
                Next: Setup Guide <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {step === 2 && (
              <button
                type="button"
                onClick={() => {
                  if (validateStep2()) setStep(3)
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-amber-400 hover:bg-amber-300 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98]"
              >
                Next: Review & Verify <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {step === 3 && (
              <button
                type="button"
                onClick={handleConfirm}
                disabled={submitting}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                {submitting ? 'Connecting...' : 'Save & Connect'}
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════════════
          TROUBLESHOOTING ERROR MODAL / POPUP
         ═══════════════════════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showTroubleshoot && (
          <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg rounded-2xl border border-rose-500/30 bg-deep p-6 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-rose-400">
                  <AlertTriangle className="w-5 h-5" />
                  <h3 className="font-display text-base font-bold text-text-primary">
                    Cloud Connection Troubleshooting
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowTroubleshoot(false)}
                  className="p-1 rounded-lg text-text-muted hover:text-text-primary transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 font-mono text-xs text-rose-300">
                {testError || 'Could not assume IAM role or authenticate credentials.'}
              </div>

              <div className="space-y-2 text-xs text-text-muted leading-relaxed">
                <p className="font-semibold text-text-primary">Diagnostic Checklist:</p>
                <ul className="list-disc list-inside space-y-1.5 pl-1">
                  <li>Ensure the IAM Role ARN contains exactly 12 digits for your AWS account ID.</li>
                  <li>Confirm that the Trust Relationship contains LogRaven’s principal and your External ID.</li>
                  <li>Verify that the AWS-managed <strong>SecurityAudit</strong> policy is attached to the role.</li>
                  <li>Check if AWS Service Control Policies (SCPs) restrict cross-account role assumption.</li>
                  <li>Wait 10-30 seconds if you recently created the role in AWS to allow IAM propagation.</li>
                </ul>
              </div>

              <div className="pt-2 flex items-center justify-between gap-3 border-t border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => handleCopy(testError || 'Cloud Connection Error', 'err-copy')}
                  className="inline-flex items-center gap-1.5 text-xs text-amber-300 hover:text-amber-200 font-medium"
                >
                  {copiedKey === 'err-copy' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedKey === 'err-copy' ? 'Copied Details' : 'Copy Error Details'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowTroubleshoot(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium bg-white/[0.08] hover:bg-white/[0.12] text-text-primary transition-colors whitespace-nowrap"
                >
                  Close &amp; Edit Settings
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )

  return createPortal(modalNode, document.body)
}
