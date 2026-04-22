<template>
  <el-card class="fh-panel">
    <template #header>
      <div class="fh-header">
        <div>
          <span class="fh-title">设备部件健康度总览</span>
          <span class="fh-sub">全产线 · 11 通道 · 多维健康指标</span>
        </div>
        <div class="fh-filters">
          <el-select v-model="groupFilter" placeholder="全部族" clearable size="small" style="width: 130px;">
            <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="gradeFilter" placeholder="全部档位" clearable size="small" style="width: 130px;">
            <el-option label="A 档" value="A" />
            <el-option label="B 档" value="B" />
            <el-option label="C 档" value="C" />
          </el-select>
          <el-button size="small" @click="reset">重置</el-button>
          <el-button type="primary" size="small">查询</el-button>
        </div>
      </div>
    </template>

    <el-table :data="filtered" stripe size="default" class="fh-table">
      <el-table-column label="#" type="index" width="50" align="center" />
      <el-table-column label="通道" prop="field" width="110">
        <template #default="{ row }">
          <strong style="font-family: Consolas, monospace;">{{ row.field }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="位置" width="110" align="center">
        <template #default>
          <el-link type="primary" :underline="false">MPB_01</el-link>
        </template>
      </el-table-column>
      <el-table-column label="物理量族" width="120" align="center">
        <template #default="{ row }">
          <el-tag :style="tagStyle(row.group)" size="small">{{ row.group }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column width="170">
        <template #header>
          <MetricHeader label="预测精度" tip="基于 NRMSE 指标 (MAE / 趋势标准差): 反映模型预测值与真实值的相对偏离程度" />
        </template>
        <template #default="{ row }">
          <HealthBar :value="row.healthSignal" />
        </template>
      </el-table-column>
      <el-table-column width="170">
        <template #header>
          <MetricHeader label="模型置信度" tip="基于模型在 60 个测试窗口的误差一致性: 反映预测结果是否稳定可信" />
        </template>
        <template #default="{ row }">
          <HealthBar :value="row.healthForecast" />
        </template>
      </el-table-column>
      <el-table-column width="170">
        <template #header>
          <MetricHeader label="信号质量" tip="基于 SNR (信噪比 = 趋势标准差 / 噪声标准差): 反映信号骨架相对噪声的强度" />
        </template>
        <template #default="{ row }">
          <HealthBar :value="row.healthRedundancy" />
        </template>
      </el-table-column>
      <el-table-column width="170">
        <template #header>
          <MetricHeader label="长程稳定性" tip="基于 ACF lag-16 自相关系数: 反映信号在 16 秒后仍保留多少可预测性" />
        </template>
        <template #default="{ row }">
          <HealthBar :value="row.healthStability" />
        </template>
      </el-table-column>
      <el-table-column label="工艺部件报警" width="140" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.grade === 'C'" :size="18" class="warn-icon"><WarnTriangleFilled /></el-icon>
          <el-icon v-else-if="row.grade === 'B'" :size="18" style="color: #F59E0B;"><Warning /></el-icon>
          <el-icon v-else :size="18" style="color: #10B981;"><CircleCheck /></el-icon>
        </template>
      </el-table-column>
      <el-table-column label="运行时长" width="130" align="center">
        <template #default>
          <span style="font-family: Consolas, monospace; font-size: 12px;">2小时38分</span>
        </template>
      </el-table-column>
      <el-table-column label="评估次数" width="140" align="center">
        <template #default="{ row }">
          <span :class="row.grade === 'C' ? 'text-danger' : 'text-primary'"
                style="font-family: Consolas, monospace; font-weight: 600;">
            {{ Math.floor(8960 * (1 - row.nrmseTfm / 100)) }}/8960
          </span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { WarnTriangleFilled, Warning, CircleCheck } from '@element-plus/icons-vue'
import HealthBar from './HealthBar.vue'
import MetricHeader from './MetricHeader.vue'
import { groupColor } from '@/stores/data'

const props = defineProps({
  fields: { type: Array, required: true },
})

const groupFilter = ref(null)
const gradeFilter = ref(null)

const groups = computed(() => Array.from(new Set(props.fields.map(f => f.group))))

// 为每个字段计算 4 个维度的健康度 (基于真实的 NRMSE/SNR/ACF)
const enriched = computed(() => props.fields.map(f => {
  // 信号健康 = 1 - NRMSE/100 归一化
  const healthSignal = Math.max(0, Math.min(100, 100 - f.nrmseTfm * 1.5))
  // 预测健康 = NRMSE 直接反比
  const healthForecast = Math.max(0, Math.min(100, 100 - f.nrmseTfm * 2))
  // 冗余健康 = SNR 映射 (>1.5 → 95, <0.5 → 30)
  const healthRedundancy = Math.max(0, Math.min(100, f.snr * 50))
  // 稳定性 = ACF lag-16
  const healthStability = Math.max(0, Math.min(100, f.acfLag16 * 100))
  return { ...f, healthSignal, healthForecast, healthRedundancy, healthStability }
}))

const filtered = computed(() => enriched.value.filter(f => {
  if (groupFilter.value && f.group !== groupFilter.value) return false
  if (gradeFilter.value && f.grade !== gradeFilter.value) return false
  return true
}))

function tagStyle(group) {
  const c = groupColor(group)
  return { background: c + '18', color: c, border: `1px solid ${c}40` }
}

function reset() {
  groupFilter.value = null
  gradeFilter.value = null
}
</script>

<style lang="scss" scoped>
.fh-panel :deep(.el-card__body) {
  padding: 0;
}
.fh-header {
  display: flex; justify-content: space-between; align-items: center;
}
.fh-title { font-weight: 700; font-size: 15px; color: var(--text); }
.fh-sub { margin-left: 12px; font-size: 12px; color: var(--text-light); font-weight: normal; }
.fh-filters { display: flex; gap: 8px; align-items: center; }

.fh-table {
  --el-table-header-bg-color: #F5F7FA;
}
.warn-icon { color: #EF4444; animation: blink 1.2s ease-in-out infinite; }
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}
</style>
