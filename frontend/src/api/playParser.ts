// LogRaven — PlayParser sandbox API
import client from './client'

export interface PlayParserQuality {
  score: number
  valid_timestamp_ratio: number
  structured_ratio: number
  warnings: string[]
}

export interface PlayParserSampleEvent {
  timestamp: string | null
  source_type: string
  hostname: string | null
  username: string | null
  source_ip: string | null
  event_type: string
  event_id: string | null
  raw_message: string
  severity_hint: string
}

export interface PlayParserEvaluateItem {
  parser_key: string
  ok: boolean
  event_count: number
  events_trimmed: boolean
  quality: PlayParserQuality | null
  error: string | null
  sample_events: PlayParserSampleEvent[] | null
}

export interface PlayParserEvaluateResponse {
  results: PlayParserEvaluateItem[]
}

export interface PlayParserDetectCandidate {
  log_type: string
  confidence: number
  reasons: string[]
}

export interface PlayParserDetectResponse {
  candidates: PlayParserDetectCandidate[]
}

export interface PlayDecoderSummary {
  ok: boolean
  manager_reachable: boolean
  event_count: number
  events_trimmed: boolean
  warning_codes: string[]
  user_messages: string[]
  error: string | null
  sample_events: PlayParserSampleEvent[] | null
}

export interface PlayParserCompareMetrics {
  native_event_count: number
  decoder_event_count: number
  count_delta: number
  sample_pairs_compared: number
  timestamp_agreement_ratio: number
  source_ip_agreement_ratio: number
}

export interface PlayParserEvaluateCompareResponse {
  parser_results: PlayParserEvaluateItem[]
  decoders: PlayDecoderSummary
  compare: PlayParserCompareMetrics | null
}

export type PlayParserPreviewMatch = 'exact' | 'substring' | 'index' | 'none'

export interface PlayParserPreviewRow {
  line_no: number
  raw: string
  parsed: Record<string, unknown> | null
  match: PlayParserPreviewMatch
}

export interface PlayParserPreviewResponse {
  preview_kind: 'parser' | 'decoder'
  key: string
  line_limit: number
  rows: PlayParserPreviewRow[]
  note: string | null
}

export type PlayParserRunMode = 'parsers_only' | 'decoders_only' | 'both'

export const playParserApi = {
  evaluate: (file: File, parserKeys: string[]) => {
    const form = new FormData()
    form.append('file', file)
    form.append('parser_keys', JSON.stringify(parserKeys))
    return client.post<PlayParserEvaluateResponse>('/api/v1/play-parser/evaluate', form)
  },

  detect: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post<PlayParserDetectResponse>('/api/v1/play-parser/detect', form)
  },

  evaluateCompare: (
    file: File,
    parserKeys: string[],
    options?: {
      sourceType?: string
      includeDecoders?: boolean
      playMode?: PlayParserRunMode
    },
  ) => {
    const form = new FormData()
    form.append('file', file)
    form.append('parser_keys', JSON.stringify(parserKeys))
    form.append('source_type', options?.sourceType ?? 'linux_endpoint')
    form.append('include_decoders', options?.includeDecoders === false ? 'false' : 'true')
    form.append('play_mode', options?.playMode ?? 'both')
    return client.post<PlayParserEvaluateCompareResponse>('/api/v1/play-parser/evaluate-compare', form)
  },

  preview: (
    file: File,
    previewTarget: string,
    options?: { sourceType?: string; lineLimit?: number },
  ) => {
    const form = new FormData()
    form.append('file', file)
    form.append('preview_target', previewTarget)
    form.append('source_type', options?.sourceType ?? 'linux_endpoint')
    form.append('line_limit', String(options?.lineLimit ?? 50))
    return client.post<PlayParserPreviewResponse>('/api/v1/play-parser/preview', form)
  },
}
