<template>
  <div class="admin-layout">
    <!-- 顶栏 -->
    <header class="admin-header">
      <div class="header-left">
        <div class="logo">
          <div class="logo-icon">
            <el-icon :size="22"><DataLine /></el-icon>
          </div>
          <span class="logo-text">MPB_01 振动预测与健康管理系统</span>
        </div>
      </div>
      <div class="header-right">
        <el-tooltip content="当前设备: MPB_01" placement="bottom">
          <div class="header-meta">
            <el-icon><Cpu /></el-icon>
            <span>MPB_01</span>
          </div>
        </el-tooltip>
        <div class="header-meta">
          <el-icon><Calendar /></el-icon>
          <span>{{ currentTime }}</span>
        </div>
        <router-link to="/dashboard" class="header-btn">
          <el-icon><Monitor /></el-icon>
          大屏模式
        </router-link>
        <el-tooltip content="系统设置" placement="bottom">
          <router-link to="/settings/users" class="header-icon-btn">
            <el-icon><Setting /></el-icon>
          </router-link>
        </el-tooltip>
        <el-dropdown trigger="click">
          <div class="header-user">
            <el-avatar :size="32" :style="{ background: '#4F7CFF' }">A</el-avatar>
            <div class="header-user-info">
              <div class="header-user-name">admin</div>
              <div class="header-user-role">超级管理员</div>
            </div>
            <el-icon class="header-user-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>
                <el-icon><User /></el-icon> 个人中心
              </el-dropdown-item>
              <el-dropdown-item>
                <el-icon><Lock /></el-icon> 修改密码
              </el-dropdown-item>
              <el-dropdown-item>
                <el-icon><Bell /></el-icon> 消息中心
              </el-dropdown-item>
              <el-dropdown-item divided>
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主体 -->
    <div class="admin-body">
      <!-- 左侧菜单 -->
      <aside class="admin-sider">
        <el-menu
          :default-active="activeMenu"
          :default-openeds="['monitoring-group', 'analysis-group', 'settings-group']"
          router
          class="admin-menu"
        >
          <el-sub-menu index="monitoring-group">
            <template #title>
              <el-icon><Monitor /></el-icon>
              <span>运行状态监控</span>
            </template>
            <el-menu-item index="/monitoring">
              <el-icon><DataAnalysis /></el-icon>
              <span>字段时序监控</span>
            </el-menu-item>
            <el-menu-item index="/alarms">
              <el-icon><Warning /></el-icon>
              <span>报警管理</span>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="analysis-group">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>智能分析</span>
            </template>
            <el-menu-item index="/forecast">
              <el-icon><MagicStick /></el-icon>
              <span>预警分析</span>
            </el-menu-item>
            <el-menu-item index="/root-cause">
              <el-icon><Share /></el-icon>
              <span>根因追溯</span>
            </el-menu-item>
            <el-menu-item index="/health">
              <el-icon><Cpu /></el-icon>
              <span>健康管理</span>
            </el-menu-item>
            <el-menu-item index="/lifetime">
              <el-icon><Clock /></el-icon>
              <span>剩余寿命</span>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/report">
            <el-icon><Document /></el-icon>
            <span>研究报告</span>
          </el-menu-item>

          <el-sub-menu index="settings-group">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            <el-menu-item index="/settings/users">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/settings/roles">
              <el-icon><UserFilled /></el-icon>
              <span>角色管理</span>
            </el-menu-item>
            <el-menu-item index="/settings/alarm">
              <el-icon><Bell /></el-icon>
              <span>告警策略</span>
            </el-menu-item>
            <el-menu-item index="/settings/fields">
              <el-icon><SetUp /></el-icon>
              <span>字段配置</span>
            </el-menu-item>
            <el-menu-item index="/settings/lines">
              <el-icon><Connection /></el-icon>
              <span>产线配置</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>

        <div class="sider-footer">
          <div class="sider-footer-label">平台状态</div>
          <div class="sider-footer-status">
            <span class="status-dot pulse-dot"></span>
            <span>在线 · 11 通道覆盖</span>
          </div>
          <div class="sider-footer-period">
            <el-icon :size="11"><Calendar /></el-icon>
            <span>监测周期 &nbsp;</span>
            <b>2024-06-11 07:23 — 09:59</b>
          </div>
          <div class="sider-footer-version">v1.0 · SINOR Compatible</div>
        </div>
      </aside>

      <!-- 内容 -->
      <main class="admin-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'

const route = useRoute()
const activeMenu = computed(() => route.path)

const currentTime = ref(dayjs().format('YYYY-MM-DD HH:mm'))
let timer = null
onMounted(() => {
  timer = setInterval(() => {
    currentTime.value = dayjs().format('YYYY-MM-DD HH:mm')
  }, 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* 顶栏 */
.admin-header {
  height: 56px;
  background: linear-gradient(90deg, #1E3A8A 0%, #2B4FD0 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(30, 58, 138, 0.15);
  z-index: 10;
}
.header-left .logo {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-icon {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}
.logo-text {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 18px;
  font-size: 13px;
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.85;
  color: white;
}
.header-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  color: white;
  text-decoration: none;
  font-size: 12.5px;
  font-weight: 500;
  transition: all 0.18s;
  &:hover {
    background: rgba(255, 255, 255, 0.25);
  }
}
.header-icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.18s;
  color: white;
  &:hover {
    background: rgba(255, 255, 255, 0.15);
  }
}
.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 14px;
  margin-left: 4px;
  border-left: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
  &:hover { opacity: 0.85; }
}
.header-user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.header-user-name {
  font-size: 13px;
  font-weight: 600;
}
.header-user-role {
  font-size: 10px;
  opacity: 0.7;
  letter-spacing: 0.02em;
}
.header-user-arrow {
  font-size: 12px;
  opacity: 0.7;
}

/* 主体布局 */
.admin-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.admin-sider {
  width: 220px;
  background: white;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.admin-menu {
  flex: 1;
  overflow-y: auto;
}
.sider-footer {
  padding: 16px;
  border-top: 1px solid var(--border);
  font-size: 11.5px;
  color: var(--text-light);
}
.sider-footer-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-mid);
  margin-bottom: 8px;
}
.sider-footer-status {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-mid);
  margin-bottom: 6px;
  font-size: 12px;
}
.sider-footer-period {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-light);
  font-size: 10.5px;
  margin-bottom: 6px;
  line-height: 1.4;
  b { color: var(--text-mid); font-weight: 600; font-family: Consolas, monospace; }
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}
.sider-footer-version {
  opacity: 0.65;
  font-size: 11px;
}

.admin-main {
  flex: 1;
  overflow: auto;
  background: var(--admin-bg);
  padding: 20px 24px;
}

/* 路由切换动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
