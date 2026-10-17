// LogRaven — Attack Path & Cloud Asset Relationship Graph (DAG)
//
// Visualizes cloud assets, relationship topologies, and flags toxic multi-hop
// combinations (e.g. Internet ➔ Security Group ➔ EC2 ➔ IAM Role ➔ S3 PII Bucket).
// Includes zoom/pan canvas, interactive node inspector drawer, and quick remediation links.

import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle,
  Flame,
  Globe,
  Network,
  Server,
  Key,
  Database,
  Lock,
  ShieldAlert,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  X,
  Loader2,
  RefreshCw,
  Layers,
  ArrowRight,
} from 'lucide-react'
import type {
  AttackPathGraph,
  GraphNode,
  GraphCategory,
  GraphSeverity,
} from '../../types/audit'
import { getAuditAttackPathGraph } from '../../api/compliance'

interface AttackPathCanvasProps {
  auditId: string
  onRemediateControl?: (controlId: string) => void
}

// Category visual styling & column positioning in left-to-right DAG
const CATEGORY_CONFIG: Record<
  GraphCategory,
  {
    tier: number
    label: string
    icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>
    accent: string
    bgBadge: string
  }
> = {
  internet: {
    tier: 0,
    label: 'Public Boundary',
    icon: Globe,
    accent: '#DB8585',
    bgBadge: 'rgba(219, 133, 133, 0.15)',
  },
  network: {
    tier: 1,
    label: 'Network / SG',
    icon: Network,
    accent: '#E3B57E',
    bgBadge: 'rgba(227, 181, 126, 0.15)',
  },
  compute: {
    tier: 2,
    label: 'Compute / Host',
    icon: Server,
    accent: '#818cf8',
    bgBadge: 'rgba(129, 140, 248, 0.15)',
  },
  identity: {
    tier: 3,
    label: 'IAM & Credentials',
    icon: Key,
    accent: '#c084fc',
    bgBadge: 'rgba(192, 132, 252, 0.15)',
  },
  database: {
    tier: 4,
    label: 'Database',
    icon: Database,
    accent: '#38bdf8',
    bgBadge: 'rgba(56, 189, 248, 0.15)',
  },
  storage: {
    tier: 4,
    label: 'Object Storage',
    icon: Database,
    accent: '#34d399',
    bgBadge: 'rgba(52, 211, 153, 0.15)',
  },
  security_service: {
    tier: 5,
    label: 'Security & Audit',
    icon: Lock,
    accent: '#94a3b8',
    bgBadge: 'rgba(148, 163, 184, 0.15)',
  },
}

const SEVERITY_COLORS: Record<GraphSeverity, { border: string; text: string; bg: string }> = {
  critical: {
    border: 'border-red-500/80',
    text: 'text-red-400',
    bg: 'bg-red-500/10',
  },
  high: {
    border: 'border-amber-500/80',
    text: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  medium: {
    border: 'border-yellow-500/70',
    text: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
  },
  low: {
    border: 'border-cyan-500/60',
    text: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
  clean: {
    border: 'border-emerald-500/60',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
}

interface PositionedNode extends GraphNode {
  x: number
  y: number
  width: number
  height: number
}

export default function AttackPathCanvas({
  auditId,
  onRemediateControl,
}: AttackPathCanvasProps) {
  const [graphData, setGraphData] = useState<AttackPathGraph | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters & Selection
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedCriticalPathId, setSelectedCriticalPathId] = useState<string | null>(null)
  const [toxicOnlyFilter, setToxicOnlyFilter] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL')

  // Pan & Zoom
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 40, y: 30 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  const fetchGraph = useCallback(() => {
    setLoading(true)
    setError(null)
    getAuditAttackPathGraph(auditId)
      .then((data) => {
        setGraphData(data)
        // If there are critical toxic paths, highlight the first one by default
        if (data.critical_paths && data.critical_paths.length > 0) {
          setSelectedCriticalPathId(data.critical_paths[0].path_id)
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load attack path graph')
      })
      .finally(() => setLoading(false))
  }, [auditId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  // Filtered nodes and edges based on user filters
  const activeCriticalPath = useMemo(() => {
    if (!graphData || !selectedCriticalPathId) return null
    return graphData.critical_paths.find((p) => p.path_id === selectedCriticalPathId) ?? null
  }, [graphData, selectedCriticalPathId])

  const { visibleNodes, visibleEdges, activeAttackNodeIds } = useMemo(() => {
    if (!graphData) return { visibleNodes: [], visibleEdges: [], activeAttackNodeIds: new Set<string>() }

    const attackIds = new Set<string>()
    if (activeCriticalPath) {
      activeCriticalPath.node_ids.forEach((id) => attackIds.add(id))
    } else {
      graphData.edges
        .filter((e) => e.is_attack_path)
        .forEach((e) => {
          attackIds.add(e.source)
          attackIds.add(e.target)
        })
    }

    let nodes = graphData.nodes

    if (toxicOnlyFilter) {
      nodes = nodes.filter((n) => attackIds.has(n.id))
    }

    if (categoryFilter !== 'ALL') {
      nodes = nodes.filter((n) => n.category === categoryFilter)
    }

    const nodeIds = new Set(nodes.map((n) => n.id))
    const edges = graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    )

    return { visibleNodes: nodes, visibleEdges: edges, activeAttackNodeIds: attackIds }
  }, [graphData, activeCriticalPath, toxicOnlyFilter, categoryFilter])

  // Layout Engine: Organizes nodes into ordered category columns
  const positionedNodes = useMemo<PositionedNode[]>(() => {
    const nodeWidth = 220
    const nodeHeight = 76
    const colSpacing = 280
    const rowSpacing = 100
    const startX = 60
    const startY = 80

    // Group by category tier
    const tiers: Record<number, GraphNode[]> = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [] }

    visibleNodes.forEach((node) => {
      const cfg = CATEGORY_CONFIG[node.category] || { tier: 2 }
      const tier = cfg.tier
      if (!tiers[tier]) tiers[tier] = []
      tiers[tier].push(node)
    })

    const result: PositionedNode[] = []

    Object.entries(tiers).forEach(([tierStr, colNodes]) => {
      const tierNum = Number(tierStr)
      const x = startX + tierNum * colSpacing
      colNodes.forEach((node, index) => {
        const y = startY + index * rowSpacing
        result.push({
          ...node,
          x,
          y,
          width: nodeWidth,
          height: nodeHeight,
        })
      })
    })

    return result
  }, [visibleNodes])

  const nodeMap = useMemo(() => {
    const map = new Map<string, PositionedNode>()
    positionedNodes.forEach((n) => map.set(n.id, n))
    return map
  }, [positionedNodes])

  // Drag pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.interactive-node')) return
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const resetView = () => {
    setZoom(1)
    setPan({ x: 40, y: 30 })
  }

  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !graphData) return null
    return graphData.nodes.find((n) => n.id === selectedNodeId) ?? null
  }, [selectedNodeId, graphData])

  if (loading) {
    return (
      <div className="ops-panel p-16 flex flex-col items-center justify-center text-text-muted min-h-[460px]">
        <Loader2 className="w-8 h-8 animate-spin text-accent mb-3" />
        <span className="text-sm font-medium">Constructing Asset Relationship DAG & Toxic Path Analyzer…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ops-panel p-10 flex flex-col items-center justify-center text-center">
        <AlertTriangle className="w-8 h-8 text-threat-critical mb-3" />
        <span className="text-sm font-semibold text-text-primary mb-1">Graph Analysis Unavailable</span>
        <p className="text-xs text-text-muted mb-4 max-w-md">{error}</p>
        <button
          onClick={fetchGraph}
          className="btn-ghost inline-flex items-center gap-2 text-xs py-2 px-3 border border-white/[0.1]"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry Analysis
        </button>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="ops-panel p-12 text-center text-text-muted">
        <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm">No asset topology data detected for this audit engagement.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* ── Top Alert Banner: Toxic Combinations ─────────────────────────── */}
      {graphData.toxic_combinations_count > 0 ? (
        <div className="relative overflow-hidden rounded-xl border border-threat-critical/40 bg-gradient-to-r from-threat-critical/[0.12] via-threat-critical/[0.04] to-transparent p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start sm:items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-threat-critical/20 border border-threat-critical/40 flex items-center justify-center flex-shrink-0">
                <Flame className="w-5 h-5 text-threat-critical animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-text-primary">
                    {graphData.toxic_combinations_count} Toxic Multi-Hop Attack Path
                    {graphData.toxic_combinations_count === 1 ? '' : 's'} Identified
                  </span>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-threat-critical/20 text-threat-critical border border-threat-critical/40 font-semibold">
                    Critical Risk
                  </span>
                </div>
                <p className="text-xs text-text-secondary mt-0.5">
                  Public ingress reaches workloads with broad read/write privileges over sensitive object storage or databases.
                </p>
              </div>
            </div>

            {/* Critical Path Selector Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => {
                  setSelectedCriticalPathId(null)
                  setToxicOnlyFilter(false)
                }}
                className={`text-[11px] font-mono px-2.5 py-1 rounded-md border transition-colors ${
                  !selectedCriticalPathId && !toxicOnlyFilter
                    ? 'border-accent bg-accent/15 text-accent font-semibold'
                    : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                }`}
              >
                All Assets
              </button>
              {graphData.critical_paths.map((cp) => {
                const active = selectedCriticalPathId === cp.path_id
                return (
                  <button
                    key={cp.path_id}
                    onClick={() => {
                      setSelectedCriticalPathId(cp.path_id)
                      setToxicOnlyFilter(true)
                    }}
                    className={`inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-md border transition-colors ${
                      active
                        ? 'border-threat-critical bg-threat-critical/20 text-red-300 font-semibold shadow-[0_0_12px_rgba(239,68,68,0.3)]'
                        : 'border-threat-critical/30 bg-threat-critical/5 text-threat-critical hover:bg-threat-critical/10'
                    }`}
                  >
                    <Flame className="w-3 h-3 text-threat-critical" />
                    <span>{cp.title}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-emerald-300 font-medium">
              Zero toxic attack paths detected. Ingress boundaries and sensitive storage remain strictly isolated.
            </span>
          </div>
          <span className="text-[10px] font-mono text-emerald-400/70 uppercase">
            {graphData.nodes.length} Assets Assessed
          </span>
        </div>
      )}

      {/* ── Canvas Controls & Filter Bar ─────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 text-xs text-text-muted mr-1">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          <button
            onClick={() => setToxicOnlyFilter(!toxicOnlyFilter)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
              toxicOnlyFilter
                ? 'border-threat-critical/60 bg-threat-critical/15 text-red-300'
                : 'border-white/[0.08] bg-white/[0.02] text-text-muted hover:text-text-secondary'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-threat-critical" />
            <span>Attack Paths Only</span>
          </button>

          {(['ALL', 'internet', 'network', 'compute', 'identity', 'storage', 'database'] as const).map(
            (cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono capitalize transition-colors border ${
                  categoryFilter === cat
                    ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300 font-medium'
                    : 'border-white/[0.06] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                }`}
              >
                {cat === 'ALL' ? 'All Tiers' : cat.replace('_', ' ')}
              </button>
            )
          )}
        </div>

        {/* Zoom & Pan Tools */}
        <div className="flex items-center gap-1 bg-surface border border-white/[0.08] rounded-lg p-1">
          <button
            onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}
            className="p-1.5 rounded hover:bg-white/[0.06] text-text-muted hover:text-text-primary transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <span className="text-[11px] font-mono px-1.5 text-text-muted select-none">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
            className="p-1.5 rounded hover:bg-white/[0.06] text-text-muted hover:text-text-primary transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="w-[1px] h-4 bg-white/[0.08] mx-0.5" />
          <button
            onClick={resetView}
            className="p-1.5 rounded hover:bg-white/[0.06] text-text-muted hover:text-text-primary transition-colors"
            title="Reset View"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Interactive Graph Canvas + Inspector Panel ───────────────────── */}
      <div className="relative ops-panel overflow-hidden border border-white/[0.08] h-[580px] bg-[#0c0d12]">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(rgba(255, 255, 255, 0.15) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {/* Viewport for Pan & Drag */}
        <div
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className={`w-full h-full overflow-hidden select-none ${
            isDragging ? 'cursor-grabbing' : 'cursor-grab'
          }`}
        >
          <div
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0',
              transition: isDragging ? 'none' : 'transform 0.05s ease-out',
            }}
            className="relative w-[1800px] h-[900px]"
          >
            {/* SVG Connecting Edges Layer */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              style={{ overflow: 'visible' }}
            >
              <defs>
                {/* Arrow markers */}
                <marker
                  id="arrow-normal"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(255, 255, 255, 0.3)" />
                </marker>
                <marker
                  id="arrow-attack"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#ef4444" />
                </marker>
              </defs>

              {visibleEdges.map((edge) => {
                const source = nodeMap.get(edge.source)
                const target = nodeMap.get(edge.target)
                if (!source || !target) return null

                const sx = source.x + source.width
                const sy = source.y + source.height / 2
                const tx = target.x
                const ty = target.y + target.height / 2

                const dx = Math.abs(tx - sx) * 0.5
                const pathD = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`

                const isAttack = edge.is_attack_path
                const isHighlighted =
                  activeCriticalPath?.node_ids.includes(edge.source) &&
                  activeCriticalPath?.node_ids.includes(edge.target)

                return (
                  <g key={edge.id}>
                    <path
                      d={pathD}
                      fill="none"
                      stroke={
                        isAttack || isHighlighted
                          ? '#ef4444'
                          : 'rgba(255, 255, 255, 0.18)'
                      }
                      strokeWidth={isAttack || isHighlighted ? 2.5 : 1.5}
                      strokeDasharray={isAttack || isHighlighted ? '6 4' : undefined}
                      markerEnd={
                        isAttack || isHighlighted
                          ? 'url(#arrow-attack)'
                          : 'url(#arrow-normal)'
                      }
                      className={isAttack || isHighlighted ? 'animate-pulse' : ''}
                      style={{
                        filter:
                          isAttack || isHighlighted
                            ? 'drop-shadow(0 0 4px rgba(239, 68, 68, 0.6))'
                            : undefined,
                      }}
                    />
                    {/* Relationship label along edge */}
                    <text
                      x={(sx + tx) / 2}
                      y={(sy + ty) / 2 - 6}
                      fill={isAttack || isHighlighted ? '#fca5a5' : '#71717a'}
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="select-none"
                    >
                      {edge.relationship.replace('_', ' ')}
                    </text>
                  </g>
                )
              })}
            </svg>

            {/* HTML Nodes Layer */}
            {positionedNodes.map((node) => {
              const cfg = CATEGORY_CONFIG[node.category] || CATEGORY_CONFIG.compute
              const Icon = cfg.icon
              const isSelected = node.id === selectedNodeId
              const isInAttack = activeAttackNodeIds.has(node.id)
              const sev = SEVERITY_COLORS[node.severity] || SEVERITY_COLORS.clean
              const hasFailing = node.failing_controls && node.failing_controls.length > 0

              return (
                <div
                  key={node.id}
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedNodeId(node.id)
                  }}
                  style={{
                    position: 'absolute',
                    left: `${node.x}px`,
                    top: `${node.y}px`,
                    width: `${node.width}px`,
                    height: `${node.height}px`,
                  }}
                  className={`interactive-node cursor-pointer rounded-xl p-2.5 transition-all duration-200 select-none border backdrop-blur-sm ${
                    isSelected
                      ? 'border-indigo-400 bg-[#1e2030] shadow-[0_0_20px_rgba(99,102,241,0.4)] scale-105 z-20'
                      : isInAttack
                      ? 'border-red-500/80 bg-[#1f1519] shadow-[0_0_14px_rgba(239,68,68,0.25)] hover:border-red-400'
                      : 'border-white/[0.08] bg-[#14151d]/90 hover:border-white/[0.2] hover:bg-[#181924]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1.5 mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <div
                        className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0"
                        style={{ background: cfg.bgBadge }}
                      >
                        <Icon className="w-3 h-3" style={{ color: cfg.accent }} />
                      </div>
                      <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider truncate">
                        {cfg.label}
                      </span>
                    </div>

                    {hasFailing ? (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                        {node.failing_controls.length} fail
                      </span>
                    ) : (
                      <span className="text-[9px] font-mono text-emerald-400">clean</span>
                    )}
                  </div>

                  <div className="text-xs font-semibold text-text-primary truncate" title={node.label}>
                    {node.label}
                  </div>

                  <div className="flex items-center justify-between mt-1 text-[10px] font-mono text-text-muted">
                    <span className="truncate max-w-[120px]">{node.provider.toUpperCase()}</span>
                    <span
                      className={`uppercase text-[9px] font-bold ${sev.text}`}
                    >
                      {node.severity}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Slide-over Node Inspector Drawer ───────────────────────────── */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 380, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 380, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="absolute right-0 top-0 bottom-0 w-80 sm:w-96 bg-[#161722]/98 border-l border-white/[0.1] shadow-2xl p-5 overflow-y-auto z-30 backdrop-blur-md flex flex-col justify-between"
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-2 border-b border-white/[0.08] pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold"
                        style={{
                          background: CATEGORY_CONFIG[selectedNode.category]?.bgBadge,
                          color: CATEGORY_CONFIG[selectedNode.category]?.accent,
                        }}
                      >
                        {selectedNode.category}
                      </span>
                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold ${
                          SEVERITY_COLORS[selectedNode.severity].bg
                        } ${SEVERITY_COLORS[selectedNode.severity].text} ${
                          SEVERITY_COLORS[selectedNode.severity].border
                        }`}
                      >
                        {selectedNode.severity}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-text-primary mt-1.5 break-all">
                      {selectedNode.label}
                    </h3>
                    <p className="text-[11px] font-mono text-text-muted break-all">
                      ID: {selectedNode.id}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedNodeId(null)}
                    className="p-1 rounded hover:bg-white/[0.08] text-text-muted hover:text-text-primary transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Cloud Metadata Attributes */}
                <div>
                  <h4 className="text-[11px] font-mono uppercase tracking-wider text-text-muted mb-2">
                    Cloud Configuration & Telemetry
                  </h4>
                  <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-text-muted">Provider</span>
                      <span className="font-mono text-text-secondary uppercase">
                        {selectedNode.provider}
                      </span>
                    </div>
                    {Object.entries(selectedNode.metadata || {}).map(([key, val]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between text-xs border-t border-white/[0.04] pt-1"
                      >
                        <span className="text-text-muted capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="font-mono text-text-secondary truncate max-w-[180px]">
                          {typeof val === 'boolean'
                            ? val
                              ? 'YES'
                              : 'NO'
                            : Array.isArray(val)
                            ? val.join(', ') || 'none'
                            : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Failing Controls Breakdown */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                      Associated Failing Controls
                    </h4>
                    <span className="text-[10px] font-mono text-red-400 font-bold">
                      {selectedNode.failing_controls.length} Deficiencies
                    </span>
                  </div>

                  {selectedNode.failing_controls.length === 0 ? (
                    <div className="rounded-lg bg-emerald-500/[0.05] border border-emerald-500/20 p-3 text-xs text-emerald-300 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>This asset passes all active cloud posture policies.</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedNode.failing_controls.map((ctrlId) => (
                        <div
                          key={ctrlId}
                          className="rounded-lg bg-threat-critical/[0.08] border border-threat-critical/30 p-2.5 flex items-center justify-between gap-2"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <ShieldAlert className="w-4 h-4 text-threat-critical flex-shrink-0" />
                            <span className="font-mono text-xs font-semibold text-red-300 truncate">
                              {ctrlId}
                            </span>
                          </div>
                          {onRemediateControl && (
                            <button
                              onClick={() => onRemediateControl(ctrlId)}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded bg-accent/20 border border-accent/40 text-[11px] font-medium text-accent hover:bg-accent/30 transition-colors flex-shrink-0"
                            >
                              <span>Fix</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Close Drawer Button */}
              <div className="pt-4 border-t border-white/[0.08]">
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="w-full py-2 rounded-lg text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] text-text-secondary transition-colors"
                >
                  Close Inspector
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
