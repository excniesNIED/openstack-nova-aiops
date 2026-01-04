import { ref, watch } from 'vue'

const STORAGE_KEY = 'pipeline.apiBaseUrl'

const defaultBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
const apiBaseUrl = ref<string>(localStorage.getItem(STORAGE_KEY) ?? defaultBaseUrl)

watch(apiBaseUrl, (v) => {
  localStorage.setItem(STORAGE_KEY, v)
})

export function useApiBaseUrl() {
  return { apiBaseUrl }
}

