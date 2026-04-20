"""Tab 4 · 预警分析 (核心) - LSTM vs TimesFM 预测对比"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import (
    FIELDS_4, FIELD_GROUPS, GROUP_COLORS, FIELD_UNITS,
    load_multifield_cache, load_summary_csv,
)
from ..charts import plot_forecast_sample, plot_nrmse_bar, apply_layout
from ..style import COLORS, hero, section_title, metric_card, badge


def render():
    hero(
        "预警分析 · 核心功能",
        "LSTM 本地训练 vs TimesFM 零样本预测 · 16 步未来窗口",
        tag="FORECAST · 预警分析",
    )

    lstm_res, fi_map = load_multifield_cache()
    if not lstm_res:
        st.error("未加载到预测缓存, 请确认 `output/multifield_cache.npz` 存在")
        return

    # 上半部分: 单窗口预测对比
    section_title("单窗口预测对比")

    col_ctrl = st.columns([2, 1, 1, 1])
    with col_ctrl[0]:
        field = st.selectbox(
            "选择预测字段",
            options=FIELDS_4,
            help="这 4 个字段包含完整的 60 个测试窗口预测结果",
        )
    with col_ctrl[1]:
        sample_idx = st.number_input(
            "样本窗口 #", min_value=1, max_value=60, value=1, step=1,
        )
    with col_ctrl[2]:
        unit = FIELD_UNITS.get(field, "")
        st.markdown(f"""
        <div style="padding-top:1.7rem;">
            <span class="badge badge-primary">{FIELD_GROUPS[field]}</span>
            <span style="color:#94A3B8;margin-left:0.5rem;font-size:0.85rem;">单位: {unit}</span>
        </div>
        """, unsafe_allow_html=True)
    with col_ctrl[3]:
        auto_pick_volatile = st.checkbox("自动选波动大的样本", value=True,
                                         help="优先显示真实值波动明显的样本")

    lr = lstm_res[field]
    preds = np.array(lr["eval_preds"])   # (60, 16)
    actuals = np.array(lr["eval_actuals"])  # (60, 16)

    # 简单的伪-TFM 预测: 使用相同 actuals 的平滑版本模拟
    # (实际上是用缓存的 LSTM 预测 + 轻微修正, 因为原 TFM 推理需要模型)
    # 注意: 为了诚实性, 我们只显示 LSTM 的缓存结果,
    # TFM 的宏观 MAE 从 summary csv 取, 详细曲线使用 actuals 的 EMA 作为近似
    # 更诚实做法: 隐藏 TFM 曲线, 但用户会看到 MAE 对比
    tfm_preds = None  # 先不画, 只显示 LSTM 详细对比

    # 自动选样本: 按 actual std 排序
    if auto_pick_volatile:
        std_per_sample = actuals.std(axis=1)
        order = np.argsort(-std_per_sample)
        # 把 sample_idx 映射到排序后位置
        actual_idx = int(order[min(sample_idx - 1, len(order) - 1)])
    else:
        actual_idx = min(sample_idx - 1, len(preds) - 1)

    actual_row = actuals[actual_idx]
    lstm_row = preds[actual_idx]

    # 显示图
    fig = plot_forecast_sample(
        actual_row, lstm_row, tfm_preds,
        title=f"{field} · 窗口 #{actual_idx + 1} · 预测 16 步",
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 本样本误差指标
    mae_sample = np.mean(np.abs(actual_row - lstm_row))
    st.markdown(f"""
    <div class="card-sub">
    本窗口 LSTM MAE = <b>{mae_sample:.4f}</b> {unit} ·
    真实值波动范围 <b>{actual_row.min():.3f} ~ {actual_row.max():.3f}</b>
    </div>
    """, unsafe_allow_html=True)

    # 整体指标卡片
    st.write("")
    section_title("整体性能摘要")
    summary_df = load_summary_csv()
    field_row = summary_df[summary_df["属性"] == field].iloc[0] if len(summary_df) else None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(metric_card(
            "LSTM MAE (60 窗口)", f"{lr['mae']:.4f}", unit=unit,
            delta=f"训练耗时 {lr['train_time']:.0f}s", delta_kind="neutral"
        ), unsafe_allow_html=True)
    with k2:
        if field_row is not None:
            tfm_mae = field_row["TFM_MAE"]
            st.markdown(metric_card(
                "TimesFM MAE (零样本)", f"{tfm_mae:.4f}", unit=unit,
                delta="无需训练", delta_kind="up",
            ), unsafe_allow_html=True)
    with k3:
        if field_row is not None:
            nrmse = field_row["NRMSE_TFM%"]
            kind = "up" if nrmse < 20 else ("neutral" if nrmse < 35 else "down")
            st.markdown(metric_card(
                "NRMSE (TFM)", f"{nrmse:.1f}", unit="%",
                delta="MAE / 趋势std", delta_kind=kind,
            ), unsafe_allow_html=True)
    with k4:
        if field_row is not None:
            imp = field_row["TFM提升%"]
            kind = "up" if imp > 0 else "down"
            st.markdown(metric_card(
                "TFM 相对提升", f"{imp:+.1f}", unit="%",
                delta="vs LSTM", delta_kind=kind,
            ), unsafe_allow_html=True)

    # 下半部分: 11 字段全景
    st.write("")
    section_title("11 字段性能全景")
    if len(summary_df):
        fig_bar = plot_nrmse_bar(summary_df)
        st.plotly_chart(fig_bar, use_container_width=True)

        with st.expander("📋 查看完整数据表", expanded=False):
            st.dataframe(
                summary_df[["属性", "类别", "SNR", "ACF_lag16",
                           "LSTM_MAE", "TFM_MAE",
                           "NRMSE_LSTM%", "NRMSE_TFM%",
                           "TFM提升%", "可用性"]],
                use_container_width=True, hide_index=True,
            )

    # 方法论提示
    st.markdown("""
    <div class="card" style="margin-top:1rem;">
        <div class="card-title">📘 方法说明</div>
        <div style="color:#475569;font-size:0.86rem;line-height:1.7;">
        • <b>信号处理</b>: 原始 1 秒信号 → Savitzky-Golay 滤波 (窗口 61, 阶数 3) → 趋势分量<br>
        • <b>LSTM</b>: 两层 LSTM (隐藏 128) + MLP 头, 本地 CUDA 训练 25 epoch<br>
        • <b>TimesFM</b>: Google 开源的 TimesFM 2.5-200M 预训练模型, 零样本推理<br>
        • <b>horizon = 16</b>: 基于可预测性与视觉跟随性的最优平衡点 (详见章节 5)<br>
        • <b>context = 256</b>: 历史窗口长度, 对 TimesFM 不敏感, 对 LSTM 敏感
        </div>
    </div>
    """, unsafe_allow_html=True)
