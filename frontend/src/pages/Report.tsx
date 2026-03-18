// LogRaven — Report Page
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from '../components/layout/Navbar'
import FindingCard from '../components/reports/FindingCard'
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
      if (s && !seen.has(s)) { seen.add(s); out.push(s) }
    }
  return out
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4 mt-8">
      <div className="w-0.5 h-4 bg-electric-500" />
      <span className="text-raven-400 text-xs uppercase tracking-widest font-medium">{label}</span>
    </div>
  )
}

export default function Report() {
  const { id }   = useParams<{ id: string }>()
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

  if (isLoading) return (
    <div className="min-h-screen bg-raven-900"><Navbar />
      <div className="flex items-center justify-center py-32 text-raven-400 text-sm font-mono">Loading report...</div>
    </div>
  )

  if (error || !report) return (
    <div className="min-h-screen bg-raven-900"><Navbar />
      <div className="flex flex-col items-center justify-center py-32 gap-3">
        <p className="text-red-400 text-sm font-mono">— Report not available.</p>
        <button
          onClick={() => navigate(`/investigations/${id}/status`)}
          className="text-raven-400 text-xs hover:text-electric-500 transition-colors"
        >
          Check analysis status →
        </button>
      </div>
    </div>
  )

  const allFindings: Finding[] = report.findings ?? []
  const correlated = allFindings.filter((f) => f.finding_type === 'correlated')
  const single     = sortBySeverity(allFindings.filter((f) => f.finding_type !== 'correlated'))
  const iocs       = uniqueIocs(allFindings)
  const counts     = report.severity_counts ?? {}

  return (
    <div className="min-h-screen bg-raven-900">
      <Navbar />

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Top bar */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <button
              onClick={() => navigate('/dashboard')}
              className="text-raven-400 text-xs hover:text-electric-500 transition-colors mb-2 block"
            >
              ← Investigations
            </button>
            <h1 className="text-white text-xl font-semibold">Security Report</h1>
            <p className="text-raven-400 text-xs font-mono mt-1">
              {new Date(report.created_at).toLocaleString('en-GB')}
            </p>
          </div>
          <button
            onClick={handleDownloadPdf}
            disabled={pdfLoading}
            className="border border-electric-500 text-electric-500 text-xs px-4 py-2 rounded-none hover:bg-electric-900 disabled:opacity-50 transition-colors uppercase tracking-wide flex-shrink-0"
          >
            {pdfLoading ? 'Loading...' : 'Download PDF'}
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Total',    value: allFindings.length,     color: 'text-raven-200' },
            { label: 'Critical', value: counts.critical ?? 0,   color: 'text-red-400' },
            { label: 'High',     value: counts.high ?? 0,       color: 'text-orange-400' },
            { label: 'Medium',   value: counts.medium ?? 0,     color: 'text-yellow-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-raven-800 border border-raven-700 p-4">
              <p className={`text-2xl font-mono font-bold ${color}`}>{value}</p>
              <p className="text-raven-400 text-xs uppercase tracking-widest mt-1">{label}</p>
            </div>
          ))}
        </div>

        {/* Executive summary */}
        {report.summary && (
          <div className="bg-raven-800 border border-raven-700 px-5 py-4 mt-6">
            <p className="text-raven-400 text-xs uppercase tracking-widest mb-2">Summary</p>
            <p className="text-raven-300 text-sm leading-relaxed">{report.summary}</p>
          </div>
        )}

        {/* Correlated findings */}
        {correlated.length > 0 && (
          <>
            <SectionHeader label="Correlated Findings" />
            <p className="text-raven-600 text-xs mb-3">
              These findings span multiple log sources — highest confidence attack indicators.
            </p>
            {correlated.map((f) => <FindingCard key={f.id} finding={f} />)}
          </>
        )}

        {/* Individual findings */}
        {single.length > 0 && (
          <>
            <SectionHeader label="Individual Findings" />
            {single.map((f) => <FindingCard key={f.id} finding={f} />)}
          </>
        )}

        {/* MITRE techniques */}
        {report.mitre_techniques && report.mitre_techniques.length > 0 && (
          <>
            <SectionHeader label="MITRE ATT&CK" />
            <div className="flex flex-wrap gap-1.5">
              {report.mitre_techniques.map((t: string) => (
                <span key={t} className="bg-raven-800 border border-raven-700 px-2 py-0.5 text-electric-400 font-mono text-xs rounded-none">
                  {t}
                </span>
              ))}
            </div>
          </>
        )}

        {/* IOCs */}
        {iocs.length > 0 && (
          <>
            <SectionHeader label={`Extracted IOCs (${iocs.length})`} />
            <div className="flex flex-wrap gap-1.5">
              {iocs.map((ioc, i) => (
                <span key={i} className="bg-raven-900 border border-raven-700 px-2 py-0.5 text-electric-400 font-mono text-xs rounded-none">
                  {ioc}
                </span>
              ))}
            </div>
          </>
        )}

        {/* No findings */}
        {allFindings.length === 0 && (
          <div className="border border-raven-700 bg-raven-800 p-10 text-center mt-8">
            <p className="text-raven-400 text-sm">No findings generated.</p>
            <p className="text-raven-600 text-xs font-mono mt-1">AI analysis may have been skipped or found no threats.</p>
          </div>
        )}

        {/* Download CTA */}
        <div className="flex justify-center mt-10 mb-4">
          <button
            onClick={handleDownloadPdf}
            disabled={pdfLoading}
            className="border border-electric-500 text-electric-500 text-xs px-8 py-2.5 rounded-none hover:bg-electric-900 disabled:opacity-50 transition-colors uppercase tracking-widest"
          >
            {pdfLoading ? 'Loading...' : 'Download Full PDF Report'}
          </button>
        </div>
      </main>
    </div>
  )
}
