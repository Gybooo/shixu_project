"""Tab 2 · 状态监控"""
import streamlit as st

from ..data import (
    ALL_FIELDS, FIELD_GROUPS, FIELD_UNITS, GROUP_COLORS,
    load_raw_field, savgol_trend, load_allfields_cache,
)
from ..charts import plot_timeseries_with_trend, plot_timeseries
from ..style import section_title, hero, metric_card


def render():
    hero(
        "实时状态监控",
        "可视化每个物理量的时序、趋势与统计特征",
        tag="MONITORING · 状态监控",
    )

    # 选择字段
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        field = st.selectbox(
            "选择监测字段",
            options=ALL_FIELDS,
            index=0,
            help="覆盖 MPB_01 传感器采集的 11 个物理量",
        )
    with c2:
        show_trend = st.toggle("叠加 SavGol 趋势", value=True)
    with c3:
        sampling_desc = st.selectbox("时间分辨率", ["1 秒", "5 秒", "30 秒"], index=0)

    s = load_raw_field(field)
    if len(s) == 0:
        st.error("数据加载失败")
        return

    # 重采样
    if sampling_desc == "5 秒":
        s = s.resample("5s").mean().dropna()
    elif sampling_desc == "30 秒":
        s = s.resample("30s").mean().dropna()

    # 顶部统计
    section_title(f"{field} · 数据概况")
    _, fi_map = load_allfields_cache()
    fi = fi_map.get(field, {})

    k1, k2, k3, k4, k5 = st.columns(5)
    unit = FIELD_UNITS.get(field, "")
    with k1:
        st.markdown(metric_card("样本点数", f"{len(s):,}", unit="点"),
                    unsafe_allow_html=True)
    with k2:
        st.markdown(metric_card("均值", f"{s.mean():.3f}", unit=unit),
                    unsafe_allow_html=True)
    with k3:
        st.markdown(metric_card("标准差", f"{s.std():.3f}", unit=unit),
                    unsafe_allow_html=True)
    with k4:
        st.markdown(metric_card("物理量族", FIELD_GROUPS[field]),
                    unsafe_allow_html=True)
    with k5:
        acf = fi.get("acf_lag16", 0)
        kind = "up" if acf > 0.75 else ("neutral" if acf > 0.55 else "down")
        st.markdown(metric_card(
            "ACF lag-16", f"{acf:.3f}",
            delta="长程记忆性" if acf > 0.75 else ("中等" if acf > 0.55 else "较弱"),
            delta_kind=kind,
        ), unsafe_allow_html=True)

    st.write("")
    # 时序图
    section_title("时序曲线")
    color = GROUP_COLORS[FIELD_GROUPS[field]]
    if show_trend:
        trend = savgol_trend(s)
        fig = plot_timeseries_with_trend(s, trend,
                                         title=f"{field} · {sampling_desc}重采样 · 共 {len(s):,} 点")
    else:
        fig = plot_timeseries(s, color=color,
                              title=f"{field} · {sampling_desc}重采样 · 共 {len(s):,} 点")
    st.plotly_chart(fig, use_container_width=True)

    # 分布直方图 & 滚动统计
    section_title("分布与波动")
    cc1, cc2 = st.columns(2)
    with cc1:
        import plotly.graph_objects as go
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=s.values, nbinsx=50,
            marker=dict(color=color, line=dict(color="white", width=1)),
            hovertemplate="值域 %{x}<br>频次 %{y}<extra></extra>",
        ))
        fig2.update_layout(
            title="数值分布直方图",
            height=320,
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(family="Inter", size=12),
            xaxis=dict(gridcolor="#E5E9F2", title=f"{field} ({unit})"),
            yaxis=dict(gridcolor="#E5E9F2", title="频次"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with cc2:
        window = max(60, len(s) // 50)
        roll_std = s.rolling(window).std()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=roll_std.index, y=roll_std.values, mode="lines",
            line=dict(color=GROUP_COLORS[FIELD_GROUPS[field]], width=1.8),
            fill="tozeroy", fillcolor="rgba(79, 124, 255, 0.12)",
            hovertemplate="%{x|%H:%M:%S}<br>滚动 std: %{y:.4f}<extra></extra>",
        ))
        fig3.update_layout(
            title=f"滚动标准差 (窗口 {window} 点)",
            height=320,
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(family="Inter", size=12),
            xaxis=dict(gridcolor="#E5E9F2", title="时间"),
            yaxis=dict(gridcolor="#E5E9F2", title="波动幅度"),
        )
        st.plotly_chart(fig3, use_container_width=True)
