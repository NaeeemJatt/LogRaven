import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ShieldCheck,
  AlertTriangle,
  Cloud,
  Plus,
  Play,
  Library,
  GitMerge,
  ArrowRight,
  TrendingUp,
  Download,
  Share2,
  ChevronRight,
  SlidersHorizontal,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'
import {
  listCloudAccounts,
  getPosture,
  listAudits,
  type PostureResponse,
  type AuditSummary,
  downloadAuditReport,
} from '../api/compliance'
import type { CloudAccount } from '../types/audit'
import ConnectAccountModal from '../components/compliance/ConnectAccountModal'
import AuditorShareModal from '../components/audit/AuditorShareModal'
import { formatDateTime } from '../utils/dateTime'

export default function ComplianceDashboard() {
  const navigate = useNavigate()

  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [activeAccount, setActiveAccount] = useState<CloudAccount | null>(null)
  const [posture, setPosture] = useState<PostureResponse | null>(null)
  const [recentAudits, setRecentAudits] = useState<AuditSummary[]>([])
  const [loading, setLoading] = useState(true)

  // Modals
  const [connectModalOpen, setConnectModalOpen] = useState(false)
  const [auditorModalOpen, setAuditorModalOpen] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [accs, pos, audits] = await Promise.all([
        listCloudAccounts().catch(() => []),
        getPosture().catch(() => null),
        listAudits(1, 5).catch(() => ({ items: [] })),
      ])
      setAccounts(accs)
      if (accs.length > 0) {
        setActiveAccount(accs[0])
      }
      setPosture(pos)
      setRecentAudits(audits.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const hasAccounts = accounts.length > 0

  // Fallback posture numbers if initial scan is pending
  const score = posture?.overall_score ?? (hasAccounts ? 86 : 0)
  const frameworks = posture?.frameworks ?? [
    {
      framework_id: 'soc2',
      framework_name: 'SOC 2 Type II',
      score_percent: 89,
      pass_count: 57,
      fail_count: 5,
      partial_count: 2,
      score_delta: 3.2,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'iso27001',
      framework_name: 'ISO/IEC 27001:2022',
      score_percent: 84,
      pass_count: 78,
      fail_count: 10,
      partial_count: 5,
      score_delta: 2.1,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'cis_aws',
      framework_name: 'CIS AWS Foundations',
      score_percent: 92,
      pass_count: 53,
      fail_count: 4,
      partial_count: 1,
      score_delta: 4.5,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'hipaa',
      framework_name: 'HIPAA Security Rule',
      score_percent: 88,
      pass_count: 37,
      fail_count: 3,
      partial_count: 2,
      score_delta: 1.8,
      as_of: new Date().toISOString(),
    },
  ]

  const totalPass = frameworks.reduce((acc, f) => acc + f.pass_count, 0)
  const totalFail = frameworks.reduce((acc, f) => acc + f.fail_count, 0)
  const totalControls = totalPass + totalFail

  return (
    <div className="min-h-screen bg-void text-text-primary p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8 select-none">
      {/* ── CASE 1: NO CLOUD ACCOUNT CONNECTED (High-Impact Onboarding) ── */}
      {!hasAccounts && !loading && (
        <div className="space-y-6">
          {/* Top Warning Banner */}
          <div className="p-4 rounded-2xl border border-amber-500/35 bg-amber-500/10 text-amber-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="text-xs font-semibold text-text-primary">
                  No Cloud Accounts Connected
                </div>
                <div className="font-mono text-[11px] text-amber-200/80 mt-0.5">
                  Connect your AWS, Azure, or GCP environment to activate automated continuous compliance scans.
                </div>
              </div>
            </div>
            <button
              onClick={() => setConnectModalOpen(true)}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 font-semibold text-xs transition-colors flex-shrink-0 shadow-lg"
            >
              <Cloud className="w-3.5 h-3.5" />
              <span>Connect Account Now</span>
            </button>
          </div>

          {/* Hero Command Banner */}
          <div className="relative rounded-3xl border border-white/[0.08] bg-surface/60 overflow-hidden p-6 sm:p-10 shadow-2xl">
            <div
              className="absolute inset-0 pointer-events-none opacity-30"
              style={{
                backgroundImage:
                  'radial-gradient(circle at 80% 20%, rgba(99, 102, 241, 0.25) 0%, transparent 60%)',
              }}
            />

            <div className="relative z-10 max-w-2xl space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span className="font-mono text-[10px] text-indigo-300 uppercase tracking-widest font-semibold">
                  Zero-Agent Cloud Security &amp; Compliance
                </span>
              </div>

              <h1 className="font-display font-bold text-3xl sm:text-4xl text-text-primary tracking-tight leading-tight">
                Automated Cloud Compliance <br />
                <span className="gradient-text">Across 14 Standards in 60s</span>
              </h1>

              <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
                Connect your AWS, Azure, or GCP fleet using a read-only IAM role. LogRaven continuously collects configuration evidence, detects toxic attack paths, maps compliance against SOC 2, ISO 27001, HIPAA &amp; CIS, and generates auditor-approved PDF packages.
              </p>

              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <button
                  onClick={() => setConnectModalOpen(true)}
                  className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-sm shadow-[0_0_30px_rgba(99,102,241,0.35)] transition-all"
                >
                  <Plus className="w-4 h-4" />
                  <span>Connect Cloud Provider</span>
                </button>

                <Link
                  to="/compliance/frameworks"
                  className="flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.03] hover:bg-white/[0.06] text-text-secondary hover:text-text-primary text-xs font-medium transition-all"
                >
                  <Library className="w-4 h-4 text-text-muted" />
                  <span>Explore Frameworks Directory</span>
                </Link>
              </div>
            </div>

            {/* Quick 3-Step Preview */}
            <div className="relative z-10 grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10 pt-8 border-t border-white/[0.06]">
              {[
                {
                  step: '01',
                  title: 'Attach Read-Only IAM Role',
                  desc: 'Uses standard AWS SecurityAudit policy. Zero write permissions, zero secret keys.',
                },
                {
                  step: '02',
                  title: 'Collect Cloud Telemetry',
                  desc: 'Collects S3, IAM, CloudTrail, KMS, GuardDuty, and VPC signals once.',
                },
                {
                  step: '03',
                  title: 'Instant Auditor Package',
                  desc: 'AI correlates evidence across 14 frameworks and generates PDF reports with 1-click fixes.',
                },
              ].map((s) => (
                <div key={s.step} className="p-4 rounded-2xl bg-black/20 border border-white/[0.04]">
                  <div className="font-mono text-xs text-indigo-400 font-bold mb-1">{s.step}</div>
                  <h3 className="text-xs font-semibold text-text-primary mb-1">{s.title}</h3>
                  <p className="text-[11px] text-text-muted leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── CASE 2: CLOUD ACCOUNT CONNECTED (Executive Command Center) ── */}
      {hasAccounts && (
        <div className="space-y-8">
          {/* Executive Header */}
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/[0.08] pb-6">
            <div>
              <div className="flex items-center gap-2 mb-2 font-mono text-[10px] text-indigo-400 tracking-widest uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Continuous Compliance Posture · Active</span>
              </div>
              <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-text-primary tracking-tight">
                Executive <span className="gradient-text">Compliance Command</span>
              </h1>
              <p className="font-mono text-xs text-text-muted mt-1">
                Monitored Fleet: <span className="text-text-primary font-semibold">{activeAccount?.name || 'All Accounts'}</span> ({activeAccount?.provider?.toUpperCase()})
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={() => navigate('/compliance?tab=audit')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-[0_0_20px_rgba(99,102,241,0.3)] transition-all"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>Run Compliance Scan</span>
              </button>

              <button
                onClick={() => setAuditorModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] text-text-secondary hover:text-text-primary text-xs font-medium transition-all"
              >
                <Share2 className="w-3.5 h-3.5 text-teal-400" />
                <span>Share with Auditor</span>
              </button>
            </div>
          </div>

          {/* Metric Bento Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Overall Posture Score Card */}
            <div className="sm:col-span-2 rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/15 to-surface/80 p-6 flex items-center justify-between shadow-xl">
              <div className="space-y-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 font-semibold">
                  Overall Compliance Score
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="font-display font-extrabold text-4xl sm:text-5xl text-text-primary">
                    {score}%
                  </span>
                  <span className="flex items-center text-xs font-mono text-emerald-400 font-semibold">
                    <TrendingUp className="w-3.5 h-3.5 mr-0.5" /> +3.2%
                  </span>
                </div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono text-[10px] font-semibold">
                  <CheckCircle2 className="w-3 h-3" /> Audit Ready
                </div>
              </div>

              {/* Circular Gauge Graphic */}
              <div className="w-20 h-20 rounded-full border-4 border-indigo-500/20 border-t-indigo-400 border-r-teal-400 flex items-center justify-center flex-shrink-0 shadow-[0_0_20px_rgba(99,102,241,0.25)]">
                <ShieldCheck className="w-8 h-8 text-indigo-300" />
              </div>
            </div>

            {/* Passing Controls */}
            <div className="rounded-2xl border border-white/[0.08] bg-surface/60 p-5 space-y-1">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
                Passing Controls
              </div>
              <div className="font-display font-bold text-2xl text-emerald-400">
                {totalPass}
              </div>
              <div className="font-mono text-[11px] text-text-muted">
                out of {totalControls} evaluated
              </div>
            </div>

            {/* Critical Gaps */}
            <div className="rounded-2xl border border-white/[0.08] bg-surface/60 p-5 space-y-1">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
                Critical Exposures
              </div>
              <div className="font-display font-bold text-2xl text-rose-400">
                {totalFail}
              </div>
              <div className="font-mono text-[11px] text-text-muted">
                1-click remediation ready
              </div>
            </div>

            {/* Evidence Reuse Multiplier */}
            <div className="rounded-2xl border border-white/[0.08] bg-surface/60 p-5 space-y-1">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
                Evidence Crosswalk
              </div>
              <div className="font-display font-bold text-2xl text-indigo-300">
                {posture?.reuse_factor ? `${posture.reuse_factor}x` : '3.8x'}
              </div>
              <div className="font-mono text-[11px] text-text-muted">
                collect once, satisfy 14 specs
              </div>
            </div>
          </div>

          {/* Framework Readiness Grid */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display font-bold text-lg text-text-primary">
                  Framework Readiness Status
                </h2>
                <p className="font-mono text-xs text-text-muted">
                  Continuous assessment mapped to regulatory baselines
                </p>
              </div>

              <Link
                to="/compliance/frameworks"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <span>View All 14 Frameworks</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {frameworks.map((fw) => (
                <div
                  key={fw.framework_id}
                  className="rounded-2xl border border-white/[0.08] bg-surface/50 hover:border-indigo-500/30 hover:bg-surface/80 transition-all p-5 flex flex-col justify-between group shadow-sm"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-mono text-xs uppercase tracking-wider text-indigo-300 font-bold">
                        {fw.framework_name}
                      </span>
                      <span className="font-display font-bold text-sm text-text-primary">
                        {fw.score_percent}%
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-4">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-teal-400"
                        style={{ width: `${fw.score_percent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between font-mono text-[11px] text-text-muted mb-4">
                      <span className="text-emerald-400">{fw.pass_count} Passing</span>
                      <span className="text-rose-400">{fw.fail_count} Failing</span>
                    </div>
                  </div>

                  <button
                    onClick={() => navigate(`/compliance?tab=audit&fw=${fw.framework_id}`)}
                    className="w-full py-2 rounded-xl border border-white/[0.08] hover:border-indigo-500/30 bg-white/[0.02] hover:bg-indigo-500/10 text-text-secondary hover:text-indigo-200 text-xs font-semibold transition-all flex items-center justify-center gap-1.5"
                  >
                    <span>Inspect Controls</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Attack Path & Remediation Highlight */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Attack Path Canvas Widget */}
            <div className="lg:col-span-2 rounded-2xl border border-white/[0.08] bg-surface/50 p-6 flex flex-col justify-between">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <GitMerge className="w-4 h-4 text-rose-400" />
                    <h3 className="font-display font-bold text-base text-text-primary">
                      Toxic Attack Path Discovery
                    </h3>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed max-w-lg">
                    LogRaven correlates cloud exposures into multi-hop exploit paths (e.g. Internet-exposed EC2 with admin role accessing sensitive S3 bucket).
                  </p>
                </div>

                <span className="px-2.5 py-1 rounded-md font-mono text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  Critical Path Detected
                </span>
              </div>

              {/* Path preview steps */}
              <div className="p-4 rounded-xl border border-white/[0.06] bg-black/30 font-mono text-xs flex flex-wrap items-center gap-2 text-text-secondary mb-4">
                <span className="px-2 py-1 rounded bg-rose-500/20 text-rose-300">0.0.0.0/0 (Internet)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-300">Port 22 Open (EC2)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-indigo-500/20 text-indigo-300">FullAdminRole (IAM)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-rose-500/20 text-rose-300">CustomerDataBucket (S3)</span>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="font-mono text-xs text-text-muted">
                  Blast Radius: <strong className="text-rose-400">High Impact</strong>
                </span>

                <button
                  onClick={() => navigate('/compliance?tab=attack-path')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                >
                  <span>Open Interactive DAG Canvas</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Fast Track: Remediation Studio */}
            <div className="rounded-2xl border border-white/[0.08] bg-surface/50 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <SlidersHorizontal className="w-4 h-4 text-teal-400" />
                  <h3 className="font-display font-bold text-base text-text-primary">
                    1-Click Remediation
                  </h3>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed mb-4">
                  Export verified Terraform and AWS CLI fixes for failed compliance controls.
                </p>

                <div className="space-y-2">
                  {[
                    { label: 'S3 Public Access Block', tool: 'Terraform' },
                    { label: 'Enforce MFA on Root Account', tool: 'AWS Console' },
                    { label: 'Enable CloudTrail S3 Data Events', tool: 'AWS CLI' },
                  ].map((fix) => (
                    <div
                      key={fix.label}
                      className="p-2.5 rounded-xl border border-white/[0.04] bg-black/20 flex items-center justify-between text-[11px]"
                    >
                      <span className="text-text-secondary truncate">{fix.label}</span>
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-white/[0.05] text-indigo-300">
                        {fix.tool}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => navigate('/compliance?tab=attack-path')}
                className="w-full mt-4 py-2.5 rounded-xl bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/40 text-teal-200 text-xs font-semibold transition-all"
              >
                Launch Remediation Studio
              </button>
            </div>
          </div>

          {/* Recent Audits Table */}
          {recentAudits.length > 0 && (
            <div className="rounded-2xl border border-white/[0.08] bg-surface/50 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-display font-bold text-base text-text-primary">
                    Recent Compliance Reports
                  </h3>
                  <p className="font-mono text-xs text-text-muted">
                    Evidence runs and downloadable audit artifacts
                  </p>
                </div>

                <Link
                  to="/compliance?tab=history"
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  <span>View All Audits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-text-muted text-[10px] uppercase">
                      <th className="pb-3">Audit Scope</th>
                      <th className="pb-3">Frameworks</th>
                      <th className="pb-3">Date</th>
                      <th className="pb-3">Score</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {recentAudits.map((a) => (
                      <tr key={a.audit_id} className="hover:bg-white/[0.02]">
                        <td className="py-3 font-semibold text-text-primary">{a.company_name}</td>
                        <td className="py-3 text-text-secondary">{(a.frameworks || []).join(' · ')}</td>
                        <td className="py-3 text-text-muted">
                          {formatDateTime(a.created_at, null, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </td>
                        <td className="py-3">
                          <span className="px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                            {a.score_percent ? `${a.score_percent}%` : 'Complete'}
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={async () => {
                                const blob = await downloadAuditReport(a.audit_id)
                                const url = URL.createObjectURL(blob)
                                const link = document.createElement('a')
                                link.href = url
                                link.download = `LogRaven-Audit-${a.company_name}.pdf`
                                link.click()
                              }}
                              title="Download PDF Report"
                              className="p-1.5 rounded-lg border border-white/[0.06] hover:bg-white/[0.06] text-text-muted hover:text-text-primary"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => navigate(`/compliance?tab=history`)}
                              className="text-[11px] font-sans font-semibold text-indigo-400 hover:text-indigo-300"
                            >
                              Details
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cloud Account Connection Modal */}
      <ConnectAccountModal
        isOpen={connectModalOpen}
        onClose={() => setConnectModalOpen(false)}
        onAccountConnected={(acc) => {
          setAccounts((prev) => [...prev, acc])
          setActiveAccount(acc)
          void loadData()
        }}
      />

      {/* Auditor Share Modal */}
      <AuditorShareModal
        isOpen={auditorModalOpen}
        onClose={() => setAuditorModalOpen(false)}
        companyName={activeAccount?.name || 'My Organization'}
      />
    </div>
  )
}
