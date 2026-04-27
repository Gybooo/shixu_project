<template>
  <div>
    <PageHeader title="方案资料" subtitle="系统能力 · 业务价值 · 资料下载" />

    <!-- 7 大发现 -->
    <div class="section-title">七项系统能力</div>
    <el-row :gutter="14" class="mb-2">
      <el-col v-for="(f, i) in findings" :key="i" :span="12">
        <div class="finding-card">
          <div class="finding-num">{{ String(i + 1).padStart(2, '0') }}</div>
          <div>
            <div class="finding-title">{{ f.title }}</div>
            <div class="finding-desc">{{ f.desc }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 部署建议 -->
    <div class="section-title mt-2">工程部署推荐配置</div>
    <div v-for="s in scenarios" :key="s.label" class="scenario-row" :style="{ borderLeftColor: s.color }">
      <div class="scenario-label" :style="{ color: s.color }">{{ s.label }}</div>
      <div class="scenario-scene">{{ s.scene }}</div>
      <div class="scenario-config"><code>{{ s.config }}</code></div>
      <div class="scenario-metric" :style="{ color: s.color }">{{ s.metric }}</div>
    </div>

    <!-- 下载 -->
    <div class="section-title mt-3">资料下载</div>
    <el-row :gutter="14">
      <el-col v-for="d in downloads" :key="d.name" :span="12">
        <el-card class="dl-card">
          <div class="dl-row">
            <div class="dl-icon"><el-icon :size="24"><Document /></el-icon></div>
            <div class="dl-content">
              <div class="dl-name">{{ d.name }}</div>
              <div class="dl-desc">{{ d.desc }}</div>
            </div>
            <a :href="d.url" :download="d.filename"
               target="_blank" class="dl-btn">
              <el-icon><Download /></el-icon> 下载
            </a>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 技术栈 -->
    <el-card class="mt-3">
      <template #header>系统架构</template>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">前端</div>
            <div class="tech-value">工业级 Web 管理台 + 可视化大屏</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">数据处理</div>
            <div class="tech-value">设备状态数据清洗与指标汇聚</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">智能引擎</div>
            <div class="tech-value">预测预警引擎 + 健康评估引擎</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">部署</div>
            <div class="tech-value">前后端解耦 · 云端发布</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { Document, Download } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'

const findings = [
  { title: '多通道状态监控', desc: '覆盖 MPB_01 的 11 个振动相关通道, 支持设备状态、趋势变化与波动水平的集中展示。' },
  { title: '实时告警管理', desc: '对振动骤降、信号中断、持续异常等事件进行自动识别, 支持分级、查询、处置与追溯。' },
  { title: '智能预警分析', desc: '对未来短时间窗口内的设备状态进行提前评估, 辅助运维人员提前发现潜在异常。' },
  { title: '健康度评估', desc: '从预测精度、信号质量、稳定性等维度形成综合健康评分, 支持 A/B/C 档位管理。' },
  { title: '根因追溯辅助', desc: '基于多字段联动关系定位相关通道, 帮助工程人员快速缩小故障排查范围。' },
  { title: '剩余寿命管理', desc: '通过部件健康度和运行时长生成维护建议, 为后续接入完整寿命评估能力预留接口。' },
  { title: '可扩展系统框架', desc: '预留用户、角色、告警策略、字段配置、产线配置等模块, 便于后续对接真实业务流程。' },
]

const scenarios = [
  { label: '场景一', scene: '振动趋势监测', config: '标准趋势清洗 + 智能预测引擎 + 16秒预警窗口', metric: '推荐', color: '#10B981' },
  { label: '场景二', scene: '短期实时预测', config: '短窗口滚动预警 + 高刷新频率状态评估', metric: '低延迟', color: '#10B981' },
  { label: '场景三', scene: '异常事件检测', config: '原始信号监测 + 事件触发 + 分级告警', metric: '高召回', color: '#F59E0B' },
  { label: '场景四', scene: '新字段接入', config: '自动计算信号质量与稳定性 → 智能分档', metric: '快速接入', color: '#4F7CFF' },
  { label: '场景五', scene: '冲击信号监控', config: '脉冲事件识别 + 人工复核 + 专项阈值', metric: '专项策略', color: '#EF4444' },
]

const downloads = [
  { name: '研究报告 (PPT)',
    filename: 'MPB_01振动预测研究报告.pptx',
    url: import.meta.env.BASE_URL + 'downloads/report.pptx',
    desc: '完整汇报材料, 覆盖系统能力、页面展示、数据概览与部署建议' },
  { name: '全字段对比表 (CSV)',
    filename: '全字段泛化测试.csv',
    url: import.meta.env.BASE_URL + 'downloads/fields-summary.csv',
    desc: '11 字段的预测精度 / 信号质量 / 长程稳定性 / 可用性档位汇总' },
  { name: '全字段验证报告 (MD)',
    filename: '全字段验证报告.md',
    url: import.meta.env.BASE_URL + 'downloads/validation-report.md',
    desc: '系统验证过程、主要发现与落地建议' },
  { name: '多属性结果 (CSV)',
    filename: '多属性泛化测试_v2.csv',
    url: import.meta.env.BASE_URL + 'downloads/multifield-results.csv',
    desc: '4 个代表字段的详细指标, 含预测精度 / 信号质量 / 引擎提升幅度' },
]
</script>

<style lang="scss" scoped>
.section-title {
  font-size: 16px; font-weight: 700; color: var(--text);
  margin: 14px 0 12px 0;
  padding-left: 12px;
  border-left: 4px solid var(--primary-light);
}

.finding-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  gap: 14px;
  height: 100%;
  margin-bottom: 10px;
  transition: all 0.18s;
  &:hover {
    border-color: var(--primary-light);
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  }
}
.finding-num {
  background: linear-gradient(135deg, #4F7CFF, #7C3AED);
  color: white;
  min-width: 46px; height: 46px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px;
  font-family: Consolas, monospace;
  letter-spacing: -0.02em;
  flex-shrink: 0;
}
.finding-title {
  font-size: 14.5px; font-weight: 700; color: var(--text);
  margin-bottom: 4px;
}
.finding-desc {
  font-size: 12.5px; color: var(--text-mid);
  line-height: 1.65;
}

.scenario-row {
  display: grid;
  grid-template-columns: 80px 150px 1fr 100px;
  align-items: center;
  padding: 10px 16px;
  background: white;
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 8px;
  margin-bottom: 6px;
  gap: 16px;
}
.scenario-label { font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.scenario-scene { font-size: 14px; font-weight: 600; color: var(--text); }
.scenario-config { font-size: 12.5px; color: var(--text-mid); font-family: Consolas, monospace; }
.scenario-metric { font-size: 13px; font-weight: 600; text-align: right; }

.dl-card {
  height: 100%;
}
.dl-row { display: flex; align-items: center; gap: 12px; }
.dl-icon {
  background: rgba(79, 124, 255, 0.12);
  color: var(--primary-light);
  width: 44px; height: 44px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.dl-content { flex: 1; min-width: 0; }
.dl-name { font-size: 14.5px; font-weight: 600; margin-bottom: 3px; }
.dl-desc { font-size: 12px; color: var(--text-mid); line-height: 1.5; }
.dl-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 14px;
  background: linear-gradient(135deg, #4F7CFF, #7C3AED);
  color: white; text-decoration: none;
  border-radius: 6px;
  font-size: 12.5px; font-weight: 600;
  transition: all 0.18s;
  &:hover {
    box-shadow: 0 4px 12px rgba(79, 124, 255, 0.35);
  }
}

.tech-row {
  padding: 8px 0;
}
.tech-label {
  font-size: 11.5px; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-light);
  font-weight: 600;
}
.tech-value {
  font-size: 13.5px; font-weight: 600; color: var(--text);
  margin-top: 4px;
}
</style>
