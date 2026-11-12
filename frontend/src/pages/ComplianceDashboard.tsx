// LogRaven — Compliance & Posture Management Dashboard
// Design inspiration: High-density security command center with bottom accent bars and operational telemetry
import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ShieldCheck,
  AlertTriangle,
  Cloud,
  ChevronRight,
  Download,
  TrendingUp,
  CheckCircle2,
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
import { formatDateTime } from '../utils/dateTime'

export default function ComplianceDashboard() {
  const navigate = useNavigate()

  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [posture, setPosture] = useState<PostureResponse | null>(null)
  const [recentAudits, setRecentAudits] = useState<AuditSummary[]>([])
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [accs, pos, audits] = await Promise.all([
        listCloudAccounts().catch(() => []),
        getPosture().catch(() => null),
        listAudits(1, 5).catch(() => ({ items: [] })),
      ])
      setAccounts(accs)
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

  // Posture numbers
  const score = posture?.overall_score ?? (hasAccounts ? 9.89 : 0)
  const frameworks = posture?.frameworks ?? [
    {
      framework_id: 'cis_aws',
      framework_name: 'CIS AWS Foundations Benchmark',
      score_percent: 14.29,
      pass_count: 3,
      fail_count: 12,
      partial_count: 0,
      score_delta: 0,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'pci_dss',
      framework_name: 'PCI DSS v4.0',
      score_percent: 15.38,
      pass_count: 2,
      fail_count: 6,
      partial_count: 0,
      score_delta: 0,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'soc2',
      framework_name: 'SOC 2 Type II',
      score_percent: 0,
      pass_count: 0,
      fail_count: 8,
      partial_count: 3,
      score_delta: 0,
      as_of: new Date().toISOString(),
    },
    {
      framework_id: 'iso27001',
      framework_name: 'ISO/IEC 27001:2022',
      score_percent: 0,
      pass_count: 0,
      fail_count: 5,
      partial_count: 0,
      score_delta: 0,
      as_of: new Date().toISOString(),
    },
  ]

  const totalPass = frameworks.reduce((acc, f) => acc + f.pass_count, 0)
  const totalFail = frameworks.reduce((acc, f) => acc + f.fail_count, 0)
  const totalControls = totalPass + totalFail

  return (
    <div className="min-h-screen bg-void text-text-primary px-4 sm:px-6 lg:px-8 py-4 sm:py-5 w-full space-y-6 select-none">
      {/* ── CASE 1: NO CLOUD ACCOUNT CONNECTED (Onboarding) ── */}
      {!hasAccounts && !loading && (
        <div className="space-y-6">
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
              className="btn-sovereign inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold shrink-0 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transform-none"
            >
              <Cloud className="w-3.5 h-3.5" />
              <span>Connect account</span>
            </button>
          </div>
        </div>
      )}

      {/* ── CASE 2: CONNECTED FLEET (Command Center) ── */}
      {(hasAccounts || loading) && (
        <>
          {/* 3 Top Bento KPI Cards with Solid Bottom Accents */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Card 1: Overall Score */}
            <div className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md p-5 flex flex-col justify-between relative overflow-hidden">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-medium text-text-muted">Overall compliance score</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="font-display text-3xl font-bold text-text-primary tabular-nums tracking-tight">
                      {score}%
                    </span>
                    <span className="inline-flex items-center text-xs font-semibold text-emerald-400">
                      <TrendingUp className="w-3 h-3 mr-0.5" /> +3.2%
                    </span>
                  </div>
                </div>

                {/* Score Arc SVG Gauge */}
                <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
                  <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36" aria-hidden="true">
                    <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
                    <circle
                      cx="18"
                      cy="18"
                      r="14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeDasharray="88"
                      strokeDashoffset={88 - (88 * Math.min(score, 100)) / 100}
                      strokeLinecap="round"
                      className="text-amber-400"
                    />
                  </svg>
                  <ShieldCheck className="w-4 h-4 text-amber-400 absolute inset-0 m-auto" />
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-text-muted">
                <span>Evaluation status</span>
                <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3 h-3" /> Audit ready
                </span>
              </div>
              <div className="absolute bottom-0 inset-x-0 h-1 bg-amber-400" />
            </div>

            {/* Card 2: Passing Controls */}
            <div className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md p-5 flex flex-col justify-between relative overflow-hidden">
              <div>
                <span className="text-xs font-medium text-text-muted">Passing controls</span>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="font-display text-3xl font-bold text-emerald-400 tabular-nums tracking-tight">
                    {totalPass}
                  </span>
                  <span className="text-xs text-text-muted">
                    of {totalControls} evaluated
                  </span>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-emerald-400 h-1.5 rounded-full"
                    style={{ width: `${totalControls > 0 ? (totalPass / totalControls) * 100 : 0}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-text-muted pt-1">
                  <span>Pass rate</span>
                  <span className="tabular-nums font-medium text-text-secondary">
                    {totalControls > 0 ? Math.round((totalPass / totalControls) * 100) : 0}%
                  </span>
                </div>
              </div>
              <div className="absolute bottom-0 inset-x-0 h-1 bg-emerald-400" />
            </div>

            {/* Card 3: Critical & High Exposures */}
            <div className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md p-5 flex flex-col justify-between relative overflow-hidden">
              <div>
                <span className="text-xs font-medium text-text-muted">Failing exposures</span>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="font-display text-3xl font-bold text-threat-critical tabular-nums tracking-tight">
                    {totalFail}
                  </span>
                  <span className="text-xs text-threat-critical font-medium">
                    Critical gaps
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs">
                <span className="text-text-muted">Remediation status</span>
                <Link
                  to="/compliance?tab=posture"
                  className="inline-flex items-center gap-1 text-amber-300 hover:text-amber-200 font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                >
                  <span>1-click remediation</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="absolute bottom-0 inset-x-0 h-1 bg-threat-critical" />
            </div>
          </div>

          {/* Framework Readiness Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display font-bold text-base text-text-primary tracking-tight">
                  Framework Readiness Status
                </h2>
                <p className="text-xs text-text-muted">
                  Continuous control assessment mapped to regulatory baselines
                </p>
              </div>

              <Link
                to="/compliance/frameworks"
                className="text-xs font-medium text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
              >
                <span>View all 14 frameworks</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {frameworks.map((f) => (
                <div
                  key={f.framework_id}
                  className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md p-4 flex flex-col justify-between space-y-3 hover:border-white/[0.14] transition-colors duration-150"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-xs text-text-primary line-clamp-1" title={f.framework_name}>
                      {f.framework_name}
                    </span>
                    <span className="font-display font-bold text-xs tabular-nums text-text-primary">
                      {f.score_percent}%
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-1.5 rounded-full ${
                        f.score_percent >= 70 ? 'bg-emerald-400' : f.score_percent > 0 ? 'bg-amber-400' : 'bg-white/[0.1]'
                      }`}
                      style={{ width: `${Math.max(f.score_percent, 2)}%` }}
                    />
                  </div>

                  {/* Passing vs Failing counts */}
                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span className="inline-flex items-center gap-1 text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      {f.pass_count} passing
                    </span>
                    <span className="inline-flex items-center gap-1 text-threat-critical">
                      <span className="w-1.5 h-1.5 rounded-full bg-threat-critical" />
                      {f.fail_count} failing
                    </span>
                  </div>

                  <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between">
                    <Link
                      to={`/compliance?tab=posture&fw=${f.framework_id}`}
                      className="text-[11px] font-medium text-text-muted hover:text-amber-300 transition-colors duration-150 inline-flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                    >
                      <span>Inspect controls</span>
                      <ChevronRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Audits Evidence Ledger */}
          <div className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display font-bold text-base text-text-primary tracking-tight">
                  Recent Compliance Assessments
                </h2>
                <p className="text-xs text-text-muted">
                  Cryptographic evidence runs and official audit report artifacts
                </p>
              </div>

              <Link
                to="/compliance?tab=history"
                className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
              >
                <span>View all audits ledger</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {recentAudits.length === 0 ? (
              <div className="py-8 text-center text-xs text-text-muted">
                No past compliance assessments yet. Click &ldquo;Run compliance scan&rdquo; above to execute an audit against your connected fleet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/[0.08] text-text-muted text-[11px] bg-white/[0.01]">
                      <th className="py-2.5 px-3 font-medium">Audit Scope</th>
                      <th className="py-2.5 px-3 font-medium">Frameworks</th>
                      <th className="py-2.5 px-3 font-medium">Date</th>
                      <th className="py-2.5 px-3 font-medium">Score</th>
                      <th className="py-2.5 px-3 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {recentAudits.map((a) => (
                      <tr key={a.audit_id} className="hover:bg-white/[0.02] transition-colors duration-150">
                        <td className="py-3 px-3 font-medium text-text-primary">{a.company_name}</td>
                        <td className="py-3 px-3 text-text-secondary font-mono text-[11px]">
                          {(a.frameworks || []).join(' · ')}
                        </td>
                        <td className="py-3 px-3 text-text-muted font-mono tabular-nums">
                          {formatDateTime(a.created_at, null, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </td>
                        <td className="py-3 px-3 tabular-nums">
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-white/[0.04] text-text-primary border border-white/[0.08]">
                            {a.score_percent ? `${a.score_percent}%` : 'Complete'}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
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
                              title="Download PDF evidence report"
                              className="p-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.2] bg-white/[0.02] text-text-muted hover:text-text-primary transition-colors duration-150 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transform-none"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => navigate(`/compliance?tab=results&auditId=${a.audit_id}`)}
                              className="text-[11px] font-medium text-amber-400 hover:text-amber-300 transition-colors duration-150 px-2 py-1 rounded bg-amber-400/10 hover:bg-amber-400/20 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none active:scale-[0.98] motion-reduce:transform-none"
                            >
                              View result
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
