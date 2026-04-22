<template>
  <div class="page-header">
    <div class="page-title-row">
      <h1 class="page-title">{{ title }}</h1>
      <div class="page-actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="subtitle" class="page-subtitle">{{ subtitle }}</div>
    <div class="page-breadcrumb">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>MPB_01 平台</el-breadcrumb-item>
        <el-breadcrumb-item v-if="module">{{ module }}</el-breadcrumb-item>
        <el-breadcrumb-item>{{ title }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: String,
  module: String,
})
</script>

<style lang="scss" scoped>
.page-header {
  margin-bottom: 18px;
}
.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.01em;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-mid);
  margin-bottom: 8px;
}
.page-breadcrumb {
  font-size: 12px;
  opacity: 0.75;
}
.page-actions {
  display: flex;
  gap: 10px;
}
</style>
