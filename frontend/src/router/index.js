import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '大屏总览', standalone: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      {
        path: 'monitoring',
        component: () => import('@/views/Monitoring.vue'),
        meta: { title: '运行状态监控', icon: 'Monitor' },
      },
      {
        path: 'alarms',
        component: () => import('@/views/Alarms.vue'),
        meta: { title: '报警管理', icon: 'Warning' },
      },
      {
        path: 'forecast',
        component: () => import('@/views/Forecast.vue'),
        meta: { title: '预警分析', icon: 'TrendCharts' },
      },
      {
        path: 'root-cause',
        component: () => import('@/views/RootCause.vue'),
        meta: { title: '根因追溯', icon: 'Share' },
      },
      {
        path: 'health',
        component: () => import('@/views/Health.vue'),
        meta: { title: '健康管理', icon: 'Cpu' },
      },
      {
        path: 'lifetime',
        component: () => import('@/views/Lifetime.vue'),
        meta: { title: '剩余寿命', icon: 'Clock' },
      },
      {
        path: 'report',
        component: () => import('@/views/Report.vue'),
        meta: { title: '研究报告', icon: 'Document' },
      },
      {
        path: 'settings/users',
        component: () => import('@/views/Settings/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User' },
      },
      {
        path: 'settings/roles',
        component: () => import('@/views/Settings/RoleManagement.vue'),
        meta: { title: '角色管理', icon: 'UserFilled' },
      },
      {
        path: 'settings/alarm',
        component: () => import('@/views/Settings/AlarmConfig.vue'),
        meta: { title: '告警策略', icon: 'Bell' },
      },
      {
        path: 'settings/fields',
        component: () => import('@/views/Settings/FieldConfig.vue'),
        meta: { title: '字段配置', icon: 'SetUp' },
      },
      {
        path: 'settings/lines',
        component: () => import('@/views/Settings/LineConfig.vue'),
        meta: { title: '产线配置', icon: 'Connection' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.afterEach((to) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} · MPB_01 振动预测平台`
  }
})

export default router
