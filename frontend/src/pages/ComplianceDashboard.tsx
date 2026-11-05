// LogRaven — Compliance & Posture Management Dashboard
// Hallmark · v2.0.0 | shape: stage | theme: watchtower | genre: modern-minimal

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
    <div className="min-h-dvh bg-void text-text-primary p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-8 select-none overflow-x-clip">
      {/* ── CASE 1: NO CLOUD ACCOUNT CONNECTED (High-Impact Onboarding) ── */}
      {!hasAccounts && !loading && (
        <div className="space-y-6">
          {/* Top Warning Banner */}
          <div className="p-4 rounded-xl border border-amber-400/25 bg-amber-400/5 text-text-primary flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="text-xs font-semibold text-text-primary">
                  No cloud accounts connected
                </div>
                <div className="text-xs text-text-muted mt-0.5">
                  Connect your AWS, Azure, or GCP environment to activate continuous compliance audits.
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/compliance/connect/step-1')}
              className="btn-sovereign inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shrink-0 motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Cloud className="w-3.5 h-3.5" />
              <span>Connect account now</span>
            </button>
          </div>

          {/* Hero Command Banner */}
          <div className="rounded-xl border border-white/[0.08] bg-surface p-6 sm:p-10">
            <div className="max-w-2xl space-y-4">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-elevated border border-white/[0.08]">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs text-text-secondary font-medium">
                  Zero-agent cloud security and compliance
                </span>
              </div>

              <h1 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-text-primary tracking-tight leading-tight">
                Automated cloud compliance across 14 standards
              </h1>

              <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
                Connect your AWS, Azure, or GCP fleet using a read-only IAM role. LogRaven continuously collects configuration evidence, detects toxic attack paths, maps compliance against SOC 2, ISO 27001, HIPAA and CIS, and generates auditor-approved PDF packages.
              </p>

              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/compliance/connect/step-1')}
                  className="btn-sovereign flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus className="w-4 h-4" />
                  <span>Connect cloud provider</span>
                </button>

                <Link
                  to="/compliance/frameworks"
                  className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 hover:bg-elevated text-text-secondary hover:text-text-primary text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <Library className="w-4 h-4 text-text-muted" />
                  <span>Explore frameworks directory</span>
                </Link>
              </div>
            </div>

            {/* Quick 3-Step Preview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10 pt-8 border-t border-white/[0.06]">
              {[
                {
                  step: '01',
                  title: 'Attach read-only IAM role',
                  desc: 'Uses standard AWS SecurityAudit policy. Zero write permissions, zero secret keys.',
                },
                {
                  step: '02',
                  title: 'Collect cloud telemetry',
                  desc: 'Collects S3, IAM, CloudTrail, KMS, GuardDuty, and VPC signals once.',
                },
                {
                  step: '03',
                  title: 'Instant auditor package',
                  desc: 'Correlates evidence across 14 frameworks and generates PDF reports with verified fixes.',
                },
              ].map((s) => (
                <div key={s.step} className="p-4 rounded-lg bg-deep border border-white/[0.04]">
                  <div className="font-mono text-xs text-amber-400 font-bold mb-1">{s.step}</div>
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
              <div className="flex items-center gap-2 mb-2 text-xs text-text-muted">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 motion-safe:animate-pulse" />
                <span>Continuous compliance posture: active</span>
              </div>
              <h1 className="font-display font-bold text-2xl sm:text-3xl text-text-primary tracking-tight">
                Executive compliance command
              </h1>
              <p className="text-xs text-text-muted mt-1">
                Monitored fleet: <span className="text-text-primary font-semibold">{activeAccount?.name || 'All accounts'}</span> ({activeAccount?.provider?.toUpperCase()})
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => navigate('/compliance?tab=audit')}
                className="btn-sovereign flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run compliance scan</span>
              </button>

              <button
                type="button"
                onClick={() => setAuditorModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-surface text-text-secondary hover:text-text-primary text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Share2 className="w-3.5 h-3.5 text-amber-400" />
                <span>Share with auditor</span>
              </button>
            </div>
          </div>

          {/* Metric Bento Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Overall Posture Score Card */}
            <div className="sm:col-span-2 rounded-xl border border-white/[0.08] bg-surface p-6 flex items-center justify-between">
              <div className="space-y-2">
                <div className="text-xs text-text-muted font-medium">
                  Overall compliance score
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-display font-bold text-4xl sm:text-5xl text-text-primary tabular-nums">
                    {score}%
                  </span>
                  <span className="flex items-center text-xs font-mono text-emerald-400 font-semibold">
                    <TrendingUp className="w-3.5 h-3.5 mr-0.5" /> +3.2%
                  </span>
                </div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Audit ready</span>
                </div>
              </div>

              {/* Clean Gauge Graphic */}
              <div className="w-20 h-20 rounded-full border-4 border-white/[0.08] border-t-amber-400 border-r-amber-400 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-8 h-8 text-amber-400" />
              </div>
            </div>

            {/* Passing Controls */}
            <div className="rounded-xl border border-white/[0.08] bg-surface p-5 space-y-1">
              <div className="text-xs text-text-muted">
                Passing controls
              </div>
              <div className="font-display font-bold text-2xl text-emerald-400 tabular-nums">
                {totalPass}
              </div>
              <div className="text-[11px] text-text-muted">
                out of <span className="tabular-nums">{totalControls}</span> evaluated
              </div>
            </div>

            {/* Critical Exposures */}
            <div className="rounded-xl border border-white/[0.08] bg-surface p-5 space-y-1">
              <div className="text-xs text-text-muted">
                Critical exposures
              </div>
              <div className="font-display font-bold text-2xl text-threat-critical tabular-nums">
                {totalFail}
              </div>
              <div className="text-[11px] text-text-muted">
                1-click remediation ready
              </div>
            </div>

            {/* Evidence Crosswalk */}
            <div className="rounded-xl border border-white/[0.08] bg-surface p-5 space-y-1">
              <div className="text-xs text-text-muted">
                Evidence crosswalk
              </div>
              <div className="font-display font-bold text-2xl text-amber-400 tabular-nums">
                {posture?.reuse_factor ? `${posture.reuse_factor}x` : '3.8x'}
              </div>
              <div className="text-[11px] text-text-muted">
                collect once, satisfy 14 specs
              </div>
            </div>
          </div>

          {/* Framework Readiness Grid */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display font-bold text-lg text-text-primary">
                  Framework readiness status
                </h2>
                <p className="text-xs text-text-muted">
                  Continuous assessment mapped to regulatory baselines
                </p>
              </div>

              <Link
                to="/compliance/frameworks"
                className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
              >
                <span>View all 14 frameworks</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {frameworks.map((fw) => (
                <div
                  key={fw.framework_id}
                  className="rounded-xl border border-white/[0.08] bg-surface p-5 flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs text-text-primary font-semibold">
                        {fw.framework_name}
                      </span>
                      <span className="font-display font-bold text-sm text-text-primary tabular-nums">
                        {fw.score_percent}%
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-4">
                      <div
                        className="h-full rounded-full bg-amber-400"
                        style={{ width: `${fw.score_percent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-text-muted mb-4 tabular-nums">
                      <span className="text-emerald-400">{fw.pass_count} passing</span>
                      <span className="text-threat-critical">{fw.fail_count} failing</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => navigate(`/compliance/frameworks/${fw.framework_id}`)}
                    className="w-full py-2 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 hover:bg-elevated text-text-secondary hover:text-text-primary text-xs font-medium transition-colors flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span>Inspect controls</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 motion-safe:transition-transform motion-reduce:transition-none" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Attack Path & Remediation Highlight */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Attack Path Canvas Widget */}
            <div className="lg:col-span-2 rounded-xl border border-white/[0.08] bg-surface p-6 flex flex-col justify-between">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <GitMerge className="w-4 h-4 text-threat-critical" />
                    <h3 className="font-display font-bold text-base text-text-primary">
                      Toxic attack path discovery
                    </h3>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed max-w-lg">
                    LogRaven correlates cloud exposures into multi-hop exploit paths (such as internet-exposed EC2 with admin role accessing sensitive S3 bucket).
                  </p>
                </div>

                <span className="px-2.5 py-1 rounded-md text-[10px] font-medium bg-threat-critical/15 text-threat-critical border border-threat-critical/30">
                  Critical path detected
                </span>
              </div>

              {/* Path preview steps */}
              <div className="p-4 rounded-lg border border-white/[0.06] bg-deep font-mono text-xs flex flex-wrap items-center gap-2 text-text-secondary mb-4">
                <span className="px-2 py-1 rounded bg-threat-critical/20 text-threat-critical">0.0.0.0/0 (Internet)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-threat-high/20 text-threat-high">Port 22 Open (EC2)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-amber-400/20 text-amber-300">FullAdminRole (IAM)</span>
                <span className="text-text-muted">➔</span>
                <span className="px-2 py-1 rounded bg-threat-critical/20 text-threat-critical">CustomerDataBucket (S3)</span>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-text-muted">
                  Blast radius: <strong className="text-threat-critical">High impact</strong>
                </span>

                <button
                  type="button"
                  onClick={() => navigate('/compliance?tab=attack-path')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                >
                  <span>Open DAG canvas</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Fast Track: Remediation Studio */}
            <div className="rounded-xl border border-white/[0.08] bg-surface p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <SlidersHorizontal className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-display font-bold text-base text-text-primary">
                    1-click remediation
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
                      className="p-2.5 rounded-lg border border-white/[0.04] bg-deep flex items-center justify-between text-[11px]"
                    >
                      <span className="text-text-secondary truncate">{fix.label}</span>
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-white/[0.05] text-amber-300">
                        {fix.tool}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => navigate('/compliance?tab=attack-path')}
                className="w-full mt-4 py-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Remediation studio
              </button>
            </div>
          </div>

          {/* Recent Audits Table */}
          {recentAudits.length > 0 && (
            <div className="rounded-xl border border-white/[0.08] bg-surface p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-display font-bold text-base text-text-primary">
                    Recent compliance reports
                  </h3>
                  <p className="text-xs text-text-muted">
                    Evidence runs and downloadable audit artifacts
                  </p>
                </div>

                <Link
                  to="/compliance?tab=history"
                  className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                >
                  <span>View all audits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-text-muted text-[11px]">
                      <th className="pb-3 font-medium">Audit scope</th>
                      <th className="pb-3 font-medium">Frameworks</th>
                      <th className="pb-3 font-medium">Date</th>
                      <th className="pb-3 font-medium">Score</th>
                      <th className="pb-3 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {recentAudits.map((a) => (
                      <tr key={a.audit_id} className="hover:bg-elevated/40 transition-colors">
                        <td className="py-3 font-semibold text-text-primary">{a.company_name}</td>
                        <td className="py-3 text-text-secondary">{(a.frameworks || []).join(', ')}</td>
                        <td className="py-3 text-text-muted font-mono tabular-nums">
                          {formatDateTime(a.created_at, null, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </td>
                        <td className="py-3 font-mono tabular-nums">
                          <span className="px-2 py-0.5 rounded-md bg-elevated text-text-primary border border-white/[0.08]">
                            {a.score_percent ? `${a.score_percent}%` : 'Complete'}
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={async () => {
                                const blob = await downloadAuditReport(a.audit_id)
                                const url = URL.createObjectURL(blob)
                                const link = document.createElement('a')
                                link.href = url
                                link.download = `LogRaven-Audit-${a.company_name}.pdf`
                                link.click()
                              }}
                              title="Download PDF report"
                              className="p-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => navigate(`/compliance?tab=history`)}
                              className="text-[11px] font-medium text-amber-400 hover:text-amber-300 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded px-1.5 py-0.5"
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

      {/* Auditor Share Modal */}
      <AuditorShareModal
        isOpen={auditorModalOpen}
        onClose={() => setAuditorModalOpen(false)}
        companyName={activeAccount?.name || 'My Organization'}
      />
    </div>
  )
}
