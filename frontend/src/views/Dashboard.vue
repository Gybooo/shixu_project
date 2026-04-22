<template>
  <div class="dashboard" v-loading="!summary">
    <!-- 顶部条 -->
    <div class="dash-header">
      <div class="dash-header-left">
        <div class="dash-clock">{{ date }}</div>
        <div class="dash-clock-time">{{ time }}</div>
      </div>
      <div class="dash-header-center">
        <div class="dash-title-bar">
          <span class="dash-title-deco">◆</span>
          <span class="dash-title-text">机器人振动预测性维护系统</span>
          <span class="dash-title-deco">◆</span>
        </div>
      </div>
      <div class="dash-header-right">
        <router-link to="/monitoring" class="exit-link">
          <el-icon><Back /></el-icon> 返回管理后台
        </router-link>
        <div class="dash-weather">
          <el-icon :size="18"><Sunny /></el-icon>
          <span>MPB_01 · 运行中</span>
        </div>
      </div>
    </div>

    <!-- 9 宫格主体 -->
    <div class="dash-grid" v-if="summary">
      <!-- 左上 · 当日告警 -->
      <div class="dash-panel">
        <div class="panel-title">
          <span class="arrow">»</span> 当日告警详情 <span class="arrow">«</span>
        </div>
        <div class="alarm-total">
          <div class="alarm-total-label">共计</div>
          <div class="alarm-total-value">{{ alarmCount }}</div>
          <div class="alarm-total-unit">次</div>
        </div>
        <div class="alarm-list">
          <div v-for="e in topAlarms" :key="e.id" class="alarm-item">
            <span class="alarm-time">{{ formatTime(e.startTime) }}</span>
            <span class="alarm-code">MPB_01</span>
            <span class="alarm-text">{{ e.type }} · {{ e.durationSeconds }}s</span>
          </div>
        </div>
      </div>

      <!-- 左中 · 空置预留 -->
      <div class="dash-panel">
        <div class="panel-title">
          <span class="arrow">»</span> 字段健康状态 <span class="arrow">«</span>
        </div>
        <v-chart :option="gradeOption" class="chart" autoresize />
      </div>

      <!-- 中间大 · 产线监控 -->
      <div class="dash-panel panel-center">
        <div class="panel-title">
          <span class="arrow">»</span> 全字段预警监控 <span class="arrow">«</span>
        </div>
        <div class="production-line">
          <div class="line-group">
            <div class="line-label">合成幅值 & 加速度 RMS</div>
            <div class="line-blocks">
              <div v-for="f in groupA" :key="f.field" class="field-block"
                   :class="'grade-' + f.grade.toLowerCase()">
                <div class="field-lights">
                  <span class="light light-r"></span>
                  <span class="light light-y"></span>
                  <span class="light light-g"></span>
                  <span class="light light-b"></span>
                </div>
                <div class="field-name">{{ f.field }}</div>
              </div>
            </div>
          </div>
          <div class="line-group">
            <div class="line-label">速度 RMS</div>
            <div class="line-blocks">
              <div v-for="f in groupB" :key="f.field" class="field-block"
                   :class="'grade-' + f.grade.toLowerCase()">
                <div class="field-lights">
                  <span class="light light-r"></span>
                  <span class="light light-y"></span>
                  <span class="light light-g"></span>
                  <span class="light light-b"></span>
                </div>
                <div class="field-name">{{ f.field }}</div>
              </div>
            </div>
          </div>
          <div class="line-group">
            <div class="line-label">冲击类</div>
            <div class="line-blocks">
              <div v-for="f in groupC" :key="f.field" class="field-block"
                   :class="'grade-' + f.grade.toLowerCase()">
                <div class="field-lights">
                  <span class="light light-r"></span>
                  <span class="light light-y"></span>
                  <span class="light light-g"></span>
                  <span class="light light-b"></span>
                </div>
                <div class="field-name">{{ f.field }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右上 · 可用性占比 -->
      <div class="dash-panel">
        <div class="panel-title">
          <span class="arrow">»</span> 字段可用性占比 <span class="arrow">«</span>
        </div>
        <v-chart :option="gradePieOption" class="chart" autoresize />
      </div>

      <!-- 右下 · NRMSE Top5 -->
      <div class="dash-panel">
        <div class="panel-title">
          <span class="arrow">»</span> 模型性能 Top5 <span class="arrow">«</span>
        </div>
        <v-chart :option="top5Option" class="chart" autoresize />
      </div>

      <!-- 左下 · 族内分布 -->
      <div class="dash-panel">
        <div class="panel-title">
          <span class="arrow">»</span> 物理量族内一致性 <span class="arrow">«</span>
        </div>
        <v-chart :option="groupOption" class="chart" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
  DatasetComponent, TransformComponent,
} from 'echarts/components'
import dayjs from 'dayjs'
import { ensureLoaded, summary, alarms, gradeColor, groupColor } from '@/stores/data'

use([
  CanvasRenderer, PieChart, BarChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
  DatasetComponent, TransformComponent,
])

const date = ref('')
const time = ref('')
let timer = null

onMounted(async () => {
  await ensureLoaded()
  const updateTime = () => {
    const now = dayjs()
    date.value = now.format('YYYY年M月D日')
    time.value = now.format('HH:mm:ss')
  }
  updateTime()
  timer = setInterval(updateTime, 1000)
})
onUnmounted(() => timer && clearInterval(timer))

const fields = computed(() => summary.value?.fields || [])
const groupA = computed(() => fields.value.filter(f =>
  ['合成幅值', '加速度RMS'].includes(f.group)))
const groupB = computed(() => fields.value.filter(f => f.group === '速度RMS'))
const groupC = computed(() => fields.value.filter(f => f.group === '冲击类'))

const alarmCount = computed(() => alarms.value?.events?.length || 0)
const topAlarms = computed(() => (alarms.value?.events || []).slice(0, 4))
function formatTime(iso) {
  return dayjs(iso).format('HH:mm:ss')
}

// ECharts 通用深色 theme
const AXIS = {
  axisLine: { lineStyle: { color: 'rgba(255,255,255,0.25)' } },
  axisLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 11 },
  splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)', type: 'dashed' } },
}

// 图表 1: 字段健康度柱状图 (各字段 NRMSE)
const gradeOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(15, 38, 103, 0.95)',
    borderColor: '#4F7CFF', textStyle: { color: 'white' },
  },
  grid: { top: 30, left: 48, right: 12, bottom: 44 },
  xAxis: {
    type: 'category',
    data: fields.value.map(f => f.field),
    ...AXIS,
    axisLabel: { ...AXIS.axisLabel, rotate: 35, fontSize: 10 },
  },
  yAxis: { type: 'value', ...AXIS, name: 'NRMSE %', nameTextStyle: { color: '#94B4FF', fontSize: 11 } },
  series: [{
    type: 'bar',
    data: fields.value.map(f => ({
      value: f.nrmseTfm.toFixed(1),
      itemStyle: { color: gradeColor(f.grade) },
    })),
    barWidth: 18,
    label: { show: true, position: 'top', color: 'white', fontSize: 10 },
  }],
}))

// 图表 2: 可用性饼图
const gradePieOption = computed(() => {
  const grades = { A: 0, B: 0, C: 0 }
  fields.value.forEach(f => grades[f.grade]++)
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 个 ({d}%)' },
    legend: {
      bottom: 0, textStyle: { color: 'rgba(255,255,255,0.75)', fontSize: 11 },
      itemWidth: 12, itemHeight: 12,
    },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#0B1B4B', borderWidth: 2 },
      label: {
        show: true, color: 'white', fontSize: 11,
        formatter: '{b}\n{d}%',
      },
      data: [
        { name: 'A 档', value: grades.A, itemStyle: { color: '#10B981' } },
        { name: 'B 档', value: grades.B, itemStyle: { color: '#F59E0B' } },
        { name: 'C 档', value: grades.C, itemStyle: { color: '#EF4444' } },
      ],
    }],
  }
})

// 图表 3: Top5 柱状图
const top5Option = computed(() => {
  const sorted = [...fields.value].sort((a, b) => a.nrmseTfm - b.nrmseTfm).slice(0, 5)
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 20, left: 64, right: 24, bottom: 24 },
    xAxis: { type: 'value', ...AXIS },
    yAxis: {
      type: 'category',
      data: sorted.map(f => f.field).reverse(),
      ...AXIS,
      axisLabel: { ...AXIS.axisLabel, fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: sorted.map(f => ({
        value: f.nrmseTfm.toFixed(1),
        itemStyle: { color: groupColor(f.group) },
      })).reverse(),
      barWidth: 14,
      label: { show: true, position: 'right', color: 'white', fontSize: 10, formatter: '{c}%' },
    }],
  }
})

// 图表 4: 物理量族箱线图
const groupOption = computed(() => {
  const groups = ['合成幅值', '加速度RMS', '速度RMS', '冲击类']
  const data = groups.map(g => {
    const vals = fields.value.filter(f => f.group === g).map(f => f.nrmseTfm)
    vals.sort((a, b) => a - b)
    if (vals.length === 0) return [0, 0, 0, 0, 0]
    const q1 = vals[Math.floor(vals.length * 0.25)] || vals[0]
    const q3 = vals[Math.floor(vals.length * 0.75)] || vals[vals.length - 1]
    const mid = vals[Math.floor(vals.length / 2)]
    return [vals[0], q1, mid, q3, vals[vals.length - 1]]
  })
  return {
    tooltip: { trigger: 'item' },
    grid: { top: 20, left: 48, right: 24, bottom: 60 },
    xAxis: {
      type: 'category', data: groups, ...AXIS,
      axisLabel: { ...AXIS.axisLabel, fontSize: 11, interval: 0 },
    },
    yAxis: { type: 'value', ...AXIS, name: 'NRMSE %', nameTextStyle: { color: '#94B4FF', fontSize: 11 } },
    series: [{
      type: 'boxplot',
      data: data,
      itemStyle: {
        color: 'rgba(79, 124, 255, 0.4)',
        borderColor: '#4F7CFF', borderWidth: 1.5,
      },
    }],
  }
})
</script>

<style lang="scss" scoped>
.dashboard {
  width: 100vw;
  height: 100vh;
  background:
    radial-gradient(ellipse at top, rgba(79, 124, 255, 0.12), transparent 60%),
    linear-gradient(135deg, #0A1536 0%, #0F2667 50%, #132B6B 100%);
  background-size: 100% 100%;
  position: relative;
  overflow: hidden;
  color: white;
  font-family: "Microsoft YaHei", sans-serif;
  padding: 14px 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 电路纹理 */
.dashboard::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79, 124, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 124, 255, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

/* Header */
.dash-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 20px;
  padding: 0 0 12px 0;
  position: relative;
  z-index: 1;
}
.dash-header-left {
  font-family: "Consolas", monospace;
  color: #7AB8FF;
}
.dash-clock {
  font-size: 13px;
  letter-spacing: 0.1em;
  opacity: 0.85;
}
.dash-clock-time {
  font-size: 18px;
  font-weight: 600;
  margin-top: 2px;
  color: white;
}
.dash-title-bar {
  background: linear-gradient(180deg, rgba(79, 124, 255, 0.25), rgba(15, 38, 103, 0.85));
  border-top: 2px solid #4F7CFF;
  border-bottom: 2px solid #4F7CFF;
  padding: 8px 46px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 0 24px rgba(79, 124, 255, 0.4);
  clip-path: polygon(30px 0%, 100% 0%, calc(100% - 30px) 100%, 0% 100%);
}
.dash-title-text {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.2em;
  background: linear-gradient(180deg, #E0F0FF, #7AB8FF);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.dash-title-deco {
  color: #4F7CFF;
  font-size: 12px;
  animation: rotate 4s linear infinite;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.dash-header-right {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 14px;
}
.exit-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid rgba(79, 124, 255, 0.5);
  border-radius: 4px;
  color: #7AB8FF;
  text-decoration: none;
  font-size: 12.5px;
  transition: all 0.2s;
  &:hover {
    background: rgba(79, 124, 255, 0.2);
    color: white;
  }
}
.dash-weather {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7AB8FF;
  font-size: 14px;
  font-weight: 600;
}

/* 网格 */
.dash-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 14px;
  position: relative;
  z-index: 1;
  min-height: 0;
}
.dash-panel {
  background: rgba(15, 38, 103, 0.4);
  border: 1px solid rgba(79, 124, 255, 0.3);
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(6px);
  position: relative;
  overflow: hidden;
  min-height: 0;
}
.dash-panel::before, .dash-panel::after {
  content: "";
  position: absolute;
  width: 14px; height: 14px;
  border: 2px solid #4F7CFF;
}
.dash-panel::before { top: 4px; left: 4px; border-right: none; border-bottom: none; }
.dash-panel::after { bottom: 4px; right: 4px; border-left: none; border-top: none; }
.panel-center {
  grid-row: span 2;
}
.panel-title {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #7AB8FF;
  padding: 4px 0 10px 0;
  .arrow {
    color: #4F7CFF;
    margin: 0 8px;
  }
}

/* 告警 */
.alarm-total {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  padding: 12px 0 14px;
}
.alarm-total-label { font-size: 13px; opacity: 0.7; }
.alarm-total-value {
  font-size: 52px;
  font-weight: 800;
  color: #FFB84C;
  text-shadow: 0 0 20px rgba(255, 184, 76, 0.6);
  font-family: "Consolas", monospace;
  line-height: 1;
}
.alarm-total-unit { font-size: 13px; opacity: 0.7; }

.alarm-list {
  flex: 1;
  overflow: auto;
}
.alarm-item {
  display: grid;
  grid-template-columns: 80px 80px 1fr;
  gap: 8px;
  padding: 6px 8px;
  font-size: 11.5px;
  border-bottom: 1px dashed rgba(79, 124, 255, 0.15);
  color: rgba(255, 255, 255, 0.82);
  font-family: "Consolas", monospace;
}
.alarm-time { color: #7AB8FF; }
.alarm-code { color: #10B981; }

/* 产线方块 */
.production-line {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  gap: 14px;
  padding: 10px 0;
}
.line-label {
  font-size: 11px;
  color: #7AB8FF;
  margin-bottom: 8px;
  letter-spacing: 0.1em;
  font-weight: 600;
  padding-left: 10px;
  border-left: 3px solid #4F7CFF;
}
.line-blocks {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
.field-block {
  background: linear-gradient(180deg, rgba(79, 124, 255, 0.2), rgba(15, 38, 103, 0.7));
  border: 1.5px solid rgba(79, 124, 255, 0.4);
  border-radius: 6px;
  padding: 10px 14px;
  min-width: 96px;
  text-align: center;
  transition: all 0.22s;
  cursor: pointer;
}
.field-block:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 18px rgba(79, 124, 255, 0.5);
}
.field-block.grade-a { border-color: rgba(16, 185, 129, 0.6); }
.field-block.grade-b { border-color: rgba(245, 158, 11, 0.6); }
.field-block.grade-c { border-color: rgba(239, 68, 68, 0.6); }
.field-lights {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;
  margin-bottom: 8px;
  padding: 4px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
}
.light {
  width: 100%;
  height: 10px;
  border-radius: 2px;
}
.grade-a .light-r { background: #EF4444; opacity: 0.15; }
.grade-a .light-y { background: #F59E0B; opacity: 0.15; }
.grade-a .light-g { background: #10B981; box-shadow: 0 0 8px #10B981; }
.grade-a .light-b { background: #4F7CFF; box-shadow: 0 0 8px #4F7CFF; }

.grade-b .light-r { background: #EF4444; opacity: 0.15; }
.grade-b .light-y { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
.grade-b .light-g { background: #10B981; opacity: 0.3; }
.grade-b .light-b { background: #4F7CFF; opacity: 0.3; }

.grade-c .light-r { background: #EF4444; box-shadow: 0 0 8px #EF4444; }
.grade-c .light-y { background: #F59E0B; opacity: 0.15; }
.grade-c .light-g { background: #10B981; opacity: 0.1; }
.grade-c .light-b { background: #4F7CFF; opacity: 0.1; }

.field-name {
  font-size: 12.5px;
  font-weight: 600;
  color: white;
  font-family: "Consolas", monospace;
}

/* ECharts */
.chart {
  flex: 1;
  width: 100%;
  min-height: 0;
}
</style>
