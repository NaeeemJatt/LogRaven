// LogRaven — Level 2 Contextual Filter Ribbon (Falcon Query Strip Architecture)
import { useState, useRef, useEffect } from 'react'
import {
  ChevronDown,
  X,
  Layers,
  SlidersHorizontal,
} from 'lucide-react'

export interface ActiveFilterState {
  viewMode?: 'misconfigurations' | 'detections' | 'inventory'
  cloudProvider?: string
  severity?: string
  region?: string
  accountId?: string
}

interface FilterBarProps {
  initialView?: 'misconfigurations' | 'detections' | 'inventory'
  onFilterChange?: (filters: ActiveFilterState) => void
}

export default function FilterBar({
  initialView = 'misconfigurations',
  onFilterChange,
}: FilterBarProps) {
  const [viewMode, setViewMode] = useState<'misconfigurations' | 'detections' | 'inventory'>(initialView)
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)

  // Filter selections
  const [cloudProvider, setCloudProvider] = useState<string>('all')
  const [severity, setSeverity] = useState<string>('all')
  const [region, setRegion] = useState<string>('all')
  const [accountId, setAccountId] = useState<string>('all')

  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setOpenDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const notifyChange = (updates: Partial<ActiveFilterState>) => {
    onFilterChange?.({
      viewMode,
      cloudProvider,
      severity,
      region,
      accountId,
      ...updates,
    })
  }

  const handleClearAll = () => {
    setCloudProvider('all')
    setSeverity('all')
    setRegion('all')
    setAccountId('all')
    setOpenDropdown(null)
    onFilterChange?.({
      viewMode,
      cloudProvider: 'all',
      severity: 'all',
      region: 'all',
      accountId: 'all',
    })
  }

  const activeCount =
    (cloudProvider !== 'all' ? 1 : 0) +
    (severity !== 'all' ? 1 : 0) +
    (region !== 'all' ? 1 : 0) +
    (accountId !== 'all' ? 1 : 0)

  return (
    <div
      ref={barRef}
      className="relative z-20 h-11 border-b border-white/[0.06] bg-deep/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between gap-3 text-xs select-none overflow-x-auto custom-scrollbar"
    >
      {/* Left: View Selector & Saved Filters */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* View Mode Selector */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenDropdown(openDropdown === 'view' ? null : 'view')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-white/[0.1] bg-white/[0.04] hover:bg-white/[0.08] text-text-primary font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-amber-400" />
            <span className="capitalize">{viewMode}</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {openDropdown === 'view' && (
            <div className="absolute left-0 top-full mt-1 w-44 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1 z-50 shadow-xl space-y-0.5">
              {(['misconfigurations', 'detections', 'inventory'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    setViewMode(mode)
                    setOpenDropdown(null)
                    notifyChange({ viewMode: mode })
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs capitalize text-left transition-colors duration-150 ${
                    viewMode === mode
                      ? 'bg-amber-400/10 text-amber-300 font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>{mode}</span>
                  {viewMode === mode && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="h-4 w-[1px] bg-white/[0.1]" />

        {/* Saved Filters Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenDropdown(openDropdown === 'saved' ? null : 'saved')}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <span>Saved filters</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {openDropdown === 'saved' && (
            <div className="absolute left-0 top-full mt-1 w-52 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1.5 z-50 shadow-xl space-y-1">
              <div className="px-2 py-1 text-[11px] font-semibold text-text-muted">Preset Views</div>
              <button
                type="button"
                onClick={() => {
                  setSeverity('critical')
                  setOpenDropdown(null)
                  notifyChange({ severity: 'critical' })
                }}
                className="w-full text-left px-2 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors duration-150"
              >
                Critical Exposures Only
              </button>
              <button
                type="button"
                onClick={() => {
                  setCloudProvider('aws')
                  setOpenDropdown(null)
                  notifyChange({ cloudProvider: 'aws' })
                }}
                className="w-full text-left px-2 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-colors duration-150 whitespace-nowrap"
              >
                Production AWS Monitored Fleet
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Middle: Filter Parameter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar flex-1">
        {/* Cloud Provider Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenDropdown(openDropdown === 'provider' ? null : 'provider')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap ${
              cloudProvider !== 'all'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300 font-medium'
                : 'border-white/[0.08] bg-white/[0.02] text-text-secondary hover:text-text-primary'
            }`}
          >
            <span>Cloud provider{cloudProvider !== 'all' ? `: ${cloudProvider.toUpperCase()}` : ''}</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {openDropdown === 'provider' && (
            <div className="absolute left-0 top-full mt-1 w-40 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1 z-50 shadow-xl space-y-0.5">
              {['all', 'aws', 'azure', 'gcp'].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => {
                    setCloudProvider(p)
                    setOpenDropdown(null)
                    notifyChange({ cloudProvider: p })
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-left transition-colors duration-150 ${
                    cloudProvider === p
                      ? 'bg-amber-400/10 text-amber-300 font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>{p === 'all' ? 'All Providers' : p}</span>
                  {cloudProvider === p && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Severity Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenDropdown(openDropdown === 'severity' ? null : 'severity')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap ${
              severity !== 'all'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300 font-medium'
                : 'border-white/[0.08] bg-white/[0.02] text-text-secondary hover:text-text-primary'
            }`}
          >
            <span>Severity{severity !== 'all' ? `: ${severity}` : ''}</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {openDropdown === 'severity' && (
            <div className="absolute left-0 top-full mt-1 w-44 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1 z-50 shadow-xl space-y-0.5">
              {[
                { id: 'all', label: 'All Severities' },
                { id: 'critical', label: 'Critical' },
                { id: 'high', label: 'High' },
                { id: 'medium', label: 'Medium' },
                { id: 'info', label: 'Informational' },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setSeverity(s.id)
                    setOpenDropdown(null)
                    notifyChange({ severity: s.id })
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-left transition-colors duration-150 ${
                    severity === s.id
                      ? 'bg-amber-400/10 text-amber-300 font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>{s.label}</span>
                  {severity === s.id && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Region Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenDropdown(openDropdown === 'region' ? null : 'region')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap ${
              region !== 'all'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300 font-medium'
                : 'border-white/[0.08] bg-white/[0.02] text-text-secondary hover:text-text-primary'
            }`}
          >
            <span>Region{region !== 'all' ? `: ${region}` : ''}</span>
            <ChevronDown className="w-3 h-3 text-text-muted" />
          </button>

          {openDropdown === 'region' && (
            <div className="absolute left-0 top-full mt-1 w-44 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-2xl p-1 z-50 shadow-xl space-y-0.5">
              {[
                { id: 'all', label: 'All Regions' },
                { id: 'us-east-1', label: 'us-east-1 (N. Virginia)' },
                { id: 'us-west-2', label: 'us-west-2 (Oregon)' },
                { id: 'eu-west-1', label: 'eu-west-1 (Ireland)' },
              ].map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => {
                    setRegion(r.id)
                    setOpenDropdown(null)
                    notifyChange({ region: r.id })
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-left transition-colors duration-150 ${
                    region === r.id
                      ? 'bg-amber-400/10 text-amber-300 font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span className="truncate">{r.label}</span>
                  {region === r.id && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Add / Remove Filter Action */}
        <button
          type="button"
          onClick={() => {
            // cycle quick filter
            if (severity === 'all') setSeverity('high')
            else setSeverity('all')
          }}
          className="flex items-center gap-1 px-2 py-1 rounded-md border border-dashed border-white/[0.12] hover:border-amber-400/40 text-text-muted hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer whitespace-nowrap"
        >
          <SlidersHorizontal className="w-3 h-3" />
          <span>Add filter</span>
        </button>
      </div>

      {/* Right: Clear All & Action */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {activeCount > 0 && (
          <button
            type="button"
            onClick={handleClearAll}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-white/[0.04] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <X className="w-3 h-3" />
            <span>Clear all</span>
            <span className="ml-0.5 text-[10px] px-1 rounded bg-amber-400/20 text-amber-300 font-mono">
              {activeCount}
            </span>
          </button>
        )}
      </div>
    </div>
  )
}
