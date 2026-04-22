<template>
  <div>
    <PageHeader title="角色管理" subtitle="平台角色权限配置与功能模块授权" module="系统设置" />

    <el-row :gutter="16" class="mb-2">
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">{{ roles.length }}</span><span class="stat-l">角色总数</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">{{ modules.length }}</span><span class="stat-l">功能模块</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">8</span><span class="stat-l">关联用户</span></div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat"><span class="stat-n">28</span><span class="stat-l">权限项</span></div></el-card></el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="h">
          <span class="title">角色 × 功能模块 权限矩阵</span>
          <div>
            <el-button size="small"><el-icon><Plus /></el-icon> 新增角色</el-button>
            <el-button type="primary" size="small"><el-icon><Check /></el-icon> 保存配置</el-button>
          </div>
        </div>
      </template>

      <el-table :data="roles" stripe size="default">
        <el-table-column label="角色编码" prop="code" width="140">
          <template #default="{ row }">
            <code style="font-family: Consolas, monospace; color: #4F7CFF;">{{ row.code }}</code>
          </template>
        </el-table-column>
        <el-table-column label="角色名称" prop="name" width="140">
          <template #default="{ row }">
            <el-tag :type="row.type" size="default" effect="dark">{{ row.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用户数" prop="userCount" width="90" align="center" />
        <el-table-column v-for="m in modules" :key="m.key" :label="m.label" min-width="110" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.perms[m.key]" />
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="150" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small">编辑</el-button>
            <el-button link :type="row.code === 'admin' ? 'info' : 'danger'" size="small" :disabled="row.code === 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-alert type="info" :closable="false" show-icon class="mt-2">
      <template #title>权限说明</template>
      <div style="font-size: 13px; line-height: 1.7;">
        • <b>超级管理员</b> 拥有所有模块权限, 不可删除<br>
        • 普通用户的权限继承自所属角色, 可在用户管理中单独覆盖<br>
        • 权限变更实时生效, 相关用户下次刷新页面后应用
      </div>
    </el-alert>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus, Check } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const modules = [
  { key: 'dashboard', label: '大屏' },
  { key: 'monitor', label: '状态监控' },
  { key: 'alarms', label: '报警管理' },
  { key: 'forecast', label: '预警分析' },
  { key: 'root', label: '根因追溯' },
  { key: 'health', label: '健康管理' },
  { key: 'settings', label: '系统设置' },
]

const roles = ref([
  {
    code: 'admin', name: '超级管理员', type: 'danger', userCount: 1,
    perms: { dashboard: true, monitor: true, alarms: true, forecast: true, root: true, health: true, settings: true },
  },
  {
    code: 'engineer', name: '工艺工程师', type: 'primary', userCount: 2,
    perms: { dashboard: true, monitor: true, alarms: true, forecast: true, root: true, health: true, settings: false },
  },
  {
    code: 'maintainer', name: '设备工程师', type: 'primary', userCount: 2,
    perms: { dashboard: true, monitor: true, alarms: true, forecast: true, root: true, health: true, settings: false },
  },
  {
    code: 'analyst', name: '数据分析师', type: 'warning', userCount: 1,
    perms: { dashboard: true, monitor: true, alarms: false, forecast: true, root: true, health: true, settings: false },
  },
  {
    code: 'qc', name: '质量工程师', type: 'success', userCount: 1,
    perms: { dashboard: true, monitor: true, alarms: true, forecast: false, root: true, health: true, settings: false },
  },
  {
    code: 'monitor', name: '振动监测组', type: 'info', userCount: 2,
    perms: { dashboard: true, monitor: true, alarms: true, forecast: false, root: false, health: false, settings: false },
  },
  {
    code: 'observer', name: '只读观察员', type: 'info', userCount: 0,
    perms: { dashboard: true, monitor: true, alarms: false, forecast: false, root: false, health: false, settings: false },
  },
])
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 14px; font-weight: 700; }
.stat { text-align: center; padding: 6px 0; }
.stat-n { display: block; font-size: 26px; font-weight: 800; color: var(--primary); font-family: Consolas, monospace; }
.stat-l { font-size: 12px; color: var(--text-mid); }
</style>
