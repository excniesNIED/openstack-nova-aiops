import { computed, onMounted, onUnmounted, ref, type Ref, watch } from 'vue'
import { getHealth, listAlerts } from '@/api/pipeline'
import type { Alert, HealthResponse } from '@/api/types'

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim()
  if (!trimmed) return '/api'
  return trimmed.replace(/\/+$/, '')
}

export function usePipelineAlerts(
  apiBaseUrl: Ref<string>,
  options: {
    pollMs?: number
    limit?: number
  } = {},
) {
  const pollMs = options.pollMs ?? 3000
  const limit = options.limit ?? 200

  const alerts = ref<Alert[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const apiOk = ref<boolean | null>(null)
  const apiLatencyMs = ref<number | null>(null)
  const health = ref<HealthResponse | null>(null)
  const lastUpdatedIso = ref<string | null>(null)

  const isReady = computed(() => apiOk.value === true && !loading.value)

  let timer: number | null = null
  let es: EventSource | null = null

  const sseUrl = computed(() => {
    const base = normalizeBaseUrl(apiBaseUrl.value)
    const fullPath = `${base}/events/alerts`
    if (fullPath.startsWith('http://') || fullPath.startsWith('https://')) return fullPath
    return new URL(fullPath, window.location.origin).toString()
  })

  const connectSse = () => {
    if (typeof EventSource === 'undefined') return
    try {
      if (es) es.close()
      es = new EventSource(sseUrl.value)

      es.addEventListener('alert', (evt) => {
        try {
          const data = (evt as MessageEvent<string>).data
          const a = JSON.parse(data) as Alert
          const existing = alerts.value.find((x) => x.alert_id === a.alert_id)
          if (existing) return
          alerts.value = [a, ...alerts.value].slice(0, limit)
          lastUpdatedIso.value = new Date().toISOString()
        } catch {
          // ignore
        }
      })

      es.addEventListener('error', () => {
        // Server may restart; polling keeps the UI consistent.
      })
    } catch {
      // ignore
    }
  }

  const refresh = async () => {
    if (loading.value) return
    loading.value = true
    error.value = null
    // Keep last known health/latency during refresh to avoid UI flicker.

    const start = performance.now()
    try {
      const h = await getHealth(apiBaseUrl.value, { timeoutMs: 8000 })
      health.value = h
      apiOk.value = !!h.ok
      apiLatencyMs.value = Math.round(performance.now() - start)

      const rows = await listAlerts(apiBaseUrl.value, { limit, offset: 0 })
      alerts.value = rows
      lastUpdatedIso.value = new Date().toISOString()
    } catch (e) {
      apiOk.value = false
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void refresh()
    timer = window.setInterval(() => void refresh(), pollMs)
    connectSse()
  })

  onUnmounted(() => {
    if (timer) window.clearInterval(timer)
    if (es) es.close()
  })

  watch(
    apiBaseUrl,
    () => {
      void refresh()
      connectSse()
    },
    { flush: 'post' },
  )

  return { alerts, loading, error, apiOk, apiLatencyMs, health, lastUpdatedIso, isReady, refresh }
}
