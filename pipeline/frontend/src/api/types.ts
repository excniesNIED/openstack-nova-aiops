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

export type DependencyCheck = {
  status: 'up' | 'down' | 'disabled' | 'not_configured' | string
  host?: string
  port?: number
  latency_ms?: number | null
  error?: string
  driver?: string
}

export type Dependencies = {
  kafka?: DependencyCheck
  spark?: DependencyCheck
  database?: DependencyCheck
  hdfs?: DependencyCheck
  hbase?: DependencyCheck
  hive?: DependencyCheck
}

export type HealthResponse = {
  ok: boolean
  replay_running?: boolean
  dependencies_ok?: boolean
  dependencies?: Dependencies
}

export type ControlStatus = {
  running: boolean
  paused?: boolean
  dataset_id: string
  log_path: string | null
  rate: number
  loop: boolean
  max_records: number
  sent_records: number
  started_at: string | null
  finished_at: string | null
  last_error: string | null
}

export type StartReplayRequest = {
  dataset_id: string
  log_name?: string
  rate?: number
  loop?: boolean
  max_records?: number
}
