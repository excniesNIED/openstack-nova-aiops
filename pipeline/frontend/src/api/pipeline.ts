import type { Alert, ControlStatus, HealthResponse, StartReplayRequest } from './types'

type FetchOptions = {
  timeoutMs?: number
  signal?: AbortSignal
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim()
  if (!trimmed) return '/api'
  return trimmed.replace(/\/+$/, '')
}

function buildUrl(baseUrl: string, path: string): string {
  const base = normalizeBaseUrl(baseUrl)
  const p = path.startsWith('/') ? path : `/${path}`
  const fullPath = `${base}${p}`
  if (fullPath.startsWith('http://') || fullPath.startsWith('https://')) return fullPath
  return new URL(fullPath, window.location.origin).toString()
}

async function fetchJson<T>(url: string, options: FetchOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeoutMs = options.timeoutMs ?? 8000
  const signal = options.signal ?? controller.signal
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status} ${res.statusText}${text ? `: ${text}` : ''}`)
    }
    return (await res.json()) as T
  } finally {
    window.clearTimeout(timeout)
  }
}

async function postJson<T>(url: string, body: unknown, options: FetchOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeoutMs = options.timeoutMs ?? 8000
  const signal = options.signal ?? controller.signal
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
      signal,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status} ${res.statusText}${text ? `: ${text}` : ''}`)
    }
    return (await res.json()) as T
  } finally {
    window.clearTimeout(timeout)
  }
}

export async function getHealth(baseUrl: string, options?: FetchOptions): Promise<HealthResponse> {
  return fetchJson<HealthResponse>(buildUrl(baseUrl, '/health'), options)
}

export async function getControlStatus(baseUrl: string, options?: FetchOptions): Promise<ControlStatus> {
  return fetchJson<ControlStatus>(buildUrl(baseUrl, '/control/status'), options)
}

export async function listControlLogs(baseUrl: string, options?: FetchOptions): Promise<Record<string, string>> {
  return fetchJson<Record<string, string>>(buildUrl(baseUrl, '/control/logs'), options)
}

export async function startReplay(
  baseUrl: string,
  req: StartReplayRequest,
  options?: FetchOptions,
): Promise<ControlStatus> {
  return postJson<ControlStatus>(buildUrl(baseUrl, '/control/start'), req, options)
}

export async function stopReplay(baseUrl: string, options?: FetchOptions): Promise<ControlStatus> {
  return postJson<ControlStatus>(buildUrl(baseUrl, '/control/stop'), {}, options)
}

export async function listAlerts(
  baseUrl: string,
  params: { limit?: number; offset?: number; status?: string } = {},
  options?: FetchOptions,
): Promise<Alert[]> {
  const url = new URL(buildUrl(baseUrl, '/alerts'))
  if (params.limit != null) url.searchParams.set('limit', String(params.limit))
  if (params.offset != null) url.searchParams.set('offset', String(params.offset))
  if (params.status) url.searchParams.set('status', params.status)
  return fetchJson<Alert[]>(url.toString(), options)
}

export async function getAlert(baseUrl: string, alertId: string, options?: FetchOptions): Promise<Alert> {
  return fetchJson<Alert>(buildUrl(baseUrl, `/alerts/${encodeURIComponent(alertId)}`), options)
}
