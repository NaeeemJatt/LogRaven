// LogRaven — Enterprise Cloud Security & Compliance Rule Catalog Explorer
// Proprietary multi-cloud rule catalog covering AWS, Azure, GCP, and OCI.
// Rule detail specifications are protected to prevent piracy of detection algorithms.

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Check,
  Shield,
  Lock,
} from 'lucide-react'
import {
  listCatalogControls,
  getCatalogSummary,
  type ListCatalogControlsParams,
} from '../../api/compliance'
import type { CatalogRuleItem, CatalogSummaryResponse } from '../../types/audit'

interface RuleCatalogExplorerProps {
  onRunNativeScan?: () => void
}

const PROVIDER_CONFIG = [
  { key: 'ALL', label: 'All Clouds' },
  { key: 'AWS', label: 'AWS' },
  { key: 'AZURE', label: 'Azure' },
  { key: 'GCP', label: 'Google Cloud' },
  { key: 'OCI', label: 'Oracle Cloud' },
]

const CRITICALITY_OPTIONS = [
  { key: 'ALL', label: 'All Severities', dot: '' },
  { key: 'CRITICAL', label: 'Critical', dot: 'bg-rose-400' },
  { key: 'HIGH', label: 'High', dot: 'bg-amber-400' },
  { key: 'MEDIUM', label: 'Medium', dot: 'bg-sky-400' },
  { key: 'LOW', label: 'Low', dot: 'bg-zinc-400' },
]

function getSeverityBadgeStyle(criticality: string) {
  const crit = (criticality || '').toUpperCase()
  switch (crit) {
    case 'CRITICAL':
      return 'border-rose-500/40 bg-rose-500/15 text-rose-300 font-semibold shadow-[0_0_8px_rgba(244,63,94,0.12)]'
    case 'HIGH':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-300 font-semibold'
    case 'MEDIUM':
      return 'border-sky-500/40 bg-sky-500/15 text-sky-300 font-medium'
    case 'LOW':
    default:
      return 'border-zinc-500/30 bg-zinc-500/15 text-zinc-400 font-normal'
  }
}

export default function RuleCatalogExplorer({ onRunNativeScan }: RuleCatalogExplorerProps = {}) {
  const [summary, setSummary] = useState<CatalogSummaryResponse | null>(null)
  const [controls, setControls] = useState<CatalogRuleItem[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(true)

  // Filters
  const [selectedProvider, setSelectedProvider] = useState<string>('ALL')
  const [selectedCriticality, setSelectedCriticality] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  // Severity Dropdown State
  const [criticalityMenuOpen, setCriticalityMenuOpen] = useState(false)
  const criticalityMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (criticalityMenuRef.current && !criticalityMenuRef.current.contains(e.target as Node)) {
        setCriticalityMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Load summary once
  useEffect(() => {
    void getCatalogSummary()
      .then((data) => setSummary(data))
      .catch(() => {})
  }, [])

  // Fetch paginated controls
  useEffect(() => {
    let active = true
    setLoading(true)

    const params: ListCatalogControlsParams = {
      page: currentPage,
      limit: pageSize,
    }
    if (selectedProvider !== 'ALL') params.provider = selectedProvider
    if (selectedCriticality !== 'ALL') params.criticality = selectedCriticality
    if (searchQuery.trim()) params.query = searchQuery.trim()

    listCatalogControls(params)
      .then((res) => {
        if (!active) return
        setControls(res.items)
        setTotalCount(res.total)
        setTotalPages(res.total_pages)
      })
      .catch(() => {
        if (!active) return
        setControls([])
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedProvider, selectedCriticality, searchQuery, currentPage, pageSize])

  const handleFilterChange = (type: 'provider' | 'criticality', value: string) => {
    setCurrentPage(1)
    if (type === 'provider') setSelectedProvider(value)
    if (type === 'criticality') setSelectedCriticality(value)
  }

  return (
    <div className="space-y-4">
      {/* ── Top Bar: Cloud Provider Tabs ───────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {PROVIDER_CONFIG.map((p) => {
            const count = p.key === 'ALL'
              ? summary?.total_rules ?? 1565
              : summary?.rules_by_provider?.[p.key] ?? 0
            const active = selectedProvider === p.key
            return (
              <button
                key={p.key}
                type="button"
                onClick={() => handleFilterChange('provider', p.key)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-mono border transition-all cursor-pointer ${
                  active
                    ? 'border-white/30 bg-white/10 text-white font-semibold shadow-sm'
                    : 'border-white/[0.08] bg-void/60 text-text-muted hover:text-white hover:border-white/20'
                }`}
              >
                <span>{p.label}</span>
                {count > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/80 font-mono">
                    {count}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {onRunNativeScan && (
          <button
            type="button"
            onClick={onRunNativeScan}
            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/20 bg-white/[0.06] text-white hover:bg-white/10 text-xs font-mono transition-colors cursor-pointer"
          >
            <Shield className="w-3.5 h-3.5 text-white/70" />
            <span>Execute Native Cloud Scan</span>
          </button>
        )}
      </div>

      {/* ── Search & Severity Filter Bar ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Full-Width Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setCurrentPage(1)
            }}
            placeholder="Search 1,565 controls by title or service (e.g. S3, SSH, IAM, RDS)..."
            className="w-full h-10 pl-10 pr-9 rounded-xl border border-white/[0.08] bg-void/60 text-text-primary placeholder:text-text-muted text-xs focus:outline-none focus:border-white/30 focus:ring-1 focus:ring-white/20 transition-colors"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setCurrentPage(1)
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white text-xs p-1 cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>

        {/* Severity Filter Dropdown (Quick color cues) */}
        <div ref={criticalityMenuRef} className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setCriticalityMenuOpen(!criticalityMenuOpen)}
            className={`h-10 flex items-center gap-2 bg-void/70 hover:bg-void border rounded-xl px-3.5 text-xs font-mono transition-colors duration-150 cursor-pointer ${
              criticalityMenuOpen ? 'border-white/30 text-white' : 'border-white/[0.08] text-text-secondary hover:text-white'
            }`}
          >
            <Filter className="w-3.5 h-3.5 text-text-muted" />
            <span>
              {CRITICALITY_OPTIONS.find((o) => o.key === selectedCriticality)?.label ?? 'All Severities'}
            </span>
            <ChevronDown className={`w-3 h-3 text-text-muted transition-transform duration-150 ${criticalityMenuOpen ? 'rotate-180' : ''}`} />
          </button>

          <AnimatePresence>
            {criticalityMenuOpen && (
              <motion.div
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 2, scale: 0.98 }}
                transition={{ duration: 0.12 }}
                className="absolute right-0 top-[calc(100%+6px)] w-44 rounded-xl border border-white/[0.12] bg-[#121316] p-1.5 z-50 shadow-2xl backdrop-blur-xl"
              >
                <div className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-text-muted border-b border-white/[0.06] mb-1">
                  Severity Level
                </div>
                {CRITICALITY_OPTIONS.map((opt) => {
                  const isSelected = selectedCriticality === opt.key
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => {
                        handleFilterChange('criticality', opt.key)
                        setCriticalityMenuOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-mono text-left transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-white/10 text-white font-semibold'
                          : 'text-text-secondary hover:text-white hover:bg-white/[0.06]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {opt.dot && <span className={`w-1.5 h-1.5 rounded-full ${opt.dot}`} />}
                        <span>{opt.label}</span>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-white flex-shrink-0" />}
                    </button>
                  )
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Rule Catalog Table / List Container ─────────────────────────────────── */}
      <div className="w-full flex flex-col rounded-xl border border-white/[0.08] bg-panel-bg/40 backdrop-blur-sm overflow-hidden">
        {/* Status Bar */}
        <div className="p-3 px-4 border-b border-white/[0.06] flex items-center justify-between text-xs text-text-muted font-mono bg-void/30">
          <div className="flex items-center gap-2 text-[11px]">
            <Lock className="w-3.5 h-3.5 flex-shrink-0 text-text-muted" />
            <span>LogRaven Enterprise Compliance Benchmark · Proprietary index</span>
          </div>
          <span>Showing {controls.length} of {totalCount} rules</span>
        </div>

        {/* List of Rules (Static, readable, non-clickable to prevent IP piracy) */}
        <div className="divide-y divide-white/[0.04]">
          {loading ? (
            <div className="flex items-center justify-center p-16 text-text-muted text-xs font-mono">
              <div className="w-5 h-5 rounded-full border-2 border-white/60 border-t-transparent animate-spin mr-3" />
              Querying rule catalog...
            </div>
          ) : controls.length === 0 ? (
            <div className="p-16 text-center text-text-muted text-xs font-mono">
              No compliance rules match the selected filters.
            </div>
          ) : (
            controls.map((r) => {
              return (
                <div
                  key={r.rule_id}
                  className="p-4 sm:p-5 hover:bg-white/[0.02] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  {/* Left: Clean Rule Title */}
                  <div className="flex-1 min-w-0 pr-2">
                    <h3 className="text-sm font-medium text-white leading-snug">
                      {r.title}
                    </h3>
                  </div>

                  {/* Right side: Severity, Provider, Service, Run Time tags (compact & small) */}
                  <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap flex-shrink-0 self-start sm:self-center">
                    {/* Colored Severity Tag */}
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-wider ${getSeverityBadgeStyle(
                        r.criticality
                      )}`}
                    >
                      {r.criticality}
                    </span>

                    {/* Cloud Provider */}
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-300 bg-white/[0.05] px-2 py-0.5 rounded border border-white/10">
                      {r.provider}
                    </span>

                    {/* Target Service */}
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 bg-white/[0.03] px-2 py-0.5 rounded border border-white/[0.06]">
                      {r.service}
                    </span>

                    {/* Execution Type / Run Time */}
                    {r.execution_type && (
                      <span className="text-[10px] font-mono tracking-wider text-text-muted bg-white/[0.02] px-2 py-0.5 rounded border border-white/[0.04]">
                        {r.execution_type}
                      </span>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Table Footer with Pagination & Page Size Counter */}
        {!loading && controls.length > 0 && (
          <div className="p-3 border-t border-white/[0.08] bg-white/[0.01] flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-text-muted font-mono">
              <span>Show:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setCurrentPage(1)
                }}
                className="px-2 py-1 rounded bg-[#101216] border border-white/10 text-text-primary focus:outline-none focus:border-amber-400/50"
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span>rules per page</span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-text-muted font-mono">
                Page {currentPage} of {totalPages || 1} ({totalCount} total)
              </span>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="p-1 rounded border border-white/10 text-text-muted hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="p-1 rounded border border-white/10 text-text-muted hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
