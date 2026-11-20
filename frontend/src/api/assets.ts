// LogRaven — Cloud Asset Inventory API Client
import client from './client'

export interface AssetRecord {
  urn: string
  account_id: string
  provider: string
  service: string
  resource_type: string
  resource_id: string
  resource_name: string
  region: string
  compliance_status: 'COMPLIANT' | 'NON_COMPLIANT' | 'UNASSESSED' | string
  failing_rule_count: number
  passing_rule_count: number
  tags: Record<string, any>
  first_seen_at: string
  last_seen_at: string
}

export interface AssetDetailRecord extends AssetRecord {
  config_json: Record<string, any>
  config_sha256: string
  cloud_account_id?: string
}

export interface AssetListResponse {
  items: AssetRecord[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface FilterOption {
  value: string
  count: number
  label?: string
}

export interface AssetFiltersResponse {
  providers: FilterOption[]
  services: FilterOption[]
  regions: FilterOption[]
  statuses: FilterOption[]
}

export interface AssetSummaryResponse {
  total_assets: number
  compliant_assets: number
  non_compliant_assets: number
  unassessed_assets: number
  services_count: number
  accounts_count: number
}

export interface AssetQueryParams {
  page?: number
  limit?: number
  search?: string
  provider?: string
  service?: string
  region?: string
  status?: string
  account_id?: string
}

export interface AssetSyncResponse {
  status: string
  synced_assets_count: number
  services: string[]
  message: string
  synced_at: string
}

export async function getAssets(params: AssetQueryParams = {}): Promise<AssetListResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.limit) query.set('limit', String(params.limit))
  if (params.search) query.set('search', params.search)
  if (params.provider && params.provider.toLowerCase() !== 'all') query.set('provider', params.provider)
  if (params.service && params.service.toLowerCase() !== 'all') query.set('service', params.service)
  if (params.region && params.region.toLowerCase() !== 'all') query.set('region', params.region)
  if (params.status && params.status.toLowerCase() !== 'all') query.set('status', params.status)
  if (params.account_id && params.account_id.toLowerCase() !== 'all') query.set('account_id', params.account_id)

  const res = await client.get<AssetListResponse>(`/api/v1/assets?${query.toString()}`)
  return res.data
}

export async function getAssetFilters(): Promise<AssetFiltersResponse> {
  const res = await client.get<AssetFiltersResponse>('/api/v1/assets/filters')
  return res.data
}

export async function getAssetSummary(): Promise<AssetSummaryResponse> {
  const res = await client.get<AssetSummaryResponse>('/api/v1/assets/summary')
  return res.data
}

export async function getAssetByUrn(urn: string): Promise<AssetDetailRecord> {
  const res = await client.get<AssetDetailRecord>(`/api/v1/assets/${encodeURIComponent(urn)}`)
  return res.data
}

export async function syncAssets(cloudAccountId?: string): Promise<AssetSyncResponse> {
  const res = await client.post<AssetSyncResponse>('/api/v1/assets/sync', {
    cloud_account_id: cloudAccountId,
  })
  return res.data
}
