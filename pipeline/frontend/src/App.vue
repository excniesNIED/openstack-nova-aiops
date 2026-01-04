<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import DashboardHeader from './components/DashboardHeader.vue'
import StatsCard from './components/StatsCard.vue'
import RadarChart from './components/RadarChart.vue'
import DonutChart from './components/DonutChart.vue'
import LineChart from './components/LineChart.vue'
import GaugePanel from './components/GaugePanel.vue'
import ActivityLog from './components/ActivityLog.vue'
import SystemStatus from './components/SystemStatus.vue'
import AlertsTable from './components/AlertsTable.vue'
import { useApiBaseUrl } from './composables/useApiBaseUrl'
import { usePipelineAlerts } from './composables/usePipelineAlerts'

const currentTime = ref(new Date().toLocaleTimeString())
let timeInterval: number | null = null

const { apiBaseUrl } = useApiBaseUrl()
const { alerts, loading, error, apiOk, apiLatencyMs, lastUpdatedIso, refresh } = usePipelineAlerts(apiBaseUrl, {
  pollMs: 3000,
  limit: 200,
})

const settingsOpen = ref(false)
const apiBaseUrlDraft = ref(apiBaseUrl.value)

const openSettings = () => {
  apiBaseUrlDraft.value = apiBaseUrl.value
  settingsOpen.value = true
}

const saveSettings = () => {
  apiBaseUrl.value = apiBaseUrlDraft.value.trim() || apiBaseUrl.value
  settingsOpen.value = false
}

const countBySeverity = computed(() => {
  const counts = { P1: 0, P2: 0, P3: 0 }
  for (const a of alerts.value) {
    if (a.severity === 'P1') counts.P1++
    else if (a.severity === 'P2') counts.P2++
    else counts.P3++
  }
  return counts
})

const kpiCards = computed(() => {
  const c = countBySeverity.value
  const total = alerts.value.length
  return [
    { title: '告警总数', value: String(total), change: '+0', icon: 'icon icon-notification', color: 'cyan' as const },
    { title: 'P1 告警', value: String(c.P1), change: '+0', icon: 'icon icon-error', color: 'magenta' as const },
    { title: 'P2 告警', value: String(c.P2), change: '+0', icon: 'icon icon-warning', color: 'orange' as const },
    { title: 'P3/其他', value: String(c.P3), change: '+0', icon: 'icon icon-success', color: 'green' as const },
  ]
})

const donutItems = computed(() => {
  const c = countBySeverity.value
  return [
    { name: 'P1', value: c.P1, color: '#ff4444' },
    { name: 'P2', value: c.P2, color: '#ffaa00' },
    { name: 'P3', value: c.P3, color: '#00ff88' },
  ]
})

const trend = computed(() => {
  const minutes = 15
  const now = Date.now()
  const buckets = Array.from({ length: minutes }, (_, i) => now - (minutes - 1 - i) * 60_000)
  const labels = buckets.map((ts) => new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }))

  const p1 = Array<number>(minutes).fill(0)
  const p2 = Array<number>(minutes).fill(0)
  const p3 = Array<number>(minutes).fill(0)

  for (const a of alerts.value) {
    const t = new Date(a.created_at).getTime()
    if (Number.isNaN(t)) continue
    const deltaMs = now - t
    if (deltaMs < 0 || deltaMs > minutes * 60_000) continue
    const idx = minutes - 1 - Math.floor(deltaMs / 60_000)
    if (idx < 0 || idx >= minutes) continue
    if (a.severity === 'P1') p1[idx]++
    else if (a.severity === 'P2') p2[idx]++
    else p3[idx]++
  }

  return {
    labels,
    series: [
      { name: 'P1', color: '#ff4444', values: p1 },
      { name: 'P2', color: '#ffaa00', values: p2 },
      { name: 'P3', color: '#00ff88', values: p3 },
    ],
  }
})

const latestAlert = computed(() => alerts.value[0] ?? null)

const radar = computed(() => {
  const a = latestAlert.value
  const counts = a?.evidence?.counts
  const total = counts?.total_records ?? 0
  const errorRatio = Number(a?.evidence?.error_ratio ?? 0)
  const warnRatio = total > 0 ? (counts?.warn_cnt ?? 0) / total : 0
  const uniqueTemplates = Object.keys(a?.evidence?.template_counts ?? {}).length
  const uniqueKeywords = Object.keys(a?.evidence?.keyword_counts ?? {}).length
  const prob = a?.prob ?? 0

  const clamp = (v: number) => Math.max(0, Math.min(100, v))
  const scaleLog = (v: number, max: number) => clamp((Math.log1p(Math.max(0, v)) / Math.log1p(max)) * 100)

  const values = [
    clamp(errorRatio * 100),
    clamp(warnRatio * 100),
    clamp(uniqueTemplates * 10),
    clamp(uniqueKeywords * 20),
    clamp(prob * 100),
    scaleLog(total, 200),
  ]

  return {
    categories: ['ERROR%', 'WARN%', 'Templates', 'Keywords', 'Prob%', 'Records'],
    current: values,
    baseline: [10, 10, 20, 20, 50, 40],
  }
})

const gauges = computed(() => {
  const c = countBySeverity.value
  const total = alerts.value.length || 1
  const healthScore = Math.max(0, Math.min(100, 100 - (c.P1 / total) * 80 - (c.P2 / total) * 40))
  const pressure = Math.max(0, Math.min(100, ((c.P1 * 3 + c.P2 * 2 + c.P3) / total) * 20))
  const confidence = Math.max(0, Math.min(100, (latestAlert.value?.prob ?? 0) * 100))
  return [
    { name: '健康度', value: healthScore, color: '#00f0ff' },
    { name: '压力', value: pressure, color: '#ff00ff' },
    { name: '置信度', value: confidence, color: '#00ff88' },
  ]
})

onMounted(() => {
  timeInterval = window.setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<template>
  <div class="dashboard">
    <DashboardHeader
      :current-time="currentTime"
      :api-base-url="apiBaseUrl"
      :api-ok="apiOk"
      :api-latency-ms="apiLatencyMs"
      :alerts-count="alerts.length"
      :on-open-settings="openSettings"
    />
    
    <main class="dashboard-content">
      <!-- Stats Row -->
      <section class="stats-row">
        <StatsCard
          v-for="c in kpiCards"
          :key="c.title"
          :title="c.title"
          :value="c.value"
          :change="c.change"
          :icon="c.icon"
          :color="c.color"
        />
      </section>

      <!-- Main Charts Row -->
      <section class="charts-row">
        <div class="chart-container large">
          <LineChart :labels="trend.labels" :series="trend.series" />
        </div>
        <div class="chart-container">
          <RadarChart :categories="radar.categories" :current="radar.current" :baseline="radar.baseline" />
        </div>
      </section>

      <!-- Bottom Row -->
      <section class="bottom-row">
        <div class="chart-container">
          <DonutChart :items="donutItems" />
        </div>
        <div class="chart-container">
          <GaugePanel title="系统健康" :gauges="gauges" />
        </div>
        <div class="chart-container">
          <ActivityLog :alerts="alerts" />
        </div>
      </section>

      <!-- Alerts Table -->
      <section class="alerts-row">
        <div class="chart-container">
          <div class="alerts-actions">
            <d-button size="sm" variant="outline" :loading="loading" @click="refresh">手动刷新</d-button>
            <d-button size="sm" variant="text" @click="openSettings">API 设置</d-button>
          </div>
          <AlertsTable :alerts="alerts" :api-base-url="apiBaseUrl" :loading="loading" :error="error" />
        </div>
      </section>

      <!-- System Status -->
      <section class="status-row">
        <SystemStatus
          :api-base-url="apiBaseUrl"
          :api-ok="apiOk"
          :api-latency-ms="apiLatencyMs"
          :last-updated-iso="lastUpdatedIso"
          :error="error"
        />
      </section>
    </main>

    <d-modal v-model="settingsOpen" title="API 设置" :close-on-click-overlay="true">
      <div class="settings">
        <div class="settings-row">
          <span class="label">API Base URL</span>
          <d-input v-model="apiBaseUrlDraft" placeholder="/api 或 http://localhost:8000" />
        </div>
        <div class="settings-hint">
          默认使用 Vite 代理：<span class="mono">/api</span> → <span class="mono">http://localhost:8000</span>
        </div>
        <div class="settings-actions">
          <d-button variant="outline" @click="settingsOpen = false">取消</d-button>
          <d-button color="primary" variant="solid" @click="saveSettings">保存</d-button>
        </div>
      </div>
    </d-modal>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.dashboard-content {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  min-height: 350px;
}

.bottom-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  min-height: 300px;
}

.alerts-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

.alerts-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.status-row {
  margin-top: auto;
}

.chart-container {
  background: var(--bg-card);
  border: 1px solid var(--border-glow);
  border-radius: 12px;
  padding: 1rem;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.chart-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: var(--gradient-cyber);
  animation: borderScan 4s linear infinite;
}

.chart-container:hover {
  border-color: var(--primary-color);
  box-shadow: 
    0 0 20px rgba(0, 240, 255, 0.15),
    inset 0 0 30px rgba(0, 240, 255, 0.03);
}

.chart-container.large {
  grid-column: span 1;
}

@keyframes borderScan {
  0% { left: -100%; }
  100% { left: 100%; }
}

@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
  
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}

.settings {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.settings-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.settings-row .label {
  width: 110px;
  color: var(--text-secondary);
  font-size: 0.85rem;
  flex-shrink: 0;
}

.settings-hint {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
