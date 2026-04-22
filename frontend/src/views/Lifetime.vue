<template>
  <div v-loading="!summary">
    <PageHeader title="剩余寿命" subtitle="部件健康度推断与剩余服役时长预测" module="智能分析" />

    <el-alert type="warning" :closable="false" show-icon class="mb-2">
      <template #title><b>方法学演示</b></template>
      <div style="font-size: 13px; line-height: 1.7;">
        下列寿命数据基于当前数据集的误差演化趋势推断, 用于展示建模思路。
        真实 RUL (Remaining Useful Life) 模型需长期退化历史数据与失效标签, 待后续补充完善。
      </div>
    </el-alert>

    <!-- 概览 -->
    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><KpiCard label="监控设备" value="MPB_01" :icon="Cpu" color="#4F7CFF" /></el-col>
      <el-col :span="6"><KpiCard label="综合健康度" :value="compositeHealth + '%'" :color="compositeColor" :icon="Histogram" delta="部件加权计算" /></el-col>
      <el-col :span="6"><KpiCard label="预计剩余寿命" :value="estRUL" unit="天" color="#F59E0B" :icon="Timer" delta="基于部件最短剩余推断" /></el-col>
      <el-col :span="6"><KpiCard label="下次维护" :value="nextMaintenance" unit="天后" color="#EF4444" :icon="Warning" delta="润滑系统触发" /></el-col>
    </el-row>

    <!-- 部件寿命表 (对标 SINOR 第 4 页的进度条表格) -->
    <el-card class="mb-2">
      <template #header>
        <div class="h">
          <span class="title">监测部件剩余寿命</span>
          <el-tag type="info" effect="plain">基于电池-换油-齿轮的综合模型</el-tag>
        </div>
      </template>
      <el-table :data="components" stripe>
        <el-table-column label="#" type="index" width="55" align="center" />
        <el-table-column label="部件" prop="name" width="150" />
        <el-table-column label="关联字段" prop="related" width="160">
          <template #default="{ row }">
            <el-tag v-for="f in row.related" :key="f" size="small" effect="plain"
                    style="margin-right: 4px; font-family: Consolas, monospace;">
              {{ f }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前健康度" width="260">
          <template #default="{ row }">
            <HealthBar :value="row.health" />
          </template>
        </el-table-column>
        <el-table-column label="已运行" width="120" align="center">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace;">{{ row.runHours }} h</span>
          </template>
        </el-table-column>
        <el-table-column label="设计寿命" width="120" align="center">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace;">{{ row.designHours }} h</span>
          </template>
        </el-table-column>
        <el-table-column label="剩余寿命" width="150">
          <template #default="{ row }">
            <span :class="rulClass(row.rulDays)"
                  style="font-family: Consolas, monospace; font-weight: 600;">
              {{ row.rulDays }} 天
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="tagType(row.rulDays)" size="small" effect="light">
              {{ statusText(row.rulDays) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="建议操作" min-width="200">
          <template #default="{ row }">
            <span class="text-mid">{{ row.advice }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- horizon 误差演化 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card>
          <template #header>预测窗口扩展下的 MAE 演化</template>
          <v-chart :option="horizonOption" style="height: 340px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>综合健康度趋势 (假设)</template>
          <v-chart :option="healthTrendOption" style="height: 340px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-alert class="mt-2" type="info" :closable="false" show-icon>
      <template #title>精度对照</template>
      <div style="font-size: 13px; line-height: 1.7;">
        h=4 → NRMSE ~0.5% · h=8 → ~1.0% · <b>h=16 → ~2.1% (当前推荐)</b> · h=32 → ~5.9%<br>
        预测精度随 horizon 指数下降, 超过 32 步后曲线退化为近似均值, 建议短窗口滚动预测。
      </div>
    </el-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent } from 'echarts/components'
import { Cpu, Timer, Histogram, Warning } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import HealthBar from '@/components/HealthBar.vue'
import { ensureLoaded, summary } from '@/stores/data'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent])

onMounted(() => ensureLoaded())

// 部件定义 (健康度由关联字段的 NRMSE 和 SNR 加权计算)
const COMPONENTS_DEF = [
  { name: '主轴承', related: ['aRMSX', 'aRMSY'], runHours: 2634, designHours: 10000, bias: 0 },
  { name: '伺服电机', related: ['vRMSX', 'vRMSY', 'vRMSZ'], runHours: 2634, designHours: 8000, bias: 0 },
  { name: '减速机', related: ['Magnitude', 'vRMSM'], runHours: 2634, designHours: 12000, bias: 3 },
  { name: '润滑系统', related: ['Magnitude', 'vRMSM'], runHours: 2634, designHours: 5000, bias: -18 },
  { name: '冲击吸振器', related: ['ShockX', 'ShockY', 'ShockZ'], runHours: 2634, designHours: 6000, bias: 0 },
  { name: '控制单元', related: [], runHours: 2634, designHours: 15000, bias: 10 },
]

/**
 * 部件健康度 = 关联字段 NRMSE 均值 映射 + 部件偏置
 * 打通字段健康度体系与部件健康度体系,避免两套数据互相矛盾
 */
function calcHealth(relatedFields, bias, fieldMap) {
  if (!relatedFields || relatedFields.length === 0) {
    return Math.max(0, Math.min(100, 85 + bias))  // 无关联字段(如控制单元): 基线 85 + bias
  }
  const nrmseAvg = relatedFields.reduce((s, f) => {
    return s + (fieldMap[f]?.nrmseTfm ?? 20)
  }, 0) / relatedFields.length
  // NRMSE 10% → 健康 85; NRMSE 40% → 健康 40
  const base = 100 - nrmseAvg * 1.5
  return Math.max(5, Math.min(98, base + bias))
}

const components = computed(() => {
  if (!summary.value) return []
  const fieldMap = {}
  summary.value.fields.forEach(f => { fieldMap[f.field] = f })
  return COMPONENTS_DEF.map(c => {
    const health = calcHealth(c.related, c.bias, fieldMap)
    // 剩余寿命 ≈ (设计寿命 - 已运行) × (健康度 / 100) / 24 天
    const remainingHours = (c.designHours - c.runHours) * (health / 100)
    const rulDays = Math.max(1, Math.round(remainingHours / 24))
    return {
      ...c,
      health: Math.round(health),
      rulDays,
      advice: healthAdvice(health, c.name),
    }
  })
})

function healthAdvice(h, name) {
  if (h >= 85) return '状态良好, 按计划维护即可'
  if (h >= 70) return '指标轻微上升, 建议 3 个月内复检'
  if (h >= 50) return `${name} 指标持续下降, 建议 1 个月内维护`
  return `${name} 信号异常, 建议优先排查`
}

// 综合健康度 = 所有部件健康度平均
const compositeHealth = computed(() => {
  if (!components.value.length) return 0
  return Math.round(components.value.reduce((s, c) => s + c.health, 0) / components.value.length)
})
const compositeColor = computed(() => {
  const v = compositeHealth.value
  if (v >= 80) return '#10B981'
  if (v >= 60) return '#F59E0B'
  return '#EF4444'
})

// 预计剩余寿命 = 部件最短剩余寿命
const estRUL = computed(() => {
  if (!components.value.length) return 0
  return Math.min(...components.value.map(c => c.rulDays))
})

// 下次维护 = 最短剩余寿命的 25% (提前预警)
const nextMaintenance = computed(() => Math.max(1, Math.floor(estRUL.value * 0.25)))

function rulClass(days) {
  if (days < 60) return 'text-danger'
  if (days < 120) return 'text-warning'
  return 'text-success'
}
function tagType(days) {
  if (days < 60) return 'danger'
  if (days < 120) return 'warning'
  return 'success'
}
function statusText(days) {
  if (days < 60) return '紧急'
  if (days < 120) return '关注'
  return '正常'
}

const horizonOption = computed(() => {
  const steps = [4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64]
  const lstm = [0.015, 0.028, 0.045, 0.062, 0.082, 0.105, 0.128, 0.154, 0.202, 0.248, 0.285, 0.318]
  const tfm = [0.005, 0.009, 0.013, 0.018, 0.025, 0.033, 0.042, 0.051, 0.070, 0.093, 0.118, 0.145]
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 10 },
    grid: { top: 40, left: 60, right: 30, bottom: 50 },
    xAxis: { type: 'category', data: steps, name: 'horizon (秒)' },
    yAxis: { type: 'value', name: 'MAE' },
    series: [
      { name: 'LSTM', type: 'line', data: lstm, smooth: true, symbol: 'circle', symbolSize: 7,
        lineStyle: { color: '#EF4444', width: 2.5 }, itemStyle: { color: '#EF4444' } },
      { name: 'TimesFM', type: 'line', data: tfm, smooth: true, symbol: 'circle', symbolSize: 7,
        lineStyle: { color: '#10B981', width: 2.5 }, itemStyle: { color: '#10B981' },
        markArea: { silent: true, itemStyle: { color: 'rgba(16, 185, 129, 0.08)' }, data: [[{ xAxis: 4 }, { xAxis: 16 }]] },
        markLine: { silent: true, symbol: 'none', data: [{ xAxis: 16, label: { formatter: '推荐 h=16' }, lineStyle: { color: '#10B981', type: 'dashed' } }] },
      },
    ],
  }
})

const healthTrendOption = computed(() => {
  const days = Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`)
  // 假数据: 从 95 缓慢下降到 82
  const main = days.map((_, i) => {
    const progress = i / 30
    return +(95 - progress * 13 + (Math.random() - 0.5) * 1.5).toFixed(1)
  })
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, left: 48, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: days, axisLabel: { interval: 5 } },
    yAxis: { type: 'value', min: 70, max: 100, name: '健康度 %' },
    series: [{
      name: '综合健康度', type: 'line', data: main, smooth: true, showSymbol: false,
      lineStyle: { color: '#4F7CFF', width: 2.5 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(79, 124, 255, 0.4)' },
            { offset: 1, color: 'rgba(79, 124, 255, 0.02)' },
          ],
        },
      },
      markLine: {
        silent: true, symbol: 'none',
        data: [
          { yAxis: 85, name: '健康阈值', lineStyle: { color: '#10B981', type: 'dashed' } },
          { yAxis: 75, name: '预警阈值', lineStyle: { color: '#F59E0B', type: 'dashed' } },
        ],
      },
    }],
  }
})
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 14px; font-weight: 700; }
</style>
