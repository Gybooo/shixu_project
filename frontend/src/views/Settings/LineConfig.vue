<template>
  <div>
    <PageHeader title="产线配置" subtitle="产线与监测设备的绑定关系管理" module="系统设置" />

    <el-alert type="info" :closable="false" show-icon class="mb-2">
      <template #title>当前平台监测范围</template>
      <div style="font-size: 13px; line-height: 1.7;">
        已纳入监测的产线 <b>1 条</b> · 已部署传感器 <b>1 台 (MPB_01)</b> · 已覆盖物理量 <b>11 通道</b>。
        后续可通过新增产线/设备扩展监测范围。
      </div>
    </el-alert>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="h">
              <span class="title">产线列表</span>
              <el-button size="small"><el-icon><Plus /></el-icon> 新增产线</el-button>
            </div>
          </template>
          <el-table :data="lines" highlight-current-row @current-change="onSelect" size="default">
            <el-table-column label="编码" prop="code" width="130">
              <template #default="{ row }">
                <code style="font-family: Consolas, monospace; color: #4F7CFF;">{{ row.code }}</code>
              </template>
            </el-table-column>
            <el-table-column label="产线名称" prop="name" width="150" />
            <el-table-column label="设备数" prop="deviceCount" align="center" width="80" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'info'" size="small" effect="light">
                  {{ row.active ? '运行中' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="h">
              <span class="title">{{ selected?.name || '产线详情' }} · 关联设备</span>
              <el-button size="small" type="primary"><el-icon><Plus /></el-icon> 绑定设备</el-button>
            </div>
          </template>
          <el-table v-if="selected" :data="selected.devices" size="default" stripe>
            <el-table-column label="#" type="index" width="55" align="center" />
            <el-table-column label="设备编码" prop="code" width="130">
              <template #default="{ row }">
                <strong style="font-family: Consolas, monospace;">{{ row.code }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="位置" prop="location" width="140" />
            <el-table-column label="传感器类型" prop="sensor" width="150" />
            <el-table-column label="监测通道" prop="channels" align="center" width="110" />
            <el-table-column label="安装日期" prop="installDate" width="130" align="center" />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small" effect="dark">
                  {{ row.status === 'online' ? '在线' : '离线' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" align="center" width="160">
              <template #default>
                <el-button link type="primary" size="small">配置</el-button>
                <el-button link type="danger" size="small">解绑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="请从左侧选择产线" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const lines = [
  {
    code: 'LINE-01', name: '振动监测试点线', deviceCount: 1, active: true,
    devices: [
      {
        code: 'MPB_01', location: '振动监测工位',
        sensor: '三轴加速度 + 冲击', channels: 11,
        installDate: '2024-06-10', status: 'online',
      },
    ],
  },
  { code: 'LINE-02', name: '扩展监测预留', deviceCount: 0, active: false, devices: [] },
  { code: 'LINE-03', name: '全厂汇聚节点', deviceCount: 0, active: false, devices: [] },
]

const selected = ref(lines[0])
function onSelect(row) { if (row) selected.value = row }
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 14px; font-weight: 700; }
</style>
