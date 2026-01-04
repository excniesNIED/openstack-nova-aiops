<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    labels: string[]
    series: Array<{ name: string; color: string; values: number[] }>
  }>(),
  { title: '告警趋势（近15分钟）' },
)

const xyConfig = ref({
  chart: {
    fontFamily: 'inherit',
    backgroundColor: 'transparent',
    color: '#e0e0ff',
    grid: {
      showVerticalLines: true,
      showHorizontalLines: true,
      labels: {
        show: true,
        color: '#8888aa',
        fontSize: 10,
        xAxisLabels: {
          values: [] as string[],
          rotation: 0,
        },
      },
    },
    title: {
      text: props.title,
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
    },
    line: {
      labels: {
        show: false,
      },
    },
  },
})

watch(
  () => props.labels,
  (labels) => {
    xyConfig.value.chart.grid.labels.xAxisLabels.values = labels
  },
  { immediate: true },
)

const xyDataset = computed(() =>
  props.series.map((s) => ({
    name: s.name,
    type: 'line' as const,
    series: s.values,
    color: s.color,
  })),
)
</script>

<template>
  <div class="line-chart">
    <VueUiXy :config="xyConfig" :dataset="xyDataset" />
  </div>
</template>

<style scoped>
.line-chart {
  width: 100%;
  height: 100%;
  min-height: 320px;
}
</style>
