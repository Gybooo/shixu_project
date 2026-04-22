<template>
  <div v-loading="!summary">
    <PageHeader title="运行状态监控" subtitle="设备通道拓扑 · 字段时序曲线与趋势分析" module="运行状态监控" />

    <!-- 产线拓扑 -->
    <div class="mb-2">
      <ProductionLineTopo :fields="fields" @select="onSelect" />
    </div>

    <el-card class="mb-2">
      <el-row :gutter="16" align="middle">
        <el-col :span="6">
          <div class="label">监测字段</div>
          <el-select v-model="selectedField" @change="draw">
            <el-option v-for="f in fields" :key="f.field" :label="f.field + ` (${f.group})`" :value="f.field" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <div class="label">叠加趋势</div>
          <el-switch v-model="showTrend" @change="draw" />
        </el-col>
        <el-col :span="14">
          <div class="stats-row" v-if="currentField">
            <div class="stat"><span class="stat-label">均值</span><span class="stat-val">{{ currentField.mean.toFixed(3) }}</span></div>
            <div class="stat"><span class="stat-label">趋势 std</span><span class="stat-val">{{ currentField.trendStd.toFixed(3) }}</span></div>
            <div class="stat"><span class="stat-label">SNR</span><span class="stat-val">{{ currentField.snr.toFixed(2) }}</span></div>
            <div class="stat"><span class="stat-label">ACF-16</span><span class="stat-val">{{ currentField.acfLag16.toFixed(3) }}</span></div>
            <div class="stat"><span class="stat-label">判据</span>
              <span :class="'badge-' + currentField.grade.toLowerCase()">{{ currentField.grade }} 档</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>时序曲线 · {{ selectedField }}</span>
          <el-tag type="info" effect="plain">{{ seriesLength }} 点 · 6s 采样</el-tag>
        </div>
      </template>
      <v-chart :option="chartOption" style="height: 440px" autoresize />
    </el-card>

    <el-row :gutter="16" class="mt-2">
      <el-col :span="12">
        <el-card>
          <template #header>数值分布</template>
          <v-chart :option="histOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>滚动标准差</template>
          <v-chart :option="rollingStdOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent } from 'echarts/components'
import dayjs from 'dayjs'
import PageHeader from '@/components/PageHeader.vue'
import ProductionLineTopo from '@/components/ProductionLineTopo.vue'
import { ensureLoaded, summary, timeseries, groupColor } from '@/stores/data'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent])

const selectedField = ref('Magnitude')
const showTrend = ref(true)

const fields = computed(() => summary.value?.fields || [])
const currentField = computed(() => fields.value.find(f => f.field === selectedField.value))
const seriesLength = computed(() => timeseries.value?.fields?.[selectedField.value]?.length || 0)

onMounted(async () => { await ensureLoaded(); draw() })
watch([() => summary.value, () => timeseries.value], () => draw())

function draw() {}  // placeholder; computed 自动更新
function onSelect(field) { selectedField.value = field }

// SavGol 近似: 移动均值 (前端不做完整 SavGol, 用滚动均值近似趋势)
function rollingMean(arr, window) {
  const out = new Array(arr.length).fill(null)
  const half = Math.floor(window / 2)
  for (let i = 0; i < arr.length; i++) {
    let sum = 0, cnt = 0
    for (let j = Math.max(0, i - half); j <= Math.min(arr.length - 1, i + half); j++) {
      if (arr[j] != null) { sum += arr[j]; cnt++ }
    }
    out[i] = cnt > 0 ? sum / cnt : null
  }
  return out
}

const chartOption = computed(() => {
  const ts = timeseries.value
  if (!ts || !ts.fields[selectedField.value]) return {}
  const data = ts.fields[selectedField.value]
  const times = ts.timestamps.map(t => dayjs(t).format('HH:mm:ss'))
  const color = groupColor(currentField.value?.group)
  const trend = showTrend.value ? rollingMean(data, 15) : null

  const series = [{
    name: '原始', type: 'line', data,
    showSymbol: false,
    lineStyle: { color, width: 1 },
    areaStyle: { color, opacity: 0.08 },
  }]
  if (trend) {
    series.push({
      name: '趋势 (滚动均值 ±45s)', type: 'line', data: trend,
      showSymbol: false,
      lineStyle: { color: '#1E3A8A', width: 2.2 },
    })
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 10 },
    grid: { top: 40, left: 60, right: 30, bottom: 60 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: { type: 'value', scale: true, name: currentField.value?.unit || '' },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 24, bottom: 10 },
    ],
    series,
  }
})

const histOption = computed(() => {
  const ts = timeseries.value
  if (!ts || !ts.fields[selectedField.value]) return {}
  const data = ts.fields[selectedField.value].filter(v => v != null)
  const bins = 40
  const min = Math.min(...data), max = Math.max(...data)
  const step = (max - min) / bins
  const hist = new Array(bins).fill(0)
  data.forEach(v => {
    const i = Math.min(bins - 1, Math.floor((v - min) / step))
    hist[i]++
  })
  const labels = hist.map((_, i) => (min + (i + 0.5) * step).toFixed(2))
  const color = groupColor(currentField.value?.group)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: labels, name: currentField.value?.unit || '' },
    yAxis: { type: 'value', name: '频次' },
    series: [{ type: 'bar', data: hist, itemStyle: { color }, barWidth: '80%' }],
  }
})

const rollingStdOption = computed(() => {
  const ts = timeseries.value
  if (!ts || !ts.fields[selectedField.value]) return {}
  const data = ts.fields[selectedField.value]
  const window = 20
  const out = new Array(data.length).fill(null)
  for (let i = window; i < data.length; i++) {
    const slice = data.slice(i - window, i).filter(v => v != null)
    if (slice.length < 3) continue
    const mean = slice.reduce((s, v) => s + v, 0) / slice.length
    const variance = slice.reduce((s, v) => s + (v - mean) ** 2, 0) / slice.length
    out[i] = Math.sqrt(variance)
  }
  const times = ts.timestamps.map(t => dayjs(t).format('HH:mm'))
  const color = groupColor(currentField.value?.group)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, left: 60, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: times, boundaryGap: false },
    yAxis: { type: 'value', scale: true, name: '波动幅度' },
    series: [{
      type: 'line', data: out, showSymbol: false,
      lineStyle: { color, width: 1.8 },
      areaStyle: { color, opacity: 0.18 },
    }],
  }
})
</script>

<style lang="scss" scoped>
.label { font-size: 12px; color: var(--text-mid); margin-bottom: 6px; }
.stats-row { display: flex; gap: 18px; align-items: center; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-label { font-size: 11px; color: var(--text-light); letter-spacing: 0.06em; text-transform: uppercase; }
.stat-val { font-size: 16px; font-weight: 600; color: var(--text); font-family: Consolas, monospace; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
</style>
