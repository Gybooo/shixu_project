<template>
  <div>
    <PageHeader title="用户管理" subtitle="平台用户账号与权限管理" module="系统设置" />

    <el-card>
      <template #header>
        <div class="h">
          <el-input v-model="keyword" placeholder="请输入用户名/姓名" style="width: 280px;" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary">
            <el-icon><Plus /></el-icon> 新增用户
          </el-button>
        </div>
      </template>

      <el-table :data="paged" stripe size="default">
        <el-table-column label="序号" type="index" width="70" align="center" />
        <el-table-column label="头像" width="100" align="center">
          <template #default="{ row }">
            <el-avatar :size="40" :style="{ background: avatarColor(row.id) }">{{ row.name[0] }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column label="用户名" prop="username" width="140" />
        <el-table-column label="姓名" prop="name" width="100" />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)" size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="所属部门" prop="dept" width="140" />
        <el-table-column label="邮箱" prop="email" width="200" />
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace; font-size: 12px;">{{ row.lastLogin }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.active ? 'success' : 'info'" size="small" effect="light">
              {{ row.active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span style="font-family: Consolas, monospace; font-size: 12px;">{{ row.createdAt }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="170" align="center">
          <template #default>
            <el-button link type="primary" size="small">编辑</el-button>
            <el-button link type="primary" size="small">重置密码</el-button>
            <el-button link type="danger" size="small">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination class="mt-2" v-model:current-page="page" :page-size="pageSize" :total="filtered.length"
                     layout="total, prev, pager, next" style="justify-content: flex-end;" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const keyword = ref('')
const page = ref(1)
const pageSize = 10

const users = [
  { id: 1, username: 'admin', name: '系统管理员', role: '超级管理员', dept: '研发中心', email: 'admin@mpb01.cn', lastLogin: '2026-04-22 09:14:28', active: true, createdAt: '2025-10-08 14:32:01' },
  { id: 2, username: 'wangze', name: '王泽', role: '工艺工程师', dept: '喷涂一线', email: 'wangze@mpb01.cn', lastLogin: '2026-04-22 08:56:12', active: true, createdAt: '2025-10-22 07:57:15' },
  { id: 3, username: 'gulun', name: '顾伦', role: '设备工程师', dept: '喷涂二线', email: 'gulun@mpb01.cn', lastLogin: '2026-04-21 16:48:07', active: true, createdAt: '2025-11-07 14:10:32' },
  { id: 4, username: 'jiguang', name: '纪广', role: '数据分析师', dept: '智能制造部', email: 'jiguang@mpb01.cn', lastLogin: '2026-04-22 09:02:45', active: true, createdAt: '2025-07-11 07:15:22' },
  { id: 5, username: 'lixiang', name: '李祥', role: '运维工程师', dept: '涂胶一线', email: 'lixiang@mpb01.cn', lastLogin: '2026-04-19 11:27:33', active: true, createdAt: '2025-12-03 10:45:18' },
  { id: 6, username: 'chenying', name: '陈英', role: '质量工程师', dept: '质检部', email: 'chenying@mpb01.cn', lastLogin: '2026-04-20 14:22:51', active: true, createdAt: '2026-01-15 09:33:42' },
  { id: 7, username: 'zhouming', name: '周明', role: '操作员', dept: '喷涂一线', email: 'zhouming@mpb01.cn', lastLogin: '2026-04-22 07:30:18', active: false, createdAt: '2026-02-20 13:18:05' },
  { id: 8, username: 'huangli', name: '黄丽', role: '操作员', dept: '涂胶二线', email: 'huangli@mpb01.cn', lastLogin: '2026-04-18 09:45:22', active: true, createdAt: '2026-03-01 11:27:33' },
]

const filtered = computed(() => {
  if (!keyword.value) return users
  const k = keyword.value.toLowerCase()
  return users.filter(u => u.username.includes(k) || u.name.includes(keyword.value))
})
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function roleTag(role) {
  if (role.includes('管理员')) return 'danger'
  if (role.includes('工程师')) return 'primary'
  if (role.includes('分析师')) return 'warning'
  return 'info'
}
function avatarColor(id) {
  const colors = ['#4F7CFF', '#7C3AED', '#10B981', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899', '#8B5CF6']
  return colors[id % colors.length]
}
</script>

<style lang="scss" scoped>
.h { display: flex; justify-content: space-between; align-items: center; }
</style>
