<template>
  <div v-loading="!summary">
    <PageHeader title="告警策略配置" subtitle="按字段配置振动告警阈值、等级与通知方式" module="系统设置" />

    <el-alert type="info" :closable="false" show-icon class="mb-2">
      当前使用判据 v2 自动分级 · 命中率 11/11 · 如需手动覆盖, 可在本页调整阈值
    </el-alert>

    <el-card>
      <template #header>
        <div class="h">
          <span class="title">字段告警配置 ({{ rules.length }} 条)</span>
          <div>
            <el-button size="small" @click="addRule">
              <el-icon><Plus /></el-icon> 新增规则
            </el-button>
            <el-button size="small" type="primary">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rules" size="default" stripe>
        <el-table-column label="#" type="index" width="55" align="center" />
        <el-table-column label="监测字段" prop="field" width="130">
          <template #default="{ row }">
            <strong style="font-family: Consolas, monospace;">{{ row.field }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="物理量族" prop="group" width="120" />
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="预警阈值 (NRMSE %)" width="170">
          <template #default="{ row }">
            <el-input-number v-model="row.warnThreshold" :min="0" :max="100" :step="1" size="small" style="width: 130px;" />
          </template>
        </el-table-column>
        <el-table-column label="告警阈值 (NRMSE %)" width="170">
          <template #default="{ row }">
            <el-input-number v-model="row.alertThreshold" :min="0" :max="100" :step="1" size="small" style="width: 130px;" />
          </template>
        </el-table-column>
        <el-table-column label="最短持续 (秒)" width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.minDuration" :min="1" :max="60" size="small" style="width: 110px;" />
          </template>
        </el-table-column>
        <el-table-column label="通知方式" width="200">
          <template #default="{ row }">
            <el-checkbox-group v-model="row.notify" size="small">
              <el-checkbox label="sms">短信</el-checkbox>
              <el-checkbox label="email">邮箱</el-checkbox>
              <el-checkbox label="wechat">微信</el-checkbox>
            </el-checkbox-group>
          </template>
        </el-table-column>
        <el-table-column label="当前档位" width="110" align="center">
          <template #default="{ row }">
            <span :class="'badge-' + row.grade.toLowerCase()">{{ row.grade }} 档</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="120">
          <template #default="{ $index }">
            <el-button link type="primary" size="small">测试</el-button>
            <el-button link type="danger" size="small" @click="rules.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="mt-2">
      <template #header><span class="title">全局通知配置</span></template>
      <el-form label-width="140px" label-position="left">
        <el-form-item label="默认通知渠道">
          <el-checkbox-group v-model="globalNotify">
            <el-checkbox label="sms">短信 (13800138***)</el-checkbox>
            <el-checkbox label="email">邮箱 (ops@mpb01.cn)</el-checkbox>
            <el-checkbox label="wechat">企业微信</el-checkbox>
            <el-checkbox label="dingtalk">钉钉机器人</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="静默时段">
          <el-time-picker v-model="silenceStart" format="HH:mm" placeholder="开始" />
          <span style="margin: 0 10px;">至</span>
          <el-time-picker v-model="silenceEnd" format="HH:mm" placeholder="结束" />
        </el-form-item>
        <el-form-item label="重复告警间隔">
          <el-input-number v-model="repeatInterval" :min="0" :max="120" style="width: 140px;" />
          <span class="text-light" style="margin-left: 10px;">分钟 (0 = 不重复)</span>
        </el-form-item>
        <el-form-item label="仅工作时段告警">
          <el-switch v-model="workdaysOnly" />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { ensureLoaded, summary } from '@/stores/data'

const rules = ref([])
const globalNotify = ref(['sms', 'email'])
const silenceStart = ref(null)
const silenceEnd = ref(null)
const repeatInterval = ref(30)
const workdaysOnly = ref(true)

onMounted(async () => {
  await ensureLoaded()
  initRules()
})
watch(() => summary.value, () => initRules())

function initRules() {
  if (!summary.value) return
  rules.value = summary.value.fields.map(f => ({
    field: f.field,
    group: f.group,
    grade: f.grade,
    enabled: f.grade !== 'C',  // C 档默认禁用
    warnThreshold: Math.round(f.nrmseTfm * 1.3),
    alertThreshold: Math.round(f.nrmseTfm * 1.8),
    minDuration: 5,
    notify: f.grade === 'A' ? ['email'] : ['sms', 'email'],
  }))
}

function addRule() {
  rules.value.unshift({
    field: '新规则', group: '自定义', grade: 'B', enabled: true,
    warnThreshold: 20, alertThreshold: 35, minDuration: 5, notify: ['email'],
  })
}
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 14px; font-weight: 700; color: var(--text); }
</style>
