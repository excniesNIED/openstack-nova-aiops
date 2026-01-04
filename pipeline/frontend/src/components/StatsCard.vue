<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string
  change: string
  icon: string
  color: 'cyan' | 'magenta' | 'green' | 'orange'
}>()

const colorMap = {
  cyan: '#00f0ff',
  magenta: '#ff00ff',
  green: '#00ff88',
  orange: '#ffaa00'
}

const cardColor = computed(() => colorMap[props.color])
const isPositive = computed(() => props.change.startsWith('+'))
</script>

<template>
  <div class="stats-card" :style="{ '--card-color': cardColor }">
    <div class="card-glow"></div>
    <div class="card-content">
      <div class="card-icon">
        <div class="icon-ring">
          <svg viewBox="0 0 60 60" class="ring-svg">
            <circle cx="30" cy="30" r="28" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
            <circle cx="30" cy="30" r="28" fill="none" stroke="currentColor" stroke-width="2" 
              stroke-dasharray="40 136" class="ring-progress"/>
          </svg>
          <div class="icon-inner">
            <i :class="icon"></i>
          </div>
        </div>
      </div>
      <div class="card-info">
        <span class="card-title">{{ title }}</span>
        <span class="card-value">{{ value }}</span>
        <span class="card-change" :class="{ positive: isPositive, negative: !isPositive }">
          <span class="change-icon">{{ isPositive ? '↑' : '↓' }}</span>
          {{ change }}
        </span>
      </div>
    </div>
    <div class="card-decoration">
      <div class="deco-line"></div>
      <div class="deco-dot"></div>
    </div>
  </div>
</template>

<style scoped>
.stats-card {
  background: var(--bg-card);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stats-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--card-color), transparent);
  opacity: 0.8;
}

.stats-card:hover {
  transform: translateY(-4px);
  border-color: var(--card-color);
  box-shadow: 
    0 10px 40px rgba(0, 0, 0, 0.3),
    0 0 20px color-mix(in srgb, var(--card-color) 20%, transparent);
}

.card-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, var(--card-color) 0%, transparent 70%);
  opacity: 0.05;
  transition: opacity 0.3s ease;
}

.stats-card:hover .card-glow {
  opacity: 0.1;
}

.card-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
  z-index: 1;
}

.card-icon {
  flex-shrink: 0;
}

.icon-ring {
  width: 60px;
  height: 60px;
  position: relative;
  color: var(--card-color);
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-progress {
  animation: ringRotate 3s linear infinite;
  transform-origin: center;
}

@keyframes ringRotate {
  0% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -176; }
}

.icon-inner {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1.5rem;
  color: var(--card-color);
  text-shadow: 0 0 10px var(--card-color);
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-title {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.card-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.card-change {
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.card-change.positive {
  color: var(--accent-color);
}

.card-change.negative {
  color: #ff4444;
}

.change-icon {
  font-size: 0.75rem;
}

.card-decoration {
  position: absolute;
  bottom: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.deco-line {
  width: 30px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--card-color));
  opacity: 0.5;
}

.deco-dot {
  width: 6px;
  height: 6px;
  background: var(--card-color);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
</style>
