// LogRaven — Dedicated Framework Details & Controls Explorer Page
import { useState, useMemo } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Play,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Shield,
  Layers,
  Terminal,
  Cpu,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Info,
  BookOpen,
} from 'lucide-react'
import { getFrameworkDetail } from '../data/frameworkControlsData'

export default function FrameworkDetailPage() {
  const { frameworkId } = useParams<{ frameworkId: string }>()
  const navigate = useNavigate()

  const framework = useMemo(() => {
    return getFrameworkDetail(frameworkId || 'soc2')
  }, [frameworkId])

  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'automated' | 'manual'>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [expandedControls, setExpandedControls] = useState<Record<string, boolean>>({
    // Expand first 2 by default
    [framework.controls[0]?.control_id]: true,
    [framework.controls[1]?.control_id]: true,
  })
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [activeRemediationTab, setActiveRemediationTab] = useState<Record<string, 'console' | 'cli' | 'terraform' | 'verify'>>({})

  // Category list
  const categories = useMemo(() => {
    const set = new Set<string>()
    framework.controls.forEach((c) => set.add(c.category))
    return ['all', ...Array.from(set)]
  }, [framework])

  // Filtered controls
  const filteredControls = useMemo(() => {
    return framework.controls.filter((c) => {
      // Type filter
      if (filterType === 'automated' && !c.automatable) return false
      if (filterType === 'manual' && c.automatable) return false

      // Category filter
      if (selectedCategory !== 'all' && c.category !== selectedCategory) return false

      // Search
      const query = search.toLowerCase().trim()
      if (!query) return true
      return (
        c.control_id.toLowerCase().includes(query) ||
        c.name.toLowerCase().includes(query) ||
        c.category.toLowerCase().includes(query) ||
        c.description.toLowerCase().includes(query)
      )
    })
  }, [framework, filterType, selectedCategory, search])

  const toggleControl = (id: string) => {
    setExpandedControls((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const expandAll = () => {
    const next: Record<string, boolean> = {}
    framework.controls.forEach((c) => {
      next[c.control_id] = true
    })
    setExpandedControls(next)
  }

  const collapseAll = () => {
    setExpandedControls({})
  }

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const handleLaunchScan = () => {
    navigate(`/compliance?tab=audit&fw=${framework.id}`)
  }

  return (
    <div className="min-h-screen bg-void text-text-primary p-4 sm:p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Breadcrumb & Back Action */}
      <div className="flex items-center justify-between gap-4">
        <Link
          to="/compliance/frameworks"
          className="inline-flex items-center gap-2 text-xs font-mono text-text-muted hover:text-indigo-300 transition-colors py-1.5 px-3 rounded-lg border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05]"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Frameworks Catalog</span>
        </Link>

        <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
          <span>Catalog</span>
          <span>/</span>
          <span className="text-text-secondary">{framework.code}</span>
        </div>
      </div>

      {/* Hero Header */}
      <div className="rounded-3xl border border-white/[0.08] bg-gradient-to-br from-[#0F172A] to-[#0A0D18] p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div
          className="pointer-events-none absolute -right-20 -top-20 w-96 h-96 rounded-full opacity-25"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.4) 0%, transparent 70%)' }}
        />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                {framework.complianceBadge}
              </span>
              <span className="px-2.5 py-1 rounded-md text-[10px] font-mono text-text-muted border border-white/[0.08] bg-white/[0.02]">
                {framework.version}
              </span>
              <span className="px-2.5 py-1 rounded-md text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/25">
                {framework.automatedRate}
              </span>
            </div>

            <h1 className="font-display font-extrabold text-2xl sm:text-4xl text-text-primary tracking-tight">
              {framework.name}
            </h1>

            <div className="font-mono text-xs text-text-muted">
              Governing Body: <strong className="text-text-secondary">{framework.governingBody}</strong>
            </div>

            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
              {framework.description}
            </p>

            <div className="p-3 rounded-xl bg-black/30 border border-white/[0.05] flex items-start gap-2.5 text-xs text-text-muted">
              <Info className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-text-secondary">Auditor Verification Standard: </strong>
                {framework.auditorExpectations}
              </div>
            </div>
          </div>

          {/* Quick Action Button */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 flex-shrink-0 self-start">
            <button
              onClick={handleLaunchScan}
              className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm shadow-[0_0_25px_rgba(99,102,241,0.35)] transition-all"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Launch {framework.code} Scan</span>
            </button>
            <div className="text-[11px] font-mono text-text-muted text-center">
              Evaluates AWS · Azure · GCP signals
            </div>
          </div>
        </div>

        {/* Bento Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-8 pt-6 border-t border-white/[0.08]">
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
            <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Total Controls</div>
            <div className="font-display font-bold text-2xl sm:text-3xl text-text-primary mt-1">
              {framework.totalControls}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">Full Standard Scope</div>
          </div>

          <div className="p-4 rounded-2xl bg-emerald-500/[0.04] border border-emerald-500/20">
            <div className="font-mono text-[10px] uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Automated Telemetry
            </div>
            <div className="font-display font-bold text-2xl sm:text-3xl text-emerald-300 mt-1">
              {framework.automatedCount}
            </div>
            <div className="text-[10px] text-emerald-400/80 mt-0.5">Continuous Cloud Scanning</div>
          </div>

          <div className="p-4 rounded-2xl bg-amber-500/[0.04] border border-amber-500/20">
            <div className="font-mono text-[10px] uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Manual &amp; Policy
            </div>
            <div className="font-display font-bold text-2xl sm:text-3xl text-amber-300 mt-1">
              {framework.manualCount}
            </div>
            <div className="text-[10px] text-amber-400/80 mt-0.5">Policy &amp; HR Evidence</div>
          </div>

          <div className="p-4 rounded-2xl bg-indigo-500/[0.04] border border-indigo-500/20">
            <div className="font-mono text-[10px] uppercase tracking-wider text-indigo-300">Automation Rate</div>
            <div className="font-display font-bold text-2xl sm:text-3xl text-indigo-300 mt-1">
              {framework.automatedRate.split(' ')[0]}
            </div>
            <div className="text-[10px] text-indigo-400/80 mt-0.5">Cloud Signal Coverage</div>
          </div>
        </div>
      </div>

      {/* Controls Explorer Section */}
      <div className="space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="font-display font-bold text-xl text-text-primary flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              <span>Framework Controls &amp; Implementation Guides</span>
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Explore every control in this standard, including automated cloud telemetry checks and step-by-step guidance for manual governance requirements.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={expandAll}
              className="px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.05] text-text-muted hover:text-text-primary text-xs font-mono transition-colors"
            >
              Expand All
            </button>
            <button
              onClick={collapseAll}
              className="px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.05] text-text-muted hover:text-text-primary text-xs font-mono transition-colors"
            >
              Collapse All
            </button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-stretch gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search controls by ID (e.g. CC6.1, A.5.1), title, or keywords..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-white/[0.08] bg-surface/70 text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          {/* Type Filter Buttons */}
          <div className="ops-panel p-1 inline-flex gap-1 flex-shrink-0">
            <button
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === 'all'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              All ({framework.totalControls})
            </button>
            <button
              onClick={() => setFilterType('automated')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === 'automated'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              ⚡ Automated ({framework.automatedCount})
            </button>
            <button
              onClick={() => setFilterType('manual')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === 'manual'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              📋 Manual &amp; Policy ({framework.manualCount})
            </button>
          </div>
        </div>

        {/* Category Pills (if multiple categories exist) */}
        {categories.length > 2 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 custom-scrollbar">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-lg text-[11px] font-mono whitespace-nowrap transition-colors border ${
                  selectedCategory === cat
                    ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-200'
                    : 'border-white/[0.06] bg-white/[0.02] text-text-muted hover:text-text-secondary'
                }`}
              >
                {cat === 'all' ? 'All Domains' : cat}
              </button>
            ))}
          </div>
        )}

        {/* Controls Cards List */}
        <div className="space-y-3 pt-2">
          {filteredControls.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-white/[0.08] bg-surface/30">
              <p className="text-text-muted text-sm">No controls found matching your search or filters.</p>
              <button
                onClick={() => {
                  setSearch('')
                  setFilterType('all')
                  setSelectedCategory('all')
                }}
                className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 underline font-mono"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            filteredControls.map((ctrl) => {
              const isExpanded = !!expandedControls[ctrl.control_id]
              const currentTab = activeRemediationTab[ctrl.control_id] || 'console'

              return (
                <div
                  key={ctrl.control_id}
                  className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
                    isExpanded
                      ? 'border-indigo-500/30 bg-surface/90 shadow-xl'
                      : 'border-white/[0.06] bg-surface/50 hover:border-white/[0.12] hover:bg-surface/70'
                  }`}
                >
                  {/* Card Header Row */}
                  <div
                    onClick={() => toggleControl(ctrl.control_id)}
                    className="p-4 sm:p-5 flex items-start justify-between gap-4 cursor-pointer select-none"
                  >
                    <div className="flex items-start gap-3.5 min-w-0">
                      <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-white/[0.04] text-text-primary border border-white/[0.08] flex-shrink-0 mt-0.5">
                        {ctrl.control_id}
                      </span>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <h3 className="font-display font-bold text-sm sm:text-base text-text-primary">
                            {ctrl.name}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap text-[11px] font-mono text-text-muted">
                          <span>{ctrl.category}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      {ctrl.automatable ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Automated Telemetry
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                          <FileText className="w-3 h-3 text-amber-400" />
                          Manual / Policy Required
                        </span>
                      )}

                      <button
                        type="button"
                        className="p-1 rounded-lg hover:bg-white/[0.05] text-text-muted hover:text-text-primary transition-colors"
                        aria-label="Toggle details"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Body */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-t border-white/[0.06] p-5 sm:p-6 bg-black/25 space-y-6"
                      >
                        {/* Requirement description */}
                        <div>
                          <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted font-medium mb-1">
                            Regulatory Requirement Description
                          </div>
                          <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">
                            {ctrl.description}
                          </p>
                        </div>

                        {/* ── AUTOMATED CONTROLS SECTION ── */}
                        {ctrl.automatable && (
                          <div className="space-y-4 pt-2">
                            {/* Monitored Signals */}
                            {ctrl.signals && ctrl.signals.length > 0 && (
                              <div>
                                <div className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 font-semibold mb-2 flex items-center gap-1.5">
                                  <Cpu className="w-3.5 h-3.5" />
                                  <span>Continuous Cloud Signals Collected by LogRaven</span>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {ctrl.signals.map((sig) => (
                                    <span
                                      key={sig}
                                      className="px-2.5 py-1 rounded-lg text-[11px] font-mono border border-indigo-500/30 bg-indigo-500/10 text-indigo-200 flex items-center gap-1.5"
                                    >
                                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                                      {sig}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* How It Works */}
                            {ctrl.howItWorks && (
                              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-text-secondary leading-relaxed">
                                <strong className="text-text-primary">How LogRaven Grades This: </strong>
                                {ctrl.howItWorks}
                              </div>
                            )}

                            {/* Technical Remediation Studio */}
                            {ctrl.remediation && (
                              <div className="rounded-2xl border border-white/[0.08] bg-[#0B0F19] overflow-hidden">
                                <div className="p-3 bg-white/[0.02] border-b border-white/[0.06] flex items-center justify-between flex-wrap gap-2">
                                  <div className="flex items-center gap-2">
                                    <Terminal className="w-4 h-4 text-indigo-400" />
                                    <span className="font-mono text-xs font-semibold text-text-primary">
                                      Technical Remediation Guide
                                    </span>
                                  </div>

                                  {/* Sub-tabs */}
                                  <div className="flex items-center gap-1 bg-black/40 p-1 rounded-lg border border-white/[0.06]">
                                    <button
                                      onClick={() =>
                                        setActiveRemediationTab((prev) => ({
                                          ...prev,
                                          [ctrl.control_id]: 'console',
                                        }))
                                      }
                                      className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                                        currentTab === 'console'
                                          ? 'bg-indigo-500/20 text-indigo-300'
                                          : 'text-text-muted hover:text-text-secondary'
                                      }`}
                                    >
                                      Console Guide
                                    </button>
                                    <button
                                      onClick={() =>
                                        setActiveRemediationTab((prev) => ({
                                          ...prev,
                                          [ctrl.control_id]: 'cli',
                                        }))
                                      }
                                      className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                                        currentTab === 'cli'
                                          ? 'bg-indigo-500/20 text-indigo-300'
                                          : 'text-text-muted hover:text-text-secondary'
                                      }`}
                                    >
                                      AWS CLI
                                    </button>
                                    <button
                                      onClick={() =>
                                        setActiveRemediationTab((prev) => ({
                                          ...prev,
                                          [ctrl.control_id]: 'terraform',
                                        }))
                                      }
                                      className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                                        currentTab === 'terraform'
                                          ? 'bg-indigo-500/20 text-indigo-300'
                                          : 'text-text-muted hover:text-text-secondary'
                                      }`}
                                    >
                                      Terraform
                                    </button>
                                    <button
                                      onClick={() =>
                                        setActiveRemediationTab((prev) => ({
                                          ...prev,
                                          [ctrl.control_id]: 'verify',
                                        }))
                                      }
                                      className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                                        currentTab === 'verify'
                                          ? 'bg-indigo-500/20 text-indigo-300'
                                          : 'text-text-muted hover:text-text-secondary'
                                      }`}
                                    >
                                      Verification
                                    </button>
                                  </div>
                                </div>

                                <div className="p-4">
                                  {currentTab === 'console' && (
                                    <ol className="space-y-2 text-xs text-text-secondary">
                                      {ctrl.remediation.consoleSteps.map((step, idx) => (
                                        <li key={idx} className="flex items-start gap-2.5">
                                          <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5 font-bold">
                                            {idx + 1}
                                          </span>
                                          <span className="leading-relaxed">{step}</span>
                                        </li>
                                      ))}
                                    </ol>
                                  )}

                                  {currentTab === 'cli' && (
                                    <div className="relative">
                                      <pre className="p-3.5 rounded-xl bg-black/60 border border-white/[0.06] font-mono text-[11px] text-emerald-300 overflow-x-auto">
                                        <code>{ctrl.remediation.cliCommand}</code>
                                      </pre>
                                      <button
                                        onClick={() => handleCopy(ctrl.remediation!.cliCommand, `${ctrl.control_id}-cli`)}
                                        className="absolute right-2.5 top-2.5 p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-text-muted hover:text-text-primary transition-colors text-xs flex items-center gap-1"
                                      >
                                        {copiedKey === `${ctrl.control_id}-cli` ? (
                                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        ) : (
                                          <Copy className="w-3.5 h-3.5" />
                                        )}
                                      </button>
                                    </div>
                                  )}

                                  {currentTab === 'terraform' && (
                                    <div className="relative">
                                      <pre className="p-3.5 rounded-xl bg-black/60 border border-white/[0.06] font-mono text-[11px] text-indigo-300 overflow-x-auto">
                                        <code>{ctrl.remediation.terraformSnippet}</code>
                                      </pre>
                                      <button
                                        onClick={() => handleCopy(ctrl.remediation!.terraformSnippet, `${ctrl.control_id}-tf`)}
                                        className="absolute right-2.5 top-2.5 p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-text-muted hover:text-text-primary transition-colors text-xs flex items-center gap-1"
                                      >
                                        {copiedKey === `${ctrl.control_id}-tf` ? (
                                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        ) : (
                                          <Copy className="w-3.5 h-3.5" />
                                        )}
                                      </button>
                                    </div>
                                  )}

                                  {currentTab === 'verify' && (
                                    <div className="relative">
                                      <pre className="p-3.5 rounded-xl bg-black/60 border border-white/[0.06] font-mono text-[11px] text-sky-300 overflow-x-auto">
                                        <code>{ctrl.remediation.verificationCommand}</code>
                                      </pre>
                                      <button
                                        onClick={() => handleCopy(ctrl.remediation!.verificationCommand, `${ctrl.control_id}-v`)}
                                        className="absolute right-2.5 top-2.5 p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-text-muted hover:text-text-primary transition-colors text-xs flex items-center gap-1"
                                      >
                                        {copiedKey === `${ctrl.control_id}-v` ? (
                                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        ) : (
                                          <Copy className="w-3.5 h-3.5" />
                                        )}
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* ── MANUAL / GOVERNANCE GUIDANCE SECTION (USER'S KEY REQUEST!) ── */}
                        {!ctrl.automatable && ctrl.manualGuide && (
                          <div className="space-y-5 pt-2">
                            {/* Why this control is manual banner */}
                            <div className="p-4 rounded-2xl bg-amber-500/[0.07] border border-amber-500/25 flex items-start gap-3">
                              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                              <div className="space-y-1">
                                <h4 className="font-display font-bold text-xs uppercase tracking-wider text-amber-300">
                                  Why This Control Requires Manual Governance
                                </h4>
                                <p className="text-xs text-text-secondary leading-relaxed">
                                  {ctrl.manualGuide.whyManual}
                                </p>
                              </div>
                            </div>

                            {/* Required Policy */}
                            <div className="p-3.5 rounded-xl bg-black/30 border border-white/[0.06] flex items-center justify-between gap-3">
                              <div className="flex items-center gap-2.5">
                                <FileText className="w-4 h-4 text-indigo-400" />
                                <div>
                                  <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
                                    Mandatory Written Policy
                                  </div>
                                  <div className="text-xs font-semibold text-text-primary">
                                    {ctrl.manualGuide.requiredPolicy}
                                  </div>
                                </div>
                              </div>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                                Executive Sign-off Required
                              </span>
                            </div>

                            {/* Step-by-Step Implementation Instructions */}
                            <div className="space-y-2">
                              <div className="font-mono text-xs uppercase tracking-wider text-text-muted font-semibold flex items-center gap-2">
                                <BookOpen className="w-4 h-4 text-indigo-400" />
                                <span>Step-by-Step Implementation Instructions</span>
                              </div>
                              <div className="space-y-2.5">
                                {ctrl.manualGuide.operationalSteps.map((step, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-3"
                                  >
                                    <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-300 font-mono text-[10px] flex items-center justify-center flex-shrink-0 mt-0.5 font-bold">
                                      {idx + 1}
                                    </span>
                                    <div className="text-xs text-text-secondary leading-relaxed">
                                      {step}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Auditor Evidence Package Checklist */}
                            <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.08] space-y-3">
                              <div className="font-mono text-xs uppercase tracking-wider text-emerald-400 font-semibold flex items-center gap-2">
                                <Shield className="w-4 h-4" />
                                <span>Auditor Evidence Package Checklist</span>
                              </div>
                              <p className="text-[11px] text-text-muted">
                                External CPAs and compliance assessors will ask for the following specific artifacts during your audit observation period:
                              </p>
                              <div className="space-y-2">
                                {ctrl.manualGuide.auditorEvidence.map((ev, idx) => (
                                  <div key={idx} className="flex items-start gap-2.5 text-xs text-text-secondary">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                    <span>{ev}</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Pitfalls & Auditor Traps to Avoid */}
                            <div className="p-3.5 rounded-xl bg-threat-critical/[0.08] border border-threat-critical/30 flex items-start gap-2.5">
                              <AlertTriangle className="w-4 h-4 text-threat-critical flex-shrink-0 mt-0.5" />
                              <div className="text-xs text-text-secondary leading-relaxed">
                                <strong className="text-threat-critical font-semibold">Auditor Trap to Avoid: </strong>
                                {ctrl.manualGuide.pitfallsToAvoid}
                              </div>
                            </div>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
