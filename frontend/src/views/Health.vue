<template>
  <div v-loading="!summary">
    <PageHeader title="健康管理" subtitle="ACF × SNR × NRMSE 三维可用性判据 · 新字段在线评估" module="智能分析">
      <template #actions>
        <el-tag type="success" effect="plain">判据 v2 · 命中率 11/11</el-tag>
      </template>
    </PageHeader>

    <!-- 判据象限图 -->
    <el-card class="mb-2">
      <template #header>
        <div class="card-header">
          <span>11 字段可用性象限</span>
          <span class="sub text-mid">横轴: ACF lag-16 · 纵轴: SNR (对数) · 气泡大小: NRMSE</span>
        </div>
      </template>
      <v-chart :option="quadrantOption" style="height: 520px" autoresize />
    </el-card>

    <!-- 计算器 -->
    <el-row :gutter="16">
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>⚡ 新字段可用性在线评估</span>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item>
              <div class="label-row">
                <span>或从已验证字段选择</span>
              </div>
              <el-select v-model="preset" @change="applyPreset" style="width: 100%;">
                <el-option label="自定义输入" value="" />
                <el-option v-for="f in fields" :key="f.field" :label="`${f.field} (${f.grade}档, NRMSE ${f.nrmseTfm.toFixed(1)}%)`" :value="f.field" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <div class="label-row">
                <span>ACF lag-16 <span class="hint">(趋势长程可预测性)</span></span>
                <b>{{ acf.toFixed(3) }}</b>
              </div>
              <el-slider v-model="acf" :min="0" :max="1" :step="0.01" :marks="{ 0.55: 'B', 0.75: 'A' }" />
            </el-form-item>

            <el-form-item>
              <div class="label-row">
                <span>SNR <span class="hint">(信噪比 = 趋势/噪声)</span></span>
                <b>{{ snr.toFixed(2) }}</b>
              </div>
              <el-slider v-model="snr" :min="0" :max="3" :step="0.05" :marks="{ 0.5: 'red', 1.3: 'A' }" />
            </el-form-item>

            <el-form-item>
              <div class="label-row">
                <span>NRMSE <span class="hint">(MAE / 趋势std)</span></span>
                <b>{{ nrmse.toFixed(1) }}%</b>
              </div>
              <el-slider v-model="nrmse" :min="0" :max="100" :step="0.5" :marks="{ 20: 'A', 35: 'C' }" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card :style="{ borderLeft: `4px solid ${gradeColor(result.grade)}` }">
          <template #header>评估结果</template>

          <div class="grade-result">
            <div class="grade-badge" :style="{ background: gradeColor(result.grade) }">{{ result.grade }}</div>
            <div>
              <div class="grade-title">{{ result.text }}</div>
              <div class="grade-sub">判据版本 v2 · 硬红线 SNR &lt; 0.5 → C 档</div>
            </div>
          </div>

          <div class="reasons">
            <div class="reasons-title">评估依据</div>
            <div v-for="(r, i) in reasons" :key="i" class="reason-row">
              <span class="reason-icon" :style="{ color: gradeColor(result.grade) }">{{ r.icon }}</span>
              <span>{{ r.text }}</span>
            </div>
          </div>

          <el-alert :title="advice" type="info" :closable="false" show-icon class="mt-2" />

          <el-collapse class="mt-2">
            <el-collapse-item title="📜 判据 v2 代码实现">
              <pre class="code-block">function classify(nrmse, acf16, snr) {
  if (snr &lt; 0.5) return 'C 不建议直接使用'  // 硬红线
  if (nrmse &lt; 20 && acf16 &gt; 0.75 && snr &gt; 1.3) return 'A 可直接部署'
  if (nrmse &lt; 25 && acf16 &gt; 0.70) return 'B 可用, 建议复核'
  return 'C 不建议直接使用'
}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent } from 'echarts/components'
import PageHeader from '@/components/PageHeader.vue'
import { ensureLoaded, summary, classifyUsability, gradeColor, groupColor } from '@/stores/data'

use([CanvasRenderer, ScatterChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent])

onMounted(() => ensureLoaded())

const fields = computed(() => summary.value?.fields || [])

const preset = ref('')
const acf = ref(0.80)
const snr = ref(1.50)
const nrmse = ref(15.0)

function applyPreset(field) {
  if (!field) return
  const f = fields.value.find(x => x.field === field)
  if (f) {
    acf.value = parseFloat(f.acfLag16.toFixed(3))
    snr.value = Math.min(3, parseFloat(f.snr.toFixed(2)))
    nrmse.value = parseFloat(f.nrmseTfm.toFixed(1))
  }
}

const result = computed(() => classifyUsability(nrmse.value, acf.value, snr.value))
const reasons = computed(() => {
  const r = []
  if (result.value.grade === 'A') {
    r.push({ icon: '✓', text: `NRMSE ${nrmse.value.toFixed(1)}% < 20%, 预测误差可控` })
    r.push({ icon: '✓', text: `ACF lag-16 = ${acf.value.toFixed(2)} > 0.75, 信号具备长程记忆` })
    r.push({ icon: '✓', text: `SNR = ${snr.value.toFixed(2)} > 1.3, 规律高于噪声` })
  } else if (result.value.grade === 'B') {
    r.push({ icon: '⚠', text: `NRMSE ${nrmse.value.toFixed(1)}%, 精度中等` })
    if (acf.value < 0.75) r.push({ icon: '⚠', text: `ACF ${acf.value.toFixed(2)}, 长程记忆中等` })
    if (snr.value < 1.3) r.push({ icon: '⚠', text: `SNR ${snr.value.toFixed(2)}, 信噪比略低` })
  } else {
    if (snr.value < 0.5) r.push({ icon: '✗', text: `SNR ${snr.value.toFixed(2)} < 0.5, 噪声掩盖信号 (硬红线)` })
    if (acf.value < 0.55) r.push({ icon: '✗', text: `ACF ${acf.value.toFixed(2)} < 0.55, 缺乏长程依赖` })
    if (nrmse.value > 35) r.push({ icon: '✗', text: `NRMSE ${nrmse.value.toFixed(1)}% > 35%, 偏差严重` })
  }
  return r
})
const advice = computed(() => {
  if (result.value.grade === 'A') return '建议直接部署: SavGol(61,3) + TimesFM + horizon=16 标准配置'
  if (result.value.grade === 'B') return '可用但需人工复核: 建议加大 context 或缩短 horizon 至 8'
  return '不建议使用本方案: 改用脉冲事件检测或分位数回归'
})

const quadrantOption = computed(() => {
  const byGroup = {}
  fields.value.forEach(f => {
    if (!byGroup[f.group]) byGroup[f.group] = []
    byGroup[f.group].push(f)
  })
  const series = Object.entries(byGroup).map(([group, arr]) => ({
    name: group,
    type: 'scatter',
    data: arr.map(f => ({
      value: [f.acfLag16, f.snr, f.nrmseTfm],
      label: { show: true, formatter: f.field, position: 'top', fontSize: 10, fontWeight: 600 },
      itemStyle: { color: groupColor(group), opacity: 0.8, borderColor: 'white', borderWidth: 2 },
    })),
    symbolSize: (v) => 14 + v[2] * 0.9,
  }))
  // 用户当前输入位置
  series.push({
    name: '当前输入',
    type: 'scatter',
    data: [{
      value: [acf.value, Math.max(0.2, snr.value), nrmse.value],
      itemStyle: { color: gradeColor(result.value.grade), borderColor: 'white', borderWidth: 3 },
      label: { show: true, formatter: '当前', position: 'right', color: gradeColor(result.value.grade), fontSize: 11, fontWeight: 700 },
    }],
    symbolSize: (v) => 22 + v[2] * 0.8,
  })
  return {
    tooltip: {
      formatter: (p) => `<b>${p.data.label?.formatter || p.seriesName}</b><br/>ACF: ${p.value[0].toFixed(3)}<br/>SNR: ${p.value[1].toFixed(3)}<br/>NRMSE: ${p.value[2].toFixed(1)}%`,
    },
    legend: { bottom: 0 },
    grid: { top: 30, left: 60, right: 40, bottom: 60 },
    xAxis: { type: 'value', name: 'ACF lag-16', min: 0.35, max: 1.0, splitNumber: 6 },
    yAxis: { type: 'log', name: 'SNR (对数)', min: 0.15, max: 3 },
    series,
  }
})
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.sub { font-size: 12px; font-weight: normal; }
.label-row { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; color: var(--text-mid); }
.label-row b { color: var(--primary); font-family: Consolas, monospace; }
.hint { color: var(--text-light); font-size: 11px; margin-left: 4px; }

.grade-result { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.grade-badge {
  width: 52px; height: 52px; border-radius: 12px;
  color: white; font-weight: 800; font-size: 28px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.grade-title { font-size: 17px; font-weight: 700; color: var(--text); }
.grade-sub { font-size: 12px; color: var(--text-light); margin-top: 3px; }

.reasons-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
.reason-row { display: flex; gap: 8px; font-size: 13px; color: var(--text-mid); padding: 3px 0; }
.reason-icon { font-weight: 700; }

.code-block {
  background: #0F172A; color: #E2E8F0;
  padding: 14px 16px; border-radius: 6px;
  font-family: Consolas, Menlo, monospace;
  font-size: 13px; line-height: 1.6;
  overflow-x: auto; margin: 0;
}
</style>
