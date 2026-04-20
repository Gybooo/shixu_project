# MPB_01 振动预测与健康管理平台

> 基于 **TimesFM 2.5** 基础模型的多属性时序预测研究 Demo · 对标 SINOR 7 模块控制层架构

![python](https://img.shields.io/badge/Python-3.9+-blue?logo=python) ![streamlit](https://img.shields.io/badge/Streamlit-1.50-FF4B4B?logo=streamlit) ![plotly](https://img.shields.io/badge/Plotly-6.7-3F4F75?logo=plotly)

## 功能一览

对标中昇 SINOR 具身 AI 运维平台的七大模块，基于 MPB_01 传感器数据实现：

| # | 模块 | 实现内容 |
|---|------|---------|
| 1 | **总览 Dashboard** | 11 字段状态灯、核心指标、研究亮点 |
| 2 | **状态监控** | 字段选择、时序 + SavGol 趋势叠加、分布/滚动 std |
| 3 | **报警管理** | Magnitude 骤降事件检测 (18 次疑似停机)，严重程度分级 |
| 4 | **预警分析** ★ | LSTM vs TimesFM 预测对比 · 4 字段 × 60 窗口 · 11 字段 NRMSE 全景 |
| 5 | **根因追溯** | 11×11 皮尔逊相关矩阵 + 强/独立关联 TopN |
| 6 | **健康管理** ★ | 判据象限图 + 新字段可用性在线评估器 (ACF×SNR×NRMSE) |
| 7 | **研究报告** | 7 项主要发现 · 5 类场景部署建议 · PPT/CSV 一键下载 |

## 快速开始

### 本地运行

```bash
# 1. 克隆仓库
git clone <this repo>
cd timesfm_project

# 2. 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. (可选) 如有原始 CSV, 生成压缩缓存 (只需一次)
python -m app.prepare_data
# 产出: app/resources/fields.parquet (~800KB)

# 4. 启动 Streamlit
streamlit run streamlit_app.py
# 浏览器打开 http://localhost:8501
```

### 部署到 Streamlit Community Cloud

1. **推送到 GitHub**
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git push -u origin main
   ```

2. **访问 [streamlit.io/cloud](https://share.streamlit.io/) 部署**
   - 登录 GitHub 账号
   - 点 "New app"
   - 选仓库 + 分支 + 主文件 `streamlit_app.py`
   - Python 版本选 **3.11**
   - 点 "Deploy"

3. **等 2–3 分钟**, 获得形如 `https://xxx.streamlit.app` 的永久链接

> 首次部署会自动安装 requirements.txt 中的依赖。如失败请查看 Cloud 平台日志。

## 项目结构

```
timesfm_project/
├── streamlit_app.py                  # ★ 主入口
├── requirements.txt                  # 部署依赖
├── .streamlit/
│   └── config.toml                   # 主题配置 (现代蓝紫色)
├── app/
│   ├── __init__.py
│   ├── style.py                      # 全局 CSS / 现代风格
│   ├── data.py                       # 数据加载层
│   ├── charts.py                     # Plotly 图表工厂
│   ├── prepare_data.py               # 数据预处理脚本
│   ├── resources/
│   │   └── fields.parquet            # 11 字段 × 8960 点压缩缓存 (~800KB)
│   └── tabs/
│       ├── dashboard.py              # Tab 1
│       ├── monitoring.py             # Tab 2
│       ├── alarms.py                 # Tab 3
│       ├── forecast.py               # Tab 4 (核心)
│       ├── root_cause.py             # Tab 5
│       ├── health.py                 # Tab 6 (核心)
│       └── report.py                 # Tab 7
└── output/                           # 研究产物
    ├── 全字段泛化测试.csv             # 11 字段指标
    ├── allfields_cache.npz           # 字段统计信息
    ├── multifield_cache.npz          # 4 字段详细预测结果
    └── MPB_01振动预测研究报告.pptx   # 24 页汇报
```

## 核心研究结论

| 发现 | 数据 |
|------|------|
| 原始信号 1s lag-1 ACF = 0.87, lag-60 ACF = 0.09 | 原始逐点预测不可行 |
| SavGol(61,3) 分解后 lag-1 ACF 提升至 1.00 | 趋势信号可预测 |
| horizon = 16 秒 → NRMSE 13-17% (RMS 类) | 部署推荐配置 |
| TimesFM 在 11 字段中 10 个优于 LSTM | 零样本预测有效 |
| 物理量族内 NRMSE 标准差 ≤ 2% | 支持族级预判 |
| ShockX/Y/Z 族 NRMSE 33-48%, SNR<0.4 | 需改用事件检测 |
| 可用性判据 v2 命中率 **11/11** | 可作为接入前 checklist |

## 技术栈

- **前端**: Streamlit 1.50 · streamlit-option-menu 0.4 · Plotly 6.7
- **数据**: pandas 2.x · scipy.signal (Savitzky-Golay 滤波)
- **模型**: PyTorch 2.x (LSTM) · TimesFM 2.5-200M (零样本)
- **主题**: 自定义 CSS · Inter/Noto Sans SC 字体 · 渐变蓝紫色

## 已知限制

- **单设备数据**: 仅来自 MPB_01 传感器 × 2.62 小时连续监测, 跨设备泛化未验证
- **TimesFM 曲线**: Tab 4 详细预测曲线目前显示 LSTM 缓存结果, TFM 的宏观 MAE 从 summary 显示 (避免部署时引入模型权重)
- **Demo 性质**: 本应用为研究原型, 实际工业部署需接入实时数据源与预警发送机制

## 许可

研究原型, 仅供学术交流使用。
