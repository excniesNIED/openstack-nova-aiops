<script setup lang="ts">
import { ref } from 'vue'

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
              text: '资源',
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
        text: '资源分配',
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

const donutDataset = ref([
  {
    name: '计算资源',
    values: [35],
    color: '#00f0ff',
  },
  {
    name: '存储资源',
    values: [28],
    color: '#ff00ff',
  },
  {
    name: '网络带宽',
    values: [22],
    color: '#00ff88',
  },
  {
    name: '缓存空间',
    values: [15],
    color: '#ffaa00',
  },
])
</script>

<template>
  <div class="donut-chart">
    <VueUiDonut :config="donutConfig" :dataset="donutDataset" />
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
}
</style>
