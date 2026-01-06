import { ref, watch } from 'vue'

import { getHealth } from '@/api/pipeline'

const STORAGE_KEY = 'pipeline.apiBaseUrl'

function guessLocalBackendBaseUrl(): string {
  const { protocol, hostname } = window.location
  if (!hostname) return 'http://localhost:8000'
  if (protocol === 'https:') return `https://${hostname}:8000`
  return `http://${hostname}:8000`
}

const stored = localStorage.getItem(STORAGE_KEY)
const defaultBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
const apiBaseUrl = ref<string>(stored ?? defaultBaseUrl)

watch(apiBaseUrl, (v) => {
  localStorage.setItem(STORAGE_KEY, v)
})

async function autoDetectApiBaseUrl() {
  if (stored != null) return
  if (apiBaseUrl.value.trim() !== '/api') return

  try {
    await getHealth('/api', { timeoutMs: 1200 })
    return
  } catch {
    // ignore
  }

  const guessed = guessLocalBackendBaseUrl()
  try {
    await getHealth(guessed, { timeoutMs: 1200 })
    apiBaseUrl.value = guessed
  } catch {
    // ignore
  }
}

void autoDetectApiBaseUrl()

export function useApiBaseUrl() {
  return { apiBaseUrl }
}
