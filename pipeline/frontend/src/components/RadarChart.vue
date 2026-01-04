<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    categories: string[]
    current: number[]
    baseline?: number[] | null
  }>(),
  { title: '告警证据画像', baseline: null },
)

const radarConfig = ref({
  style: {
    fontFamily: 'inherit',
    chart: {
      backgroundColor: 'transparent',
      color: '#e0e0ff',
      layout: {
        plots: {
          show: true,
          radius: 2,
        },
        outerPolygon: {
          stroke: 'rgba(0, 240, 255, 0.3)',
          strokeWidth: 1,
        },
        dataPolygon: {
          strokeWidth: 2,
          transparent: true,
          opacity: 25,
          useGradient: true,
        },
        grid: {
          show: true,
          stroke: 'rgba(0, 240, 255, 0.15)',
          strokeWidth: 1,
        },
        labels: {
          dataLabels: {
            show: true,
            fontSize: 12,
            color: '#e0e0ff',
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
        backgroundColor: 'rgba(10, 20, 40, 0.95)',
        color: '#e0e0ff',
        borderRadius: 8,
        borderColor: 'rgba(0, 240, 255, 0.3)',
        borderWidth: 1,
      },
    },
  },
})

const radarDataset = computed(() => ({
  categories: props.categories.map((name) => ({ name })),
  series: [
    { name: '当前窗口', values: props.current, color: '#00f0ff' },
    ...(props.baseline && props.baseline.length ? [{ name: '基线', values: props.baseline, color: '#ff00ff' }] : []),
  ],
}))
</script>

<template>
  <div class="radar-chart">
    <VueUiRadar
      :config="radarConfig"
      :dataset="radarDataset"
    />
  </div>
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
