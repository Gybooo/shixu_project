<template>
  <div class="kpi-card">
    <div class="kpi-icon" :style="{ background: color + '22', color }">
      <el-icon :size="22"><component :is="icon" /></el-icon>
    </div>
    <div class="kpi-content">
      <div class="kpi-label">{{ label }}</div>
      <div class="kpi-value-row">
        <span class="kpi-value" :style="{ color }">{{ value }}</span>
        <span class="kpi-unit">{{ unit }}</span>
      </div>
      <div v-if="delta" class="kpi-delta">{{ delta }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: [String, Number],
  unit: String,
  delta: String,
  color: { type: String, default: '#4F7CFF' },
  icon: [String, Object, Function],
})
</script>

<style lang="scss" scoped>
.kpi-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: all 0.18s;
}
.kpi-card:hover {
  border-color: var(--primary-light);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.kpi-content {
  flex: 1;
  min-width: 0;
}
.kpi-label {
  font-size: 12.5px;
  color: var(--text-mid);
  margin-bottom: 2px;
}
.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.kpi-value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.01em;
  font-family: Consolas, monospace;
}
.kpi-unit {
  font-size: 12px;
  color: var(--text-mid);
}
.kpi-delta {
  font-size: 11.5px;
  color: var(--text-light);
  margin-top: 3px;
}
</style>
