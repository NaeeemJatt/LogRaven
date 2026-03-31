// LogRaven — Security report (matches dashboard chrome)
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, Download } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import FindingCard from '../components/reports/FindingCard'
import CorrelationCard from '../components/reports/CorrelationCard'
import IOCTable from '../components/reports/IOCTable'
import MitreMatrix from '../components/reports/MitreMatrix'
import SeverityChart from '../components/reports/SeverityChart'
import { investigationsApi } from '../api/investigations'
import type { Finding } from '../types/report'

const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'informational']

function sortBySeverity(findings: Finding[]): Finding[] {
  return [...findings].sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity))
}

function uniqueIocs(findings: Finding[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const f of findings)
    for (const ioc of f.iocs ?? []) {
      const s = String(ioc).trim()
      if (s && !seen.has(s)) {
        seen.add(s)
        out.push(s)
      }
    }
  return out
}

function iocSourceHints(findings: Finding[]): Record<string, string> {
  const m: Record<string, string> = {}
  for (const f of findings) {
    const hint =
      f.source_files && f.source_files.length > 0
        ? f.source_files.join(', ')
        : (f.title?.slice(0, 48) ?? 'Finding')
    for (const ioc of f.iocs ?? []) {
      const s = String(ioc).trim()
      if (s && m[s] === undefined) m[s] = hint
    }
  }
  return m
}

function SectionHeader({ label, subtitle }: { label: string; subtitle?: string }) {
  return (
    <div className="mb-4 mt-10 first:mt-0">
      <div className="flex items-center gap-3 mb-1">
        <div className="h-5 w-1 rounded-full bg-electric-500" />
        <span className="text-xs font-semibold uppercase tracking-[0.15em] text-electric-400/90">
          {label}
        </span>
      </div>
      {subtitle && <p className="text-sm text-raven-500 pl-4">{subtitle}</p>}
    </div>
  )
}

function StatCard({
  label,
  value,
  valueClass,
}: {
  label: string
  value: number
  valueClass: string
}) {
  return (
    <div className="rounded-xl border border-raven-700 bg-raven-800/80 p-5 shadow-lg shadow-black/10">
      <p className={`text-3xl font-bold tabular-nums ${valueClass}`}>{value}</p>
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-raven-500">{label}</p>
    </div>
  )
}

export default function Report() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [pdfLoading, setPdfLoading] = useState(false)

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['report', id],
    queryFn: async () => (await investigationsApi.getReport(id!)).data,
    enabled: !!id,
  })

  const handleDownloadPdf = async () => {
    setPdfLoading(true)
    try {
      const res = await investigationsApi.getReportDownload(id!)
      window.open(res.data.download_url, '_blank')
    } catch {
      alert('PDF not ready. Run analysis first.')
    } finally {
      setPdfLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-raven-950">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          <div
            className="h-10 w-10 rounded-full border-2 border-raven-700 border-t-electric-500 animate-spin"
            aria-hidden
          />
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-raven-950">
        <Navbar />
        <div className="flex flex-col items-center justify-center py-32 gap-3 px-4">
          <p className="text-rose-400 text-sm text-center border border-rose-900/50 bg-rose-950/30 px-4 py-3 rounded-lg max-w-md">
            Report not available.
          </p>
          <button
            type="button"
            onClick={() => navigate(`/investigations/${id}/status`)}
            className="text-sm text-electric-400 hover:text-electric-300 transition-colors"
          >
            Check analysis status →
          </button>
        </div>
      </div>
    )
  }

  const allFindings: Finding[] = report.findings ?? []
  const correlated = allFindings.filter((f) => f.finding_type === 'correlated')
  const single = sortBySeverity(allFindings.filter((f) => f.finding_type !== 'correlated'))
  const iocs = uniqueIocs(allFindings)
  const iocHints = iocSourceHints(allFindings)
  const counts = report.severity_counts ?? {}

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between mb-10">
          <div>
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="inline-flex items-center gap-1 text-sm text-raven-500 hover:text-electric-400 transition-colors mb-4"
            >
              <ChevronLeft className="h-4 w-4" />
              Investigations
            </button>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">Security report</h1>
            <p className="text-raven-500 text-sm font-mono mt-2">
              {new Date(report.created_at).toLocaleString('en-GB')}
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={pdfLoading}
            className="inline-flex items-center justify-center gap-2 self-start rounded-lg border border-electric-500/60 bg-electric-500/10 px-5 py-2.5 text-sm font-semibold text-electric-400 hover:bg-electric-500/15 hover:border-electric-400 disabled:opacity-50 transition-colors shrink-0"
          >
            <Download className="h-4 w-4" />
            {pdfLoading ? 'Preparing…' : 'Download PDF'}
          </button>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total" value={allFindings.length} valueClass="text-white" />
          <StatCard label="Critical" value={counts.critical ?? 0} valueClass="text-red-400" />
          <StatCard label="High" value={counts.high ?? 0} valueClass="text-orange-400" />
          <StatCard label="Medium" value={counts.medium ?? 0} valueClass="text-yellow-400" />
        </div>

        <div className="mb-10">
          <SeverityChart counts={counts} />
        </div>

        {report.summary && (
          <div className="rounded-xl border border-raven-700 bg-raven-900/80 px-6 py-5 mb-10 shadow-lg shadow-black/15">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-raven-500 mb-3">Summary</p>
            <p className="text-raven-200 text-sm leading-relaxed">{report.summary}</p>
          </div>
        )}

        {correlated.length > 0 && (
          <>
            <SectionHeader
              label="Correlated findings"
              subtitle="These findings span multiple log sources — highest-confidence attack indicators."
            />
            <div className="space-y-3">
              {correlated.map((f) => (
                <CorrelationCard key={f.id} finding={f} />
              ))}
            </div>
          </>
        )}

        {single.length > 0 && (
          <>
            <SectionHeader label="Individual findings" />
            <div className="space-y-3">
              {single.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          </>
        )}

        {report.mitre_techniques && report.mitre_techniques.length > 0 && (
          <>
            <SectionHeader label="MITRE ATT&CK" />
            <MitreMatrix techniques={report.mitre_techniques} />
          </>
        )}

        {iocs.length > 0 && (
          <>
            <SectionHeader label={`Extracted IOCs (${iocs.length})`} />
            <IOCTable values={iocs} sourceHint={iocHints} />
          </>
        )}

        {allFindings.length === 0 && (
          <div className="rounded-xl border border-raven-700 bg-raven-800/40 px-8 py-14 text-center mt-8">
            <p className="text-raven-300 text-sm">No findings generated.</p>
            <p className="text-raven-600 text-xs font-mono mt-2">
              AI analysis may have been skipped or found no threats.
            </p>
          </div>
        )}

        <div className="flex justify-center mt-12 mb-6">
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={pdfLoading}
            className="inline-flex items-center gap-2 rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-50 text-raven-950 font-semibold text-sm px-8 py-3 transition-colors"
          >
            <Download className="h-4 w-4" />
            {pdfLoading ? 'Preparing…' : 'Download full PDF report'}
          </button>
        </div>
      </main>
    </div>
  )
}
