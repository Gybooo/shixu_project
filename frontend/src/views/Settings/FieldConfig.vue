<template>
  <div v-loading="!summary">
    <PageHeader title="字段配置" subtitle="管理监测字段的元信息与采样参数" module="系统设置" />

    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">{{ fields.length }}</span><span class="stat-l">总字段数</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">11</span><span class="stat-l">启用字段</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">4</span><span class="stat-l">物理量族</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">1 Hz</span><span class="stat-l">采样频率</span></div></el-card></el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="h">
          <span class="title">字段元数据 ({{ fields.length }})</span>
          <el-button size="small"><el-icon><Plus /></el-icon> 新增字段</el-button>
        </div>
      </template>

      <el-table :data="fields" stripe size="default">
        <el-table-column label="#" type="index" width="55" align="center" />
        <el-table-column label="字段编码" prop="field" width="120">
          <template #default="{ row }">
            <strong style="font-family: Consolas, monospace; color: #4F7CFF;">{{ row.field }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="显示名称" width="140">
          <template #default="{ row }">{{ nameMap[row.field] || row.field }}</template>
        </el-table-column>
        <el-table-column label="物理量族" prop="group" width="120" />
        <el-table-column label="单位" prop="unit" width="80" align="center" />
        <el-table-column label="均值" width="110" align="right">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace;">{{ row.mean.toFixed(3) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="采样频率" width="110" align="center">
          <template #default>
            <el-tag size="small" effect="plain">1 Hz</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分解方法" width="150" align="center">
          <template #default>
            <el-tag size="small" type="info">SavGol(61,3)</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预测模型" width="140" align="center">
          <template #default>
            <el-tag size="small" type="success">TimesFM 2.5</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前档位" width="100" align="center">
          <template #default="{ row }">
            <span :class="'badge-' + row.grade.toLowerCase()">{{ row.grade }} 档</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="70" align="center">
          <template #default>
            <el-switch :model-value="true" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="160" align="center">
          <template #default>
            <el-button link type="primary" size="small">编辑</el-button>
            <el-button link type="primary" size="small">重新校准</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { ensureLoaded, summary } from '@/stores/data'

onMounted(() => ensureLoaded())

const fields = computed(() => summary.value?.fields || [])

const nameMap = {
  Magnitude: '合成振动幅值',
  aRMSX: '加速度 RMS X 轴', aRMSY: '加速度 RMS Y 轴', aRMSZ: '加速度 RMS Z 轴',
  vRMSX: '速度 RMS X 轴', vRMSY: '速度 RMS Y 轴', vRMSZ: '速度 RMS Z 轴', vRMSM: '速度 RMS 合成',
  ShockX: '冲击峰值 X 轴', ShockY: '冲击峰值 Y 轴', ShockZ: '冲击峰值 Z 轴',
}
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 14px; font-weight: 700; }
.stat { text-align: center; padding: 6px 0; }
.stat-n { display: block; font-size: 26px; font-weight: 800; color: var(--primary); font-family: Consolas, monospace; }
.stat-l { font-size: 12px; color: var(--text-mid); }
</style>
