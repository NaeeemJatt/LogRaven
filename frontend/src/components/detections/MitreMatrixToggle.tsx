// LogRaven — Next-Gen SIEM Detections Toolbar & MITRE ATT&CK Matrix Controls
import { useState } from 'react'
import {
  ArrowUpDown,
  Layers,
  Sparkles,
  Grid,
  List,
  ShieldAlert,
} from 'lucide-react'

interface MitreMatrixToggleProps {
  mitreMatrixActive: boolean
  onToggleMitreMatrix: (active: boolean) => void
  groupBy: string
  onGroupByChange: (group: string) => void
  sortBy: string
  onSortByChange: (sort: string) => void
  onOpenRiskTuning?: () => void
  viewMode?: 'table' | 'split'
  onViewModeChange?: (mode: 'table' | 'split') => void
}

export default function MitreMatrixToggle({
  mitreMatrixActive,
  onToggleMitreMatrix,
  groupBy,
  onGroupByChange,
  sortBy,
  onSortByChange,
  onOpenRiskTuning,
  viewMode = 'table',
  onViewModeChange,
}: MitreMatrixToggleProps) {
  const [groupMenuOpen, setGroupMenuOpen] = useState(false)
  const [sortMenuOpen, setSortMenuOpen] = useState(false)

  const groupOptions = [
    { id: 'none', label: 'None' },
    { id: 'tactic', label: 'MITRE Tactic' },
    { id: 'technique', label: 'MITRE Technique' },
    { id: 'severity', label: 'Severity' },
    { id: 'category', label: 'Category' },
    { id: 'account', label: 'Cloud Account' },
  ]

  const sortOptions = [
    { id: 'time_desc', label: 'Time: Newest to oldest' },
    { id: 'time_asc', label: 'Time: Oldest to newest' },
    { id: 'severity_desc', label: 'Severity: Highest first' },
    { id: 'risk_desc', label: 'Risk score: Highest first' },
  ]

  const currentSortLabel = sortOptions.find((o) => o.id === sortBy)?.label ?? 'Time: Newest to oldest'
  const currentGroupLabel = groupOptions.find((o) => o.id === groupBy)?.label ?? 'None'

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-2 px-3 rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-sm select-none">
      {/* Left: MITRE ATT&CK Matrix Toggle & Risk Tuning */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        {/* MITRE ATT&CK Toggle */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-white/[0.08] bg-white/[0.02]">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs font-medium text-text-primary">MITRE ATT&CK® matrix</span>
          <button
            type="button"
            role="switch"
            aria-checked={mitreMatrixActive}
            aria-label="Toggle MITRE ATT&CK matrix view"
            onClick={() => onToggleMitreMatrix(!mitreMatrixActive)}
            className={`w-8 h-4 rounded-full transition-colors duration-150 relative p-0.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer ${
              mitreMatrixActive ? 'bg-amber-400' : 'bg-white/[0.15]'
            }`}
          >
            <span
              className={`block w-3 h-3 rounded-full bg-void transition-transform duration-150 motion-reduce:transition-none ${
                mitreMatrixActive ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Risk Score Tuning Button */}
        <button
          type="button"
          onClick={onOpenRiskTuning}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-amber-400/40 bg-white/[0.02] hover:bg-amber-400/10 text-xs font-medium text-text-secondary hover:text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
        >
          <Sparkles className="w-3 h-3 text-amber-400" />
          <span>Risk score tuning</span>
        </button>
      </div>

      {/* Right: Group By, Sort By, Layout View Mode */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
        {/* Group By Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setGroupMenuOpen(!groupMenuOpen)
              setSortMenuOpen(false)
            }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.05] text-xs font-medium text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <Layers className="w-3 h-3 text-text-muted" />
            <span>Group by: <strong className="text-text-primary font-normal">{currentGroupLabel}</strong></span>
          </button>

          {groupMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-44 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-xl p-1 z-50 space-y-0.5">
              <div className="px-2 py-1 text-[11px] font-semibold text-text-muted">Group Detections By</div>
              {groupOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    onGroupByChange(opt.id)
                    setGroupMenuOpen(false)
                  }}
                  className={`w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors duration-150 ${
                    groupBy === opt.id
                      ? 'bg-amber-400/15 text-amber-300 font-medium'
                      : 'text-text-secondary hover:bg-white/[0.05] hover:text-text-primary'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Sort By Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setSortMenuOpen(!sortMenuOpen)
              setGroupMenuOpen(false)
            }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.05] text-xs font-medium text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <ArrowUpDown className="w-3 h-3 text-text-muted" />
            <span className="truncate max-w-[180px]">{currentSortLabel}</span>
          </button>

          {sortMenuOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-52 rounded-xl border border-white/[0.12] bg-deep/95 backdrop-blur-xl p-1 z-50 space-y-0.5">
              <div className="px-2 py-1 text-[11px] font-semibold text-text-muted">Sort Detections By</div>
              {sortOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    onSortByChange(opt.id)
                    setSortMenuOpen(false)
                  }}
                  className={`w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors duration-150 ${
                    sortBy === opt.id
                      ? 'bg-amber-400/15 text-amber-300 font-medium'
                      : 'text-text-secondary hover:bg-white/[0.05] hover:text-text-primary'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* View Mode Toggle (Grid Table vs Split Inspector) */}
        {onViewModeChange && (
          <div className="hidden sm:inline-flex items-center rounded-lg border border-white/[0.08] bg-white/[0.02] p-0.5">
            <button
              type="button"
              aria-label="Table view"
              onClick={() => onViewModeChange('table')}
              className={`p-1.5 rounded-md transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer ${
                viewMode === 'table' ? 'bg-amber-400/15 text-amber-300' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              aria-label="Split preview"
              onClick={() => onViewModeChange('split')}
              className={`p-1.5 rounded-md transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer ${
                viewMode === 'split' ? 'bg-amber-400/15 text-amber-300' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
