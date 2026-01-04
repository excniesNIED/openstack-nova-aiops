<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import DashboardHeader from './components/DashboardHeader.vue'
import StatsCard from './components/StatsCard.vue'
import RadarChart from './components/RadarChart.vue'
import DonutChart from './components/DonutChart.vue'
import LineChart from './components/LineChart.vue'
import GaugePanel from './components/GaugePanel.vue'
import ActivityLog from './components/ActivityLog.vue'
import SystemStatus from './components/SystemStatus.vue'

const currentTime = ref(new Date().toLocaleTimeString())
let timeInterval: number | null = null

onMounted(() => {
  timeInterval = window.setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString()
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<template>
  <div class="dashboard">
    <DashboardHeader :current-time="currentTime" />
    
    <main class="dashboard-content">
      <!-- Stats Row -->
      <section class="stats-row">
        <StatsCard 
          title="数据流量" 
          value="2.4 TB" 
          change="+12.5%" 
          icon="icon-data" 
          color="cyan"
        />
        <StatsCard 
          title="活跃节点" 
          value="128" 
          change="+3" 
          icon="icon-node" 
          color="magenta"
        />
        <StatsCard 
          title="处理任务" 
          value="1,847" 
          change="+156" 
          icon="icon-task" 
          color="green"
        />
        <StatsCard 
          title="系统负载" 
          value="67%" 
          change="-2.3%" 
          icon="icon-cpu" 
          color="orange"
        />
      </section>

      <!-- Main Charts Row -->
      <section class="charts-row">
        <div class="chart-container large">
          <LineChart />
        </div>
        <div class="chart-container">
          <RadarChart />
        </div>
      </section>

      <!-- Bottom Row -->
      <section class="bottom-row">
        <div class="chart-container">
          <DonutChart />
        </div>
        <div class="chart-container">
          <GaugePanel />
        </div>
        <div class="chart-container">
          <ActivityLog />
        </div>
      </section>

      <!-- System Status -->
      <section class="status-row">
        <SystemStatus />
      </section>
    </main>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.dashboard-content {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  min-height: 350px;
}

.bottom-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  min-height: 300px;
}

.status-row {
  margin-top: auto;
}

.chart-container {
  background: var(--bg-card);
  border: 1px solid var(--border-glow);
  border-radius: 12px;
  padding: 1rem;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.chart-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: var(--gradient-cyber);
  animation: borderScan 4s linear infinite;
}

.chart-container:hover {
  border-color: var(--primary-color);
  box-shadow: 
    0 0 20px rgba(0, 240, 255, 0.15),
    inset 0 0 30px rgba(0, 240, 255, 0.03);
}

.chart-container.large {
  grid-column: span 1;
}

@keyframes borderScan {
  0% { left: -100%; }
  100% { left: 100%; }
}

@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
  
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
