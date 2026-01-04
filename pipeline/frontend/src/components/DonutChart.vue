<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  title?: string
  items: Array<{ name: string; value: number; color: string }>
}>()

const donutConfig = ref({
  style: {
    fontFamily: 'inherit',
    chart: {
      backgroundColor: 'transparent',
      color: '#e0e0ff',
      layout: {
        labels: {
          dataLabels: {
            show: true,
            useLabelSlots: false,
            color: '#e0e0ff',
            fontSize: 12,
          },
          value: {
            show: true,
            color: '#e0e0ff',
            fontSize: 14,
            bold: true,
            rounding: 1,
            prefix: '',
            suffix: '%',
          },
          hollow: {
            show: true,
            total: {
              show: true,
              bold: true,
              fontSize: 24,
              color: '#00f0ff',
              text: '告警',
              offsetY: -10,
              value: {
                show: true,
                color: '#e0e0ff',
                fontSize: 16,
                bold: false,
                suffix: '',
                prefix: '',
                offsetY: 10,
              },
            },
          },
          percentage: {
            color: '#e0e0ff',
            fontSize: 12,
            bold: true,
          },
        },
        donut: {
          strokeWidth: 60,
          borderWidth: 2,
          useShadow: true,
          shadowColor: 'rgba(0, 240, 255, 0.3)',
        },
      },
      title: {
        text: props.title ?? '告警等级分布',
        color: '#00f0ff',
        fontSize: 16,
        bold: true,
        textAlign: 'left',
        paddingLeft: 12,
        paddingTop: 12,
      },
      legend: {
        show: false,
        backgroundColor: 'transparent',
        color: '#e0e0ff',
        fontSize: 11,
      },
      tooltip: {
        show: true,
        backgroundColor: 'rgba(10, 20, 40, 0.95)',
        color: '#e0e0ff',
        borderRadius: 8,
        borderColor: 'rgba(0, 240, 255, 0.3)',
        borderWidth: 1,
      },
    },
  },
})

const donutDataset = computed(() =>
  props.items.map((it) => ({
    name: it.name,
    values: [it.value],
    color: it.color,
  })),
)
</script>

<template>
  <div class="donut-chart">
    <VueUiDonut
      :config="donutConfig"
      :dataset="donutDataset"
    />
    <div class="legend">
      <div
        v-for="it in props.items"
        :key="it.name"
        class="legend-item"
      >
        <span
          class="dot"
          :style="{ background: it.color }"
        />
        <span class="name">{{ it.name }}</span>
        <span class="value mono">{{ it.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut-chart {
  width: 100%;
  height: 100%;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.5rem;
}

.legend {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.25rem 0.75rem;
  padding: 0 0.5rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.2);
}

.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
</style>
