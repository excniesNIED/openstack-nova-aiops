export type AlertSeverity = 'P1' | 'P2' | 'P3' | string

export type AlertStatus = 'new' | 'ack' | 'resolved' | string

export type AlertEvidenceCounts = {
  error_cnt: number
  warn_cnt: number
  info_cnt: number
  total_records: number
}

export type AlertEvidence = {
  top_templates?: string[]
  template_counts?: Record<string, number>
  keyword_counts?: Record<string, number>
  error_examples?: Array<Record<string, unknown>>
  error_ratio?: number
  counts?: AlertEvidenceCounts
}

export type Alert = {
  alert_id: string
  created_at: string
  entity_key: string
  window_start: string
  window_end: string
  pred_class: string
  pred_label_id: number
  prob: number
  threshold: number
  severity: AlertSeverity
  status: AlertStatus
  evidence: AlertEvidence
}

export type HealthResponse = {
  ok: boolean
}

