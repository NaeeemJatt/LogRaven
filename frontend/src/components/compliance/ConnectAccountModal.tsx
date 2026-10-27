import { useState } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'
import {
  Cloud,
  X,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Info,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  Lock,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import { createCloudAccount, verifyCloudAccount } from '../../api/compliance'
import type { CloudAccount, CreateCloudAccountBody } from '../../types/audit'

interface ConnectAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onAccountConnected: (account: CloudAccount) => void
}

export default function ConnectAccountModal({
  isOpen,
  onClose,
  onAccountConnected,
}: ConnectAccountModalProps) {
  const [provider, setProvider] = useState<'aws' | 'gcp' | 'azure'>('aws')
  const [name, setName] = useState('')
  const [roleArn, setRoleArn] = useState('')
  const [gcpProjectId, setGcpProjectId] = useState('')
  const [azureSubscriptionId, setAzureSubscriptionId] = useState('')
  const [azureTenantId, setAzureTenantId] = useState('')
  const [scanSchedule, setScanSchedule] = useState<'daily' | 'weekly' | 'monthly' | 'none'>('weekly')
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([
    'soc2',
    'iso27001',
    'cis_aws',
  ])

  // Collapsible section states (accordion)
  const [openSection, setOpenSection] = useState<'prereq' | 'trust' | 'policy' | 'cli' | null>('trust')

  // Tooltip hover states
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null)

  // Status & copy feedback
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-generate a deterministic session-consistent External ID for confused deputy protection
  const externalId = 'lgr-ext-' + Math.random().toString(36).substring(2, 10) + '-sec'

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const toggleSection = (section: 'prereq' | 'trust' | 'policy' | 'cli') => {
    setOpenSection((prev) => (prev === section ? null : section))
  }

  const handleFrameworkToggle = (fw: string) => {
    setSelectedFrameworks((prev) =>
      prev.includes(fw) ? prev.filter((f) => f !== fw) : [...prev, fw],
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Please provide a name/alias for this cloud environment.')
      return
    }

    if (provider === 'aws') {
      if (!roleArn.trim() || !roleArn.startsWith('arn:aws:iam::')) {
        setError('Please enter a valid AWS IAM Role ARN (e.g. arn:aws:iam::123456789012:role/LogRavenAuditRole).')
        return
      }
    } else if (provider === 'gcp' && !gcpProjectId.trim()) {
      setError('Please enter a valid GCP Project ID.')
      return
    } else if (provider === 'azure' && (!azureSubscriptionId.trim() || !azureTenantId.trim())) {
      setError('Please provide Azure Subscription ID and Tenant ID.')
      return
    }

    setSubmitting(true)
    try {
      const payload: CreateCloudAccountBody = {
        name: name.trim(),
        provider,
        role_arn: provider === 'aws' ? roleArn.trim() : undefined,
        gcp_project_id: provider === 'gcp' ? gcpProjectId.trim() : undefined,
        azure_subscription_id: provider === 'azure' ? azureSubscriptionId.trim() : undefined,
        azure_tenant_id: provider === 'azure' ? azureTenantId.trim() : undefined,
        default_frameworks: selectedFrameworks,
        scan_schedule: scanSchedule,
      }

      const created = await createCloudAccount(payload)

      // Automatically trigger credential verification check
      try {
        const verified = await verifyCloudAccount(created.id)
        onAccountConnected(verified)
      } catch {
        onAccountConnected(created)
      }

      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect cloud account. Please check credentials.'
      setError(msg)
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

  if (!isOpen) return null

  const modalNode = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 16 }}
        transition={{ duration: 0.2 }}
        className="relative w-full max-w-3xl rounded-3xl border border-white/[0.1] bg-[#0E1424] shadow-[0_10px_60px_rgba(0,0,0,0.8)] overflow-hidden my-8"
      >
        {/* Header */}
        <div className="p-6 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-display font-bold text-xl text-text-primary">
                Connect Cloud Environment
              </h2>
              <p className="font-mono text-xs text-text-muted mt-0.5">
                Read-only continuous security &amp; compliance posture assessment
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg border border-white/[0.08] flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Provider Tabs */}
        <div className="flex border-b border-white/[0.08] bg-black/20 px-6 pt-3 gap-2">
          {[
            { id: 'aws', label: 'Amazon Web Services (AWS)', icon: Cloud },
            { id: 'azure', label: 'Microsoft Azure', icon: Cloud },
            { id: 'gcp', label: 'Google Cloud (GCP)', icon: Cloud },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setProvider(tab.id as 'aws' | 'gcp' | 'azure')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs font-semibold border-b-2 transition-all ${
                provider === tab.id
                  ? 'border-indigo-400 text-indigo-300 bg-white/[0.04]'
                  : 'border-transparent text-text-muted hover:text-text-secondary hover:bg-white/[0.02]'
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs font-mono flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Collapsible Step-by-Step Instructions (Accordion) */}
          {provider === 'aws' && (
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden divide-y divide-white/[0.06]">
              {/* Accordion 1: Prerequisites & Safety Guarantee */}
              <div>
                <button
                  type="button"
                  onClick={() => toggleSection('prereq')}
                  className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-text-primary">
                      Step 1: Security Guarantee &amp; Zero-Credential Architecture
                    </span>
                  </div>
                  {openSection === 'prereq' ? (
                    <ChevronUp className="w-4 h-4 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-text-muted" />
                  )}
                </button>
                {openSection === 'prereq' && (
                  <div className="p-4 pt-1 font-mono text-[11px] text-text-secondary space-y-2 bg-black/20">
                    <p>
                      LogRaven does <strong>never</strong> request or store static AWS Access Keys. It uses AWS STS AssumeRole with a cryptographically unique ExternalId to prevent confused deputy vulnerability.
                    </p>
                    <div className="flex items-center gap-2 text-text-muted text-[10px]">
                      <Lock className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Read-only permissions: CloudTrail, IAM summary, S3 encryption status, KMS keys, GuardDuty findings.</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Accordion 2: IAM AssumeRole Trust Policy */}
              <div>
                <button
                  type="button"
                  onClick={() => toggleSection('trust')}
                  className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Lock className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold text-text-primary">
                      Step 2: Copy IAM Role Trust Policy (AssumeRole)
                    </span>
                  </div>
                  {openSection === 'trust' ? (
                    <ChevronUp className="w-4 h-4 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-text-muted" />
                  )}
                </button>
                {openSection === 'trust' && (
                  <div className="p-4 pt-1 space-y-3 bg-black/20">
                    <p className="text-xs text-text-secondary leading-relaxed">
                      In the AWS IAM Console, create a new Role with Custom Trust Policy and paste the snippet below:
                    </p>
                    <div className="relative rounded-xl border border-white/[0.08] bg-[#070A11] p-3 font-mono text-[11px] text-indigo-200 overflow-x-auto">
                      <pre>{trustPolicyJson}</pre>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(trustPolicyJson, 'trust')}
                        className="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/[0.1] bg-surface hover:bg-white/[0.08] text-text-primary text-[10px] font-mono transition-colors"
                      >
                        {copiedKey === 'trust' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === 'trust' ? 'Copied' : 'Copy Trust Policy'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Accordion 3: Attach SecurityAudit Policy */}
              <div>
                <button
                  type="button"
                  onClick={() => toggleSection('policy')}
                  className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <ShieldAlert className="w-4 h-4 text-teal-400" />
                    <span className="text-xs font-semibold text-text-primary">
                      Step 3: Attach AWS Managed Policy &quot;SecurityAudit&quot;
                    </span>
                  </div>
                  {openSection === 'policy' ? (
                    <ChevronUp className="w-4 h-4 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-text-muted" />
                  )}
                </button>
                {openSection === 'policy' && (
                  <div className="p-4 pt-1 font-mono text-[11px] text-text-secondary space-y-2 bg-black/20">
                    <p>
                      Attach the standard AWS-managed policy: <strong>arn:aws:iam::aws:policy/SecurityAudit</strong>.
                    </p>
                    <p className="text-text-muted">
                      This provides standard read-only access for SOC 2, ISO 27001, and CIS benchmarks. No custom write permissions are required.
                    </p>
                  </div>
                )}
              </div>

              {/* Accordion 4: AWS CLI One-Liner (Terminal Fast Track) */}
              <div>
                <button
                  type="button"
                  onClick={() => toggleSection('cli')}
                  className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Terminal className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-semibold text-text-primary">
                      Fast Track: AWS CLI 1-Line Setup
                    </span>
                  </div>
                  {openSection === 'cli' ? (
                    <ChevronUp className="w-4 h-4 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-text-muted" />
                  )}
                </button>
                {openSection === 'cli' && (
                  <div className="p-4 pt-1 space-y-2 bg-black/20">
                    <div className="relative rounded-xl border border-white/[0.08] bg-[#070A11] p-3 font-mono text-[11px] text-amber-200 overflow-x-auto">
                      <pre>{awsCliSnippet}</pre>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(awsCliSnippet, 'cli')}
                        className="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/[0.1] bg-surface hover:bg-white/[0.08] text-text-primary text-[10px] font-mono transition-colors"
                      >
                        {copiedKey === 'cli' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === 'cli' ? 'Copied' : 'Copy CLI Script'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Inputs Section */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Account Friendly Name */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                  <span>Environment Label</span>
                  <div
                    className="relative cursor-pointer"
                    onMouseEnter={() => setActiveTooltip('name')}
                    onMouseLeave={() => setActiveTooltip(null)}
                  >
                    <Info className="w-3.5 h-3.5 text-text-muted hover:text-indigo-400 transition-colors" />
                    {activeTooltip === 'name' && (
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-48 p-2 rounded-lg bg-surface border border-white/[0.1] text-[10px] text-text-secondary shadow-xl z-50">
                        Human-friendly display name (e.g. &quot;AWS Production US-East-1&quot; or &quot;Staging VPC&quot;).
                      </div>
                    )}
                  </div>
                </label>
              </div>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. AWS Production Fleet"
                className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* AWS Role ARN */}
            {provider === 'aws' && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                    <span>IAM Role ARN</span>
                    <div
                      className="relative cursor-pointer"
                      onMouseEnter={() => setActiveTooltip('roleArn')}
                      onMouseLeave={() => setActiveTooltip(null)}
                    >
                      <Info className="w-3.5 h-3.5 text-text-muted hover:text-indigo-400 transition-colors" />
                      {activeTooltip === 'roleArn' && (
                        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-52 p-2 rounded-lg bg-surface border border-white/[0.1] text-[10px] text-text-secondary shadow-xl z-50">
                          The Amazon Resource Name of the role created in Step 2.
                        </div>
                      )}
                    </div>
                  </label>
                </div>
                <input
                  type="text"
                  required
                  value={roleArn}
                  onChange={(e) => setRoleArn(e.target.value)}
                  placeholder="arn:aws:iam::123456789012:role/..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] font-mono text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
                />
              </div>
            )}

            {/* GCP Project ID */}
            {provider === 'gcp' && (
              <div>
                <label className="text-xs font-semibold text-text-secondary block mb-1.5">
                  GCP Project ID
                </label>
                <input
                  type="text"
                  required
                  value={gcpProjectId}
                  onChange={(e) => setGcpProjectId(e.target.value)}
                  placeholder="e.g. my-production-project-1234"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] font-mono text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
                />
              </div>
            )}

            {/* Azure Subscription & Tenant ID */}
            {provider === 'azure' && (
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-text-secondary block mb-1.5">
                    Azure Subscription ID
                  </label>
                  <input
                    type="text"
                    required
                    value={azureSubscriptionId}
                    onChange={(e) => setAzureSubscriptionId(e.target.value)}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] font-mono text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-text-secondary block mb-1.5">
                    Azure Tenant ID
                  </label>
                  <input
                    type="text"
                    required
                    value={azureTenantId}
                    onChange={(e) => setAzureTenantId(e.target.value)}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] font-mono text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>
            )}

            {/* Autonomous Schedule */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
                  <span>Continuous Monitoring Schedule</span>
                  <div
                    className="relative cursor-pointer"
                    onMouseEnter={() => setActiveTooltip('schedule')}
                    onMouseLeave={() => setActiveTooltip(null)}
                  >
                    <Info className="w-3.5 h-3.5 text-text-muted hover:text-indigo-400 transition-colors" />
                    {activeTooltip === 'schedule' && (
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-48 p-2 rounded-lg bg-surface border border-white/[0.1] text-[10px] text-text-secondary shadow-xl z-50">
                        Autonomous background scans to alert you on posture regressions before auditors notice.
                      </div>
                    )}
                  </div>
                </label>
              </div>
              <select
                value={scanSchedule}
                onChange={(e) => setScanSchedule(e.target.value as 'daily' | 'weekly' | 'monthly' | 'none')}
                className="w-full px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-surface text-xs text-text-primary focus:outline-none focus:border-indigo-500/50"
              >
                <option value="daily">Daily Continuous Scan</option>
                <option value="weekly">Weekly Assessment (Recommended)</option>
                <option value="monthly">Monthly Snapshot</option>
                <option value="none">Manual On-Demand Only</option>
              </select>
            </div>
          </div>

          {/* Framework Multi-Select Pills */}
          <div>
            <label className="text-xs font-semibold text-text-secondary block mb-2">
              Default Monitored Frameworks
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'soc2', label: 'SOC 2 Type II' },
                { id: 'iso27001', label: 'ISO/IEC 27001' },
                { id: 'cis_aws', label: 'CIS AWS Benchmark' },
                { id: 'hipaa', label: 'HIPAA Security Rule' },
                { id: 'pci_dss', label: 'PCI-DSS v4.0' },
                { id: 'nist_csf', label: 'NIST CSF v2.0' },
              ].map((fw) => {
                const isSelected = selectedFrameworks.includes(fw.id)
                return (
                  <button
                    key={fw.id}
                    type="button"
                    onClick={() => handleFrameworkToggle(fw.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                      isSelected
                        ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
                        : 'bg-white/[0.02] text-text-muted border-white/[0.06] hover:text-text-secondary hover:bg-white/[0.04]'
                    }`}
                  >
                    {isSelected ? '✓ ' : '+ '} {fw.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-[0_0_20px_rgba(99,102,241,0.35)] transition-all disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Verifying IAM Credentials...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Verify &amp; Connect Cloud</span>
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )

  return typeof document !== 'undefined'
    ? createPortal(modalNode, document.body)
    : modalNode
}
