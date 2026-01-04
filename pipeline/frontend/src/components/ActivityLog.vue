<script setup lang="ts">
import { computed } from 'vue'
import type { Alert } from '@/api/types'

type LogType = 'info' | 'success' | 'warning' | 'error'

const props = defineProps<{
  alerts: Alert[]
}>()

const logs = computed(() => {
  return props.alerts.slice(0, 7).map((a) => {
    const t = new Date(a.created_at)
    const time = Number.isNaN(t.getTime())
      ? a.created_at
      : t.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    const type: LogType = a.severity === 'P1' ? 'error' : a.severity === 'P2' ? 'warning' : 'info'
    const message = `[${a.severity}] ${a.pred_class} @ ${a.entity_key} (p=${(a.prob * 100).toFixed(1)}%)`
    return { id: a.alert_id, time, type, message }
  })
})

const getTypeClass = (type: string) => {
  return {
    info: 'log-info',
    success: 'log-success',
    warning: 'log-warning',
    error: 'log-error',
  }[type] || 'log-info'
}

const getTypeIcon = (type: string) => {
  return {
    info: 'ℹ',
    success: '✓',
    warning: '⚠',
    error: '✕',
  }[type] || 'ℹ'
}
</script>

<template>
  <div class="activity-log">
    <h3 class="panel-title">
      最新告警（活动流）
    </h3>
    <div class="log-list">
      <TransitionGroup name="log">
        <div 
          v-for="log in logs"
          :key="log.id"
          class="log-entry"
          :class="getTypeClass(log.type)"
        >
          <span class="log-icon">{{ getTypeIcon(log.type) }}</span>
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </TransitionGroup>
      <div
        v-if="logs.length === 0"
        class="empty"
      >
        暂无告警
      </div>
    </div>
  </div>
</template>

<style scoped>
.activity-log {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 0.75rem;
  padding-left: 0.5rem;
  flex-shrink: 0;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  border-left: 3px solid;
  font-size: 0.8rem;
  transition: all 0.3s ease;
}

.log-entry:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 0.7rem;
  flex-shrink: 0;
}

.log-time {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.log-message {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-info {
  border-color: var(--primary-color);
}
.log-info .log-icon {
  background: rgba(0, 240, 255, 0.2);
  color: var(--primary-color);
}

.log-success {
  border-color: var(--accent-color);
}
.log-success .log-icon {
  background: rgba(0, 255, 136, 0.2);
  color: var(--accent-color);
}

.log-warning {
  border-color: #ffaa00;
}
.log-warning .log-icon {
  background: rgba(255, 170, 0, 0.2);
  color: #ffaa00;
}

.log-error {
  border-color: #ff4444;
}
.log-error .log-icon {
  background: rgba(255, 68, 68, 0.2);
  color: #ff4444;
}

/* Transition animations */
.log-enter-active {
  transition: all 0.4s ease;
}

.log-leave-active {
  transition: all 0.3s ease;
}

.log-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.log-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.log-move {
  transition: transform 0.3s ease;
}

.empty {
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 0.5rem 0.75rem;
}
</style>
