<template>
  <div>
    <PageHeader title="研究报告" subtitle="核心结论 · 工程建议 · 资料下载" />

    <!-- 7 大发现 -->
    <div class="section-title">七项主要发现</div>
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
      <template #header>技术栈</template>
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">前端</div>
            <div class="tech-value">Vue 3 + Element Plus + ECharts</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">数据处理</div>
            <div class="tech-value">pandas · scipy.signal</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">模型</div>
            <div class="tech-value">PyTorch LSTM · TimesFM 2.5</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="tech-row">
            <div class="tech-label">部署</div>
            <div class="tech-value">Vite · Vercel</div>
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
  { title: '原始信号不可逐点预测', desc: '1s 尺度 lag-1 ACF=0.87, lag-60 仅 0.09, 接近高频噪声, 逐点预测必然退化为均值。' },
  { title: '信号分解显著提升可预测性', desc: 'SavGol(61,3) 分解后的趋势信号 lag-1 ACF 提升至 1.00, 成为可预测的建模对象。' },
  { title: 'horizon=16 为最佳平衡点', desc: 'MAE 随窗口指数增长. horizon=16 在误差 (约 2.1%) 与业务价值之间达到最优平衡。' },
  { title: 'TimesFM 零样本预测优于 LSTM', desc: '11 个字段中 TimesFM 于 10 个领先 LSTM, 平均提升约 41%, 且无需训练与微调。' },
  { title: '物理量族内一致性强', desc: '族内 NRMSE 标准差 ≤ 2%, 支持族级预判, 新字段按族归档, 无需逐字段训练。' },
  { title: '冲击类信号整族不适用', desc: 'ShockX/Y/Z 族 SNR < 0.4, NRMSE 33-48%, 需改用事件检测或分位数回归。' },
  { title: '三指标判据命中率 100%', desc: 'ACF lag-16 + SNR + NRMSE 组成的可用性判据 v2 对 11 字段命中率 11/11。' },
]

const scenarios = [
  { label: '场景一', scene: '振动趋势监测', config: 'SavGol(61,3) + TimesFM + h=16', metric: 'NRMSE ~14%', color: '#10B981' },
  { label: '场景二', scene: '短期实时预测', config: 'SavGol(31,2) + TimesFM + h=8', metric: 'NRMSE ~7%', color: '#10B981' },
  { label: '场景三', scene: '异常事件检测', config: '原始信号 + LSTM + 残差三级告警', metric: '高召回', color: '#F59E0B' },
  { label: '场景四', scene: '新字段接入', config: 'ACF + SNR 预判 → 判据 v2', metric: '零训练', color: '#4F7CFF' },
  { label: '场景五', scene: '冲击信号监控', config: 'ShockX/Y/Z 事件检测', metric: '替代方案', color: '#EF4444' },
]

const downloads = [
  { name: '研究报告 (PPT)',
    filename: 'MPB_01振动预测研究报告.pptx',
    url: import.meta.env.BASE_URL + 'downloads/report.pptx',
    desc: '24 页幻灯片, 覆盖数据概览、算法对比、信号分解、全字段验证等章节' },
  { name: '全字段对比表 (CSV)',
    filename: '全字段泛化测试.csv',
    url: import.meta.env.BASE_URL + 'downloads/fields-summary.csv',
    desc: '11 字段的预测精度 / 信号质量 / 长程稳定性 / 可用性档位汇总' },
  { name: '全字段验证报告 (MD)',
    filename: '全字段验证报告.md',
    url: import.meta.env.BASE_URL + 'downloads/validation-report.md',
    desc: '完整验证过程、三项主要发现、判据修订与落地建议' },
  { name: '多属性结果 (CSV)',
    filename: '多属性泛化测试_v2.csv',
    url: import.meta.env.BASE_URL + 'downloads/multifield-results.csv',
    desc: '4 个代表字段的详细指标, 含预测精度 / 信号质量 / 模型提升幅度' },
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
