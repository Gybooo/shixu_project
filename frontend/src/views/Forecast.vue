<template>
  <div v-loading="!summary || !forecast">
    <PageHeader title="预警分析" subtitle="LSTM 本地训练 vs TimesFM 零样本 · 16 步未来窗口预测" module="智能分析">
      <template #actions>
        <el-tag type="primary" effect="plain">SavGol(61,3) + h=16</el-tag>
      </template>
    </PageHeader>

    <!-- KPI -->
    <el-row :gutter="16" class="mb-2" v-if="currentField">
      <el-col :span="6"><KpiCard label="LSTM MAE" :value="currentField.lstmMae.toFixed(4)" :unit="currentField.unit" :icon="DataAnalysis" /></el-col>
      <el-col :span="6"><KpiCard label="TimesFM MAE (零样本)" :value="currentField.tfmMae.toFixed(4)" :unit="currentField.unit" color="#10B981" :icon="MagicStick" /></el-col>
      <el-col :span="6"><KpiCard label="NRMSE (TFM)" :value="currentField.nrmseTfm.toFixed(1)" unit="%" :color="nrmseColor" :icon="TrendCharts" /></el-col>
      <el-col :span="6"><KpiCard label="TFM 相对 LSTM" :value="(currentField.tfmImprove > 0 ? '+' : '') + currentField.tfmImprove.toFixed(1)" unit="%" :color="currentField.tfmImprove > 0 ? '#10B981' : '#EF4444'" :icon="Promotion" /></el-col>
    </el-row>

    <!-- 预测曲线 -->
    <el-card class="mb-2">
      <template #header>
        <div class="card-header">
          <span>单窗口预测对比</span>
          <div class="ctrl">
            <el-select v-model="selectedField" style="width: 180px;">
              <el-option v-for="f in forecastFields" :key="f" :label="f" :value="f" />
            </el-select>
            <span class="label-inline">样本窗口</span>
            <el-input-number v-model="sampleIdx" :min="1" :max="60" size="small" style="width: 110px;" />
            <el-checkbox v-model="autoPick">自动选波动最大的</el-checkbox>
          </div>
        </div>
      </template>

      <v-chart :option="forecastOption" style="height: 380px" autoresize />
      <div class="sub-info" v-if="sampleMae !== null">
        本窗口 LSTM MAE = <b>{{ sampleMae.toFixed(4) }}</b> · 真实值波动 <b>{{ actualMin.toFixed(3) }} ~ {{ actualMax.toFixed(3) }}</b>
      </div>
    </el-card>

    <!-- 11 字段全景 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>11 字段 NRMSE 全景对比</span>
          <el-tag type="info" effect="plain">颜色 = 物理量族</el-tag>
        </div>
      </template>
      <v-chart :option="panoramaOption" style="height: 400px" autoresize />

      <el-table :data="sortedFields" class="mt-2" size="small" stripe>
        <el-table-column label="字段" prop="field" width="110" />
        <el-table-column label="物理量族" width="130">
          <template #default="{ row }">
            <el-tag :style="{ background: groupColor(row.group) + '22', color: groupColor(row.group), border: 'none' }" size="small">{{ row.group }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="SNR" prop="snr" width="90" align="right">
          <template #default="{ row }">{{ row.snr.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="ACF-16" prop="acfLag16" width="90" align="right">
          <template #default="{ row }">{{ row.acfLag16.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="LSTM MAE" width="110" align="right">
          <template #default="{ row }">{{ row.lstmMae.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="TFM MAE" width="110" align="right">
          <template #default="{ row }">{{ row.tfmMae.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="NRMSE LSTM" width="110" align="right">
          <template #default="{ row }">{{ row.nrmseLstm.toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="NRMSE TFM" width="110" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.nrmseTfm < 20 ? '#10B981' : row.nrmseTfm < 35 ? '#F59E0B' : '#EF4444', fontWeight: 600 }">
              {{ row.nrmseTfm.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="TFM 提升" width="110" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.tfmImprove > 0 ? '#10B981' : '#EF4444' }">
              {{ row.tfmImprove > 0 ? '+' : '' }}{{ row.tfmImprove.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="可用性" align="center">
          <template #default="{ row }">
            <span :class="'badge-' + row.grade.toLowerCase()">{{ row.grade }} 档</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent } from 'echarts/components'
import { DataAnalysis, MagicStick, TrendCharts, Promotion } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import { ensureLoaded, summary, forecast, groupColor } from '@/stores/data'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent])

const selectedField = ref('Magnitude')
const sampleIdx = ref(1)
const autoPick = ref(true)

onMounted(() => ensureLoaded())

const forecastFields = computed(() => Object.keys(forecast.value || {}))
const currentField = computed(() => (summary.value?.fields || []).find(f => f.field === selectedField.value))
const nrmseColor = computed(() => {
  if (!currentField.value) return '#4F7CFF'
  const n = currentField.value.nrmseTfm
  return n < 20 ? '#10B981' : n < 35 ? '#F59E0B' : '#EF4444'
})

const sortedFields = computed(() => [...(summary.value?.fields || [])].sort((a, b) => a.nrmseTfm - b.nrmseTfm))

// 预测曲线数据选择
const selectedSample = computed(() => {
  const fc = forecast.value?.[selectedField.value]
  if (!fc) return null
  const actuals = fc.actuals
  const preds = fc.preds
  let idx = sampleIdx.value - 1
  if (autoPick.value) {
    const stds = actuals.map(row => {
      const m = row.reduce((s, v) => s + v, 0) / row.length
      return Math.sqrt(row.reduce((s, v) => s + (v - m) ** 2, 0) / row.length)
    })
    const sortedIdx = [...stds.keys()].sort((a, b) => stds[b] - stds[a])
    idx = sortedIdx[Math.min(sampleIdx.value - 1, sortedIdx.length - 1)]
  }
  idx = Math.max(0, Math.min(idx, actuals.length - 1))
  return {
    idx,
    actual: actuals[idx],
    lstm: preds[idx],
  }
})

const sampleMae = computed(() => {
  const s = selectedSample.value
  if (!s) return null
  const diffs = s.actual.map((a, i) => Math.abs(a - s.lstm[i]))
  return diffs.reduce((sum, v) => sum + v, 0) / diffs.length
})
const actualMin = computed(() => selectedSample.value ? Math.min(...selectedSample.value.actual) : 0)
const actualMax = computed(() => selectedSample.value ? Math.max(...selectedSample.value.actual) : 0)

const forecastOption = computed(() => {
  const s = selectedSample.value
  if (!s) return {}
  const steps = Array.from({ length: 16 }, (_, i) => `t+${i + 1}`)
  const color = groupColor(currentField.value?.group)

  // 模拟 TFM: 用 actual 的轻度平滑作为"TimesFM 预测"(实际 TFM MAE 从 summary 给)
  // 真诚注释: 这里前端没法跑 TFM 模型, 只展示 LSTM 缓存 + 真实值
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 10 },
    grid: { top: 40, left: 60, right: 30, bottom: 50 },
    xAxis: { type: 'category', data: steps, name: '预测步 (秒)' },
    yAxis: { type: 'value', scale: true, name: currentField.value?.unit || '' },
    series: [
      {
        name: '真实值', type: 'line', data: s.actual,
        symbol: 'circle', symbolSize: 6,
        lineStyle: { color: '#0F172A', width: 2.5 },
        itemStyle: { color: '#0F172A' },
      },
      {
        name: 'LSTM 预测', type: 'line', data: s.lstm,
        symbol: 'circle', symbolSize: 5,
        lineStyle: { color: '#EF4444', width: 2, type: 'dashed' },
        itemStyle: { color: '#EF4444' },
      },
    ],
  }
})

const panoramaOption = computed(() => {
  const fields = summary.value?.fields || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 10, data: ['LSTM', 'TimesFM'] },
    grid: { top: 40, left: 60, right: 30, bottom: 60 },
    xAxis: {
      type: 'category', data: fields.map(f => f.field),
      axisLabel: { rotate: 25, fontSize: 11 },
    },
    yAxis: {
      type: 'value', name: 'NRMSE %',
    },
    series: [
      {
        name: 'LSTM', type: 'bar',
        data: fields.map(f => ({ value: f.nrmseLstm.toFixed(1), itemStyle: { color: groupColor(f.group), opacity: 0.45 } })),
        barGap: 0,
      },
      {
        name: 'TimesFM', type: 'bar',
        data: fields.map(f => ({ value: f.nrmseTfm.toFixed(1), itemStyle: { color: groupColor(f.group) } })),
        markLine: {
          silent: true,
          symbol: 'none',
          label: { formatter: '{b} {c}%' },
          data: [
            { yAxis: 20, name: 'A档', lineStyle: { color: '#10B981', type: 'dashed' } },
            { yAxis: 35, name: 'C档', lineStyle: { color: '#EF4444', type: 'dashed' } },
          ],
        },
      },
    ],
  }
})
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.ctrl { display: flex; align-items: center; gap: 12px; font-weight: normal; }
.label-inline { font-size: 13px; color: var(--text-mid); }
.sub-info { margin-top: 10px; font-size: 13px; color: var(--text-mid); }
</style>
