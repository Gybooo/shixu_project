"""Tab 6 · 健康管理 (核心) - 可用性判据计算器 + 象限图"""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ..data import (
    load_summary_csv, load_allfields_cache, ALL_FIELDS,
    classify_usability, FIELD_GROUPS, GROUP_COLORS,
)
from ..charts import plot_quadrant, plot_nrmse_by_group
from ..style import COLORS, hero, section_title, metric_card, badge


def render():
    hero(
        "健康管理 · 核心功能",
        "三维可用性判据 (ACF × SNR × NRMSE) · 新字段在线评估",
        tag="HEALTH · 健康管理",
    )

    summary_df = load_summary_csv()
    if summary_df.empty:
        st.error("未加载到数据")
        return

    # 上半部分: 全字段判据象限图
    section_title("11 字段可用性象限")
    st.markdown("""
    <div class="card-sub">
    每个气泡代表一个字段。横轴反映信号长程可预测性, 纵轴反映信噪比,
    气泡大小反映 NRMSE 误差。A 档字段集中于右上, C 档字段聚集于左下。
    </div>
    """, unsafe_allow_html=True)
    fig = plot_quadrant(summary_df, height=540)
    st.plotly_chart(fig, use_container_width=True)

    # 族内分布
    st.write("")
    section_title("按物理量族 NRMSE 分布")
    st.markdown("""
    <div class="card-sub">
    族内标准差不超过 2% (RMS 类) 或 8% (冲击类), 支持<b>族级预判</b>: 同族任一字段通过验证后,
    其他字段可默认归入同档, 无需逐字段重训。
    </div>
    """, unsafe_allow_html=True)
    fig_group = plot_nrmse_by_group(summary_df, height=320)
    st.plotly_chart(fig_group, use_container_width=True)

    # 下半部分: 交互式判据计算器
    st.write("")
    section_title("⚡ 新字段可用性在线评估")
    st.markdown("""
    <div class="card-sub">
    对于新接入的字段, 无需训练模型, 只需提供三个信号指标 (ACF lag-16, SNR, NRMSE),
    系统将自动给出 A/B/C 档位与部署建议。
    </div>
    """, unsafe_allow_html=True)

    cc1, cc2 = st.columns([2, 3])

    with cc1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">输入指标</div>', unsafe_allow_html=True)

        preset = st.selectbox(
            "或从已验证字段中选择",
            ["自定义"] + ALL_FIELDS,
            index=0,
        )

        if preset != "自定义":
            row = summary_df[summary_df["属性"] == preset].iloc[0]
            acf_default = float(row["ACF_lag16"])
            snr_default = float(row["SNR"])
            nrmse_default = float(row["NRMSE_TFM%"]) / 100.0
        else:
            acf_default = 0.80
            snr_default = 1.50
            nrmse_default = 0.15

        acf = st.slider("ACF lag-16", 0.0, 1.0, acf_default, 0.01,
                        help="趋势信号在 16 步后的自相关系数, 反映长程可预测性")
        snr = st.slider("SNR (信噪比)", 0.0, 3.0, min(snr_default, 3.0), 0.05,
                        help="趋势 std / 噪声 std")
        nrmse_pct = st.slider("NRMSE (%)", 0.0, 100.0, nrmse_default * 100, 0.5,
                              help="MAE / 趋势 std × 100%")
        nrmse = nrmse_pct / 100.0

        st.markdown('</div>', unsafe_allow_html=True)

    with cc2:
        # 判定结果
        grade, grade_desc = classify_usability(nrmse, acf, snr)
        kind = {"A": "a", "B": "b", "C": "c"}[grade]
        color = {"A": COLORS["success"], "B": COLORS["warning"],
                 "C": COLORS["danger"]}[grade]

        reasons = []
        if grade == "A":
            reasons.append(("✓", "NRMSE < 20%, 预测误差可控"))
            reasons.append(("✓", "ACF > 0.75, 信号具备长程记忆"))
            reasons.append(("✓", "SNR > 1.3, 规律明显高于噪声"))
            advice = "方案可直接部署 · 使用 SavGol + TimesFM + h=16 标准配置"
        elif grade == "B":
            reasons.append(("⚠", f"NRMSE 为 {nrmse_pct:.1f}%, 误差偏大"))
            if acf < 0.75:
                reasons.append(("⚠", f"ACF 为 {acf:.2f}, 长程记忆性中等"))
            if snr < 1.3 and snr >= 0.5:
                reasons.append(("⚠", f"SNR 为 {snr:.2f}, 信噪比偏低"))
            advice = "可用但需人工复核 · 建议加大 context 或缩短 horizon"
        else:
            if snr < 0.5:
                reasons.append(("✗", f"SNR 仅 {snr:.2f}, 噪声掩盖信号 (硬红线)"))
            if acf < 0.55:
                reasons.append(("✗", f"ACF 仅 {acf:.2f}, 信号缺乏长程依赖"))
            if nrmse > 0.35:
                reasons.append(("✗", f"NRMSE 达 {nrmse_pct:.1f}%, 严重偏差"))
            advice = "不建议用本方案 · 改用事件检测或分位数回归"

        reasons_html = "".join([
            f'<li style="margin:0.4rem 0;"><span style="color:{color};font-weight:700;margin-right:0.5rem;">{icon}</span>{txt}</li>'
            for icon, txt in reasons
        ])

        st.markdown(
            f'<div class="card" style="border-left: 4px solid {color};">'
            f'  <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">'
            f'    <div style="background:{color};color:white;width:54px;height:54px;border-radius:14px;'
            f'                display:flex;align-items:center;justify-content:center;'
            f'                font-size:1.7rem;font-weight:800;flex-shrink:0;">{grade}</div>'
            f'    <div>'
            f'      <div style="font-size:1.15rem;font-weight:700;color:#0F172A;line-height:1.3;">{grade_desc}</div>'
            f'      <div style="font-size:0.78rem;color:#94A3B8;margin-top:0.25rem;line-height:1.4;">'
            f'        判据版本 v2 · 对 MPB_01 的 11 字段命中率 100%</div>'
            f'    </div>'
            f'  </div>'
            f'  <div style="font-size:0.88rem;color:#475569;margin-bottom:0.5rem;font-weight:600;">评估依据</div>'
            f'  <ul style="list-style:none;padding:0;margin:0;font-size:0.85rem;color:#475569;">{reasons_html}</ul>'
            f'  <div style="margin-top:0.9rem;padding-top:0.7rem;border-top:1px solid #E5E9F2;">'
            f'    <div style="font-size:0.78rem;color:#94A3B8;font-weight:600;margin-bottom:0.25rem;">部署建议</div>'
            f'    <div style="font-size:0.9rem;color:#0F172A;font-weight:500;line-height:1.5;">{advice}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # 位置指示
        st.markdown(f"""
        <div style="margin-top:0.8rem;font-size:0.8rem;color:#94A3B8;text-align:center;">
            当前位置: ACF = {acf:.3f} · SNR = {snr:.3f} · NRMSE = {nrmse_pct:.1f}%
        </div>
        """, unsafe_allow_html=True)

    # 底部: 判据代码展示
    with st.expander("📜 判据 v2 代码实现", expanded=False):
        st.code("""
def classify_usability(nrmse, acf16, snr):
    # 硬红线: 噪声掩盖信号
    if snr < 0.5:
        return "C", "不建议直接使用"
    # A 档: 三条阈值同时满足
    if nrmse < 0.20 and acf16 > 0.75 and snr > 1.3:
        return "A", "可直接部署"
    # B 档: 次级可用
    if nrmse < 0.25 and acf16 > 0.70:
        return "B", "可用, 建议复核"
    return "C", "不建议直接使用"
        """, language="python")
