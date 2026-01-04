<script setup lang="ts">
import { computed, h, ref, resolveComponent } from 'vue'
import { getAlert } from '@/api/pipeline'
import type { Alert } from '@/api/types'

const props = withDefaults(
  defineProps<{
    alerts: Alert[]
    apiBaseUrl: string
    loading?: boolean
    error?: string | null
  }>(),
  {
    loading: false,
    error: null,
  },
)

const modalVisible = ref(false)
const detail = ref<Alert | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)

const openDetail = async (row: Alert) => {
  modalVisible.value = true
  detail.value = null
  detailError.value = null
  detailLoading.value = true
  try {
    detail.value = await getAlert(props.apiBaseUrl, row.alert_id, { timeoutMs: 8000 })
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : String(e)
  } finally {
    detailLoading.value = false
  }
}

const toLocalTime = (iso: string) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-CN', { hour12: false })
}

const severityType = (severity: string) => {
  if (severity === 'P1') return 'danger'
  if (severity === 'P2') return 'warning'
  return 'success'
}

const severityFormatter = (_row: Record<string, unknown>, _column: unknown, cellValue: unknown) => {
  const DTag = resolveComponent('d-tag') as unknown
  const severity = String(cellValue ?? '')
  return h(
    DTag as never,
    { type: severityType(severity), size: 'sm', titleContent: severity },
    { default: () => severity || '--' },
  )
}

const timeFormatter = (row: Record<string, unknown>) => {
  const createdAt = String(row.created_at ?? '')
  return h('span', { class: 'mono' }, toLocalTime(createdAt))
}

const probFormatter = (_row: Record<string, unknown>, _column: unknown, cellValue: unknown) => {
  const v = typeof cellValue === 'number' ? cellValue : Number(cellValue ?? 0)
  return h('span', { class: 'mono' }, `${(v * 100).toFixed(1)}%`)
}

const actionFormatter = (row: Record<string, unknown>) => {
  const DButton = resolveComponent('d-button') as unknown
  return h(
    DButton as never,
    {
      variant: 'text',
      size: 'sm',
      color: 'primary',
      onClick: (e: Event) => {
        e.stopPropagation()
        void openDetail(row as unknown as Alert)
      },
    },
    { default: () => '详情' },
  )
}

const detailSummary = computed(() => {
  const r = detail.value
  if (!r) return null
  const counts = r.evidence?.counts
  const errorRatio = r.evidence?.error_ratio
  const templates = r.evidence?.top_templates ?? []
  return {
    createdAt: toLocalTime(r.created_at),
    entityKey: r.entity_key,
    predClass: r.pred_class,
    probPct: `${(r.prob * 100).toFixed(1)}%`,
    severity: r.severity,
    errorRatioPct: errorRatio == null ? '--' : `${(Number(errorRatio) * 100).toFixed(1)}%`,
    countsText: counts
      ? `ERROR=${counts.error_cnt} WARN=${counts.warn_cnt} INFO=${counts.info_cnt} TOTAL=${counts.total_records}`
      : '--',
    topTemplates: templates.slice(0, 10),
  }
})
</script>

<template>
  <div class="alerts-table">
    <div class="table-header">
      <h3 class="panel-title">告警列表（来自 FastAPI）</h3>
      <div class="table-meta">
        <d-tag v-if="props.loading" type="primary" size="sm">拉取中…</d-tag>
        <d-tag v-else-if="props.error" type="danger" size="sm" :title-content="props.error">API 异常</d-tag>
        <d-tag v-else type="success" size="sm">已连接</d-tag>
        <span class="meta-text mono">limit={{ props.alerts.length }}</span>
      </div>
    </div>

    <d-table
      :data="props.alerts"
      size="sm"
      :scrollable="true"
      max-height="320px"
      :row-hovered-highlight="true"
      empty="暂无告警（或尚未启动回放/流式任务）"
    >
      <d-column header="时间" :width="170" :formatter="timeFormatter" />
      <d-column field="severity" header="等级" :width="80" :formatter="severityFormatter" />
      <d-column field="pred_class" header="类型" :width="160" show-overflow-tooltip />
      <d-column field="entity_key" header="实体" :width="220" show-overflow-tooltip />
      <d-column field="prob" header="置信度" :width="110" :formatter="probFormatter" />
      <d-column header="操作" :width="90" :formatter="actionFormatter" />
    </d-table>

    <d-modal v-model="modalVisible" title="告警详情" :close-on-click-overlay="true">
      <template v-if="detailLoading">
        <div class="modal-loading">加载中…</div>
      </template>
      <template v-else-if="detailError">
        <d-tag type="danger" size="sm" :title-content="detailError">加载失败</d-tag>
        <div class="mono mt">{{ detailError }}</div>
      </template>
      <template v-else-if="detailSummary">
        <div class="detail-grid">
          <div><span class="label">时间</span><span class="mono">{{ detailSummary.createdAt }}</span></div>
          <div><span class="label">等级</span><span class="mono">{{ detailSummary.severity }}</span></div>
          <div><span class="label">类型</span><span class="mono">{{ detailSummary.predClass }}</span></div>
          <div><span class="label">置信度</span><span class="mono">{{ detailSummary.probPct }}</span></div>
          <div><span class="label">实体</span><span class="mono">{{ detailSummary.entityKey }}</span></div>
          <div><span class="label">ERROR%</span><span class="mono">{{ detailSummary.errorRatioPct }}</span></div>
          <div class="span-2"><span class="label">计数</span><span class="mono">{{ detailSummary.countsText }}</span></div>
          <div class="span-2">
            <span class="label">Top Templates</span>
            <span class="mono">{{ detailSummary.topTemplates.join(', ') || '--' }}</span>
          </div>
        </div>

        <div class="mt">
          <h4 class="sub-title">ERROR 证据（error_examples）</h4>
          <pre class="pre">{{ detail?.evidence?.error_examples?.slice(0, 5) ?? [] }}</pre>
        </div>
      </template>
      <template v-else>
        <div class="modal-loading">未选择告警</div>
      </template>
    </d-modal>
  </div>
</template>

<style scoped>
.alerts-table {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.table-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.meta-text {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.modal-loading {
  padding: 0.75rem 0;
  color: var(--text-secondary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem 1rem;
}

.detail-grid > div {
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
}

.label {
  width: 90px;
  color: var(--text-secondary);
  font-size: 0.85rem;
  flex-shrink: 0;
}

.span-2 {
  grid-column: span 2;
}

.mt {
  margin-top: 0.75rem;
}

.sub-title {
  font-size: 0.95rem;
  color: var(--primary-color);
  margin: 0 0 0.5rem 0;
}

.pre {
  max-height: 240px;
  overflow: auto;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0.75rem;
  border-radius: 8px;
}
</style>

