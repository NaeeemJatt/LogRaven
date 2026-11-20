// LogRaven — Compliance Audit Results (Control Room stage)
//
// Multi-framework master-detail navigator: framework tabs + score summary on
// top, then either a filterable control browser (list + detail with evidence &
// remediation) or a shared-signal crosswalk view.

import { useEffect, useMemo, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  Loader2, FileText, ListChecks,
  Network,
  ShieldAlert, ChevronDown,
  Download, FileSpreadsheet, Share2,
} from 'lucide-react'
import { useAuditNavStore } from '../../store/auditNavStore'
import type {
  AuditStatusResponse, ControlResult, CrosswalkResponse, FrameworkResult, ExceptionResponse,
} from '../../types/audit'
import {
  downloadAuditReport, downloadEvidencePack, getCrosswalk,
  suppressControl, unsuppressControl, listAuditExceptions,
  type SuppressControlBody,
} from '../../api/compliance'
import SuppressFindingModal from './SuppressFindingModal'
import AttackPathCanvas from './AttackPathCanvas'

export type ViewMode = 'controls' | 'attack_path' | 'crosswalk' | 'exceptions'

interface AuditResultsProps {
  results: AuditStatusResponse
  auditId: string
  initialFrameworkId?: string
  initialView?: ViewMode
  onFrameworkChange?: (frameworkId: string) => void
  onViewChange?: (view: ViewMode) => void
  onStartNew?: () => void
  /** When set, shows a Share button in the actions column. */
  onShare?: () => void
  /** Public share view: hides authenticated-only actions (downloads / new / share). */
  readOnly?: boolean
}

const STATUS_ORDER: Record<string, number> = { FAIL: 0, PARTIAL: 1, SUPPRESSED: 2, PASS: 3 }
const STATUS_COLOR: Record<string, string> = {
  PASS:       '#8FBDAD',
  FAIL:       '#DB8585',
  PARTIAL:    '#D9C27E',
  SUPPRESSED: '#A371F7',
}
type StatusFilter = 'ALL' | 'FAIL' | 'PARTIAL' | 'SUPPRESSED' | 'PASS'

export type EnrichedControlResult = ControlResult & {
  framework_id?: string
  framework_name?: string
}

export function formatFrameworkName(name?: string): string {
  if (!name) return '—'
  if (/^CIS[\s_-]*AWS/i.test(name)) return 'CIS AWS'
  return name
}

function sortedResults<T extends ControlResult>(results: T[]): T[] {
  return [...results].sort((a, b) => (STATUS_ORDER[a.status] ?? 3) - (STATUS_ORDER[b.status] ?? 3))
}

function deriveFrameworks(results: AuditStatusResponse): FrameworkResult[] {
  const normalize = (fws: FrameworkResult[]) =>
    fws.map((fw) => ({
      ...fw,
      framework_name: formatFrameworkName(fw.framework_name),
    }))

  if (results.framework_results?.length) return normalize(results.framework_results)
  // Fall back to the legacy flat shape (single framework).
  const controls = results.results ?? []
  return [{
    framework_id: results.frameworks?.[0] ?? 'soc2',
    framework_name: formatFrameworkName(results.frameworks?.[0] ?? 'SOC 2'),
    controls_assessed: controls.length,
    pass_count: results.pass_count ?? 0,
    fail_count: results.fail_count ?? 0,
    partial_count: results.partial_count ?? 0,
    suppressed_count: results.suppressed_count ?? 0,
    score_percent: results.score_percent ?? 0,
    raw_score_percent: results.raw_score_percent ?? results.score_percent ?? 0,
    results: controls,
  }]
}

function findMatchingFramework(frameworks: FrameworkResult[], targetId?: string): string | null {
  if (!targetId || !frameworks.length) return null
  const clean = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '')
  const targetClean = clean(targetId)

  // 1. Exact match
  const exact = frameworks.find((f) => f.framework_id.toLowerCase() === targetId.toLowerCase())
  if (exact) return exact.framework_id

  // 2. Normalized alphanumeric match (e.g. cis_aws == cis-aws == cisaws)
  const norm = frameworks.find((f) => clean(f.framework_id) === targetClean)
  if (norm) return norm.framework_id

  // 3. Substring match on framework_id or framework_name
  const partial = frameworks.find(
    (f) => clean(f.framework_id).includes(targetClean) ||
           targetClean.includes(clean(f.framework_id)) ||
           clean(f.framework_name).includes(targetClean)
  )
  if (partial) return partial.framework_id

  return null
}


function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

type ColumnKey = 'name' | 'status' | 'controlId' | 'assets' | 'framework'

interface ColumnDef {
  key: ColumnKey
  label: string
  defaultWeight: number
  minWeight: number
}

const COLUMN_DEFS: Record<ColumnKey, ColumnDef> = {
  name: { key: 'name', label: 'Name', defaultWeight: 44, minWeight: 20 },
  status: { key: 'status', label: 'Status', defaultWeight: 11, minWeight: 7 },
  controlId: { key: 'controlId', label: 'Control Number', defaultWeight: 14, minWeight: 9 },
  assets: { key: 'assets', label: 'Assets', defaultWeight: 9, minWeight: 6 },
  framework: { key: 'framework', label: 'Framework', defaultWeight: 22, minWeight: 14 },
}

const COLUMNS: ColumnKey[] = ['name', 'status', 'controlId', 'assets', 'framework']
const PAGE_SIZE_OPTIONS = [20, 30, 40, 50, 100] as const

export default function AuditResults({
  results,
  auditId,
  initialFrameworkId,
  initialView,
  onFrameworkChange,
  onViewChange,
  onShare,
  readOnly = false,
}: AuditResultsProps) {
  const [localResults, setLocalResults] = useState<AuditStatusResponse>(results)
  useEffect(() => { setLocalResults(results) }, [results])

  const frameworks = useMemo(() => deriveFrameworks(localResults), [localResults])
  const [activeFwId, setActiveFwId] = useState<string>('ALL')
  const [pageSize, setPageSize] = useState<number>(20)
  const [currentPage, setCurrentPage] = useState<number>(1)

  useEffect(() => {
    if (initialFrameworkId && initialFrameworkId.toLowerCase() !== 'all') {
      const matched = findMatchingFramework(frameworks, initialFrameworkId)
      if (matched) setActiveFwId(matched)
    }
  }, [initialFrameworkId, frameworks])

  const handleSelectFramework = (fwId: string) => {
    setActiveFwId(fwId)
    setSelectedCategory(null)
    setSelectedControlName(null)
    setControlSearch('')
    setExpandedId(null)
    onFrameworkChange?.(fwId === 'ALL' ? 'all' : fwId)
  }

  const [view, setView] = useState<ViewMode>(initialView || 'controls')

  useEffect(() => {
    if (initialView && initialView !== view) {
      setView(initialView)
    }
  }, [initialView])

  const handleViewChange = (newView: ViewMode) => {
    setView(newView)
    onViewChange?.(newView)
  }

  const [downloading, setDownloading] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [filter, setFilter] = useState<StatusFilter>('ALL')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedControlName, setSelectedControlName] = useState<string | null>(null)
  const [controlSearch, setControlSearch] = useState('')
  const [activeDropdown, setActiveDropdown] = useState<'framework' | 'status' | 'category' | 'name' | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedControlForModal, setSelectedControlForModal] = useState<(ControlResult & { framework_id?: string }) | null>(null)
  const filterBarRef = useRef<HTMLDivElement>(null)
  const exportMenuRef = useRef<HTMLDivElement>(null)
  const [exportOpen, setExportOpen] = useState(false)

  const [crosswalk, setCrosswalk] = useState<CrosswalkResponse | null>(null)
  const [suppressionModalOpen, setSuppressionModalOpen] = useState(false)
  const [_actionLoading, setActionLoading] = useState(false)

  // Table container ref for calculating real-time drag ratios bounded to container
  const tableContainerRef = useRef<HTMLDivElement>(null)

  // Slider column weight adjustment state (proportional fr units bounded strictly to table width)
  const [colWidths, setColWidths] = useState<Record<ColumnKey, number>>({
    name: 44,
    status: 11,
    controlId: 14,
    assets: 9,
    framework: 22,
  })
  const [activeResizing, setActiveResizing] = useState<ColumnKey | null>(null)
  const resizingRef = useRef<{
    colKey: ColumnKey
    colIndex: number
    startX: number
    startWidths: Record<ColumnKey, number>
    containerWidth: number
  } | null>(null)

  const handleResizeStart = (key: ColumnKey, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const colIndex = COLUMNS.indexOf(key)
    if (colIndex < 0 || colIndex >= COLUMNS.length - 1) return

    const containerWidth = tableContainerRef.current?.getBoundingClientRect().width || 1000
    const startWidths = { ...colWidths }

    setActiveResizing(key)
    resizingRef.current = {
      colKey: key,
      colIndex,
      startX: e.clientX,
      startWidths,
      containerWidth,
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const onMouseMove = (moveEvent: MouseEvent) => {
      if (!resizingRef.current) return
      const { colKey: activeKey, colIndex: idx, startX, startWidths: baseWidths, containerWidth: cWidth } = resizingRef.current
      const deltaPx = moveEvent.clientX - startX
      const deltaWeight = (deltaPx / cWidth) * 100

      const newWidths = { ...baseWidths }

      if (deltaWeight > 0) {
        // Dragging right: expanding left column by moving into and absorbing from columns to the right
        const rightCols = COLUMNS.slice(idx + 1)
        const maxAbsorbable = rightCols.reduce(
          (acc, c) => acc + Math.max(0, baseWidths[c] - COLUMN_DEFS[c].minWeight),
          0
        )
        const appliedDelta = Math.min(deltaWeight, maxAbsorbable)
        newWidths[activeKey] = baseWidths[activeKey] + appliedDelta

        let remaining = appliedDelta
        for (const c of rightCols) {
          if (remaining <= 0) break
          const canTake = Math.max(0, baseWidths[c] - COLUMN_DEFS[c].minWeight)
          const take = Math.min(canTake, remaining)
          newWidths[c] = Number((baseWidths[c] - take).toFixed(2))
          remaining -= take
        }
        newWidths[activeKey] = Number(newWidths[activeKey].toFixed(2))
      } else if (deltaWeight < 0) {
        // Dragging left: shrinking left column, expanding immediate right neighbor
        const maxShrink = Math.max(0, baseWidths[activeKey] - COLUMN_DEFS[activeKey].minWeight)
        const actualShrink = Math.min(-deltaWeight, maxShrink)
        newWidths[activeKey] = Number((baseWidths[activeKey] - actualShrink).toFixed(2))

        const rightCol = COLUMNS[idx + 1]
        newWidths[rightCol] = Number((baseWidths[rightCol] + actualShrink).toFixed(2))
      }

      setColWidths(newWidths)
    }

    const onMouseUp = () => {
      resizingRef.current = null
      setActiveResizing(null)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  const getGridTemplate = () => {
    return `${colWidths.name}fr ${colWidths.status}fr ${colWidths.controlId}fr ${colWidths.assets}fr ${colWidths.framework}fr`
  }

  const renderCell = (key: ColumnKey, control: EnrichedControlResult) => {
    const color = STATUS_COLOR[control.status] ?? '#93A4B5'
    const ruleName = control.control_name || control.category || `Control ${control.control_id}`
    const isFailing = control.status === 'FAIL' || control.status === 'PARTIAL'
    const isPassing = control.status === 'PASS'
    const rawFailingAssets = control.failing_resources ?? []
    const rawPassedAssets = control.passed_resources ?? []
    const failingAssetCount = rawFailingAssets.length > 0 ? rawFailingAssets.length : (isFailing ? 1 : 0)
    const passedAssetCount = rawPassedAssets.length > 0 ? rawPassedAssets.length : (isPassing ? 1 : 0)

    switch (key) {
      case 'name':
        return (
          <div className="min-w-0 pr-2">
            <span className="text-sm font-medium text-text-primary truncate block" title={ruleName}>
              {ruleName}
            </span>
          </div>
        )
      case 'status':
        return (
          <div className="flex items-center">
            <span
              className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full border inline-block font-mono"
              style={{ color, backgroundColor: color + '18', borderColor: color + '3a' }}
            >
              {control.status}
            </span>
          </div>
        )
      case 'controlId':
        return (
          <div className="font-mono text-xs text-text-muted font-medium truncate">
            {control.control_id}
          </div>
        )
      case 'assets': {
        const count = isFailing
          ? failingAssetCount
          : isPassing
          ? passedAssetCount
          : control.status === 'SUPPRESSED'
          ? 1
          : 0

        return (
          <div className="flex items-center">
            <span className="font-mono text-xs text-text-secondary tabular-nums" title={`${count} asset(s)`}>
              {count}
            </span>
          </div>
        )
      }
      case 'framework':
        return (
          <div className="truncate">
            <span
              className="text-xs font-medium text-text-secondary truncate block"
              title={formatFrameworkName(control.framework_name)}
            >
              {formatFrameworkName(control.framework_name)}
            </span>
          </div>
        )
    }
  }

  const company = localResults.company_name ?? ''

  const allControls: EnrichedControlResult[] = useMemo(() => {
    if (activeFwId !== 'ALL') {
      const fw = frameworks.find((f) => f.framework_id === activeFwId) ?? frameworks[0]
      return sortedResults(fw?.results ?? []).map((c) => ({
        ...c,
        framework_id: fw?.framework_id,
        framework_name: fw?.framework_name,
      }))
    }
    const list: EnrichedControlResult[] = []
    frameworks.forEach((fw) => {
      (fw.results ?? []).forEach((c) => {
        list.push({
          ...c,
          framework_id: fw.framework_id,
          framework_name: fw.framework_name,
        })
      })
    })
    return sortedResults(list)
  }, [frameworks, activeFwId])

  const categories = useMemo(() => {
    const set = new Set<string>()
    allControls.forEach((c) => {
      if (c.category) set.add(c.category)
    })
    return Array.from(set).sort()
  }, [allControls])

  const controlNames = useMemo(() => {
    const set = new Set<string>()
    allControls.forEach((c) => {
      const name = c.control_name || c.category || c.control_id
      if (name) set.add(name)
    })
    return Array.from(set).sort()
  }, [allControls])

  const totalExceptions = useMemo(
    () => frameworks.reduce((acc, f) => acc + (f.suppressed_count ?? 0), 0),
    [frameworks],
  )

  const visible: EnrichedControlResult[] = useMemo(() => {
    let list: EnrichedControlResult[] = allControls
    if (filter !== 'ALL') {
      list = list.filter((r) => r.status === filter)
    }
    if (selectedCategory) {
      list = list.filter((r) => r.category === selectedCategory)
    }
    if (selectedControlName) {
      list = list.filter((r) => (r.control_name || r.category || r.control_id) === selectedControlName)
    }
    return list
  }, [allControls, filter, selectedCategory, selectedControlName])

  useEffect(() => {
    setCurrentPage(1)
  }, [activeFwId, filter, selectedCategory, selectedControlName, pageSize])

  const totalControls = visible.length
  const totalPages = Math.max(1, Math.ceil(totalControls / pageSize))
  const startIndex = (currentPage - 1) * pageSize
  const endIndex = Math.min(startIndex + pageSize, totalControls)
  const paginatedControls = useMemo(() => {
    return visible.slice(startIndex, endIndex)
  }, [visible, startIndex, endIndex])

  const dropdownControlNames = useMemo(() => {
    let list = controlNames
    if (controlSearch.trim()) {
      const q = controlSearch.toLowerCase().trim()
      list = list.filter((name) => name.toLowerCase().includes(q))
    }
    return list
  }, [controlNames, controlSearch])

  // Close dropdown on outside click or escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (filterBarRef.current && !filterBarRef.current.contains(e.target as Node)) {
        setActiveDropdown(null)
      }
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setExportOpen(false)
      }
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveDropdown(null)
        setExportOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const setAuditNav = useAuditNavStore((s) => s.setAuditNav)
  const resetAuditNav = useAuditNavStore((s) => s.resetAuditNav)

  useEffect(() => {
    setAuditNav({
      isAuditActive: true,
      auditId,
      activeFrameworkId: activeFwId,
      companyName: company,
      totalExceptions,
      downloading,
      onDownloadPdf: !readOnly ? handleDownloadPdf : null,
      onDownloadCsv: !readOnly ? handleDownloadCsv : null,
      onDownloadZip: !readOnly ? handleDownloadZip : null,
      onShare: (!readOnly && onShare) ? onShare : null,
    })
    return () => {
      resetAuditNav()
    }
  }, [auditId, activeFwId, company, totalExceptions, downloading, onShare, readOnly, setAuditNav, resetAuditNav])

  useEffect(() => {
    if (view !== 'crosswalk' || crosswalk) return
    const ids = frameworks.map((f) => f.framework_id)
    getCrosswalk(ids).then(setCrosswalk).catch(() => setCrosswalk({ crosswalk: [], reuse_factor: null }))
  }, [view, crosswalk, frameworks])

  const handleSuppress = async (data: SuppressControlBody) => {
    if (!selectedControlForModal) return
    const fwId = selectedControlForModal.framework_id || (activeFwId !== 'ALL' ? activeFwId : frameworks[0]?.framework_id)
    if (!fwId) return
    const updated = await suppressControl(auditId, selectedControlForModal.control_id, fwId, data)
    setLocalResults((prev) => {
      const copy = { ...prev }
      if (copy.framework_results) {
        copy.framework_results = copy.framework_results.map((fw) => {
          if (fw.framework_id !== fwId) return fw
          const updatedControls = fw.results.map((c) => (c.control_id === selectedControlForModal.control_id ? updated : c))
          const pass = updatedControls.filter((c) => c.status === 'PASS').length
          const supp = updatedControls.filter((c) => c.status === 'SUPPRESSED').length
          const fail = updatedControls.filter((c) => c.status === 'FAIL').length
          const partial = updatedControls.filter((c) => c.status === 'PARTIAL').length
          const eff = Math.max(updatedControls.length - supp, 1)
          const scoreVal = Number(((pass / eff) * 100).toFixed(2))
          return {
            ...fw,
            results: updatedControls,
            pass_count: pass,
            suppressed_count: supp,
            fail_count: fail,
            partial_count: partial,
            score_percent: scoreVal,
          }
        })
      }
      return copy
    })
    setSuppressionModalOpen(false)
    setSelectedControlForModal(null)
  }

  const handleUnsuppress = async (controlId: string, frameworkId: string) => {
    setActionLoading(true)
    try {
      const updated = await unsuppressControl(auditId, controlId, frameworkId)
      setLocalResults((prev) => {
        const copy = { ...prev }
        if (copy.framework_results) {
          copy.framework_results = copy.framework_results.map((fw) => {
            if (fw.framework_id !== frameworkId) return fw
            const updatedControls = fw.results.map((c) => (c.control_id === controlId ? updated : c))
            const pass = updatedControls.filter((c) => c.status === 'PASS').length
            const supp = updatedControls.filter((c) => c.status === 'SUPPRESSED').length
            const fail = updatedControls.filter((c) => c.status === 'FAIL').length
            const partial = updatedControls.filter((c) => c.status === 'PARTIAL').length
            const eff = Math.max(updatedControls.length - supp, 1)
            const scoreVal = Number(((pass / eff) * 100).toFixed(2))
            return {
              ...fw,
              results: updatedControls,
              pass_count: pass,
              suppressed_count: supp,
              fail_count: fail,
              partial_count: partial,
              score_percent: scoreVal,
            }
          })
        }
        return copy
      })
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Failed to revoke exception.')
    } finally {
      setActionLoading(false)
    }
  }

  const runDownload = async (key: string, fn: () => Promise<void>) => {
    setDownloading(key)
    setDownloadError(null)
    try { await fn() }
    catch (err) { setDownloadError(err instanceof Error ? err.message : 'Download failed') }
    finally { setDownloading(null) }
  }

  const handleDownloadPdf = () => runDownload('pdf', async () => {
    const targetFw = activeFwId !== 'ALL' ? activeFwId : undefined
    const blob = await downloadAuditReport(auditId, targetFw, 'pdf')
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_${targetFw || 'all'}_evidence.pdf`)
  })
  const handleDownloadCsv = () => runDownload('csv', async () => {
    const targetFw = activeFwId !== 'ALL' ? activeFwId : undefined
    const blob = await downloadAuditReport(auditId, targetFw, 'csv')
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_${targetFw || 'all'}_results.csv`)
  })
  const handleDownloadZip = () => runDownload('zip', async () => {
    const blob = await downloadEvidencePack(auditId)
    downloadBlob(blob, `${company.replace(/\s+/g, '_')}_evidence_pack.zip`)
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {downloadError && (
        <p className="text-xs px-3 py-2.5 rounded-lg border border-threat-critical/30 bg-threat-critical/[0.06] text-threat-critical">
          {downloadError}
        </p>
      )}

      {/* ── View Content ── */}
      {view === 'crosswalk' ? (
        <CrosswalkView data={crosswalk} />
      ) : view === 'exceptions' ? (
        <ExceptionsLogView
          auditId={auditId}
          readOnly={readOnly}
          onRevoke={handleUnsuppress}
        />
      ) : view === 'attack_path' ? (
        <AttackPathCanvas
          auditId={auditId}
          onRemediateControl={(controlId) => {
            setExpandedId(controlId)
            handleViewChange('controls')
          }}
        />
      ) : (
        <div className="space-y-4">
          {/* ── Modern SOC Dropdown Filter Toolbar ── */}
          <div
            ref={filterBarRef}
            className="ops-panel p-2.5 flex items-center gap-2 flex-wrap text-xs select-none relative z-20"
          >
            {/* 1. Framework Dropdown Pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setActiveDropdown(activeDropdown === 'framework' ? null : 'framework')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  activeDropdown === 'framework'
                    ? 'border-amber-400/50 bg-amber-400/10 text-amber-300 shadow-sm ring-1 ring-amber-400/30'
                    : 'border-white/[0.1] bg-[#1a1d24] text-text-secondary hover:text-text-primary hover:bg-[#222630] hover:border-white/[0.16]'
                }`}
              >
                <span>Framework</span>
                <span className="text-white/40 font-mono">=</span>
                <span className="text-text-primary font-semibold max-w-[200px] truncate">
                  {activeFwId === 'ALL' ? 'All' : formatFrameworkName(frameworks.find((f) => f.framework_id === activeFwId)?.framework_name || activeFwId)}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'framework' ? 'rotate-180' : ''}`} />
              </button>

              {activeDropdown === 'framework' && (
                <div className="absolute left-0 top-full mt-1.5 w-72 rounded-xl border border-white/[0.12] bg-[#16181f]/95 shadow-2xl p-1.5 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                  <div className="max-h-60 overflow-y-auto space-y-0.5">
                    <button
                      type="button"
                      onClick={() => {
                        handleSelectFramework('ALL')
                        setActiveDropdown(null)
                      }}
                      className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left truncate ${
                        activeFwId === 'ALL'
                          ? 'bg-amber-400/15 text-amber-300 font-semibold'
                          : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                      }`}
                    >
                      All
                    </button>
                    {frameworks.map((fw) => {
                      const isCurrent = fw.framework_id === activeFwId
                      return (
                        <button
                          key={fw.framework_id}
                          type="button"
                          onClick={() => {
                            handleSelectFramework(fw.framework_id)
                            setActiveDropdown(null)
                          }}
                          className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left truncate ${
                            isCurrent
                              ? 'bg-amber-400/15 text-amber-300 font-semibold'
                              : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                          }`}
                        >
                          {formatFrameworkName(fw.framework_name)}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 2. Status Dropdown Pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setActiveDropdown(activeDropdown === 'status' ? null : 'status')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  filter !== 'ALL' || activeDropdown === 'status'
                    ? 'border-indigo-400/50 bg-indigo-400/10 text-indigo-300 shadow-sm ring-1 ring-indigo-400/30'
                    : 'border-white/[0.1] bg-[#1a1d24] text-text-secondary hover:text-text-primary hover:bg-[#222630] hover:border-white/[0.16]'
                }`}
              >
                <span>Status</span>
                <span className="text-white/40 font-mono">=</span>
                <span className="text-text-primary font-semibold">{filter === 'ALL' ? 'All' : filter}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'status' ? 'rotate-180' : ''}`} />
              </button>

              {activeDropdown === 'status' && (
                <div className="absolute left-0 top-full mt-1.5 w-48 rounded-xl border border-white/[0.12] bg-[#16181f]/95 shadow-2xl p-1.5 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                  <div className="space-y-0.5">
                    {[
                      { key: 'ALL', label: 'All' },
                      { key: 'FAIL', label: 'Fail' },
                      { key: 'PARTIAL', label: 'Partial' },
                      { key: 'SUPPRESSED', label: 'Exceptions' },
                      { key: 'PASS', label: 'Pass' },
                    ].map((opt) => {
                      const isCurrent = filter === opt.key
                      return (
                        <button
                          key={opt.key}
                          type="button"
                          onClick={() => {
                            setFilter(opt.key as StatusFilter)
                            setActiveDropdown(null)
                          }}
                          className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                            isCurrent
                              ? 'bg-indigo-400/15 text-indigo-300 font-semibold'
                              : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                          }`}
                        >
                          {opt.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 3. Category Dropdown Pill */}
            {categories.length > 0 && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setActiveDropdown(activeDropdown === 'category' ? null : 'category')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                    selectedCategory || activeDropdown === 'category'
                      ? 'border-sky-400/50 bg-sky-400/10 text-sky-300 shadow-sm ring-1 ring-sky-400/30'
                      : 'border-white/[0.1] bg-[#1a1d24] text-text-secondary hover:text-text-primary hover:bg-[#222630] hover:border-white/[0.16]'
                  }`}
                >
                  <span>Category</span>
                  <span className="text-white/40 font-mono">=</span>
                  <span className="text-text-primary font-semibold max-w-[140px] truncate">{selectedCategory || 'All'}</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'category' ? 'rotate-180' : ''}`} />
                </button>

                {activeDropdown === 'category' && (
                  <div className="absolute left-0 top-full mt-1.5 w-64 rounded-xl border border-white/[0.12] bg-[#16181f]/95 shadow-2xl p-1.5 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                    <div className="max-h-60 overflow-y-auto space-y-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedCategory(null)
                          setActiveDropdown(null)
                        }}
                        className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                          !selectedCategory
                            ? 'bg-sky-400/15 text-sky-300 font-semibold'
                            : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                        }`}
                      >
                        All
                      </button>
                      {categories.map((cat) => {
                        const isCurrent = selectedCategory === cat
                        return (
                          <button
                            key={cat}
                            type="button"
                            onClick={() => {
                              setSelectedCategory(cat)
                              setActiveDropdown(null)
                            }}
                            className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left truncate ${
                              isCurrent
                                ? 'bg-sky-400/15 text-sky-300 font-semibold'
                                : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                            }`}
                          >
                            {cat}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 4. Name Dropdown Pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setActiveDropdown(activeDropdown === 'name' ? null : 'name')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer max-w-[320px] sm:max-w-[420px] ${
                  selectedControlName || activeDropdown === 'name'
                    ? 'border-amber-400/50 bg-amber-400/10 text-amber-300 shadow-sm ring-1 ring-amber-400/30'
                    : 'border-white/[0.1] bg-[#1a1d24] text-text-secondary hover:text-text-primary hover:bg-[#222630] hover:border-white/[0.16]'
                }`}
              >
                <span className="flex-shrink-0">Name</span>
                <span className="text-white/40 font-mono flex-shrink-0">=</span>
                <span className="truncate text-text-primary font-semibold">
                  {selectedControlName || 'All'}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-text-muted flex-shrink-0 transition-transform duration-150 ${activeDropdown === 'name' ? 'rotate-180' : ''}`} />
              </button>

              {activeDropdown === 'name' && (
                <div className="absolute left-0 top-full mt-1.5 w-80 sm:w-96 rounded-xl border border-white/[0.12] bg-[#16181f]/95 shadow-2xl p-2 z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                  <div className="relative mb-2">
                    <input
                      type="text"
                      value={controlSearch}
                      onChange={(e) => setControlSearch(e.target.value)}
                      placeholder="Filter by control name..."
                      className="w-full h-8 px-3 rounded-lg border border-white/[0.1] bg-[#101116] text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-amber-400/50"
                      autoFocus
                    />
                  </div>
                  <div className="max-h-64 overflow-y-auto space-y-0.5">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedControlName(null)
                        setActiveDropdown(null)
                      }}
                      className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                        !selectedControlName
                          ? 'bg-amber-400/15 text-amber-300 font-semibold'
                          : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                      }`}
                    >
                      All
                    </button>
                    {dropdownControlNames.length === 0 ? (
                      <div className="p-3 text-center text-xs text-text-muted">No controls match</div>
                    ) : (
                      dropdownControlNames.map((name) => {
                        const isCurrent = name === selectedControlName
                        return (
                          <button
                            key={name}
                            type="button"
                            onClick={() => {
                              setSelectedControlName(name)
                              setActiveDropdown(null)
                            }}
                            className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                              isCurrent
                                ? 'bg-amber-400/15 text-amber-300 font-semibold'
                                : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.06]'
                            }`}
                          >
                            <div className="line-clamp-2 leading-relaxed">{name}</div>
                          </button>
                        )
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 5. Reset Filters Button */}
            {(activeFwId !== 'ALL' || filter !== 'ALL' || selectedCategory !== null || selectedControlName !== null) && (
              <button
                type="button"
                onClick={() => {
                  setActiveFwId('ALL')
                  setFilter('ALL')
                  setSelectedCategory(null)
                  setSelectedControlName(null)
                  onFrameworkChange?.('all')
                }}
                className="inline-flex items-center px-2.5 py-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 text-xs font-medium cursor-pointer transition-colors"
                title="Reset all filters"
              >
                <span>Reset</span>
              </button>
            )}

            {/* 6. Controls Count & Export Button at the end of the second menu */}
            <div className="flex items-center gap-3 ml-auto flex-shrink-0">
              <span className="font-mono text-[11px] text-text-muted font-normal tabular-nums px-1">
                {visible.length} controls
              </span>

              {/* Export Dropdown at the end of the second menu */}
              <div className="relative" ref={exportMenuRef}>
                <button
                  type="button"
                  onClick={() => setExportOpen((prev) => !prev)}
                  disabled={downloading !== null}
                  className="btn-sovereign h-7 py-1 px-3 rounded-lg font-semibold text-xs flex items-center justify-between gap-1.5 cursor-pointer shadow-sm transition-all"
                  title="Export or share compliance assessment"
                >
                  <div className="flex items-center gap-1.5">
                    {downloading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5" />
                    )}
                    <span>{downloading ? `${downloading.toUpperCase()}…` : 'Export'}</span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${exportOpen ? 'rotate-180' : ''}`} />
                </button>

                {exportOpen && (
                  <div className="absolute right-0 top-full mt-1.5 w-56 rounded-xl border border-white/[0.12] bg-[#121316]/95 backdrop-blur-xl shadow-2xl p-1.5 z-50 space-y-1 animate-in fade-in zoom-in-95 duration-100">
                    <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-text-muted border-b border-white/[0.06]">
                      Export Formats
                    </div>
                    <button
                      type="button"
                      onClick={() => { setExportOpen(false); handleDownloadPdf(); }}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.06] rounded-lg transition-colors text-left group cursor-pointer"
                    >
                      <div className="w-6 h-6 rounded flex items-center justify-center bg-amber-400/10 text-amber-300 group-hover:bg-amber-400/20 flex-shrink-0">
                        <FileText className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-text-primary leading-tight">PDF Report</span>
                        <span className="text-[10px] text-text-muted leading-tight">Audit findings & evidence</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => { setExportOpen(false); handleDownloadCsv(); }}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.06] rounded-lg transition-colors text-left group cursor-pointer"
                    >
                      <div className="w-6 h-6 rounded flex items-center justify-center bg-emerald-400/10 text-emerald-300 group-hover:bg-emerald-400/20 flex-shrink-0">
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-text-primary leading-tight">CSV Spreadsheet</span>
                        <span className="text-[10px] text-text-muted leading-tight">Control table & gap status</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => { setExportOpen(false); handleDownloadZip(); }}
                      className="w-full flex items-center gap-2.5 px-2.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.06] rounded-lg transition-colors text-left group cursor-pointer"
                    >
                      <div className="w-6 h-6 rounded flex items-center justify-center bg-indigo-400/10 text-indigo-300 group-hover:bg-indigo-400/20 flex-shrink-0">
                        <Download className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-text-primary leading-tight">Evidence ZIP</span>
                        <span className="text-[10px] text-text-muted leading-tight">Complete raw telemetry pack</span>
                      </div>
                    </button>
                    {onShare && (
                      <>
                        <div className="my-1 border-t border-white/[0.08]" />
                        <button
                          type="button"
                          onClick={() => { setExportOpen(false); onShare(); }}
                          className="w-full flex items-center gap-2.5 px-2.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/[0.06] rounded-lg transition-colors text-left group cursor-pointer"
                        >
                          <div className="w-6 h-6 rounded flex items-center justify-center bg-sky-400/10 text-sky-300 group-hover:bg-sky-400/20 flex-shrink-0">
                            <Share2 className="w-3.5 h-3.5" />
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="font-semibold text-text-primary leading-tight">Share Audit</span>
                            <span className="text-[10px] text-text-muted leading-tight">Generate secure link</span>
                          </div>
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Controls List: All Controls according to applied filters (Shows only Rule Name) ── */}
          <div className="ops-panel overflow-hidden min-h-[480px]">
            {visible.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-center p-12 space-y-3">
                <ListChecks className="w-10 h-10 text-text-ghost" strokeWidth={1.25} />
                <div className="text-sm font-semibold text-text-primary">No controls match the applied filters.</div>
                <p className="text-xs text-text-muted max-w-sm">
                  Try selecting "All" from the filters above to view the full inventory.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setActiveFwId('ALL')
                    setFilter('ALL')
                    setSelectedCategory(null)
                    setSelectedControlName(null)
                    onFrameworkChange?.('all')
                  }}
                  className="btn-sovereign px-3.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer"
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <>
                <div ref={tableContainerRef} className="w-full overflow-x-auto">
                {/* ── Table Columns Header: Slider adjustable widths ── */}
                <div className="border-b border-white/[0.08] bg-white/[0.02] w-full min-w-[650px]">
                  <div
                    className="px-5 py-2.5 items-center text-[10px] font-mono uppercase tracking-wider text-text-muted select-none"
                    style={{ display: 'grid', gridTemplateColumns: getGridTemplate(), gap: '12px' }}
                  >
                    {COLUMNS.map((colKey, idx) => {
                      const def = COLUMN_DEFS[colKey]
                      const isLast = idx === COLUMNS.length - 1
                      return (
                        <div
                          key={colKey}
                          className={`relative flex items-center justify-between py-1 font-semibold text-text-secondary select-none ${
                            isLast ? 'pr-1' : 'pr-3'
                          }`}
                        >
                          <span className="truncate">{def.label}</span>

                          {/* Slider handle on the right edge */}
                          {!isLast && (
                            <div
                              onMouseDown={(e) => handleResizeStart(colKey, e)}
                              onDoubleClick={() => setColWidths({
                                name: 44,
                                status: 11,
                                controlId: 14,
                                assets: 9,
                                framework: 22,
                              })}
                              className="absolute right-0 top-0 bottom-0 w-3 -mr-1.5 cursor-col-resize z-20 flex items-center justify-center group"
                              title="Slide left or right to adjust column width within table (Double-click to reset)"
                            >
                              <div
                                className={`w-[2px] rounded transition-all ${
                                  activeResizing === colKey
                                    ? 'bg-amber-400 h-full'
                                    : 'bg-white/20 group-hover:bg-amber-400 h-3.5 group-hover:h-full'
                                }`}
                              />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div className="divide-y divide-white/[0.06] w-full min-w-[650px]">
                  {paginatedControls.map((control) => {
                    const rowKey = `${control.framework_id || 'fw'}_${control.control_id}`
                    const isExpanded = expandedId === rowKey
                    const isFailing = control.status === 'FAIL' || control.status === 'PARTIAL'
                    const isPassing = control.status === 'PASS'
                    const rawFailingAssets = control.failing_resources ?? []
                    const rawPassedAssets = control.passed_resources ?? []

                    return (
                      <div
                        key={rowKey}
                        className="hover:bg-white/[0.02] transition-colors"
                      >
                        {/* Control Row: Dynamic columns based on colWidths */}
                        <div
                          onClick={() => setExpandedId(isExpanded ? null : rowKey)}
                          className="px-5 py-3.5 items-center cursor-pointer select-none hover:bg-white/[0.02] transition-colors"
                          style={{ display: 'grid', gridTemplateColumns: getGridTemplate(), gap: '12px' }}
                        >
                          {COLUMNS.map((colKey) => (
                            <div key={colKey} className="min-w-0">
                              {renderCell(colKey, control)}
                            </div>
                          ))}
                        </div>

                        {/* Optional Expandable drawer: only shown when user explicitly clicks a row */}
                        {isExpanded && (
                          <div className="px-5 pb-5 pt-3 border-t border-white/[0.04] bg-void/40 space-y-4 text-xs animate-in fade-in duration-150">
                            <div className="flex items-center justify-between gap-4 pt-1">
                              <div className="text-xs text-text-muted">
                                <span className="font-semibold text-text-primary">{control.control_id}</span> — {control.category || formatFrameworkName(control.framework_name)}
                              </div>
                              {!readOnly && control.status !== 'PASS' && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedControlForModal(control)
                                    setSuppressionModalOpen(true)
                                  }}
                                  className="px-2.5 py-1 rounded-md border border-purple-500/30 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 text-xs font-medium cursor-pointer transition-colors"
                                >
                                  Suppress / Add Exception
                                </button>
                              )}
                            </div>

                            {/* Failing cloud assets breakdown (if control failed) */}
                            {rawFailingAssets.length > 0 ? (
                              <div className="space-y-1.5 p-3 rounded-lg border border-rose-500/20 bg-rose-500/[0.04]">
                                <span className="font-semibold text-rose-300 block mb-1">
                                  Failing Cloud Assets ({rawFailingAssets.length}):
                                </span>
                                <div className="space-y-1">
                                  {rawFailingAssets.map((asset, i) => (
                                    <div
                                      key={i}
                                      className="px-2.5 py-1 rounded bg-[#101217] border border-rose-500/20 font-mono text-[11px] text-rose-200 truncate select-all"
                                    >
                                      {asset}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : isFailing ? (
                              <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/[0.04] text-rose-200">
                                <span className="font-semibold text-rose-300 block mb-1">Tenant / Cloud Account Policy Failure</span>
                                This control failed at the cloud provider boundary (e.g. root account MFA, IAM password complexity, or organization-level audit logging). All workloads under this cloud account are impacted until the account baseline is remediated.
                              </div>
                            ) : null}

                            {/* Passing cloud assets breakdown (if control passed) */}
                            {rawPassedAssets.length > 0 ? (
                              <div className="space-y-1.5 p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04]">
                                <span className="font-semibold text-emerald-300 block mb-1">
                                  Passing Cloud Assets ({rawPassedAssets.length}):
                                </span>
                                <div className="space-y-1">
                                  {rawPassedAssets.map((asset, i) => (
                                    <div
                                      key={i}
                                      className="px-2.5 py-1 rounded bg-[#101217] border border-emerald-500/20 font-mono text-[11px] text-emerald-200 truncate select-all"
                                    >
                                      {asset}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : isPassing ? (
                              <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] text-emerald-200">
                                <span className="font-semibold text-emerald-300 block mb-1">Tenant / Cloud Baseline Compliant</span>
                                This control is verified operating effectively against live cloud infrastructure telemetry.
                              </div>
                            ) : null}

                            {control.ai_description && (
                              <div className="p-3 rounded-lg border border-white/[0.06] bg-[#12141a] text-text-secondary leading-relaxed">
                                {control.ai_description}
                              </div>
                            )}

                            {control.remediation && (
                              <div className="p-3 rounded-lg border border-amber-400/20 bg-amber-400/[0.03] text-text-secondary leading-relaxed">
                                <span className="font-semibold text-amber-300 block mb-1">Remediation Guidance:</span>
                                {control.remediation}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* ── Table Footer Pagination & Controls-per-page Counter ── */}
              <div className="border-t border-white/[0.08] bg-white/[0.02] px-5 py-3 flex items-center justify-between gap-4 flex-wrap text-xs select-none">
                {/* Left: Showing range */}
                <div className="text-text-muted font-mono text-[11px] tabular-nums">
                  Showing <span className="font-semibold text-text-primary">{totalControls === 0 ? 0 : startIndex + 1}</span>–<span className="font-semibold text-text-primary">{endIndex}</span> of <span className="font-semibold text-text-primary">{totalControls}</span> controls
                </div>

                {/* Center / Right: Counter and Page Navigation */}
                <div className="flex items-center gap-4 ml-auto">
                  {/* Rows per page selector counter */}
                  <div className="flex items-center gap-2">
                    <span className="text-text-secondary text-[11px]">Show:</span>
                    <div className="inline-flex items-center rounded-lg border border-white/[0.1] bg-[#16181f] p-0.5">
                      {PAGE_SIZE_OPTIONS.map((size) => (
                        <button
                          key={size}
                          type="button"
                          onClick={() => {
                            setPageSize(size)
                            setCurrentPage(1)
                          }}
                          className={`px-2.5 py-1 rounded-md text-[11px] font-mono transition-colors cursor-pointer ${
                            pageSize === size
                              ? 'bg-amber-400/20 text-amber-300 font-semibold shadow-sm'
                              : 'text-text-muted hover:text-text-primary hover:bg-white/[0.04]'
                          }`}
                        >
                          {size}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Pagination Previous / Next buttons */}
                  {totalPages > 1 && (
                    <div className="flex items-center gap-1.5 border-l border-white/[0.08] pl-4">
                      <button
                        type="button"
                        disabled={currentPage <= 1}
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        className="px-2.5 py-1 rounded-md border border-white/[0.1] bg-[#16181f] text-text-secondary hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer text-[11px]"
                      >
                        Prev
                      </button>
                      <span className="text-[11px] font-mono text-text-muted px-1.5 tabular-nums">
                        {currentPage} / {totalPages}
                      </span>
                      <button
                        type="button"
                        disabled={currentPage >= totalPages}
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        className="px-2.5 py-1 rounded-md border border-white/[0.1] bg-[#16181f] text-text-secondary hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer text-[11px]"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
          </div>
        </div>
      )}

      {selectedControlForModal && (
        <SuppressFindingModal
          isOpen={suppressionModalOpen}
          onClose={() => {
            setSuppressionModalOpen(false)
            setSelectedControlForModal(null)
          }}
          controlId={selectedControlForModal.control_id}
          controlName={selectedControlForModal.control_name}
          frameworkId={selectedControlForModal.framework_id || (activeFwId !== 'ALL' ? activeFwId : frameworks[0]?.framework_id)}
          onConfirm={handleSuppress}
        />
      )}

      <p className="flex items-center justify-center gap-1.5 text-xs text-center text-text-muted">
        <FileText className="w-3.5 h-3.5 flex-shrink-0" />
        Deterministic compliance audit report. Review by a qualified security professional before submission.
      </p>
    </motion.div>
  )
}

// ── Exceptions log view: business logic exceptions for auditors ───────────
function ExceptionsLogView({
  auditId,
  readOnly,
  onRevoke,
}: {
  auditId: string
  readOnly: boolean
  onRevoke: (controlId: string, frameworkId: string) => Promise<void>
}) {
  const [exceptions, setExceptions] = useState<ExceptionResponse[]>([])
  const [loading, setLoading] = useState(true)

  const fetchExceptions = () => {
    setLoading(true)
    listAuditExceptions(auditId)
      .then(setExceptions)
      .catch(() => setExceptions([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchExceptions()
  }, [auditId])

  if (loading) {
    return (
      <div className="ops-panel p-10 flex items-center justify-center text-sm text-text-muted">
        <Loader2 className="w-4 h-4 animate-spin mr-2 text-purple-400" /> Loading exceptions log…
      </div>
    )
  }

  return (
    <div className="ops-panel overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-semibold text-text-primary">
            Auditor Log: Business Exceptions & Compensating Controls
          </span>
        </div>
        <span className="font-mono text-[11px] text-purple-300">
          {exceptions.length} Active Exception{exceptions.length === 1 ? '' : 's'}
        </span>
      </div>

      {exceptions.length === 0 ? (
        <div className="px-5 py-12 text-center text-sm text-text-muted">
          No business logic exceptions recorded for this engagement. All controls are evaluated strictly against raw cloud telemetry.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] bg-white/[0.02] text-text-muted font-mono text-[10px] uppercase">
                <th className="px-4 py-3">Control / Framework</th>
                <th className="px-4 py-3">Business Justification</th>
                <th className="px-4 py-3">Compensating Controls</th>
                <th className="px-4 py-3">Risk / Review Date</th>
                {!readOnly && <th className="px-4 py-3 text-right">Action</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {exceptions.map((exc) => (
                <tr key={exc.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 align-top font-mono">
                    <span className="text-purple-300 font-semibold">{exc.control_id}</span>
                    <span className="block text-[10px] text-text-muted uppercase mt-0.5">{exc.framework}</span>
                  </td>
                  <td className="px-4 py-3 align-top text-text-primary max-w-xs leading-relaxed">
                    {exc.business_justification}
                  </td>
                  <td className="px-4 py-3 align-top text-text-secondary max-w-xs leading-relaxed">
                    {exc.compensating_controls || <span className="text-text-muted italic">None documented</span>}
                  </td>
                  <td className="px-4 py-3 align-top text-text-muted font-mono text-[11px] whitespace-nowrap">
                    <span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 uppercase mb-1">
                      {exc.risk_level}
                    </span>
                    <span className="block text-[10px] text-text-muted">
                      Review: {exc.expires_at ? exc.expires_at.split('T')[0] : 'Perpetual'}
                    </span>
                  </td>
                  {!readOnly && (
                    <td className="px-4 py-3 align-top text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={async () => {
                          await onRevoke(exc.control_id, exc.framework)
                          fetchExceptions()
                        }}
                        className="px-2.5 py-1 rounded text-[11px] text-purple-300 hover:text-purple-100 border border-purple-500/30 hover:border-purple-500/60 transition-colors"
                      >
                        Revoke
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Crosswalk view: one shared signal → controls across frameworks ─────────
function CrosswalkView({ data }: { data: CrosswalkResponse | null }) {
  if (!data) {
    return (
      <div className="ops-panel p-10 flex items-center justify-center text-sm text-text-muted">
        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Building crosswalk…
      </div>
    )
  }
  return (
    <div className="ops-panel overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/[0.07] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-indigo-300" />
          <span className="text-sm font-semibold text-text-primary">Evidence crosswalk</span>
        </div>
        {data.reuse_factor != null && (
          <span className="font-mono text-[11px] text-text-muted">
            reuse factor <span className="text-indigo-300 font-semibold">{data.reuse_factor}×</span>
          </span>
        )}
      </div>
      <div className="max-h-[calc(100vh-24rem)] min-h-[400px] overflow-y-auto divide-y divide-white/[0.05]">
        {data.crosswalk.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-text-muted">No shared signals for these frameworks.</div>
        ) : (
          data.crosswalk.map((row) => (
            <div key={row.signal} className="px-5 py-3.5">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs font-semibold text-indigo-300">{row.signal}</span>
                <span className="text-[10px] font-mono text-text-muted">
                  {row.framework_count} frameworks · {row.control_count} controls
                </span>
              </div>
              <p className="text-[11px] text-text-muted mt-0.5">{row.description}</p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {row.controls.map((c) => (
                  <span key={`${c.framework_id}-${c.control_id}`}
                    className="inline-flex items-center gap-1 rounded-md border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 text-[10px] font-mono text-text-muted">
                    <span className="text-indigo-400/70">{c.framework_id}</span> {c.control_id}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

