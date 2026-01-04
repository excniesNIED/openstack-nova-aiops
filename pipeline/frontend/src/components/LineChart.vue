<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const makeWindow = () => {
  const now = Date.now()
  const labels = Array.from({ length: 24 }, (_, i) =>
    new Date(now - (23 - i) * 3600000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  )
  const inbound = Array.from({ length: 24 }, () => Math.floor(Math.random() * 500) + 200)
  const outbound = inbound.map(v => Math.floor(v * 0.7))
  return { labels, inbound, outbound }
}

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
          values: [],
          rotation: 0,
        },
      },
    },
    title: {
      text: '实时流量（模拟）',
      color: '#00f0ff',
      fontSize: 16,
      bold: true,
      textAlign: 'left',
      paddingLeft: 12,
      paddingTop: 12,
    },
    legend: {
      show: true,
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

const initial = makeWindow()
xyConfig.value.chart.grid.labels.xAxisLabels.values = initial.labels

const xyDataset = ref([
  { name: '入站流量', type: 'line', series: initial.inbound, color: '#00f0ff' },
  { name: '出站流量', type: 'line', series: initial.outbound, color: '#ff00ff' },
])

let updateInterval: number | null = null

const updateData = () => {
  const next = makeWindow()
  xyConfig.value.chart.grid.labels.xAxisLabels.values = next.labels
  xyDataset.value = [
    { name: '入站流量', type: 'line', series: next.inbound, color: '#00f0ff' },
    { name: '出站流量', type: 'line', series: next.outbound, color: '#ff00ff' },
  ]
}

onMounted(() => {
  updateInterval = window.setInterval(updateData, 3000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
})
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
