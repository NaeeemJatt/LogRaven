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
}
