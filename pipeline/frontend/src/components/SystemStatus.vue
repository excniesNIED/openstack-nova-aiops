<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface ServiceStatus {
  name: string
  status: 'online' | 'warning' | 'offline'
  latency: number
  uptime: string
}

const services = ref<ServiceStatus[]>([
  { name: 'Kafka 集群', status: 'online', latency: 12, uptime: '99.99%' },
  { name: 'Flink 引擎', status: 'online', latency: 8, uptime: '99.95%' },
  { name: 'Redis 缓存', status: 'online', latency: 3, uptime: '100%' },
  { name: 'PostgreSQL', status: 'online', latency: 15, uptime: '99.98%' },
  { name: 'Elasticsearch', status: 'warning', latency: 45, uptime: '99.87%' },
  { name: 'API Gateway', status: 'online', latency: 5, uptime: '99.99%' },
])

let updateInterval: number | null = null

const updateStatus = () => {
  services.value = services.value.map(s => ({
    ...s,
    latency: Math.max(1, s.latency + Math.floor((Math.random() - 0.5) * 10)),
    status: Math.random() > 0.95 ? 'warning' : s.status === 'warning' && Math.random() > 0.7 ? 'online' : s.status,
  }))
}

onMounted(() => {
  updateInterval = window.setInterval(updateStatus, 3000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
})

const getStatusClass = (status: string) => {
  return {
    online: 'status-online',
    warning: 'status-warning',
    offline: 'status-offline',
  }[status] || 'status-online'
}

const getStatusText = (status: string) => {
  return {
    online: '运行中',
    warning: '警告',
    offline: '离线',
  }[status] || '未知'
}
</script>

<template>
  <div class="system-status">
    <div class="status-header">
      <h3 class="panel-title">服务状态</h3>
      <div class="status-summary">
        <span class="summary-item online">
          <span class="dot"></span>
          {{ services.filter(s => s.status === 'online').length }} 在线
        </span>
        <span class="summary-item warning">
          <span class="dot"></span>
          {{ services.filter(s => s.status === 'warning').length }} 警告
        </span>
        <span class="summary-item offline">
          <span class="dot"></span>
          {{ services.filter(s => s.status === 'offline').length }} 离线
        </span>
      </div>
    </div>
    
    <div class="services-grid">
      <div 
        v-for="service in services" 
        :key="service.name" 
        class="service-card"
        :class="getStatusClass(service.status)"
      >
        <div class="service-indicator">
          <span class="indicator-dot"></span>
        </div>
        <div class="service-info">
          <span class="service-name">{{ service.name }}</span>
          <span class="service-status">{{ getStatusText(service.status) }}</span>
        </div>
        <div class="service-metrics">
          <div class="metric">
            <span class="metric-label">延迟</span>
            <span class="metric-value">{{ service.latency }}ms</span>
          </div>
          <div class="metric">
            <span class="metric-label">可用性</span>
            <span class="metric-value">{{ service.uptime }}</span>
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

.services-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
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
