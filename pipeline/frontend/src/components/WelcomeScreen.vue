<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getControlStatus, listControlLogs, startReplay, stopReplay } from '@/api/pipeline'
import type { ControlStatus } from '@/api/types'

const props = defineProps<{
  apiBaseUrl: string
  onOpenSettings?: () => void
}>()

const emit = defineEmits<{
  (e: 'entered'): void
}>()

const statusLoading = ref(false)
const statusError = ref<string | null>(null)
const status = ref<ControlStatus | null>(null)

const logsLoading = ref(false)
const logs = ref<Record<string, string>>({})

const datasetOptions = [
  { value: '', label: '不选择（自定义）', defaultLog: '' },
  { value: 'sample', label: '示例（sample）', defaultLog: 'openstack-nova-sample.log' },
  { value: 'normal', label: '正常创建（normal）', defaultLog: 'openstack-nova-normal-vm-create.log' },
  { value: 'fault1', label: '创建后立即销毁（fault1）', defaultLog: 'openstack-vm-destroy-immediately-after-create.log' },
  { value: 'fault2', label: 'DHCP 关闭（fault2）', defaultLog: 'openstack-nova-dhcpoff.log' },
  { value: 'fault3', label: '创建后 undefine（fault3）', defaultLog: 'openstack-nova-undefine-vm-after-create.log' },
]

const datasetId = ref(window.localStorage.getItem('replay.datasetId') ?? datasetOptions[1]!.value)
const logName = ref(window.localStorage.getItem('replay.logName') ?? datasetOptions[1]!.defaultLog)
const rate = ref<number>(50)
const loop = ref<boolean>(false)
const maxRecords = ref<number>(0)

const running = computed(() => status.value?.running === true)
const lastError = computed(() => status.value?.last_error ?? null)

const refresh = async () => {
  statusLoading.value = true
  statusError.value = null
  try {
    status.value = await getControlStatus(props.apiBaseUrl, { timeoutMs: 8000 })
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : String(e)
  } finally {
    statusLoading.value = false
  }
}

const loadLogs = async () => {
  logsLoading.value = true
  try {
    logs.value = await listControlLogs(props.apiBaseUrl, { timeoutMs: 8000 })
  } catch {
    logs.value = {}
  } finally {
    logsLoading.value = false
  }
}

const onDatasetChange = (v: string | number | (string | number)[]) => {
  const id = String(Array.isArray(v) ? v[0] : v)
  datasetId.value = id
  const opt = datasetOptions.find((o) => o.value === id)
  if (opt) logName.value = opt.defaultLog
  window.localStorage.setItem('replay.datasetId', datasetId.value)
  window.localStorage.setItem('replay.logName', logName.value)
}

const starting = ref(false)
const startNow = async () => {
  starting.value = true
  statusError.value = null
  try {
    status.value = await startReplay(props.apiBaseUrl, {
      dataset_id: datasetId.value || 'custom',
      log_name: logName.value.trim(),
      rate: Number.isFinite(rate.value) ? rate.value : 50,
      loop: loop.value,
      max_records: maxRecords.value,
    })
    window.localStorage.setItem('replay.datasetId', datasetId.value)
    window.localStorage.setItem('replay.logName', logName.value)
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : String(e)
  } finally {
    starting.value = false
  }
}

const stopping = ref(false)
const stopNow = async () => {
  stopping.value = true
  statusError.value = null
  try {
    status.value = await stopReplay(props.apiBaseUrl)
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : String(e)
  } finally {
    stopping.value = false
  }
}

onMounted(async () => {
  await Promise.all([refresh(), loadLogs()])
})
</script>

<template>
  <div class="welcome">
    <div class="topbar">
      <div class="brand">
        <img
          class="brand-logo"
          src="/logo.svg"
          alt="logo"
        >
        <div class="brand-text">
          <div class="title">
            OpenStack AIOps Pipeline
          </div>
          <div class="subtitle">
            点击开始后，后端回放日志 → Kafka → Spark → 在线推理 → 告警看板
          </div>
        </div>
      </div>
      <d-button
        variant="outline"
        class="settings-btn"
        @click="props.onOpenSettings?.()"
      >
        <i class="icon icon-setting" />
        API 设置
      </d-button>
    </div>

    <div class="grid">
      <div class="panel cyber-card">
        <div class="panel-header">
          <h2 class="panel-title">
            启动回放
          </h2>
          <div class="panel-meta">
            <d-tag
              v-if="running"
              type="success"
              size="sm"
            >
              回放运行中
            </d-tag>
            <d-tag
              v-else
              type="primary"
              size="sm"
            >
              未启动
            </d-tag>
            <d-button
              size="sm"
              variant="text"
              :loading="statusLoading"
              @click="refresh"
            >
              刷新
            </d-button>
          </div>
        </div>

        <div class="form">
          <div class="row">
            <div class="label">
              数据集
            </div>
            <d-select
              :model-value="datasetId"
              style="width: 100%"
              :options="datasetOptions.map((o) => ({ label: o.label, value: o.value }))"
              @update:model-value="onDatasetChange"
            />
          </div>

          <div class="row">
            <div class="label">
              日志文件
            </div>
            <d-select
              v-if="Object.keys(logs).length"
              v-model="logName"
              style="width: 100%"
              :loading="logsLoading"
              :options="Object.keys(logs).map((k) => ({ label: k, value: k }))"
            />
            <d-input
              v-else
              v-model="logName"
              style="width: 100%"
              placeholder="例如 openstack-nova-sample.log"
            />
          </div>

          <div class="row">
            <div class="label">
              速率
            </div>
            <div class="inline">
              <d-input-number
                v-model="rate"
                :min="0"
                :max="2000"
                :step="10"
                style="width: 160px"
              />
              <span class="hint mono">records/s（0=尽快回放）</span>
            </div>
          </div>

          <div class="row">
            <div class="label">
              循环
            </div>
            <div class="inline">
              <d-switch v-model="loop" />
              <span class="hint">结束后从头回放</span>
            </div>
          </div>

          <div class="row">
            <div class="label">
              上限
            </div>
            <div class="inline">
              <d-input-number
                v-model="maxRecords"
                :min="0"
                :max="2000000"
                :step="1000"
                style="width: 160px"
              />
              <span class="hint mono">0=不限制</span>
            </div>
          </div>
        </div>

        <div
          v-if="statusError || lastError"
          class="error"
        >
          <d-tag
            type="danger"
            size="sm"
          >
            启动失败
          </d-tag>
          <div class="mono">
            {{ statusError || lastError }}
          </div>
        </div>

        <div class="actions">
          <d-button
            color="primary"
            variant="solid"
            size="md"
            :loading="starting"
            :disabled="running || !logName.trim()"
            @click="startNow"
          >
            开始
          </d-button>
          <d-button
            variant="outline"
            size="md"
            :loading="stopping"
            :disabled="!running"
            @click="stopNow"
          >
            停止
          </d-button>
          <d-button
            variant="text"
            size="md"
            :disabled="!running"
            @click="emit('entered')"
          >
            进入看板
          </d-button>
        </div>
      </div>

      <div class="panel cyber-card">
        <div class="panel-header">
          <h2 class="panel-title">
            运行状态
          </h2>
        </div>

        <div class="status">
          <div class="kv">
            <span class="k">API Base</span><span class="v mono">{{ props.apiBaseUrl || '/api' }}</span>
          </div>
          <div class="kv">
            <span class="k">回放进度</span><span class="v mono">{{ status?.sent_records ?? 0 }}</span>
          </div>
          <div class="kv">
            <span class="k">日志</span>
            <span class="v mono">{{ status?.log_path ?? '—' }}</span>
          </div>
          <div class="kv">
            <span class="k">开始时间</span><span class="v mono">{{ status?.started_at ?? '—' }}</span>
          </div>
          <div class="kv">
            <span class="k">结束时间</span><span class="v mono">{{ status?.finished_at ?? '—' }}</span>
          </div>
        </div>

        <div class="tips">
          <div class="tip-title">
            提示
          </div>
          <ul>
            <li>需要先启动 Spark Streaming（raw→features），否则不会产生告警。</li>
            <li>回放只是写入 Kafka：`openstack.raw`，推理告警来自 `openstack.features`。</li>
            <li>建议演示速率 30～200 records/s，避免“瞬间读完”。</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: clamp(1rem, 2vw, 1.5rem);
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(180deg, rgba(10, 20, 40, 0.95) 0%, rgba(10, 20, 40, 0.8) 100%);
  border: 1px solid var(--border-glow);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.brand-logo {
  width: 52px;
  height: 52px;
  filter: drop-shadow(0 0 12px rgba(0, 240, 255, 0.35));
}

.brand-text .title {
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  background: var(--gradient-cyber);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-text .subtitle {
  margin-top: 0.25rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.45;
  max-width: 72ch;
}

.settings-btn {
  border-color: var(--border-glow);
  color: var(--text-secondary);
}

.welcome :deep(.devui-input),
.welcome :deep(.devui-select),
.welcome :deep(.devui-input-number),
.welcome :deep(.devui-dropdown-origin),
.welcome :deep(.devui-switch) {
  color: var(--text-primary);
}

.welcome :deep(.devui-input__wrapper),
.welcome :deep(.devui-select .devui-select-input),
.welcome :deep(.devui-input-number),
.welcome :deep(.devui-dropdown-origin),
.welcome :deep(.devui-select-input),
.welcome :deep(.devui-input input),
.welcome :deep(.devui-input-number input),
.welcome :deep(.devui-select input) {
  background: rgba(10, 20, 40, 0.92);
  border-color: rgba(0, 240, 255, 0.22);
}

.welcome :deep(.devui-input input::placeholder),
.welcome :deep(.devui-input-number input::placeholder),
.welcome :deep(.devui-select input::placeholder) {
  color: rgba(224, 224, 255, 0.55);
}

.welcome :deep(.devui-tag),
.welcome :deep(.devui-tag-primary),
.welcome :deep(.devui-tag-success),
.welcome :deep(.devui-tag-danger) {
  border-color: rgba(0, 240, 255, 0.22);
}

.grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
  gap: 1.1rem;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.panel-title {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.35;
  color: var(--primary-color);
  letter-spacing: 0.06em;
}

.panel-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.row {
  display: grid;
  grid-template-columns: minmax(110px, 132px) minmax(0, 1fr);
  align-items: start;
  gap: 0.9rem;
}

.label {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.35;
  padding-top: 0.35rem;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.inline {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.hint {
  color: var(--text-secondary);
  font-size: 0.82rem;
  line-height: 1.5;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.error {
  border: 1px solid rgba(255, 68, 68, 0.35);
  background: rgba(255, 68, 68, 0.08);
  padding: 0.75rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.actions {
  margin-top: 0.35rem;
  display: flex;
  gap: 0.9rem;
  flex-wrap: wrap;
}

.welcome :deep(.devui-btn),
.welcome :deep(.devui-btn-outline),
.welcome :deep(.devui-btn-text),
.welcome :deep(.devui-btn-primary) {
  color: var(--text-primary);
}

.welcome :deep(.devui-btn-primary) {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.9), rgba(0, 240, 255, 0.6));
  border-color: rgba(0, 240, 255, 0.65);
  box-shadow: 0 0 18px rgba(0, 240, 255, 0.18);
}

.welcome :deep(.devui-btn-primary:hover:not(:disabled)) {
  background: linear-gradient(135deg, rgba(0, 240, 255, 1), rgba(0, 240, 255, 0.7));
  border-color: rgba(0, 240, 255, 0.85);
}

.welcome :deep(.devui-btn:disabled),
.welcome :deep(.devui-btn-primary:disabled),
.welcome :deep(.devui-btn-outline:disabled),
.welcome :deep(.devui-btn-text:disabled) {
  background: rgba(10, 20, 40, 0.45);
  border-color: rgba(0, 240, 255, 0.14);
  color: rgba(224, 224, 255, 0.5);
  box-shadow: none;
}

.welcome :deep(.devui-btn-outline) {
  background: rgba(10, 20, 40, 0.55);
  border-color: rgba(0, 240, 255, 0.28);
}

.welcome :deep(.devui-btn-text) {
  color: rgba(224, 224, 255, 0.9);
}

.status {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.7rem;
}

.kv {
  display: grid;
  grid-template-columns: minmax(96px, 120px) minmax(0, 1fr);
  align-items: start;
  gap: 0.75rem;
  padding: 0.5rem 0.65rem;
  background: rgba(0, 240, 255, 0.04);
  border: 1px solid rgba(0, 240, 255, 0.12);
  border-radius: 10px;
}

.k {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.3;
  white-space: nowrap;
}

.v {
  color: var(--text-primary);
  font-size: 0.85rem;
  line-height: 1.45;
  min-width: 0;
  word-break: break-word;
}

.tips {
  margin-top: 0.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 0.75rem;
  color: var(--text-secondary);
  font-size: 0.86rem;
  line-height: 1.55;
}

.tip-title {
  color: var(--primary-color);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.tips ul {
  padding-left: 1.2rem;
  margin: 0;
}

.tips li {
  margin: 0.45rem 0;
}

@media (max-width: 1320px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .topbar {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .row {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .label {
    padding-top: 0;
  }

  .kv {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }

  .v {
    max-width: 100%;
  }
}
</style>
