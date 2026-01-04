import { computed, onMounted, onUnmounted, ref, type Ref, watch } from 'vue'
import { getHealth, listAlerts } from '@/api/pipeline'
import type { Alert } from '@/api/types'

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
  const lastUpdatedIso = ref<string | null>(null)

  const isReady = computed(() => apiOk.value === true && !loading.value)

  let timer: number | null = null

  const refresh = async () => {
    loading.value = true
    error.value = null
    apiLatencyMs.value = null

    const start = performance.now()
    try {
      const h = await getHealth(apiBaseUrl.value, { timeoutMs: 3000 })
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
  })

  onUnmounted(() => {
    if (timer) window.clearInterval(timer)
  })

  watch(
    apiBaseUrl,
    () => {
      void refresh()
    },
    { flush: 'post' },
  )

  return { alerts, loading, error, apiOk, apiLatencyMs, lastUpdatedIso, isReady, refresh }
}

