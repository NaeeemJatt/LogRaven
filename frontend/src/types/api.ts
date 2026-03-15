// LogRaven — API Response TypeScript Types

export interface ErrorResponse {
  error: string
  code: string
  detail?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface DownloadResponse {
  download_url: string
  expires_in: number
}
