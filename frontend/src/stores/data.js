/**
 * 全局数据加载 (基于 fetch 读 public/data/*.json)
 */
import { ref, shallowRef } from 'vue'
import dayjs from 'dayjs'

const BASE = import.meta.env.BASE_URL + 'data/'

async function loadJson(file) {
  const res = await fetch(BASE + file)
  if (!res.ok) throw new Error(`Load ${file} failed: ${res.status}`)
  return await res.json()
}

// 共享状态
export const meta = shallowRef(null)
export const summary = shallowRef(null)
export const timeseries = shallowRef(null)
export const forecast = shallowRef(null)
export const correlation = shallowRef(null)
export const alarms = shallowRef(null)

const loading = ref(false)
const loaded = ref(false)

// 监测周期元信息 (从原始数据得到)
export const monitorPeriod = shallowRef({
  startTime: '2024-06-11T07:23:04',
  endTime: '2024-06-11T09:59:59',
  durationHours: 2.62,
  startTimeDisplay: '2024-06-11 07:23',
  endTimeDisplay: '09:59',
})

/**
 * 时间平移: 将原始数据 (2024-06-11) 的时刻平移到"今天"
 * 保留时分秒,仅替换日期,让 UI 呈现"当日监测"的连贯感
 */
export function shiftToToday(iso) {
  if (!iso) return iso
  const src = dayjs(iso)
  const today = dayjs()
  return today
    .hour(src.hour())
    .minute(src.minute())
    .second(src.second())
    .millisecond(src.millisecond())
    .toISOString()
}

export async function ensureLoaded() {
  if (loaded.value) return
  if (loading.value) {
    await new Promise((resolve) => {
      const timer = setInterval(() => {
        if (loaded.value) { clearInterval(timer); resolve() }
      }, 50)
    })
    return
  }
  loading.value = true
  try {
    const [m, s, t, f, c, a] = await Promise.all([
      loadJson('meta.json'),
      loadJson('summary.json'),
      loadJson('timeseries.json'),
      loadJson('forecast.json'),
      loadJson('correlation.json'),
      loadJson('alarms.json'),
    ])
    // 平移告警时间到今天 (2024 → today)
    if (a && a.events) {
      a.events = a.events.map(e => ({
        ...e,
        startTime: shiftToToday(e.startTime),
        endTime: shiftToToday(e.endTime),
      }))
    }

    meta.value = m
    summary.value = s
    timeseries.value = t
    forecast.value = f
    correlation.value = c
    alarms.value = a
    loaded.value = true
  } finally {
    loading.value = false
  }
}

// 工具函数
export function groupColor(group) {
  const colors = {
    '合成幅值': '#4F7CFF',
    '加速度RMS': '#10B981',
    '速度RMS': '#7C3AED',
    '冲击类': '#EF4444',
  }
  return colors[group] || '#94A3B8'
}

export function gradeColor(grade) {
  return { A: '#10B981', B: '#F59E0B', C: '#EF4444' }[grade] || '#94A3B8'
}

export function classifyUsability(nrmse, acf16, snr) {
  if (snr < 0.5) return { grade: 'C', text: '不建议直接使用' }
  if (nrmse < 20 && acf16 > 0.75 && snr > 1.3) return { grade: 'A', text: '可直接部署' }
  if (nrmse < 25 && acf16 > 0.70) return { grade: 'B', text: '可用, 建议复核' }
  return { grade: 'C', text: '不建议直接使用' }
}
