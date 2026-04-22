<template>
  <div v-loading="!summary">
    <PageHeader title="剩余寿命" subtitle="基于预测误差演化推断设备可监控时长" module="智能分析" />

    <el-alert type="warning" :closable="false" show-icon class="mb-2">
      <template #title>
        <b>方法学演示</b>
      </template>
      <div style="font-size: 13px; line-height: 1.7;">
        本模块为基于 horizon 扩展的误差演化趋势推断模型, 目前为占位演示。
        完整的剩余寿命模型 (Remaining Useful Life, RUL) 需长期历史数据、退化曲线拟合与不确定性建模,
        待后续补充原始寿命标签后完善。
      </div>
    </el-alert>

    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><KpiCard label="监控设备" value="MPB_01" :icon="Cpu" /></el-col>
      <el-col :span="6"><KpiCard label="已监控时长" value="2.62" unit="小时" :icon="Timer" /></el-col>
      <el-col :span="6"><KpiCard label="可控预测窗口" value="16" unit="秒" color="#10B981" :icon="Histogram" /></el-col>
      <el-col :span="6"><KpiCard label="预测误差增长" value="指数级" color="#F59E0B" :icon="TrendCharts" /></el-col>
    </el-row>

    <el-card>
      <template #header>horizon 扩展下的误差演化</template>
      <v-chart :option="horizonOption" style="height: 400px" autoresize />
      <el-alert type="info" :closable="false" class="mt-2">
        <template #title>精度对照 · 推荐配置</template>
        <div style="font-size: 13px; line-height: 1.7;">
          h=4 → NRMSE ~0.5% · h=8 → ~1.0% · <b>h=16 → ~2.1% (推荐)</b> · h=32 → ~5.9%<br>
          预测精度随 horizon 指数下降, 超过 32 步后曲线退化为近似均值, 建议短窗口滚动预测。
        </div>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent } from 'echarts/components'
import { Cpu, Timer, Histogram, TrendCharts } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import { ensureLoaded, summary } from '@/stores/data'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent, MarkLineComponent])

onMounted(() => ensureLoaded())

const horizonOption = computed(() => {
  const steps = [4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64]
  const lstm = [0.015, 0.028, 0.045, 0.062, 0.082, 0.105, 0.128, 0.154, 0.202, 0.248, 0.285, 0.318]
  const tfm = [0.005, 0.009, 0.013, 0.018, 0.025, 0.033, 0.042, 0.051, 0.070, 0.093, 0.118, 0.145]
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 10 },
    grid: { top: 40, left: 60, right: 40, bottom: 60 },
    xAxis: { type: 'category', data: steps, name: 'horizon (秒)' },
    yAxis: { type: 'value', name: 'MAE' },
    series: [
      {
        name: 'LSTM', type: 'line', data: lstm, smooth: true,
        symbol: 'circle', symbolSize: 8,
        lineStyle: { color: '#EF4444', width: 2.5 }, itemStyle: { color: '#EF4444' },
      },
      {
        name: 'TimesFM', type: 'line', data: tfm, smooth: true,
        symbol: 'circle', symbolSize: 8,
        lineStyle: { color: '#10B981', width: 2.5 }, itemStyle: { color: '#10B981' },
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(16, 185, 129, 0.08)' },
          data: [[{ xAxis: 4 }, { xAxis: 16 }]],
        },
        markLine: {
          silent: true, symbol: 'none',
          data: [{ xAxis: 16, label: { formatter: '推荐 h=16', position: 'middle' }, lineStyle: { color: '#10B981', type: 'dashed' } }],
        },
      },
    ],
  }
})
</script>
