<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const gauges = ref([
  { name: 'CPU', value: 67, color: '#00f0ff' },
  { name: '内存', value: 54, color: '#ff00ff' },
  { name: '磁盘', value: 78, color: '#00ff88' },
])

const createGaugeConfig = (color: string) => ({
  style: {
    fontFamily: 'inherit',
    chart: {
      backgroundColor: 'transparent',
      layout: {
        track: {
          size: 0.8,
          useGradient: true,
          gradientFrom: 'rgba(255,255,255,0.05)',
          gradientTo: 'rgba(255,255,255,0.1)',
        },
        markers: {
          show: true,
          color: 'rgba(255,255,255,0.3)',
          bold: false,
          fontSize: 8,
          offsetY: 0,
          roundingValue: 0,
        },
        pointer: {
          type: 'pointy',
          size: 1,
          stroke: color,
          strokeWidth: 3,
          useRatingColor: false,
          color: color,
          circle: {
            radius: 8,
            stroke: color,
            strokeWidth: 2,
            color: 'rgba(10, 20, 40, 0.9)',
          },
        },
      },
      legend: {
        show: true,
        fontSize: 24,
        prefix: '',
        suffix: '%',
        bold: true,
        roundingValue: 0,
        color: color,
        offsetY: 0,
      },
      title: {
        show: false,
      },
    },
  },
})

let updateInterval: number | null = null

const updateGauges = () => {
  gauges.value = gauges.value.map(g => ({
    ...g,
    value: Math.min(100, Math.max(20, g.value + (Math.random() - 0.5) * 10)),
  }))
}

onMounted(() => {
  updateInterval = window.setInterval(updateGauges, 2000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
})
</script>

<template>
  <div class="gauge-panel">
    <h3 class="panel-title">系统负载</h3>
    <div class="gauges-grid">
      <div v-for="gauge in gauges" :key="gauge.name" class="gauge-item">
        <VueUiGauge 
          :config="createGaugeConfig(gauge.color)" 
          :dataset="{
            value: gauge.value,
            series: [
              { from: 0, to: 60, color: '#00ff88', name: '正常' },
              { from: 60, to: 85, color: '#ffaa00', name: '偏高' },
              { from: 85, to: 100, color: '#ff4444', name: '告警' },
            ],
          }" 
        />
        <span class="gauge-label" :style="{ color: gauge.color }">{{ gauge.name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gauge-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
  padding-left: 0.5rem;
}

.gauges-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  align-items: center;
}

.gauge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.gauge-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}
</style>
