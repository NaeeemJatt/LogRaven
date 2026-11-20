// LogRaven — Cloud Asset Inventory & Discovery Console
import { useState, useEffect, useCallback } from 'react'
import {
  Server,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Download,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Cloud,
} from 'lucide-react'
import {
  getAssets,
  getAssetFilters,
  getAssetSummary,
  getAssetByUrn,
  syncAssets,
  type AssetRecord,
  type AssetDetailRecord,
  type FilterOption,
  type AssetSummaryResponse,
} from '../api/assets'
import AssetFilterBar from '../components/assets/AssetFilterBar'
import AssetDetailDrawer from '../components/assets/AssetDetailDrawer'

const SERVICE_NAME_MAP: Record<string, string> = {
  EC2: 'EC2',
  SECURITY_GROUP: 'Security Group',
  LOAD_BALANCER: 'Load Balancer',
  API_GATEWAY: 'API Gateway',
  LOG_GROUP: 'Log Group',
  LAMBDA: 'Lambda',
  RDS: 'RDS',
  KINESIS: 'Kinesis',
  EKS: 'EKS',
  ECS: 'ECS',
  ECR: 'ECR',
  DYNAMODB: 'DynamoDB',
  ELASTICACHE: 'ElastiCache',
  SECRETS_MANAGER: 'Secrets Manager',
  ACM: 'ACM',
  WAF: 'WAF',
  CLOUD_FRONT: 'CloudFront',
  ROUTE_53: 'Route 53',
  SQS: 'SQS',
  SNS: 'SNS',
  CLOUD_TRAIL: 'CloudTrail',
  IAM: 'IAM',
  S3: 'S3',
  KMS: 'KMS',
  VPC: 'VPC',
}

export default function AssetInventoryPage() {
  const [assets, setAssets] = useState<AssetRecord[]>([])
  const [summary, setSummary] = useState<AssetSummaryResponse | null>(null)
  const [filters, setFilters] = useState<{
    providers: FilterOption[]
    services: FilterOption[]
    regions: FilterOption[]
    statuses: FilterOption[]
  }>({ providers: [], services: [], regions: [], statuses: [] })

  // Active filter state
  const [selectedCloud, setSelectedCloud] = useState('all')
  const [selectedService, setSelectedService] = useState('all')
  const [selectedRegion, setSelectedRegion] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [search, setSearch] = useState('')

  // Pagination
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  // Loading & Sync state
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncFeedback, setSyncFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Detail drawer
  const [selectedAsset, setSelectedAsset] = useState<AssetDetailRecord | null>(null)

  // Load summary and filters
  const loadFiltersAndSummary = useCallback(async () => {
    try {
      const [sumData, filterData] = await Promise.all([
        getAssetSummary(),
        getAssetFilters(),
      ])
      setSummary(sumData)
      setFilters(filterData)
    } catch (err) {
      console.error('Failed to load asset summary/filters:', err)
    }
  }, [])

  // Load assets based on current filters
  const loadAssets = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getAssets({
        page,
        limit: pageSize,
        search,
        provider: selectedCloud,
        service: selectedService,
        region: selectedRegion,
        status: selectedStatus,
      })
      setAssets(res.items)
      setTotal(res.total)
      setTotalPages(res.total_pages)
    } catch (err) {
      console.error('Failed to load assets:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, selectedCloud, selectedService, selectedRegion, selectedStatus])

  useEffect(() => {
    void loadFiltersAndSummary()
  }, [loadFiltersAndSummary])

  useEffect(() => {
    void loadAssets()
  }, [loadAssets])

  // Reset to page 1 on filter changes
  useEffect(() => {
    setPage(1)
  }, [selectedCloud, selectedService, selectedRegion, selectedStatus, search, pageSize])

  const handleSync = async () => {
    setSyncing(true)
    setSyncFeedback(null)
    try {
      const res = await syncAssets()
      const msg =
        res.synced_assets_count > 0
          ? `Discovered ${res.synced_assets_count} assets across ${res.services.join(', ')}`
          : 'Cloud asset discovery completed. All connected cloud accounts are synchronized.'
      setSyncFeedback({ type: 'success', message: msg })
      await Promise.all([loadAssets(), loadFiltersAndSummary()])
    } catch (err: any) {
      console.error('Asset sync failed:', err)
      const detail =
        err?.response?.data?.detail || err?.message || 'Cloud asset discovery failed. Verify credentials in Cloud Accounts.'
      setSyncFeedback({
        type: 'error',
        message: typeof detail === 'string' ? detail : 'Cloud asset discovery failed. Verify credentials in Cloud Accounts.',
      })
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncFeedback(null), 6000)
    }
  }

  const handleRowClick = async (asset: AssetRecord) => {
    try {
      const detail = await getAssetByUrn(asset.urn)
      setSelectedAsset(detail)
    } catch (err) {
      console.error('Failed to load asset details:', err)
      // Fallback to basic record
      setSelectedAsset({
        ...asset,
        config_json: {},
        config_sha256: 'unhashed',
      })
    }
  }

  const exportCsv = () => {
    const headers = ['URN', 'Name', 'Provider', 'Service', 'Resource Type', 'Region', 'Status', 'Account ID', 'Last Seen']
    const rows = assets.map((a) => [
      `"${a.urn}"`,
      `"${a.resource_name}"`,
      `"${a.provider}"`,
      `"${a.service}"`,
      `"${a.resource_type}"`,
      `"${a.region}"`,
      `"${a.compliance_status}"`,
      `"${a.account_id}"`,
      `"${a.last_seen_at}"`,
    ])
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `lograven_asset_inventory_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="relative px-4 sm:px-6 lg:px-8 pt-3 sm:pt-4 pb-8 w-full max-w-[1600px] mx-auto">
      <div className="space-y-4">
        {/* Top Header & Actions */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-text-muted flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-amber-400/80" /> Cloud Assets
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-text-primary">
              Asset Inventory
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              Normalized canonical asset inventory across connected cloud accounts and telemetry streams.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleSync}
              disabled={syncing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 text-amber-300 hover:bg-amber-400/15 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? 'Discovering Assets…' : 'Discover Assets'}</span>
            </button>

            <button
              type="button"
              onClick={exportCsv}
              disabled={assets.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] bg-deep/80 text-text-secondary hover:text-text-primary hover:bg-white/[0.04] text-xs font-medium transition-colors cursor-pointer disabled:opacity-40"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Sync alert notification */}
        {syncFeedback && (
          <div
            className={`p-3 text-xs font-mono rounded-lg border flex items-center justify-between animate-in fade-in duration-200 ${
              syncFeedback.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
            }`}
          >
            <div className="flex items-center gap-2">
              {syncFeedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{syncFeedback.message}</span>
            </div>
            <button
              type="button"
              onClick={() => setSyncFeedback(null)}
              className="text-text-muted hover:text-text-primary ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Top KPI Summary Tier */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl border border-white/[0.08] bg-deep/80 p-4">
            <span className="text-xs font-medium text-text-muted block">Total Discovered Assets</span>
            <div className="text-2xl font-semibold text-text-primary font-mono mt-1">
              {summary ? summary.total_assets.toLocaleString() : '—'}
            </div>
            <span className="text-[11px] text-text-muted mt-1 block">Across all cloud regions</span>
          </div>

          <div className="rounded-xl border border-white/[0.08] bg-deep/80 p-4">
            <span className="text-xs font-medium text-text-muted block flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/80" /> Compliant Baseline
            </span>
            <div className="text-2xl font-semibold text-emerald-400 font-mono mt-1">
              {summary ? summary.compliant_assets.toLocaleString() : '—'}
            </div>
            <span className="text-[11px] text-text-muted mt-1 block">Zero active posture violations</span>
          </div>

          <div className="rounded-xl border border-white/[0.08] bg-deep/80 p-4">
            <span className="text-xs font-medium text-text-muted block flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400/80" /> Assets With Gaps
            </span>
            <div className="text-2xl font-semibold text-rose-400 font-mono mt-1">
              {summary ? summary.non_compliant_assets.toLocaleString() : '—'}
            </div>
            <span className="text-[11px] text-text-muted mt-1 block">Flagged by CSPM rules</span>
          </div>

          <div className="rounded-xl border border-white/[0.08] bg-deep/80 p-4">
            <span className="text-xs font-medium text-text-muted block">Monitored Services</span>
            <div className="text-2xl font-semibold text-text-primary font-mono mt-1">
              {summary ? summary.services_count : '—'}
            </div>
            <span className="text-[11px] text-text-muted mt-1 block">Active cloud resource types</span>
          </div>
        </div>

        {/* Filter Ribbon */}
        <AssetFilterBar
          selectedCloud={selectedCloud}
          onSelectCloud={setSelectedCloud}
          selectedService={selectedService}
          onSelectService={setSelectedService}
          selectedRegion={selectedRegion}
          onSelectRegion={setSelectedRegion}
          selectedStatus={selectedStatus}
          onSelectStatus={setSelectedStatus}
          search={search}
          onSearchChange={setSearch}
          clouds={filters.providers}
          services={filters.services}
          regions={filters.regions}
          statuses={filters.statuses}
          totalMatches={total}
        />

        {/* Assets Table */}
        <div className="rounded-xl border border-white/[0.08] bg-[#0E1015]/90 overflow-hidden shadow-2xl">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
              <p className="text-xs text-text-muted font-mono">Loading cloud asset inventory…</p>
            </div>
          ) : assets.length === 0 ? (
            <div className="py-16 text-center space-y-3">
              <Server className="w-10 h-10 text-text-muted mx-auto opacity-40" />
              <h3 className="text-sm font-semibold text-text-primary">No Matching Assets Found</h3>
              <p className="text-xs text-text-muted max-w-sm mx-auto">
                No cloud resources match your active filter criteria. Try adjusting your filters or run cloud discovery.
              </p>
              <button
                type="button"
                onClick={handleSync}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-400/40 bg-amber-400/10 text-amber-300 text-xs font-semibold cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Run Cloud Discovery</span>
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.08] bg-white/[0.02] text-text-muted font-mono text-[11px]">
                    <th className="px-4 py-3 font-medium">Asset name & resource ID</th>
                    <th className="px-3 py-3 font-medium">Status</th>
                    <th className="px-3 py-3 font-medium">Cloud provider</th>
                    <th className="px-3 py-3 font-medium">Service</th>
                    <th className="px-3 py-3 font-medium">Region</th>
                    <th className="px-4 py-3 text-right font-medium">Last discovered</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {assets.map((asset) => {
                    const isCompliant = asset.compliance_status === 'COMPLIANT'
                    return (
                      <tr
                        key={asset.urn}
                        onClick={() => handleRowClick(asset)}
                        className="hover:bg-white/[0.03] transition-colors cursor-pointer group"
                      >
                        <td className="px-4 py-3 min-w-0">
                          <div className="flex items-center gap-2">
                            <div className="min-w-0">
                              <span className="font-semibold text-text-primary block truncate group-hover:text-amber-300 transition-colors">
                                {asset.resource_name}
                              </span>
                              <span className="text-[11px] font-mono text-text-muted truncate block">
                                {asset.resource_type} • {asset.resource_id}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="px-3 py-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                              isCompliant
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}
                          >
                            {isCompliant ? <ShieldCheck className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                            {asset.compliance_status}
                          </span>
                        </td>

                        <td className="px-3 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 font-mono text-text-secondary">
                            <Cloud className="w-3.5 h-3.5 text-text-muted" />
                            <span>{asset.provider}</span>
                            <span className="text-[10px] text-text-muted">({asset.account_id})</span>
                          </div>
                        </td>

                        <td className="px-3 py-3 whitespace-nowrap font-mono text-text-secondary">
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono text-text-secondary bg-white/[0.03] border border-white/[0.08]">
                            {SERVICE_NAME_MAP[asset.service] || asset.service}
                          </span>
                        </td>

                        <td className="px-3 py-3 whitespace-nowrap font-mono text-text-muted text-[11px]">
                          {asset.region}
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-text-muted text-[11px]">
                          {new Date(asset.last_seen_at).toLocaleDateString()}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Table Footer with Pagination & Page Size Counter */}
          {!loading && assets.length > 0 && (
            <div className="p-3 border-t border-white/[0.08] bg-white/[0.01] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-text-muted font-mono">
                <span>Show:</span>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="px-2 py-1 rounded bg-[#101216] border border-white/10 text-text-primary focus:outline-none focus:border-amber-400/50"
                >
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
                <span>assets per page</span>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-text-muted font-mono">
                  Page {page} of {totalPages} ({total} total)
                </span>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1 rounded border border-white/10 text-text-muted hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-1 rounded border border-white/10 text-text-muted hover:text-text-primary hover:bg-white/[0.06] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Asset Detail Drawer */}
        <AssetDetailDrawer
          asset={selectedAsset}
          onClose={() => setSelectedAsset(null)}
        />
      </div>
    </div>
  )
}
