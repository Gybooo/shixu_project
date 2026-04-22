<template>
  <div class="hbar">
    <div class="hbar-track">
      <div class="hbar-fill" :style="{ width: pct + '%', background: color }"></div>
    </div>
    <span class="hbar-val" :style="{ color }">{{ Math.round(value) }}%</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
})

const pct = computed(() => Math.max(0, Math.min(100, props.value)))
const color = computed(() => {
  const v = props.value
  if (v >= 75) return '#10B981'
  if (v >= 50) return '#F59E0B'
  return '#EF4444'
})
</script>

<style lang="scss" scoped>
.hbar {
  display: flex; align-items: center; gap: 8px;
  width: 100%;
}
.hbar-track {
  flex: 1;
  height: 6px;
  background: #E5E9F2;
  border-radius: 3px;
  overflow: hidden;
  min-width: 50px;
}
.hbar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
.hbar-val {
  font-size: 11px;
  font-weight: 600;
  font-family: Consolas, monospace;
  min-width: 34px;
  text-align: right;
}
</style>
