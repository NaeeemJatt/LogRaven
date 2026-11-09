// LogRaven — Executive Cloud Security Posture Command Dashboard
// Hallmark · v2.0.0 | shape: stage | theme: watchtower | genre: modern-minimal (CrowdStrike Falcon Standard)

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Cloud,
  Play,
  Share2,
  ChevronRight,
  GitMerge,
  SlidersHorizontal,
  AlertTriangle,
  Plus,
  Library,
  ArrowRight,
} from 'lucide-react'
import {
  listCloudAccounts,
  getPosture,
  type PostureResponse,
} from '../api/compliance'
import type { CloudAccount } from '../types/audit'
import AuditorShareModal from '../components/audit/AuditorShareModal'
import PostureKpiCard from '../components/compliance/PostureKpiCard'
import AdversaryRisksCard from '../components/compliance/AdversaryRisksCard'
import IomRulesTable from '../components/compliance/IomRulesTable'
import MisconfiguredAccountsTable from '../components/compliance/MisconfiguredAccountsTable'
import PostureDonutChart from '../components/compliance/PostureDonutChart'
import { AssetsBarChart, AssetsTimeSeriesChart } from '../components/compliance/AssetsTimeSeriesChart'

export default function ComplianceDashboard() {
  const navigate = useNavigate()

  const [accounts, setAccounts] = useState<CloudAccount[]>([])
  const [activeAccount, setActiveAccount] = useState<CloudAccount | null>(null)
  const [posture, setPosture] = useState<PostureResponse | null>(null)
  const [loading, setLoading] = useState(true)

  // Modals
  const [auditorModalOpen, setAuditorModalOpen] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [accs, pos] = await Promise.all([
        listCloudAccounts().catch(() => []),
        getPosture().catch(() => null),
      ])
      setAccounts(accs)
      if (accs.length > 0) {
        setActiveAccount(accs[0])
      }
      setPosture(pos)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const hasAccounts = accounts.length > 0

  const frameworks = posture?.frameworks ?? [
    {
      framework_id: 'soc2',
      framework_name: 'SOC 2 Type II',
      score_percent: 89,
      pass_count: 57,
      fail_count: 5,
    },
    {
      framework_id: 'cis_aws',
      framework_name: 'CIS AWS Foundations',
      score_percent: 92,
      pass_count: 53,
      fail_count: 4,
    },
    {
      framework_id: 'pci_dss',
      framework_name: 'PCI DSS v4.0',
      score_percent: 85,
      pass_count: 48,
      fail_count: 8,
    },
    {
      framework_id: 'iso27001',
      framework_name: 'ISO/IEC 27001:2022',
      score_percent: 84,
      pass_count: 78,
      fail_count: 10,
    },
  ]

  return (
    <div className="min-h-dvh bg-void text-text-primary p-4 sm:p-6 lg:p-8 w-full space-y-8 select-none overflow-x-clip">
      {/* ── CASE 1: NO CLOUD ACCOUNT CONNECTED (High-Impact Onboarding) ── */}
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
                  Connect your AWS, Azure, or GCP environment to activate continuous posture assessments.
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

          <div className="rounded-xl border border-white/[0.08] bg-surface p-6 sm:p-10">
            <div className="max-w-2xl space-y-4">
              <h1 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-text-primary tracking-tight leading-tight">
                Enterprise cloud security posture command
              </h1>
              <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
                Connect your AWS fleet using a read-only IAM role. LogRaven continuously monitors indicators of misconfiguration (IOM), correlates adversary attack paths, and ensures framework readiness across SOC 2, ISO 27001, and CIS.
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
          </div>
        </div>
      )}

      {/* ── CASE 2: CLOUD ACCOUNT CONNECTED (Falcon Master Posture View) ── */}
      {hasAccounts && (
        <div className="space-y-8">
          {/* Executive Header */}
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/[0.08] pb-5">
            <div>
              <div className="flex items-center gap-2 mb-1.5 text-xs text-text-muted">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>Continuous compliance posture: active</span>
              </div>
              <h1 className="font-display font-bold text-2xl sm:text-3xl text-text-primary tracking-tight">
                Executive compliance command
              </h1>
              <p className="text-xs text-text-muted mt-1">
                Monitored fleet: <span className="text-text-primary font-semibold">{activeAccount?.name || 'Production'}</span> ({activeAccount?.provider?.toUpperCase() ?? 'AWS'})
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => navigate('/compliance?tab=audit')}
                className="btn-sovereign flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run compliance scan</span>
              </button>

              <button
                type="button"
                onClick={() => setAuditorModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-surface text-text-secondary hover:text-text-primary text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                <Share2 className="w-3.5 h-3.5 text-amber-400" />
                <span>Share with auditor</span>
              </button>
            </div>
          </div>

          {/* ── TIER 1: 4 TOP KPI BENTO CARDS (CrowdStrike Pattern) ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Attack Paths */}
            <PostureKpiCard
              title="Attack paths"
              value={8}
              lastRefreshed="19:05:00"
              onClick={() => navigate('/compliance?tab=posture')}
            />

            {/* 2. Adversary Aware Risks Intelligence */}
            <AdversaryRisksCard
              lastRefreshed="19:05:08"
              onClick={() => navigate('/alerts')}
            />

            {/* 3. Critical IOM Rules (Solid Crimson Bottom Accent Bar) */}
            <PostureKpiCard
              title="Critical IOM rules"
              value={0}
              accentColor="critical"
              lastRefreshed="19:05:05"
              onClick={() => navigate('/compliance?tab=audit&severity=critical')}
            />

            {/* 4. High IOM Rules (Solid Orange Bottom Accent Bar) */}
            <PostureKpiCard
              title="High IOM rules"
              value={30}
              accentColor="high"
              lastRefreshed="19:05:05"
              onClick={() => navigate('/compliance?tab=audit&severity=high')}
            />
          </div>

          {/* ── TIER 2: MIDDLE OPERATIONAL TABLES (Top 10 IOM & Accounts) ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Top Detected IOM Rules by Severity */}
            <IomRulesTable lastRefreshed="19:05:05" />

            {/* Right: Top Misconfigured Accounts */}
            <MisconfiguredAccountsTable lastRefreshed="19:05:05" />
          </div>

          {/* ── TIER 3: BOTTOM TELEMETRY & ANALYTICS VISUALIZATIONS ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 1. Total Open IOMs Count by Severity Donut Chart (7k Metric) */}
            <PostureDonutChart
              totalCount="7k"
              highCount={540}
              mediumCount={5329}
              infoCount={1761}
              lastRefreshed="19:05:06"
            />

            {/* 2. Assets with IOMs Bar Chart */}
            <AssetsBarChart lastRefreshed="19:05:08" />

            {/* 3. Assets with IOM's by Asset Type (7-Day Multi-Line Series) */}
            <AssetsTimeSeriesChart lastRefreshed="19:05:07" />
          </div>

          {/* ── TIER 4: TOXIC ATTACK PATHS & 1-CLICK REMEDIATION FAST-TRACK ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Attack Path Canvas Widget */}
            <div className="lg:col-span-2 rounded-xl border border-white/[0.08] bg-surface p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between mb-3">
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
                  <span className="px-2.5 py-1 rounded-md text-[10px] font-medium bg-threat-critical/15 text-threat-critical border border-threat-critical/30 shrink-0">
                    Critical path detected
                  </span>
                </div>

                {/* Path preview steps */}
                <div className="p-3.5 rounded-lg border border-white/[0.06] bg-deep font-mono text-xs flex flex-wrap items-center gap-2 text-text-secondary my-3">
                  <span className="px-2 py-1 rounded bg-threat-critical/20 text-threat-critical">0.0.0.0/0 (Internet)</span>
                  <span className="text-text-muted">➔</span>
                  <span className="px-2 py-1 rounded bg-threat-high/20 text-threat-high">Port 22 Open (EC2)</span>
                  <span className="text-text-muted">➔</span>
                  <span className="px-2 py-1 rounded bg-amber-400/20 text-amber-300">FullAdminRole (IAM)</span>
                  <span className="text-text-muted">➔</span>
                  <span className="px-2 py-1 rounded bg-threat-critical/20 text-threat-critical">CustomerDataBucket (S3)</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-white/[0.04]">
                <span className="text-xs text-text-muted">
                  Blast radius: <strong className="text-threat-critical">High impact</strong>
                </span>

                <button
                  type="button"
                  onClick={() => navigate('/compliance?tab=posture')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
                >
                  <span>Open attack path canvas</span>
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
                    1-click remediation studio
                  </h3>
                </div>
                <p className="text-xs text-text-secondary leading-relaxed mb-4">
                  Export verified Terraform and AWS CLI fixes for failed compliance controls.
                </p>

                <div className="p-3 rounded-lg border border-white/[0.06] bg-deep space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-primary text-[11px] font-medium">S3 Public Access Block</span>
                    <span className="text-[10px] text-amber-400 bg-amber-400/10 px-1.5 py-0.5 rounded font-medium">Terraform</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-primary text-[11px] font-medium">IAM MFA Enforcement</span>
                    <span className="text-[10px] text-sky-400 bg-sky-400/10 px-1.5 py-0.5 rounded font-medium">AWS CLI</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-white/[0.04]">
                <button
                  type="button"
                  onClick={() => navigate('/compliance?tab=posture')}
                  className="w-full py-2 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 hover:bg-elevated text-text-primary text-xs font-medium transition-colors flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  <span>Open remediation studio</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* ── TIER 5: REGULATORY FRAMEWORK READINESS CARDS ── */}
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
                  className="rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-text-primary font-semibold">
                        {fw.framework_name}
                      </span>
                      <span className="font-display font-bold text-sm text-text-primary tabular-nums">
                        {fw.score_percent}%
                      </span>
                    </div>

                    <div className="w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-3">
                      <div
                        className="h-full rounded-full bg-amber-400"
                        style={{ width: `${fw.score_percent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-text-muted mb-3 tabular-nums">
                      <span className="text-emerald-400">{fw.pass_count} passing</span>
                      <span className="text-threat-critical">{fw.fail_count} failing</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => navigate(`/compliance?tab=audit&fw=${fw.framework_id}`)}
                    className="w-full py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.18] bg-elevated/40 hover:bg-elevated text-text-secondary hover:text-text-primary text-xs font-medium transition-colors flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span>Inspect controls</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 motion-safe:transition-transform motion-reduce:transition-none" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Global Auditor Vault Share Modal */}
      <AuditorShareModal
        isOpen={auditorModalOpen}
        onClose={() => setAuditorModalOpen(false)}
        companyName={activeAccount?.name || 'Production'}
      />
    </div>
  )
}
