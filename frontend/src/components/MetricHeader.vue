<template>
  <el-tooltip :content="tip" placement="top" effect="dark">
    <span class="metric-header">
      {{ label }}
      <el-icon class="info-icon"><InfoFilled /></el-icon>
    </span>
  </el-tooltip>
</template>

<script setup>
import { InfoFilled } from '@element-plus/icons-vue'

defineProps({
  label: { type: String, required: true },
  tip: { type: String, required: true },
})
</script>

<style lang="scss" scoped>
.metric-header {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: help;
  font-weight: 600;
}
.info-icon {
  font-size: 12px;
  color: var(--text-light);
  opacity: 0.7;
  transition: opacity 0.18s;
}
.metric-header:hover .info-icon {
  opacity: 1;
  color: var(--primary-light);
}
</style>
