<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface LogEntry {
  id: number
  time: string
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
}

const logs = ref<LogEntry[]>([
  { id: 1, time: '10:42:15', type: 'success', message: '数据同步完成 - 节点 A12' },
  { id: 2, time: '10:41:58', type: 'info', message: '新任务已分配 - Task #2847' },
  { id: 3, time: '10:41:32', type: 'warning', message: '节点 B07 响应延迟' },
  { id: 4, time: '10:40:45', type: 'success', message: '批处理作业完成' },
  { id: 5, time: '10:40:12', type: 'info', message: '数据流接入 - Stream #156' },
  { id: 6, time: '10:39:28', type: 'error', message: '连接超时 - 节点 C03' },
  { id: 7, time: '10:38:55', type: 'success', message: '缓存刷新完成' },
])

const messages = [
  { type: 'success' as const, message: '数据同步完成' },
  { type: 'info' as const, message: '新任务已分配' },
  { type: 'warning' as const, message: '节点响应延迟' },
  { type: 'success' as const, message: '批处理作业完成' },
  { type: 'info' as const, message: '数据流接入' },
  { type: 'error' as const, message: '连接超时' },
  { type: 'success' as const, message: '缓存刷新完成' },
  { type: 'info' as const, message: '配置更新' },
]

let logId = 8
let updateInterval: number | null = null

const addLog = () => {
  const randomMsg = messages[Math.floor(Math.random() * messages.length)]!
  const newLog: LogEntry = {
    id: logId++,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    type: randomMsg.type,
    message: `${randomMsg.message} - #${Math.floor(Math.random() * 9000) + 1000}`,
  }
  logs.value = [newLog, ...logs.value.slice(0, 6)]
}

onMounted(() => {
  updateInterval = window.setInterval(addLog, 4000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
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
    <h3 class="panel-title">活动日志</h3>
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
</style>
