<script setup lang="ts">
const props = defineProps<{
  currentTime: string
  apiBaseUrl: string
  apiOk: boolean | null
  apiLatencyMs: number | null
  alertsCount: number
  datasetId?: string
  datasetOptions?: Array<{ label: string; value: string }>
  replayRunning?: boolean
  replayPaused?: boolean
  onDatasetChange?: (datasetId: string) => void
  onStartReplay?: () => void
  onPauseReplay?: () => void
  onResumeReplay?: () => void
  onStopReplay?: () => void
  onSwitchReplay?: () => void
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
        <div
          class="logo-icon"
          aria-hidden="true"
        >
          <img
            class="logo-img"
            src="/logo.svg"
            alt=""
          >
        </div>
        <div class="logo-text">
          <h1>OPENSTACK</h1>
          <span>Nova 日志告警看板</span>
        </div>
      </div>
    </div>

    <div class="header-center">
      <div class="status-bar">
        <div
          class="status-item"
          :class="{ online: props.apiOk === true }"
        >
          <span class="status-dot" />
          <span>{{ statusText() }}</span>
        </div>
        <div class="divider" />
        <div class="status-item">
          <span>延迟: </span>
          <span class="highlight">{{ props.apiLatencyMs == null ? '--' : `${props.apiLatencyMs}ms` }}</span>
        </div>
        <div class="divider" />
        <div class="status-item">
          <span>告警数: </span>
          <span class="highlight">{{ props.alertsCount }}</span>
        </div>
      </div>
    </div>

    <div class="header-right">
      <div class="dataset-controls">
        <d-select
          v-if="props.datasetOptions?.length"
          :model-value="props.datasetId"
          class="dataset-select"
          :options="props.datasetOptions"
          @update:model-value="props.onDatasetChange?.(String(Array.isArray($event) ? $event[0] : $event))"
        />
        <div class="dataset-actions">
          <button
            class="icon-btn"
            type="button"
            :disabled="props.replayRunning === true"
            aria-label="Start dataset replay"
            title="Start"
            @click="props.onStartReplay?.()"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
          </button>
          <button
            class="icon-btn"
            type="button"
            :disabled="props.replayRunning !== true"
            aria-label="Pause or resume dataset replay"
            :title="props.replayPaused === true ? 'Resume' : 'Pause'"
            @click="props.replayPaused === true ? props.onResumeReplay?.() : props.onPauseReplay?.()"
          >
            <svg
              v-if="props.replayPaused === true"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
            </svg>
          </button>
          <button
            class="icon-btn"
            type="button"
            :disabled="props.replayRunning !== true"
            aria-label="Stop dataset replay"
            title="Stop"
            @click="props.onStopReplay?.()"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M6 6h12v12H6z" />
            </svg>
          </button>
          <button
            class="icon-btn"
            type="button"
            aria-label="Switch dataset replay"
            title="Switch"
            @click="props.onSwitchReplay?.()"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M7 7h9l-2-2 1.4-1.4L20.8 9l-5.4 5.4L14 13l2-2H7V7zM17 17H8l2 2-1.4 1.4L3.2 15l5.4-5.4L10 11l-2 2h9v4z"
              />
            </svg>
          </button>
        </div>
      </div>
      <div class="time-display">
        <div class="time-label">
          系统时间
        </div>
        <div class="time-value">
          {{ currentTime }}
        </div>
      </div>
      <d-button
        variant="outline"
        class="header-btn"
        @click="props.onOpenSettings?.()"
      >
        <i class="icon icon-setting" />
        设置
      </d-button>
    </div>
  </header>
</template>

<style scoped>
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.25rem;
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
  animation: logoFloat 6s ease-in-out infinite;
}

.logo-img {
  width: 100%;
  height: 100%;
  display: block;
  filter: drop-shadow(0 0 12px rgba(0, 240, 255, 0.35));
}

@keyframes logoFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
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
  gap: 1.1rem;
  padding: 0.45rem 1.1rem;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 20px;
  flex-wrap: wrap;
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

.dataset-controls {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.dataset-select {
  width: 210px;
}

.dashboard-header :deep(.devui-select),
.dashboard-header :deep(.devui-dropdown-origin),
.dashboard-header :deep(.devui-select-input),
.dashboard-header :deep(.devui-select .devui-select-input),
.dashboard-header :deep(.devui-select input) {
  color: var(--text-primary);
}

.dashboard-header :deep(.devui-select .devui-select-input),
.dashboard-header :deep(.devui-select-input),
.dashboard-header :deep(.devui-select input) {
  background: rgba(10, 20, 40, 0.78);
  border-color: rgba(0, 240, 255, 0.22);
}

.dataset-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(0, 240, 255, 0.22);
  background: rgba(10, 20, 40, 0.75);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.icon-btn:hover:not(:disabled) {
  border-color: rgba(0, 240, 255, 0.6);
  color: var(--text-primary);
  background: rgba(0, 240, 255, 0.06);
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.header-btn {
  border-color: var(--border-glow);
  color: var(--text-secondary);
}

.header-btn:hover {
  border-color: rgba(0, 240, 255, 0.6);
  color: var(--text-primary);
  background: rgba(0, 240, 255, 0.06);
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
  height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-color: var(--border-glow);
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.header-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}

@media (max-width: 980px) {
  .dashboard-header {
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .header-center {
    order: 3;
    flex: 0 0 100%;
    justify-content: flex-start;
  }

  .status-bar {
    width: 100%;
    justify-content: space-between;
  }

  .divider {
    display: none;
  }

  .time-display {
    margin-right: 0;
  }

  .dataset-controls {
    order: 2;
    width: 100%;
    justify-content: space-between;
  }

  .dataset-select {
    width: min(360px, 100%);
    flex: 1;
  }
}
</style>
