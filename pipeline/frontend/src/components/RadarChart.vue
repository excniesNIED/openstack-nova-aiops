<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

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
        text: '性能指标分析',
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
        backgroundColor: 'rgba(10, 20, 40, 0.95)',
        color: '#e0e0ff',
        borderRadius: 8,
        borderColor: 'rgba(0, 240, 255, 0.3)',
        borderWidth: 1,
      },
    },
  },
})

const radarDataset = ref({
  categories: [
    { name: 'CPU' },
    { name: '内存' },
    { name: '网络' },
    { name: '磁盘' },
    { name: '响应' },
    { name: '吞吐' },
  ],
  series: [
    {
      name: '当前',
      values: [85, 72, 90, 65, 78, 88],
      color: '#00f0ff',
    },
    {
      name: '基准',
      values: [70, 80, 75, 70, 85, 75],
      color: '#ff00ff',
    },
  ],
})

let updateInterval: number | null = null

const updateData = () => {
  const currentSeries = radarDataset.value.series[0]
  if (!currentSeries) return
  radarDataset.value = {
    ...radarDataset.value,
    series: [
      {
        name: '当前',
        values: currentSeries.values.map(() => 
          Math.floor(Math.random() * 30) + 60
        ),
        color: '#00f0ff',
      },
      {
        name: '基准',
        values: [70, 80, 75, 70, 85, 75],
        color: '#ff00ff',
      },
    ],
  }
}

onMounted(() => {
  updateInterval = window.setInterval(updateData, 5000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
})
</script>

<template>
  <div class="radar-chart">
    <VueUiRadar :config="radarConfig" :dataset="radarDataset" />
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
