// LogRaven — High-Density Next-Gen SIEM Detections Table (CrowdStrike Falcon SIEM Standard)
import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Globe,
  Fingerprint,
  Cloud,
  Box,
  ChevronLeft,
  ChevronRight,
  Shield,
  Layers,
  ExternalLink,
  Loader2,
  Inbox,
  MoreVertical,
} from 'lucide-react'
import SeverityHexBadge from './SeverityHexBadge'
import type { FeedFinding } from '../../api/investigations'

export type DetectionTab = 'detections' | 'leads' | 'cases'

interface DetectionsTableProps {
  findings: FeedFinding[]
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  onSelectFinding: (finding: FeedFinding) => void
  activeTab: DetectionTab
  onTabChange: (tab: DetectionTab) => void
  currentPage: number
  totalPages: number
  totalCount: number
  onPageChange: (page: number) => void
  pageSize?: number
  onPageSizeChange?: (size: number) => void
  isLoading?: boolean
}

interface GroupedFindings {
  dateLabel: string
  items: FeedFinding[]
}

export default function DetectionsTable({
  findings,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onSelectFinding,
  activeTab,
  onTabChange,
  currentPage,
  totalPages,
  totalCount,
  onPageChange,
  pageSize = 25,
  onPageSizeChange,
  isLoading = false,
}: DetectionsTableProps) {
  // Format detect time as tabular HH:mm:ss
  const formatDetectTime = (dateStr?: string | null) => {
    if (!dateStr) return '12:00:00'
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return '12:00:00'
    return d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  // Format date grouping label (e.g. "Today, Nov. 5, 2026")
  const getDateLabel = (dateStr?: string | null) => {
    if (!dateStr) return 'Today, Nov. 5, 2026'
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return 'Today, Nov. 5, 2026'

    const now = new Date()
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear()

    const formatted = d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })

    return isToday ? `Today, ${formatted}` : formatted
  }

  // Group findings chronologically by date string
  const groupedFindings = useMemo<GroupedFindings[]>(() => {
    const map = new Map<string, FeedFinding[]>()
    for (const f of findings) {
      const label = getDateLabel(f.created_at)
      const existing = map.get(label)
      if (existing) {
        existing.push(f)
      } else {
        map.set(label, [f])
      }
    }
    return Array.from(map.entries()).map(([dateLabel, items]) => ({
      dateLabel,
      items,
    }))
  }, [findings])

  // Derive category icon & label
  const getCategory = (finding: FeedFinding) => {
    const type = (finding.finding_type || '').toLowerCase()
    if (type.includes('web') || type.includes('http') || type.includes('xss') || type.includes('sqli')) {
      return { icon: Globe, label: 'Web' }
    }
    if (type.includes('iam') || type.includes('user') || type.includes('cred') || type.includes('auth')) {
      return { icon: Fingerprint, label: 'Identity' }
    }
    if (type.includes('s3') || type.includes('cloud') || type.includes('bucket') || type.includes('lambda')) {
      return { icon: Cloud, label: 'Cloud' }
    }
    return { icon: Box, label: 'Infrastructure' }
  }

  const isAllSelected = findings.length > 0 && selectedIds.size === findings.length

  return (
    <div className="rounded-xl border border-white/[0.08] bg-deep/80 backdrop-blur-md overflow-hidden select-none">
      {/* Top Bar: Tabs & Status pulse */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-b border-white/[0.08] bg-white/[0.01]">
        {/* Tab strip */}
        <div role="tablist" className="flex items-center gap-1">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'detections'}
            onClick={() => onTabChange('detections')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-400/15 text-amber-300 border border-amber-400/30 flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
          >
            <span>Detections</span>
            <span className="text-[11px] font-mono opacity-80">({totalCount.toLocaleString()})</span>
          </button>
        </div>

        {/* Telemetry Status Indicator */}
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
          <span>List is up to date</span>
          <span className="text-white/20">·</span>
          <span className="tabular-nums text-text-primary font-medium">{totalCount} results</span>
        </div>
      </div>

      {/* Detections Data Grid */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/[0.08] bg-white/[0.02] text-text-muted font-medium">
              <th className="py-2.5 pl-4 pr-2 w-8">
                <input
                  type="checkbox"
                  aria-label="Select all detections"
                  checked={isAllSelected}
                  onChange={onToggleSelectAll}
                  className="rounded border-white/20 bg-void/50 text-amber-400 focus:ring-amber-400 focus:ring-offset-0 cursor-pointer"
                />
              </th>
              <th className="py-2.5 px-3 whitespace-nowrap">Severity</th>
              <th className="py-2.5 px-3 whitespace-nowrap">Detect time</th>
              <th className="py-2.5 px-3 min-w-[220px]">Name</th>
              <th className="py-2.5 px-3 whitespace-nowrap">Category</th>
              <th className="py-2.5 px-3 min-w-[240px]">Attributes</th>
              <th className="py-2.5 px-3 whitespace-nowrap">Assigned to</th>
              <th className="py-2.5 px-3 whitespace-nowrap">Status</th>
              <th className="py-2.5 px-3 whitespace-nowrap">Source</th>
              <th className="py-2.5 pr-4 pl-2 text-right w-10">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-white/[0.04]">
            {isLoading ? (
              <tr>
                <td colSpan={10} className="py-16 text-center text-text-muted">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <Loader2 className="w-6 h-6 text-amber-400 animate-spin" aria-hidden="true" />
                    <span>Streaming detections from LogRaven SIEM telemetry engine…</span>
                  </div>
                </td>
              </tr>
            ) : findings.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-16 text-center text-text-muted">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <Inbox className="w-8 h-8 text-text-muted/60" aria-hidden="true" />
                    <span className="font-medium text-text-secondary">No detections matching the current filter query</span>
                    <span className="text-[11px]">Adjust your severity, cloud provider, or search parameters above</span>
                  </div>
                </td>
              </tr>
            ) : (
              groupedFindings.map((group) => (
                <React.Fragment key={group.dateLabel}>
                  {/* Timeline Date Group Header Row */}
                  <tr className="bg-white/[0.03] border-y border-white/[0.06]">
                    <td colSpan={10} className="py-1.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" aria-hidden="true" />
                        <span className="font-medium text-text-primary text-[11px] tracking-tight">
                          {group.dateLabel}
                        </span>
                        <span className="text-[10px] text-text-muted font-mono">
                          ({group.items.length} {group.items.length === 1 ? 'event' : 'events'})
                        </span>
                      </div>
                    </td>
                  </tr>

                  {/* Individual Detection Rows */}
                  {group.items.map((finding) => {
                    const isSelected = selectedIds.has(finding.id)
                    const category = getCategory(finding)
                    const CategoryIcon = category.icon
                    const timeStr = formatDetectTime(finding.created_at)

                    return (
                      <tr
                        key={finding.id}
                        className={`hover:bg-white/[0.02] transition-colors duration-150 ${
                          isSelected ? 'bg-amber-400/[0.04]' : ''
                        }`}
                      >
                        {/* Checkbox */}
                        <td className="py-2.5 pl-4 pr-2">
                          <input
                            type="checkbox"
                            aria-label={`Select detection ${finding.title}`}
                            checked={isSelected}
                            onChange={() => onToggleSelect(finding.id)}
                            className="rounded border-white/20 bg-void/50 text-amber-400 focus:ring-amber-400 focus:ring-offset-0 cursor-pointer"
                          />
                        </td>

                        {/* Severity Hex Badge */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <SeverityHexBadge severity={finding.severity} />
                        </td>

                        {/* Detect Time */}
                        <td className="py-2.5 px-3 whitespace-nowrap font-mono text-[11px] text-text-secondary">
                          {timeStr}
                        </td>

                        {/* Name (Clickable link) */}
                        <td className="py-2.5 px-3">
                          <button
                            type="button"
                            onClick={() => onSelectFinding(finding)}
                            className="text-left font-medium text-text-primary hover:text-amber-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer line-clamp-1 max-w-[280px]"
                            title={finding.title}
                          >
                            {finding.title}
                          </button>
                        </td>

                        {/* Category */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5 text-text-secondary">
                            <CategoryIcon className="w-3.5 h-3.5 text-text-muted shrink-0" aria-hidden="true" />
                            <span>{category.label}</span>
                          </div>
                        </td>

                        {/* Attributes (Multi-Hop Metadata) */}
                        <td className="py-2.5 px-3">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {/* Correlation Rule / Investigation */}
                            {finding.investigation?.name && (
                              <Link
                                to={`/investigations/${finding.investigation.id}`}
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-[10px] text-text-secondary hover:text-amber-300 border border-white/[0.06] transition-colors duration-150"
                                title={`Linked investigation: ${finding.investigation.name}`}
                              >
                                <Layers className="w-2.5 h-2.5 text-text-muted" aria-hidden="true" />
                                <span className="truncate max-w-[110px]">{finding.investigation.name}</span>
                              </Link>
                            )}

                            {/* MITRE Tactic / Technique */}
                            {finding.mitre_technique_id && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-400/10 text-[10px] font-mono text-amber-300 border border-amber-400/25">
                                <Shield className="w-2.5 h-2.5" aria-hidden="true" />
                                <span>{finding.mitre_technique_id}</span>
                              </span>
                            )}

                            {/* Source Files / Hosts Count */}
                            {finding.source_files && finding.source_files.length > 0 && (
                              <span className="text-[10px] font-mono text-text-muted bg-white/[0.02] border border-white/[0.05] rounded px-1.5 py-0.5">
                                {finding.source_files.length} {finding.source_files.length === 1 ? 'file' : 'files'}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Assigned To */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5">
                            <div className="w-5 h-5 rounded-full bg-amber-400/15 border border-amber-400/30 text-amber-300 flex items-center justify-center text-[10px] font-semibold">
                              LR
                            </div>
                            <span className="text-text-secondary">Security Ops</span>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            Active
                          </span>
                        </td>

                        {/* Source Product */}
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <div className="flex flex-col max-w-[140px]">
                            <span className="text-text-primary font-medium text-[11px] truncate">
                              {finding.finding_type || 'Cloud Log Event'}
                            </span>
                            <span className="text-[10px] text-text-muted font-mono truncate">
                              {finding.source_files?.[0] || 'SIEM Telemetry'}
                            </span>
                          </div>
                        </td>

                        {/* Row Actions */}
                        <td className="py-2.5 pr-4 pl-2 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => onSelectFinding(finding)}
                              aria-label="Open report"
                              className="p-1 rounded text-text-muted hover:text-amber-300 hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
                            >
                              <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              aria-label="More row actions"
                              className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
                            >
                              <MoreVertical className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-t border-white/[0.08] bg-white/[0.01] text-xs text-text-muted">
        {/* Page size selector */}
        {onPageSizeChange && (
          <div className="flex items-center gap-2">
            <span>Show:</span>
            <select
              value={pageSize}
              aria-label="Rows per page"
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="rounded-lg border border-white/[0.08] bg-void/60 text-xs text-text-primary px-2 py-1 focus:border-amber-400 focus:outline-none cursor-pointer"
            >
              <option value={10}>10 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
          </div>
        )}

        {/* Page stepping */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="tabular-nums text-text-secondary">
            Page {currentPage} of {Math.max(totalPages, 1)}
          </span>

          <div className="inline-flex items-center gap-1">
            <button
              type="button"
              aria-label="Previous page"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => onPageChange(currentPage - 1)}
              className="p-1 rounded-md border border-white/[0.08] hover:border-white/[0.2] bg-white/[0.02] text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Next page"
              disabled={currentPage >= totalPages || isLoading}
              onClick={() => onPageChange(currentPage + 1)}
              className="p-1 rounded-md border border-white/[0.08] hover:border-white/[0.2] bg-white/[0.02] text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none cursor-pointer"
            >
              <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
