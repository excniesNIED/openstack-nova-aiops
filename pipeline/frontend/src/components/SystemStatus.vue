<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DependencyCheck, HealthResponse } from '@/api/types'

type ServiceStatusKind = 'online' | 'warning' | 'offline' | 'unknown'

const props = defineProps<{
  apiBaseUrl: string
  apiOk: boolean | null
  apiLatencyMs: number | null
  health: HealthResponse | null
  lastUpdatedIso: string | null
  error: string | null
}>()

type ServiceItem = {
  key: string
  name: string
  status: ServiceStatusKind
  rawStatus?: string
  latencyMs?: number | null
  availability: string
  endpoint?: string | null
}

const showOptional = ref(false)

const normalizeDep = (
  dep?: DependencyCheck,
): { kind: ServiceStatusKind; availability: string; latencyMs: number | null; rawStatus: string; endpoint: string | null } => {
  const raw = (dep?.status ?? 'unknown') as string
  const latencyMs = dep?.latency_ms ?? null
  const endpoint = dep?.host && dep?.port ? `${dep.host}:${dep.port}` : null

  if (raw === 'up') return { kind: 'online', availability: 'OK', latencyMs, rawStatus: raw, endpoint }
  if (raw === 'down') return { kind: 'offline', availability: 'DOWN', latencyMs, rawStatus: raw, endpoint }
  if (raw === 'not_configured') return { kind: 'unknown', availability: 'N/A', latencyMs, rawStatus: raw, endpoint: null }
  if (raw === 'disabled') return { kind: 'unknown', availability: 'N/A', latencyMs, rawStatus: raw, endpoint }
  return { kind: 'unknown', availability: '--', latencyMs, rawStatus: raw, endpoint }
}

const services = computed(() => {
  const apiStatus: ServiceStatusKind =
    props.apiOk === true ? (props.apiLatencyMs != null && props.apiLatencyMs > 1000 ? 'warning' : 'online') : props.apiOk === false ? 'offline' : 'unknown'
  const apiLatency = props.apiLatencyMs ?? null
  const apiUptime = props.apiOk === true ? 'OK' : props.apiOk === false ? 'DOWN' : '--'

  const deps = props.health?.dependencies ?? {}
  const kafka = normalizeDep(deps.kafka)
  const spark = normalizeDep(deps.spark)
  const database = normalizeDep(deps.database)
  const hdfs = normalizeDep(deps.hdfs)
  const hbase = normalizeDep(deps.hbase)
  const hive = normalizeDep(deps.hive)

  const dbDriver = deps.database?.driver ?? ''
  const dbName = dbDriver.includes('mysql') ? 'MariaDB' : dbDriver.includes('sqlite') ? 'SQLite' : 'Database'

  return [
    {
      key: 'api',
      name: 'FastAPI Backend',
      status: apiStatus,
      latencyMs: apiLatency,
      availability: apiUptime,
      endpoint: props.apiBaseUrl,
    },
    { key: 'kafka', name: 'Kafka', status: kafka.kind, rawStatus: kafka.rawStatus, latencyMs: kafka.latencyMs, availability: kafka.availability, endpoint: kafka.endpoint },
    { key: 'spark', name: 'Spark', status: spark.kind, rawStatus: spark.rawStatus, latencyMs: spark.latencyMs, availability: spark.availability, endpoint: spark.endpoint },
    { key: 'db', name: dbName, status: database.kind, rawStatus: database.rawStatus, latencyMs: database.latencyMs, availability: database.availability, endpoint: database.endpoint },
    { key: 'hdfs', name: 'HDFS', status: hdfs.kind, rawStatus: hdfs.rawStatus, latencyMs: hdfs.latencyMs, availability: hdfs.availability, endpoint: hdfs.endpoint },
    { key: 'hbase', name: 'HBase', status: hbase.kind, rawStatus: hbase.rawStatus, latencyMs: hbase.latencyMs, availability: hbase.availability, endpoint: hbase.endpoint },
    { key: 'hive', name: 'Hive', status: hive.kind, rawStatus: hive.rawStatus, latencyMs: hive.latencyMs, availability: hive.availability, endpoint: hive.endpoint },
  ] satisfies ServiceItem[]
})

const isOptional = (s: ServiceItem) => s.rawStatus === 'not_configured' || s.rawStatus === 'disabled'

const optionalCount = computed(() => services.value.filter(isOptional).length)

const visibleServices = computed(() => {
  if (showOptional.value) return services.value
  return services.value.filter((s) => !isOptional(s))
})

const getStatusClass = (status: string) => {
  return {
    online: 'status-online',
    warning: 'status-warning',
    offline: 'status-offline',
    unknown: 'status-unknown',
  }[status] || 'status-online'
}

const getStatusText = (status: ServiceStatusKind, rawStatus?: string) => {
  if (rawStatus === 'not_configured') return '未配置'
  if (rawStatus === 'disabled') return '未启用'
  return { online: '运行中', warning: '警告', offline: '离线', unknown: '未知' }[status] || '未知'
}
</script>

<template>
  <div class="system-status">
    <div class="status-header">
      <h3 class="panel-title">
        服务状态
      </h3>
      <div class="status-summary">
        <span class="summary-item online">
          <span class="dot" />
          {{ visibleServices.filter(s => s.status === 'online').length }} 在线
        </span>
        <span class="summary-item warning">
          <span class="dot" />
          {{ visibleServices.filter(s => s.status === 'warning').length }} 警告
        </span>
        <span class="summary-item offline">
          <span class="dot" />
          {{ visibleServices.filter(s => s.status === 'offline').length }} 离线
        </span>
        <span class="summary-item unknown">
          <span class="dot" />
          {{ visibleServices.filter(s => s.status === 'unknown').length }} 未检测
        </span>
      </div>
    </div>

    <div class="meta">
      <div class="mono">
        API: {{ props.apiBaseUrl }}
      </div>
      <div class="mono">
        Last: {{ props.lastUpdatedIso ? new Date(props.lastUpdatedIso).toLocaleTimeString('zh-CN') : '--' }}
      </div>
      <button
        v-if="optionalCount > 0"
        type="button"
        class="toggle"
        @click="showOptional = !showOptional"
      >
        {{ showOptional ? '收起' : `查看更多（${optionalCount}项未启用）` }}
      </button>
      <div
        v-if="props.error"
        class="mono err"
      >
        {{ props.error }}
      </div>
    </div>
    
    <div class="services-grid">
      <div
        v-for="service in visibleServices"
        :key="service.key"
        class="service-card"
        :class="getStatusClass(service.status)"
      >
        <div class="service-indicator">
          <span class="indicator-dot" />
        </div>
        <div class="service-info">
          <span class="service-name">{{ service.name }}</span>
          <span class="service-status">{{ getStatusText(service.status, service.rawStatus) }}</span>
          <span
            v-if="service.endpoint"
            class="service-endpoint mono"
            :title="service.endpoint"
          >
            {{ service.endpoint }}
          </span>
        </div>
        <div class="service-metrics">
          <div class="metric">
            <span class="metric-label">延迟</span>
            <span class="metric-value">{{ service.latencyMs != null ? `${service.latencyMs}ms` : '—' }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">可用性</span>
            <span class="metric-value">{{ service.availability }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.system-status {
  background: var(--bg-card);
  border: 1px solid var(--border-glow);
  border-radius: 12px;
  padding: 1rem;
  position: relative;
  overflow: hidden;
}

.system-status::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: var(--gradient-cyber);
  animation: borderScan 5s linear infinite;
}

@keyframes borderScan {
  0% { left: -100%; }
  100% { left: 100%; }
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.status-summary {
  display: flex;
  gap: 1.5rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.summary-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.summary-item.online .dot {
  background: var(--accent-color);
  box-shadow: 0 0 8px var(--accent-color);
}

.summary-item.warning .dot {
  background: #ffaa00;
  box-shadow: 0 0 8px #ffaa00;
}

.summary-item.offline .dot {
  background: #ff4444;
  box-shadow: 0 0 8px #ff4444;
}

.summary-item.unknown .dot {
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.15);
}

.meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.toggle {
  margin-left: auto;
  padding: 0;
  border: none;
  background: transparent;
  color: rgba(224, 224, 255, 0.8);
  cursor: pointer;
  font-size: 0.8rem;
}

.toggle:hover {
  color: var(--text-primary);
  text-decoration: underline;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.err {
  color: #ff4444;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.service-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: all 0.3s ease;
}

.service-card:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: translateY(-2px);
}

.service-card.status-online {
  border-left: 3px solid var(--accent-color);
}

.service-card.status-warning {
  border-left: 3px solid #ffaa00;
}

.service-card.status-offline {
  border-left: 3px solid #ff4444;
}

.service-card.status-unknown {
  border-left: 3px solid rgba(255, 255, 255, 0.25);
}

.service-indicator {
  display: flex;
  align-items: center;
}

.indicator-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-online .indicator-dot {
  background: var(--accent-color);
  box-shadow: 0 0 10px var(--accent-color);
}

.status-warning .indicator-dot {
  background: #ffaa00;
  box-shadow: 0 0 10px #ffaa00;
}

.status-offline .indicator-dot {
  background: #ff4444;
  box-shadow: 0 0 10px #ff4444;
}

.status-unknown .indicator-dot {
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.15);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.service-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.service-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.service-status {
  font-size: 0.7rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.service-endpoint {
  font-size: 0.7rem;
  color: rgba(224, 224, 255, 0.65);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.service-metrics {
  display: flex;
  gap: 1rem;
  margin-top: auto;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 0.65rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.metric-value {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--primary-color);
  font-family: 'Courier New', monospace;
}

@media (max-width: 1200px) {
  .services-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .services-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .status-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
}
</style>
