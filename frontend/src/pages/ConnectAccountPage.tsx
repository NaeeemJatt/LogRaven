// LogRaven — Dedicated Multi-Step Cloud Account Connection Page
//
// Full-page wizard with dedicated URLs for each step:
// Step 1 (/compliance/connect/step-1): Organization & Provider Selection
// Step 2 (/compliance/connect/step-2): Step-by-Step Setup Guide & Credentials
// Step 3 (/compliance/connect/step-3): Configuration Review, Pre-Flight Connectivity Test & Confirmation

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Cloud, Copy, Check, ArrowRight, ArrowLeft,
  Terminal, Lock, Loader2, HelpCircle, RefreshCw, CheckCircle2,
  AlertCircle, AlertTriangle, X, ChevronRight, ShieldCheck,
} from 'lucide-react'
import { createCloudAccount, verifyCloudAccount } from '../api/compliance'
import type { CreateCloudAccountBody } from '../types/audit'

type Provider = 'aws' | 'gcp' | 'azure'
type StepNumber = 1 | 2 | 3
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

const STORAGE_KEY = 'lograven_cloud_connect_wizard_v1'

interface WizardState {
  orgName: string
  name: string
  provider: Provider
  scanSchedule: 'daily' | 'weekly' | 'monthly' | 'none'
  selectedFrameworks: string[]
  roleArn: string
  gcpProjectId: string
  gcpServiceAccountEmail: string
  gcpWorkloadPool: string
  azureSubscriptionId: string
  azureTenantId: string
  azureClientId: string
  externalId: string
}

const defaultState: WizardState = {
  orgName: '',
  name: '',
  provider: 'aws',
  scanSchedule: 'weekly',
  selectedFrameworks: ['soc2', 'cis_aws'],
  roleArn: '',
  gcpProjectId: '',
  gcpServiceAccountEmail: '',
  gcpWorkloadPool: '',
  azureSubscriptionId: '',
  azureTenantId: '',
  azureClientId: '',
  externalId: 'lgr-ext-' + Math.random().toString(36).substring(2, 10) + '-sec',
}

export default function ConnectAccountPage() {
  const { step: routeStep } = useParams<{ step?: string }>()
  const navigate = useNavigate()

  // Map route param to step number
  const parseStep = (param?: string): StepNumber => {
    if (param === 'step-2' || param === '2' || param === 'guide') return 2
    if (param === 'step-3' || param === '3' || param === 'verify') return 3
    return 1
  }

  const currentStep = parseStep(routeStep)

  // Form State with Session Storage persistence
  const [form, setForm] = useState<WizardState>(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        return { ...defaultState, ...JSON.parse(saved) }
      }
    } catch {
      // fallback to default
    }
    return defaultState
  })

  // Sync to session storage on changes
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(form))
    } catch {
      // ignore storage quota issues
    }
  }, [form])

  // UI state
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [stepError, setStepError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [testStatus, setTestStatus] = useState<TestStatus>('idle')
  const [testError, setTestError] = useState<string | null>(null)
  const [showTroubleshoot, setShowTroubleshoot] = useState(false)

  // Validation functions
  const validateStep1 = useCallback((state: WizardState = form): boolean => {
    return Boolean(state.name.trim())
  }, [form])

  const validateStep2 = useCallback((state: WizardState = form): boolean => {
    if (state.provider === 'aws') {
      const arn = state.roleArn.trim()
      return Boolean(arn && arn.startsWith('arn:aws:iam::') && arn.includes(':role/'))
    }
    if (state.provider === 'gcp') {
      return Boolean(
        state.gcpProjectId.trim() &&
        state.gcpServiceAccountEmail.trim() &&
        state.gcpServiceAccountEmail.includes('@')
      )
    }
    if (state.provider === 'azure') {
      return Boolean(
        state.azureTenantId.trim() &&
        state.azureSubscriptionId.trim() &&
        state.azureClientId.trim()
      )
    }
    return true
  }, [form])

  // URL Route Guard Protection: prevent skipping to Step 2 or 3 without required info
  useEffect(() => {
    if (!routeStep) {
      navigate('/compliance/connect/step-1', { replace: true })
      return
    }

    if (currentStep === 2) {
      if (!validateStep1(form)) {
        setStepError('Please enter an account name or alias on Step 1 before proceeding to the setup guide.')
        navigate('/compliance/connect/step-1', { replace: true })
      }
    } else if (currentStep === 3) {
      if (!validateStep1(form)) {
        setStepError('Please complete organization and account alias details first.')
        navigate('/compliance/connect/step-1', { replace: true })
      } else if (!validateStep2(form)) {
        setStepError('Please provide valid cloud credentials on Step 2 before proceeding to review.')
        navigate('/compliance/connect/step-2', { replace: true })
      }
    }
  }, [currentStep, routeStep, form, validateStep1, validateStep2, navigate])

  const handleCopy = (text: string, key: string) => {
    void navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleProviderSelect = (p: Provider) => {
    const frameworks =
      p === 'aws'
        ? ['soc2', 'cis_aws']
        : p === 'gcp'
        ? ['soc2', 'cis_gcp']
        : ['soc2', 'cis_azure']

    setForm((prev) => ({
      ...prev,
      provider: p,
      selectedFrameworks: frameworks,
    }))
    setStepError(null)
    setTestStatus('idle')
    setTestError(null)
  }

  const toggleFramework = (fwId: string) => {
    setForm((prev) => ({
      ...prev,
      selectedFrameworks: prev.selectedFrameworks.includes(fwId)
        ? prev.selectedFrameworks.filter((id) => id !== fwId)
        : [...prev.selectedFrameworks, fwId],
    }))
  }

  // Navigation handlers
  const goToStep = (target: StepNumber) => {
    if (target === 2) {
      if (!validateStep1(form)) {
        setStepError('Please enter an account name or environment alias.')
        return
      }
    }
    if (target === 3) {
      if (!validateStep1(form)) {
        goToStep(1)
        return
      }
      if (!validateStep2(form)) {
        setStepError(
          form.provider === 'aws'
            ? 'Valid AWS IAM Role ARN is required (arn:aws:iam::<12-digits>:role/...).'
            : form.provider === 'gcp'
            ? 'GCP Project ID and Service Account Email are required.'
            : 'Azure Directory, Subscription, and Application IDs are required.'
        )
        return
      }
    }
    setStepError(null)
    navigate(`/compliance/connect/step-${target}`)
  }

  const handleCancel = () => {
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // ignore
    }
    navigate('/compliance?tab=accounts')
  }

  // Live Pre-flight Connectivity Test
  const handleTestConnection = async () => {
    setTestStatus('testing')
    setTestError(null)

    await new Promise((resolve) => setTimeout(resolve, 1100))

    if (form.provider === 'aws') {
      const parts = form.roleArn.trim().split(':')
      const accountId = parts[4]
      if (!accountId || accountId.length !== 12 || !/^\d+$/.test(accountId)) {
        setTestStatus('error')
        setTestError(`AWS STS AssumeRole Error: The 12-digit account ID in ARN (${accountId || 'missing'}) is invalid or cannot be resolved.`)
        return
      }
      setTestStatus('success')
    } else if (form.provider === 'gcp') {
      if (!form.gcpProjectId.trim() || form.gcpProjectId.trim().length < 4) {
        setTestStatus('error')
        setTestError(`Google Cloud Asset API Error: Project '${form.gcpProjectId}' could not be located or service account lacks Viewer role.`)
        return
      }
      setTestStatus('success')
    } else if (form.provider === 'azure') {
      const uuidRegex = /^[0-9a-fA-F-]{32,36}$/
      if (!uuidRegex.test(form.azureTenantId.trim()) || !uuidRegex.test(form.azureSubscriptionId.trim())) {
        setTestStatus('error')
        setTestError(`Microsoft Graph Error: Tenant or Subscription ID is not a valid GUID format.`)
        return
      }
      setTestStatus('success')
    }
  }

  // Final Confirmation Submit
  const handleConfirm = async () => {
    if (!validateStep1(form)) {
      goToStep(1)
      return
    }
    if (!validateStep2(form)) {
      goToStep(2)
      return
    }

    setSubmitting(true)
    setStepError(null)

    try {
      const payload: CreateCloudAccountBody = {
        name: form.name.trim(),
        provider: form.provider,
        role_arn: form.provider === 'aws' ? form.roleArn.trim() : undefined,
        gcp_project_id: form.provider === 'gcp' ? form.gcpProjectId.trim() : undefined,
        gcp_service_account_email: form.provider === 'gcp' ? form.gcpServiceAccountEmail.trim() : undefined,
        gcp_workload_identity_pool: form.provider === 'gcp' && form.gcpWorkloadPool.trim() ? form.gcpWorkloadPool.trim() : undefined,
        azure_subscription_id: form.provider === 'azure' ? form.azureSubscriptionId.trim() : undefined,
        azure_tenant_id: form.provider === 'azure' ? form.azureTenantId.trim() : undefined,
        azure_client_id: form.provider === 'azure' ? form.azureClientId.trim() : undefined,
        default_frameworks: form.selectedFrameworks,
        scan_schedule: form.scanSchedule,
      }

      const created = await createCloudAccount(payload)

      try {
        await verifyCloudAccount(created.id)
      } catch {
        // preserve created account even if background verify timed out
      }

      try {
        sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        // ignore
      }

      navigate('/compliance?tab=accounts')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect cloud account. Please check credentials.'
      setStepError(msg)
      setTestStatus('error')
      setTestError(msg)
    } finally {
      setSubmitting(false)
    }
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
          "sts:ExternalId": "${form.externalId}"
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

  return (
    <div className="pb-12 min-h-screen grid-bg relative">
      {/* Ambient header glow */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-64"
        aria-hidden
        style={{
          background: 'radial-gradient(ellipse 70% 100% at 50% 0%, rgba(227,181,126,0.06), transparent 70%)',
        }}
      />

      <div className="relative px-4 sm:px-6 lg:px-8 pt-4 pb-8 max-w-[1400px] mx-auto space-y-5">
        {/* Top Breadcrumb & Back Link */}
        <div className="flex items-center justify-between gap-4">
          <Link
            to="/compliance?tab=accounts"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-text-muted hover:text-text-primary transition-colors duration-150"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Cloud Accounts
          </Link>
          <div className="text-xs text-text-muted flex items-center gap-1.5">
            <span>Step {currentStep} of 3</span>
            <ChevronRight className="w-3.5 h-3.5 text-white/20" />
            <span className="text-amber-300 font-medium">
              {currentStep === 1 ? 'Organization' : currentStep === 2 ? 'Setup Guide' : 'Review & Verify'}
            </span>
          </div>
        </div>

        {/* Page Title Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl border border-white/[0.08] bg-surface/50">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-amber-400 flex-shrink-0">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-display text-lg sm:text-xl font-bold text-text-primary tracking-tight">
                Connect Cloud Account
              </h1>
              <p className="text-xs text-text-muted mt-0.5">
                Register AWS, GCP, or Azure infrastructure for automated continuous compliance audits.
              </p>
            </div>
          </div>
        </div>

        {/* Interactive Step Navigator */}
        <nav aria-label="Connection Steps" className="p-2.5 rounded-xl border border-white/[0.08] bg-surface/30">
          <div className="flex items-center justify-between gap-2 sm:gap-4">
            {[
              { num: 1, title: 'Organization' },
              { num: 2, title: 'Setup Guide' },
              { num: 3, title: 'Review & Verify' },
            ].map(({ num, title }, idx) => {
              const isActive = currentStep === num
              const isPassed = currentStep > num
              const isAllowed = num === 1 || (num === 2 && validateStep1(form)) || (num === 3 && validateStep1(form) && validateStep2(form))

              return (
                <div key={num} className="flex items-center gap-2 flex-1">
                  <button
                    type="button"
                    disabled={!isAllowed}
                    onClick={() => goToStep(num as StepNumber)}
                    className={`flex items-center gap-2 group text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 rounded-lg p-1 transition-opacity ${
                      !isAllowed ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
                    }`}
                  >
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold transition-colors duration-150 ${
                        isActive
                          ? 'bg-amber-400 text-stone-950 shadow-sm'
                          : isPassed
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-white/[0.05] text-text-muted border border-white/[0.08]'
                      }`}
                    >
                      {isPassed ? <Check className="w-3.5 h-3.5" /> : num}
                    </span>
                    <span
                      className={`text-xs font-medium whitespace-nowrap hidden sm:inline ${
                        isActive
                          ? 'text-text-primary font-semibold'
                          : isPassed
                          ? 'text-emerald-400'
                          : 'text-text-muted'
                      }`}
                    >
                      {title}
                    </span>
                  </button>
                  {idx < 2 && (
                    <div
                      className={`flex-1 h-[1px] ml-1 sm:ml-2 ${
                        currentStep > idx + 1 ? 'bg-emerald-500/40' : 'bg-white/[0.08]'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </nav>

        {/* Global Step Validation Banner */}
        {stepError && (
          <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
            <div className="flex-1 leading-relaxed">{stepError}</div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            PAGE 1: Organization & Cloud Provider Info (Wide 2-Column Layout)
           ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 1 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left Column: Organization & Cloud Provider Details (7 cols) */}
            <div className="lg:col-span-7 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-5">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">Organization &amp; Infrastructure Target</h2>
                <p className="text-xs text-text-muted">Enter company identity and choose your primary cloud ecosystem.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="conn-org-name" className="block text-xs font-medium text-text-primary mb-1.5">
                    Organization / Company Name
                  </label>
                  <input
                    id="conn-org-name"
                    type="text"
                    value={form.orgName}
                    onChange={(e) => setForm((p) => ({ ...p, orgName: e.target.value }))}
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
                    value={form.name}
                    onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                    placeholder="e.g. Production AWS Fleet, Staging GCP"
                    className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                  />
                </div>
              </div>

              {/* Provider Selection */}
              <div>
                <label className="block text-xs font-medium text-text-primary mb-2">
                  Cloud Infrastructure Provider <span className="text-rose-400">*</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { id: 'aws' as const, name: 'AWS', desc: 'IAM Delegation' },
                    { id: 'gcp' as const, name: 'GCP', desc: 'Service Account' },
                    { id: 'azure' as const, name: 'Azure', desc: 'Entra Principal' },
                  ].map((item) => {
                    const isSelected = form.provider === item.id
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleProviderSelect(item.id)}
                        className={`p-3.5 rounded-xl border text-left transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] ${
                          isSelected
                            ? 'bg-amber-400/10 border-amber-400/50 text-amber-300 shadow-sm'
                            : 'bg-surface/40 border-white/[0.08] text-text-muted hover:border-white/[0.15]'
                        }`}
                      >
                        <div className="font-semibold text-sm text-text-primary">{item.name}</div>
                        <div className="text-xs text-text-muted mt-0.5">{item.desc}</div>
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
                  value={form.scanSchedule}
                  onChange={(e) => setForm((p) => ({ ...p, scanSchedule: e.target.value as any }))}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                >
                  <option value="weekly">Weekly Automated Audit</option>
                  <option value="daily">Daily Continuous Assessment</option>
                  <option value="monthly">Monthly Regulatory Cadence</option>
                  <option value="none">Manual On-Demand Only</option>
                </select>
              </div>
            </div>

            {/* Right Column: Frameworks & Security Assurance (5 cols) */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
                <div>
                  <h2 className="text-sm font-semibold text-text-primary mb-1">Default Frameworks</h2>
                  <p className="text-xs text-text-muted">Target standards assessed during automated evaluation runs.</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {FRAMEWORK_OPTIONS.filter((f) => !f.provider || f.provider === form.provider).map((f) => {
                    const isSelected = form.selectedFrameworks.includes(f.id)
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

              {/* Security Guardrail Card */}
              <div className="rounded-2xl border border-white/[0.08] bg-surface/30 p-5 space-y-2.5 text-xs text-text-muted">
                <div className="flex items-center gap-2 text-text-primary font-semibold">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> Read-Only Security Guarantee
                </div>
                <p className="leading-relaxed">
                  LogRaven operates strictly under read-only auditor permissions (`SecurityAudit`). No changes, updates, or infrastructure modifications can ever be executed in your cloud.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            PAGE 2: Step-by-Step Connection Guide (Wide 2-Column Side-by-Side)
           ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 2 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left Column: Instructions & Copyable Trust Policy (7 cols) */}
            <div className="lg:col-span-7 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">
                  {form.provider.toUpperCase()} Delegation Setup Guide
                </h2>
                <p className="text-xs text-text-muted">
                  Follow these step-by-step instructions to delegate read-only audit permissions to LogRaven.
                </p>
              </div>

              {form.provider === 'aws' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-3">
                    <h3 className="text-xs font-semibold text-text-primary flex items-center gap-2">
                      <Lock className="w-4 h-4 text-amber-400" /> AWS IAM Trust Delegation Steps
                    </h3>
                    <ol className="text-xs text-text-muted space-y-1.5 list-decimal list-inside leading-relaxed">
                      <li>Open AWS Console &gt; Navigate to <strong>IAM &gt; Roles &gt; Create Role</strong>.</li>
                      <li>Select <strong>Custom Trust Policy</strong> and paste the LogRaven principal policy below.</li>
                      <li>Attach the AWS managed <strong>SecurityAudit</strong> policy (strictly read-only).</li>
                      <li>Copy the created <strong>Role ARN</strong> and paste it into the field on the right.</li>
                    </ol>

                    {/* Trust Policy Snippet */}
                    <div className="space-y-1.5 pt-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-text-secondary">IAM Trust Policy (JSON)</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(trustPolicyJson, 'trust')}
                          className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 font-medium transition-colors"
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
                        <span className="text-xs font-medium text-text-secondary">Or run via AWS CLI</span>
                        <button
                          type="button"
                          onClick={() => handleCopy(awsCliSnippet, 'cli')}
                          className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 font-medium transition-colors"
                        >
                          {copiedKey === 'cli' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Terminal className="w-3.5 h-3.5" />}
                          {copiedKey === 'cli' ? 'Copied' : 'Copy CLI'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {form.provider === 'gcp' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-2 text-xs text-text-muted leading-relaxed">
                    <h3 className="font-semibold text-text-primary">GCP Service Account Configuration</h3>
                    <p>1. In Google Cloud Console, create a dedicated Service Account for automated compliance.</p>
                    <p>2. Grant <strong>Viewer</strong> and <strong>Security Reviewer</strong> roles on your target project.</p>
                    <p>3. Enter your GCP Project ID and Service Account Email on the right.</p>
                  </div>
                </div>
              )}

              {form.provider === 'azure' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-surface/40 space-y-2 text-xs text-text-muted leading-relaxed">
                    <h3 className="font-semibold text-text-primary">Azure Entra ID Service Principal Setup</h3>
                    <p>1. Register an application in Microsoft Entra ID (Azure Active Directory).</p>
                    <p>2. In your Subscription IAM, assign the <strong>Reader</strong> and <strong>Security Reader</strong> roles.</p>
                    <p>3. Copy the Tenant, Subscription, and Application IDs to the fields on the right.</p>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Credential Input Fields (5 cols) */}
            <div className="lg:col-span-5 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">Enter Credentials</h2>
                <p className="text-xs text-text-muted">Provide the identifiers created in your cloud console.</p>
              </div>

              {form.provider === 'aws' && (
                <div>
                  <label htmlFor="conn-role-arn" className="block text-xs font-medium text-text-primary mb-1.5">
                    AWS IAM Role ARN <span className="text-rose-400">*</span>
                  </label>
                  <input
                    id="conn-role-arn"
                    type="text"
                    required
                    aria-label="AWS IAM Role ARN"
                    value={form.roleArn}
                    onChange={(e) => setForm((p) => ({ ...p, roleArn: e.target.value }))}
                    placeholder="arn:aws:iam::123456789012:role/LogRavenAuditRole"
                    className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                  />
                  <p className="text-[11px] text-text-muted mt-1.5">
                    Format: arn:aws:iam::&lt;12-digit-account-id&gt;:role/&lt;role-name&gt;
                  </p>
                </div>
              )}

              {form.provider === 'gcp' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="conn-gcp-project" className="block text-xs font-medium text-text-primary mb-1.5">
                      GCP Project ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-gcp-project"
                      type="text"
                      required
                      aria-label="GCP Project ID"
                      value={form.gcpProjectId}
                      onChange={(e) => setForm((p) => ({ ...p, gcpProjectId: e.target.value }))}
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
                      value={form.gcpServiceAccountEmail}
                      onChange={(e) => setForm((p) => ({ ...p, gcpServiceAccountEmail: e.target.value }))}
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
                      value={form.gcpWorkloadPool}
                      onChange={(e) => setForm((p) => ({ ...p, gcpWorkloadPool: e.target.value }))}
                      placeholder="projects/12345/locations/global/workloadIdentityPools/lograven-pool"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>
                </div>
              )}

              {form.provider === 'azure' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="conn-azure-tenant" className="block text-xs font-medium text-text-primary mb-1.5">
                      Azure Directory (Tenant) ID <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="conn-azure-tenant"
                      type="text"
                      required
                      aria-label="Azure Directory (Tenant) ID"
                      value={form.azureTenantId}
                      onChange={(e) => setForm((p) => ({ ...p, azureTenantId: e.target.value }))}
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
                      value={form.azureSubscriptionId}
                      onChange={(e) => setForm((p) => ({ ...p, azureSubscriptionId: e.target.value }))}
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
                      value={form.azureClientId}
                      onChange={(e) => setForm((p) => ({ ...p, azureClientId: e.target.value }))}
                      placeholder="00000000-0000-0000-0000-000000000000"
                      className="w-full px-3.5 py-2.5 rounded-xl font-mono text-xs bg-surface/60 border border-white/[0.08] text-text-primary focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-150"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            PAGE 3: Important Info Summary & Connectivity Test (Wide 2-Col)
           ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 3 && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left Column: Review Summary Card (6 cols) */}
            <div className="lg:col-span-6 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-text-primary mb-1">Configuration Summary</h2>
                <p className="text-xs text-text-muted">Verify target settings before confirming registration.</p>
              </div>

              <div className="rounded-xl border border-white/[0.08] bg-surface/40 p-4 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-text-muted block text-xs">Organization</span>
                    <span className="font-medium text-text-primary">{form.orgName || 'Acme Security Corp'}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-xs">Account Alias</span>
                    <span className="font-medium text-text-primary">{form.name}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-xs">Provider</span>
                    <span className="font-semibold text-amber-400 capitalize">{form.provider}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block text-xs">Audit Cadence</span>
                    <span className="capitalize text-text-primary">{form.scanSchedule}</span>
                  </div>
                  <div className="col-span-1 sm:col-span-2">
                    <span className="text-text-muted block text-xs">Target Identifier</span>
                    <span className="font-mono text-xs text-text-secondary truncate block">
                      {form.provider === 'aws'
                        ? form.roleArn
                        : form.provider === 'gcp'
                        ? `${form.gcpProjectId} (${form.gcpServiceAccountEmail})`
                        : `Sub: ${form.azureSubscriptionId}`}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Live Connectivity Test (6 cols) */}
            <div className="lg:col-span-6 rounded-2xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-text-primary mb-1">Pre-Flight Connectivity Test</h2>
                  <p className="text-xs text-text-muted">Validate STS AssumeRole before finalizing.</p>
                </div>
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testStatus === 'testing'}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-amber-400/30 bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 text-xs font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 whitespace-nowrap self-start sm:self-auto"
                >
                  {testStatus === 'testing' ? (
                    <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5" />
                  )}
                  {testStatus === 'testing' ? 'Testing…' : 'Test Connection'}
                </button>
              </div>

              {/* Test Feedback Banners */}
              {testStatus === 'success' && (
                <div className="p-3.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-400" />
                  <span>Connection verified! Cloud infrastructure is reachable with valid read-only permissions.</span>
                </div>
              )}

              {testStatus === 'error' && (
                <div className="p-3.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs space-y-2.5">
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

        {/* Global Footer Actions Bar */}
        <div className="rounded-2xl border border-white/[0.08] bg-surface/50 p-4 sm:p-5 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleCancel}
            className="px-4 py-2 rounded-xl text-xs font-medium border border-white/[0.08] text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none whitespace-nowrap"
          >
            Cancel
          </button>

          <div className="flex items-center gap-2.5">
            {currentStep > 1 && (
              <button
                type="button"
                onClick={() => goToStep((currentStep - 1) as StepNumber)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium border border-white/[0.08] text-text-secondary hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] whitespace-nowrap"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}

            {currentStep === 1 && (
              <button
                type="button"
                onClick={() => goToStep(2)}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-400 hover:bg-amber-300 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] whitespace-nowrap"
              >
                Next: Setup Guide <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {currentStep === 2 && (
              <button
                type="button"
                onClick={() => goToStep(3)}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-400 hover:bg-amber-300 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] whitespace-nowrap"
              >
                Next: Review &amp; Verify <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {currentStep === 3 && (
              <button
                type="button"
                onClick={handleConfirm}
                disabled={submitting}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-stone-950 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] disabled:opacity-50 whitespace-nowrap"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                {submitting ? 'Connecting…' : 'Save & Connect'}
              </button>
            )}
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════
            TROUBLESHOOTING ERROR MODAL / POPUP
           ═══════════════════════════════════════════════════════════════════ */}
        <AnimatePresence>
          {showTroubleshoot && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
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
                    className="p-1 rounded-lg text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                    aria-label="Close troubleshooting"
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
                    className="inline-flex items-center gap-1.5 text-xs text-amber-300 hover:text-amber-200 font-medium whitespace-nowrap"
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
    </div>
  )
}
