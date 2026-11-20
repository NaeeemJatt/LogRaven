// LogRaven — Asset Inventory Filter Ribbon
import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Search, X, RotateCcw } from 'lucide-react'
import type { FilterOption } from '../../api/assets'

interface AssetFilterBarProps {
  selectedCloud: string
  onSelectCloud: (cloud: string) => void
  selectedService: string
  onSelectService: (service: string) => void
  selectedRegion: string
  onSelectRegion: (region: string) => void
  selectedStatus: string
  onSelectStatus: (status: string) => void
  search: string
  onSearchChange: (search: string) => void
  clouds: FilterOption[]
  services: FilterOption[]
  regions: FilterOption[]
  statuses: FilterOption[]
  totalMatches: number
}

export default function AssetFilterBar({
  selectedCloud,
  onSelectCloud,
  selectedService,
  onSelectService,
  selectedRegion,
  onSelectRegion,
  selectedStatus,
  onSelectStatus,
  search,
  onSearchChange,
  clouds,
  services,
  regions,
  statuses,
  totalMatches,
}: AssetFilterBarProps) {
  const [activeDropdown, setActiveDropdown] = useState<'cloud' | 'service' | 'region' | 'status' | null>(null)
  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setActiveDropdown(null)
      }
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setActiveDropdown(null)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [])

  const hasActiveFilters =
    selectedCloud !== 'all' ||
    selectedService !== 'all' ||
    selectedRegion !== 'all' ||
    selectedStatus !== 'all' ||
    search.trim().length > 0

  const handleReset = () => {
    onSelectCloud('all')
    onSelectService('all')
    onSelectRegion('all')
    onSelectStatus('all')
    onSearchChange('')
    setActiveDropdown(null)
  }

  return (
    <div ref={barRef} className="ops-panel px-3 py-2 flex flex-wrap items-center justify-between gap-3 text-xs mb-4">
      {/* Left side: Filter pills */}
      <div className="flex flex-wrap items-center gap-2">
        {/* 1. Cloud Provider Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setActiveDropdown(activeDropdown === 'cloud' ? null : 'cloud')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              selectedCloud !== 'all' || activeDropdown === 'cloud'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                : 'border-white/[0.08] bg-deep/80 text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
            }`}
          >
            <span>Cloud</span>
            <span className="text-white/40 font-mono">=</span>
            <span className="text-text-primary font-semibold">{selectedCloud === 'all' ? 'All' : selectedCloud.toUpperCase()}</span>
            <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'cloud' ? 'rotate-180' : ''}`} />
          </button>

          {activeDropdown === 'cloud' && (
            <div className="absolute left-0 top-full mt-1.5 w-48 rounded-xl border border-white/[0.1] bg-surface/95 shadow-xl p-1.5 z-50 backdrop-blur-xl">
              <div className="space-y-0.5">
                <button
                  type="button"
                  onClick={() => {
                    onSelectCloud('all')
                    setActiveDropdown(null)
                  }}
                  className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                    selectedCloud === 'all' ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>All Clouds</span>
                </button>
                {clouds.map((c) => (
                  <button
                    key={c.value}
                    type="button"
                    onClick={() => {
                      onSelectCloud(c.value)
                      setActiveDropdown(null)
                    }}
                    className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                      selectedCloud.toLowerCase() === c.value.toLowerCase() ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                    }`}
                  >
                    <span>{c.label || c.value.toUpperCase()}</span>
                    <span className="text-[10px] text-text-muted font-mono">{c.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 2. Service Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setActiveDropdown(activeDropdown === 'service' ? null : 'service')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              selectedService !== 'all' || activeDropdown === 'service'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                : 'border-white/[0.08] bg-deep/80 text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
            }`}
          >
            <span>Service</span>
            <span className="text-white/40 font-mono">=</span>
            <span className="text-text-primary font-semibold max-w-[150px] truncate">
              {(() => {
                if (selectedService === 'all') return 'All'
                const match = services.find((s) => s.value.toLowerCase() === selectedService.toLowerCase())
                if (match) return match.label || match.value
                if (selectedService.toUpperCase() === 'SECURITY_GROUP') return 'Security Groups'
                if (selectedService.toUpperCase() === 'LOAD_BALANCER') return 'Load Balancers'
                if (selectedService.toUpperCase() === 'API_GATEWAY') return 'API Gateway'
                if (selectedService.toUpperCase() === 'LOG_GROUP') return 'Log Groups'
                if (selectedService.toUpperCase() === 'LAMBDA') return 'Lambda'
                return selectedService.toUpperCase()
              })()}
            </span>
            <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'service' ? 'rotate-180' : ''}`} />
          </button>

          {activeDropdown === 'service' && (
            <div className="absolute left-0 top-full mt-1.5 w-64 rounded-xl border border-white/[0.1] bg-surface/95 shadow-xl p-1.5 z-50 backdrop-blur-xl">
              <div className="max-h-60 overflow-y-auto space-y-0.5 custom-scrollbar">
                <button
                  type="button"
                  onClick={() => {
                    onSelectService('all')
                    setActiveDropdown(null)
                  }}
                  className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                    selectedService === 'all' ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>All Services</span>
                </button>
                {services.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => {
                      onSelectService(s.value)
                      setActiveDropdown(null)
                    }}
                    className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                      selectedService.toLowerCase() === s.value.toLowerCase() ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                    }`}
                  >
                    <span className="truncate">{s.label || s.value.toUpperCase()}</span>
                    <span className="text-[10px] text-text-muted font-mono ml-2">{s.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 3. Region Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setActiveDropdown(activeDropdown === 'region' ? null : 'region')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              selectedRegion !== 'all' || activeDropdown === 'region'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                : 'border-white/[0.08] bg-deep/80 text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
            }`}
          >
            <span>Region</span>
            <span className="text-white/40 font-mono">=</span>
            <span className="text-text-primary font-semibold max-w-[120px] truncate">{selectedRegion === 'all' ? 'All' : selectedRegion}</span>
            <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'region' ? 'rotate-180' : ''}`} />
          </button>

          {activeDropdown === 'region' && (
            <div className="absolute left-0 top-full mt-1.5 w-52 rounded-xl border border-white/[0.1] bg-surface/95 shadow-xl p-1.5 z-50 backdrop-blur-xl">
              <div className="max-h-60 overflow-y-auto space-y-0.5 custom-scrollbar">
                <button
                  type="button"
                  onClick={() => {
                    onSelectRegion('all')
                    setActiveDropdown(null)
                  }}
                  className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                    selectedRegion === 'all' ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>All Regions</span>
                </button>
                {regions.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => {
                      onSelectRegion(r.value)
                      setActiveDropdown(null)
                    }}
                    className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                      selectedRegion.toLowerCase() === r.value.toLowerCase() ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                    }`}
                  >
                    <span className="truncate">{r.label || r.value}</span>
                    <span className="text-[10px] text-text-muted font-mono ml-2">{r.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 4. Status Pill */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setActiveDropdown(activeDropdown === 'status' ? null : 'status')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              selectedStatus !== 'all' || activeDropdown === 'status'
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-300'
                : 'border-white/[0.08] bg-deep/80 text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
            }`}
          >
            <span>Status</span>
            <span className="text-white/40 font-mono">=</span>
            <span className="text-text-primary font-semibold">{selectedStatus === 'all' ? 'All' : selectedStatus.replace('_', ' ')}</span>
            <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-150 ${activeDropdown === 'status' ? 'rotate-180' : ''}`} />
          </button>

          {activeDropdown === 'status' && (
            <div className="absolute left-0 top-full mt-1.5 w-48 rounded-xl border border-white/[0.1] bg-surface/95 shadow-xl p-1.5 z-50 backdrop-blur-xl">
              <div className="space-y-0.5">
                <button
                  type="button"
                  onClick={() => {
                    onSelectStatus('all')
                    setActiveDropdown(null)
                  }}
                  className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left ${
                    selectedStatus === 'all' ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                  }`}
                >
                  <span>All Statuses</span>
                </button>
                {statuses.map((st) => (
                  <button
                    key={st.value}
                    type="button"
                    onClick={() => {
                      onSelectStatus(st.value)
                      setActiveDropdown(null)
                    }}
                    className={`w-full px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer text-left flex items-center justify-between ${
                      selectedStatus.toLowerCase() === st.value.toLowerCase() ? 'bg-amber-400/10 text-amber-300 font-semibold' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                    }`}
                  >
                    <span>{st.label || st.value.replace('_', ' ')}</span>
                    <span className="text-[10px] text-text-muted font-mono ml-2">{st.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Clear filters button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/10 text-xs text-text-muted hover:text-text-primary hover:bg-white/[0.06] transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Right side: Search input & count */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-text-muted font-mono">
          {totalMatches.toLocaleString()} {totalMatches === 1 ? 'asset' : 'assets'}
        </span>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search assets, URN, tags..."
            className="w-48 sm:w-64 pl-8 pr-8 py-1.5 rounded-lg border border-white/[0.1] bg-[#101216] text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/30 transition-all font-mono"
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
