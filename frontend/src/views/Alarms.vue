<template>
  <div v-loading="!alarms">
    <PageHeader title="报警管理" subtitle="振动骤降/停机事件检测与分级处理" module="运行状态监控" />

    <!-- 筛选条 -->
    <el-card class="mb-2">
      <el-row :gutter="16" align="middle">
        <el-col :span="5">
          <div class="label">事件类型</div>
          <el-select v-model="filters.type" placeholder="全部" clearable>
            <el-option label="振动骤降" value="振动骤降" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <div class="label">状态</div>
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="已处理" value="已处理" />
            <el-option label="未处理" value="未处理" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <div class="label">严重程度</div>
          <el-select v-model="filters.severity" placeholder="全部" clearable>
            <el-option label="A 轻微" value="A" />
            <el-option label="B 中等" value="B" />
            <el-option label="C 严重" value="C" />
          </el-select>
        </el-col>
        <el-col :span="9" style="text-align: right;">
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" @click="() => {}">查询</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- KPI 四张卡 -->
    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><KpiCard label="事件总数" :value="stats.total" unit="次" :icon="Bell" /></el-col>
      <el-col :span="6"><KpiCard label="已处理" :value="stats.resolved" unit="次" color="#10B981" :icon="SuccessFilled" /></el-col>
      <el-col :span="6"><KpiCard label="未处理" :value="stats.unresolved" unit="次" color="#EF4444" :icon="WarnTriangleFilled" /></el-col>
      <el-col :span="6"><KpiCard label="累计停机" :value="stats.totalDuration" unit="秒" :icon="Timer" /></el-col>
    </el-row>

    <!-- 表格 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警事件列表 ({{ filteredEvents.length }})</span>
          <el-tag type="info" effect="plain">基于 Magnitude 骤降阈值 z=3.0, 最短 3s</el-tag>
        </div>
      </template>

      <el-table :data="pagedEvents" stripe style="width: 100%">
        <el-table-column label="#" prop="id" width="55" align="center" />
        <el-table-column label="事件时间" width="170">
          <template #default="{ row }">
            <div style="font-family: Consolas, monospace;">{{ formatTime(row.startTime) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="设备" width="100" align="center">
          <template #default><el-tag size="small" type="info">MPB_01</el-tag></template>
        </el-table-column>
        <el-table-column label="字段" prop="field" width="120" align="center" />
        <el-table-column label="事件类型" prop="type" width="120" />
        <el-table-column label="持续时长" width="120" align="center">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace;">{{ row.durationSeconds }} 秒</span>
          </template>
        </el-table-column>
        <el-table-column label="最低值" width="120" align="center">
          <template #default="{ row }">
            <span class="text-danger" style="font-family: Consolas, monospace;">{{ row.minValue.toFixed(3) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" width="110" align="center">
          <template #default="{ row }">
            <span :class="'badge-' + row.severity.toLowerCase()">
              {{ row.severity }} {{ row.severity === 'A' ? '轻微' : row.severity === 'B' ? '中等' : '严重' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '已处理' ? 'success' : 'danger'" size="small" effect="light">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center">
          <template #default>
            <el-button link type="primary" size="small">查看</el-button>
            <el-button link type="primary" size="small">处理</el-button>
            <el-button link type="danger" size="small">忽略</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-2"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="filteredEvents.length"
        layout="total, prev, pager, next, jumper"
        style="justify-content: flex-end;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { Bell, SuccessFilled, WarnTriangleFilled, Timer } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import { ensureLoaded, alarms } from '@/stores/data'

onMounted(() => ensureLoaded())

const filters = ref({ type: null, status: null, severity: null })
const currentPage = ref(1)
const pageSize = 10

const events = computed(() => alarms.value?.events || [])

const filteredEvents = computed(() => events.value.filter(e => {
  if (filters.value.type && e.type !== filters.value.type) return false
  if (filters.value.status && e.status !== filters.value.status) return false
  if (filters.value.severity && e.severity !== filters.value.severity) return false
  return true
}))
const pagedEvents = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredEvents.value.slice(start, start + pageSize)
})

const stats = computed(() => ({
  total: events.value.length,
  resolved: events.value.filter(e => e.status === '已处理').length,
  unresolved: events.value.filter(e => e.status === '未处理').length,
  totalDuration: events.value.reduce((s, e) => s + e.durationSeconds, 0),
}))

function resetFilters() {
  filters.value = { type: null, status: null, severity: null }
}
function formatTime(iso) {
  return dayjs(iso).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style lang="scss" scoped>
.label { font-size: 12px; color: var(--text-mid); margin-bottom: 6px; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
</style>
