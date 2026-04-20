"""Tab 7 · 研究报告 - 下载 + 核心结论"""
import os
import streamlit as st

from ..data import OUTPUT_DIR, ROOT
from ..style import hero, section_title, COLORS


def render():
    hero(
        "研究报告",
        "完整 PPT / Markdown / CSV 原始数据下载 · 核心结论一览",
        tag="REPORT · 研究报告",
    )

    # 七大发现
    section_title("七项主要发现")

    findings = [
        ("01", "原始信号不可逐点预测",
         "1 秒尺度信号 lag-1 自相关 0.87, 但 lag-60 仅 0.09, 接近高频噪声,"
         " 逐点预测必然退化为均值输出。"),
        ("02", "信号分解显著提升可预测性",
         "Savitzky-Golay(61,3) 分解后的趋势信号, lag-1 自相关提升至 1.00, "
         "成为具备充分可预测性的建模对象。"),
        ("03", "horizon=16 秒为最佳平衡点",
         "MAE 随预测窗口呈指数增长。horizon=16 在误差 (~2.1%) 与业务价值"
         "之间达到较优平衡。"),
        ("04", "TimesFM 零样本预测优于 LSTM",
         "在 11 个字段中, TimesFM 于 10 个字段领先 LSTM, 平均提升约 41%, "
         "且无需训练与微调。"),
        ("05", "物理量族内一致性强",
         "族内 NRMSE 标准差不超过 2%, 支持族级预判, 新字段接入可按族归档,"
         " 无需逐字段训练。"),
        ("06", "冲击类信号整族不适用",
         "ShockX/Y/Z 族的 SNR < 0.4, NRMSE 33-48%, 需改用事件检测或分位数"
         "回归等替代方案。"),
        ("07", "三指标判据命中率 100%",
         "ACF lag-16 + SNR + NRMSE 构成的可用性判据 v2, 对 11 个字段的"
         "归档命中率达 11/11。"),
    ]

    for num, title, desc in findings:
        st.markdown(f"""
        <div class="card" style="margin-bottom:0.75rem;">
            <div style="display:flex;gap:1rem;align-items:flex-start;">
                <div style="background:linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
                            color:white;min-width:52px;height:52px;border-radius:14px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.1rem;font-weight:800;letter-spacing:-0.02em;">
                    {num}
                </div>
                <div style="flex:1;">
                    <div style="font-size:1.05rem;font-weight:700;color:#0F172A;margin-bottom:0.3rem;">
                        {title}
                    </div>
                    <div style="font-size:0.88rem;color:#475569;line-height:1.65;">
                        {desc}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 工程部署推荐
    st.write("")
    section_title("工程部署推荐配置")

    scenarios = [
        ("场景一", "振动趋势监测", "SavGol(61,3) + TimesFM + h=16", "NRMSE 约 14%", "success"),
        ("场景二", "短期实时预测", "SavGol(31,2) + TimesFM + h=8", "NRMSE 约 7%", "success"),
        ("场景三", "异常事件检测", "原始信号 + LSTM + 残差三级告警", "高召回", "warning"),
        ("场景四", "新字段接入", "ACF + SNR 预判 → 可用性判据 v2", "零训练", "primary"),
        ("场景五", "冲击信号监控", "ShockX/Y/Z 使用脉冲事件检测", "替代方案", "danger"),
    ]

    color_map = {
        "success": COLORS["success"], "warning": COLORS["warning"],
        "primary": COLORS["primary"], "danger": COLORS["danger"],
    }

    for label, scene, config, metric, color_name in scenarios:
        color = color_map[color_name]
        st.markdown(f"""
        <div style="display:flex;align-items:center;padding:0.85rem 1.2rem;background:white;
                    border:1px solid #E5E9F2;border-radius:12px;margin-bottom:0.5rem;
                    border-left:4px solid {color};">
            <div style="min-width:80px;font-size:0.78rem;font-weight:700;color:{color};
                        letter-spacing:0.04em;text-transform:uppercase;">
                {label}
            </div>
            <div style="flex:1;font-size:0.95rem;font-weight:600;color:#0F172A;">
                {scene}
            </div>
            <div style="flex:2;font-size:0.85rem;color:#475569;font-family:'Consolas', monospace;">
                {config}
            </div>
            <div style="min-width:100px;text-align:right;font-size:0.82rem;font-weight:600;color:{color};">
                {metric}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 资源下载
    st.write("")
    section_title("报告与数据下载")

    dl_items = [
        ("研究报告 (PPT)",
         os.path.join(OUTPUT_DIR, "MPB_01振动预测研究报告.pptx"),
         "包含 24 张幻灯片, 覆盖数据概览、算法对比、信号分解、全字段验证等全部章节"),
        ("全字段对比表 (CSV)",
         os.path.join(OUTPUT_DIR, "全字段泛化测试.csv"),
         "11 个字段的 NRMSE、SNR、ACF、可用性档位汇总"),
        ("全字段验证报告 (Markdown)",
         os.path.join(OUTPUT_DIR, "全字段验证报告.md"),
         "完整的验证过程、三项主要发现、判据修订与落地建议"),
        ("多属性初步结果 (CSV)",
         os.path.join(OUTPUT_DIR, "多属性泛化测试_v2.csv"),
         "4 个代表字段的详细指标, 含 NRMSE / SNR / 提升幅度"),
    ]

    for title, path, desc in dl_items:
        if not os.path.exists(path):
            continue
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"""
            <div style="padding:0.75rem 0;">
                <div style="font-size:0.98rem;font-weight:600;color:#0F172A;">{title}</div>
                <div style="font-size:0.82rem;color:#94A3B8;margin-top:0.15rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            with open(path, "rb") as f:
                fname = os.path.basename(path)
                st.download_button(
                    label="⬇  下载",
                    data=f.read(),
                    file_name=fname,
                    mime="application/octet-stream",
                    use_container_width=True,
                )

    # 技术栈信息
    st.markdown("""
    <div class="card" style="margin-top:1.5rem;">
        <div class="card-title">🛠️ 技术栈</div>
        <div style="color:#475569;font-size:0.86rem;line-height:1.7;">
        • 数据处理: <code>pandas</code> · <code>scipy.signal</code> (Savitzky-Golay 滤波)<br>
        • 深度学习: <code>PyTorch 2.x</code> (LSTM) · <code>TimesFM 2.5-200M</code> (零样本预测)<br>
        • 可视化: <code>Plotly</code> · <code>Matplotlib</code><br>
        • Web 前端: <code>Streamlit 1.50</code>
        </div>
    </div>
    """, unsafe_allow_html=True)
