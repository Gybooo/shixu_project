<template>
  <div v-loading="!correlation">
    <PageHeader title="根因追溯" subtitle="11 × 11 字段相关矩阵 · 故障关联定位" module="智能分析" />

    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><KpiCard label="字段对总数" :value="55" unit="对" :icon="Connection" /></el-col>
      <el-col :span="6"><KpiCard label="强相关" :value="strongCount" unit="对 (|r|>0.7)" color="#10B981" :icon="Link" /></el-col>
      <el-col :span="6"><KpiCard label="中度相关" :value="midCount" unit="对 (0.3~0.7)" color="#F59E0B" :icon="Share" /></el-col>
      <el-col :span="6"><KpiCard label="几乎无关" :value="weakCount" unit="对 (|r|<0.3)" color="#94A3B8" :icon="Close" /></el-col>
    </el-row>

    <el-card class="mb-2">
      <template #header>相关矩阵热力图</template>
      <v-chart :option="heatmapOption" style="height: 560px" autoresize />
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><span class="text-success">强相关 Top 5</span></template>
          <el-table :data="topPairs" size="small">
            <el-table-column label="#" prop="rank" width="50" align="center" />
            <el-table-column label="字段 A" prop="a" />
            <el-table-column label="字段 B" prop="b" />
            <el-table-column label="r" prop="r" align="right" width="100">
              <template #default="{ row }">
                <span class="text-success" style="font-weight: 600; font-family: Consolas, monospace;">{{ row.r.toFixed(3) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span class="text-light">独立关联 Top 5</span></template>
          <el-table :data="bottomPairs" size="small">
            <el-table-column label="#" prop="rank" width="50" align="center" />
            <el-table-column label="字段 A" prop="a" />
            <el-table-column label="字段 B" prop="b" />
            <el-table-column label="r" prop="r" align="right" width="100">
              <template #default="{ row }">
                <span style="font-family: Consolas, monospace;">{{ row.r.toFixed(3) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-alert class="mt-2" type="info" :closable="false" show-icon>
      <template #title>
        <b>根因定位建议</b>
      </template>
      <div style="font-size: 13px; line-height: 1.7;">
        Magnitude 与 aRMS/vRMS 系列相关系数 0.86-0.98, 本质源于同一物理量, 可互为冗余参考;
        Shock 系列与其他字段基本独立 (r ~ 0.05), 瞬时撞击事件需独立建模。
        定位故障时建议优先查看强相关字段的同期走势, 可快速缩小故障范围。
      </div>
    </el-alert>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { Connection, Link, Share, Close } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import { ensureLoaded, correlation } from '@/stores/data'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

onMounted(() => ensureLoaded())

const allPairs = computed(() => {
  const data = correlation.value
  if (!data) return []
  const out = []
  for (let i = 0; i < data.fields.length; i++) {
    for (let j = i + 1; j < data.fields.length; j++) {
      out.push({ a: data.fields[i], b: data.fields[j], r: data.matrix[i][j] })
    }
  }
  return out.sort((a, b) => Math.abs(b.r) - Math.abs(a.r))
})

const strongCount = computed(() => allPairs.value.filter(p => Math.abs(p.r) > 0.7).length)
const midCount = computed(() => allPairs.value.filter(p => Math.abs(p.r) > 0.3 && Math.abs(p.r) <= 0.7).length)
const weakCount = computed(() => allPairs.value.filter(p => Math.abs(p.r) <= 0.3).length)

const topPairs = computed(() => allPairs.value.slice(0, 5).map((p, i) => ({ ...p, rank: i + 1 })))
const bottomPairs = computed(() => [...allPairs.value].sort((a, b) => Math.abs(a.r) - Math.abs(b.r)).slice(0, 5).map((p, i) => ({ ...p, rank: i + 1 })))

const heatmapOption = computed(() => {
  const data = correlation.value
  if (!data) return {}
  const seriesData = []
  for (let i = 0; i < data.fields.length; i++) {
    for (let j = 0; j < data.fields.length; j++) {
      seriesData.push([j, i, data.matrix[i][j]])
    }
  }
  return {
    tooltip: {
      formatter: (p) => `<b>${data.fields[p.value[0]]} × ${data.fields[p.value[1]]}</b><br/>r = ${p.value[2].toFixed(3)}`,
    },
    grid: { top: 30, left: 90, right: 60, bottom: 80 },
    xAxis: { type: 'category', data: data.fields, axisLabel: { rotate: 30 } },
    yAxis: { type: 'category', data: data.fields },
    visualMap: {
      min: -1, max: 1,
      orient: 'vertical',
      right: 0, top: 'center',
      inRange: { color: ['#EF4444', '#FCD34D', '#FFFFFF', '#93C5FD', '#4F7CFF'] },
    },
    series: [{
      type: 'heatmap',
      data: seriesData,
      label: { show: true, formatter: (p) => p.value[2].toFixed(2), fontSize: 10 },
      itemStyle: { borderColor: 'white', borderWidth: 1 },
    }],
  }
})
</script>
