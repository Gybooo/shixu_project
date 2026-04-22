<template>
  <div class="topo-wrap">
    <div class="topo-title">
      <div class="topo-title-left">
        <el-icon><Monitor /></el-icon>
        <span>MPB_01 振动传感器 · 信号通道布局</span>
      </div>
      <div class="topo-legend">
        <span class="dot dot-a"></span> A 档字段 ({{ counts.A }})
        <span class="dot dot-b"></span> B 档 ({{ counts.B }})
        <span class="dot dot-c"></span> C 档 ({{ counts.C }})
      </div>
    </div>

    <div class="topo-content">
      <!-- 顶部: 传感器主体 -->
      <div class="sensor-header">
        <div class="sensor-box">
          <el-icon :size="28"><Cpu /></el-icon>
          <div class="sensor-label">MPB_01 传感器</div>
          <div class="sensor-status">
            <span class="status-pulse"></span> 在线 · 11 通道
          </div>
        </div>
        <div class="connect-line"></div>
      </div>

      <!-- 3 组 × 通道 -->
      <div class="groups">
        <div v-for="g in groups" :key="g.name" class="group" :style="{ borderColor: g.color }">
          <div class="group-header" :style="{ background: g.color + '15', color: g.color }">
            <span class="group-name">{{ g.name }}</span>
            <span class="group-count">{{ g.fields.length }} 通道</span>
          </div>
          <div class="group-channels">
            <div
              v-for="f in g.fields" :key="f.field"
              class="channel" :class="'grade-' + f.grade.toLowerCase()"
              @click="$emit('select', f.field)"
            >
              <div class="channel-top">
                <div class="channel-light"></div>
                <div class="channel-name">{{ f.field }}</div>
              </div>
              <div class="channel-metric">
                <span class="metric-label">NRMSE</span>
                <span class="metric-val">{{ f.nrmseTfm.toFixed(1) }}%</span>
              </div>
              <div class="channel-metric">
                <span class="metric-label">SNR</span>
                <span class="metric-val">{{ f.snr.toFixed(2) }}</span>
              </div>
              <div class="channel-grade" :class="'badge-' + f.grade.toLowerCase()">
                {{ f.grade }} 档 · {{ f.gradeText.slice(2) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Monitor, Cpu } from '@element-plus/icons-vue'

const props = defineProps({
  fields: { type: Array, required: true },
})
defineEmits(['select'])

const groups = computed(() => {
  const byGroup = {}
  props.fields.forEach(f => {
    if (!byGroup[f.group]) byGroup[f.group] = []
    byGroup[f.group].push(f)
  })
  const colors = {
    '合成幅值': '#4F7CFF',
    '加速度RMS': '#10B981',
    '速度RMS': '#7C3AED',
    '冲击类': '#EF4444',
  }
  return Object.entries(byGroup).map(([name, fields]) => ({
    name, fields, color: colors[name] || '#94A3B8',
  }))
})

const counts = computed(() => {
  const c = { A: 0, B: 0, C: 0 }
  props.fields.forEach(f => c[f.grade]++)
  return c
})
</script>

<style lang="scss" scoped>
.topo-wrap {
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px 22px;
}
.topo-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.topo-title-left {
  display: flex; align-items: center; gap: 8px;
  font-weight: 700; font-size: 15px; color: var(--text);
}
.topo-legend {
  display: flex; align-items: center; gap: 18px;
  font-size: 12px; color: var(--text-mid);
}
.dot {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  margin-right: 4px; vertical-align: middle;
}
.dot-a { background: #10B981; }
.dot-b { background: #F59E0B; }
.dot-c { background: #EF4444; }

.topo-content {
  background: linear-gradient(180deg, #F8FAFD, #EDF1F8);
  border-radius: 10px;
  padding: 20px;
  position: relative;
}

.sensor-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 0;
}
.sensor-box {
  background: linear-gradient(135deg, #1E3A8A, #4F7CFF);
  color: white;
  padding: 14px 32px;
  border-radius: 12px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  box-shadow: 0 8px 24px rgba(30, 58, 138, 0.25);
  position: relative;
  z-index: 2;
  min-width: 220px;
}
.sensor-label {
  font-size: 14px; font-weight: 700; letter-spacing: 0.02em;
  margin-top: 2px;
}
.sensor-status {
  font-size: 11px; opacity: 0.85;
  display: flex; align-items: center; gap: 5px;
}
.status-pulse {
  width: 7px; height: 7px; border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.35);
  animation: pulse-dot 1.8s ease-in-out infinite;
}
.connect-line {
  width: 2px; height: 24px;
  background: linear-gradient(180deg, #4F7CFF, #94A3B8);
  margin-top: -2px;
}

.groups {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.group {
  background: white;
  border: 2px dashed transparent;
  border-radius: 10px;
  padding: 12px;
  position: relative;
}
.group::before {
  content: "";
  position: absolute;
  top: -14px; left: 50%;
  width: 2px; height: 14px;
  background: #CBD5E1;
  transform: translateX(-50%);
}
.group-header {
  display: flex; justify-content: space-between;
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 700; font-size: 12.5px;
  margin-bottom: 10px;
}
.group-name { letter-spacing: 0.02em; }
.group-count { opacity: 0.75; font-weight: 500; }

.group-channels {
  display: flex; flex-direction: column; gap: 8px;
}
.channel {
  background: #F8FAFD;
  border: 1px solid var(--border);
  border-left-width: 3px;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.18s;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 12px;
}
.channel:hover {
  transform: translateX(2px);
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
}
.channel.grade-a { border-left-color: #10B981; }
.channel.grade-b { border-left-color: #F59E0B; }
.channel.grade-c { border-left-color: #EF4444; }

.channel-top {
  grid-column: span 2;
  display: flex; align-items: center; gap: 7px;
  margin-bottom: 3px;
}
.channel-light {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0;
}
.grade-a .channel-light { background: #10B981; box-shadow: 0 0 6px rgba(16,185,129,0.5); }
.grade-b .channel-light { background: #F59E0B; box-shadow: 0 0 6px rgba(245,158,11,0.5); }
.grade-c .channel-light { background: #EF4444; box-shadow: 0 0 6px rgba(239,68,68,0.5); }
.channel-name {
  font-weight: 600; font-size: 12px;
  color: var(--text); font-family: Consolas, monospace;
  letter-spacing: -0.01em;
}
.channel-metric {
  font-size: 10.5px; display: flex; justify-content: space-between;
  color: var(--text-mid);
}
.metric-label { color: var(--text-light); letter-spacing: 0.04em; text-transform: uppercase; font-size: 9.5px; }
.metric-val { font-weight: 600; color: var(--text); font-family: Consolas, monospace; }
.channel-grade {
  grid-column: span 2;
  margin-top: 5px; text-align: center;
  padding: 2px 6px; border-radius: 3px;
  font-size: 10px; font-weight: 600;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.35); }
  50% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.1); }
}
</style>
