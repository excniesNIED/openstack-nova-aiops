<script setup lang="ts">
const props = defineProps<{
  currentTime: string
  apiBaseUrl: string
  apiOk: boolean | null
  apiLatencyMs: number | null
  alertsCount: number
  onOpenSettings?: () => void
}>()

const statusText = () => {
  if (props.apiOk === true) return 'API 已连接'
  if (props.apiOk === false) return 'API 离线'
  return 'API 未检测'
}
</script>

<template>
  <header class="dashboard-header">
    <div class="header-left">
      <div class="logo-container">
        <div class="logo-icon">
          <svg viewBox="0 0 100 100" class="logo-svg">
            <polygon points="50,5 95,27.5 95,72.5 50,95 5,72.5 5,27.5" fill="none" stroke="currentColor" stroke-width="2"/>
            <polygon points="50,20 80,35 80,65 50,80 20,65 20,35" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="50" cy="50" r="15" fill="none" stroke="currentColor" stroke-width="2"/>
            <circle cx="50" cy="50" r="5" fill="currentColor"/>
          </svg>
        </div>
        <div class="logo-text">
          <h1>OPENSTACK</h1>
          <span>Nova 日志告警看板（AIOps Demo）</span>
        </div>
      </div>
    </div>

    <div class="header-center">
      <div class="status-bar">
        <div class="status-item" :class="{ online: props.apiOk === true }">
          <span class="status-dot"></span>
          <span>{{ statusText() }}</span>
        </div>
        <div class="divider"></div>
        <div class="status-item">
          <span>延迟: </span>
          <span class="highlight">{{ props.apiLatencyMs == null ? '--' : `${props.apiLatencyMs}ms` }}</span>
        </div>
        <div class="divider"></div>
        <div class="status-item">
          <span>告警数: </span>
          <span class="highlight">{{ props.alertsCount }}</span>
        </div>
      </div>
    </div>

    <div class="header-right">
      <div class="time-display">
        <div class="time-label">系统时间</div>
        <div class="time-value">{{ currentTime }}</div>
      </div>
      <d-button variant="outline" class="header-btn" @click="props.onOpenSettings?.()">
        <i class="icon icon-setting"></i>
      </d-button>
      <d-button variant="outline" class="header-btn">
        <i class="icon icon-notification"></i>
      </d-button>
    </div>
  </header>
</template>

<style scoped>
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: linear-gradient(180deg, rgba(10, 20, 40, 0.95) 0%, rgba(10, 20, 40, 0.8) 100%);
  border-bottom: 1px solid var(--border-glow);
  position: relative;
}

.dashboard-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--primary-color), var(--secondary-color), var(--primary-color), transparent);
  animation: headerGlow 3s ease-in-out infinite;
}

@keyframes headerGlow {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-icon {
  width: 50px;
  height: 50px;
  color: var(--primary-color);
  animation: logoRotate 10s linear infinite;
}

.logo-svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 10px var(--primary-color));
}

@keyframes logoRotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.logo-text h1 {
  font-size: 1.8rem;
  font-weight: 700;
  letter-spacing: 4px;
  background: var(--gradient-cyber);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.logo-text span {
  font-size: 0.75rem;
  color: var(--text-secondary);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.5rem 1.5rem;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.status-item.online {
  color: var(--accent-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-color);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 0 10px var(--accent-color);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}

.highlight {
  color: var(--primary-color);
  font-weight: 600;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--border-glow);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.time-display {
  text-align: right;
  margin-right: 1rem;
}

.time-label {
  font-size: 0.7rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.time-value {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--primary-color);
  font-family: 'Courier New', monospace;
  text-shadow: 0 0 10px var(--primary-color);
}

.header-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-color: var(--border-glow);
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.header-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}
</style>
