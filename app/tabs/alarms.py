"""Tab 3 · 报警管理"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..data import load_raw_field, detect_shutdown_events
from ..style import COLORS, hero, section_title, metric_card, badge


def render():
    hero(
        "报警管理",
        "异常事件检测 · 停机识别 · 历史事件追溯",
        tag="ALARMS · 报警管理",
    )

    s = load_raw_field("Magnitude")
    if len(s) == 0:
        st.error("数据加载失败")
        return

    # 参数区
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown("""
        <div class="card-sub">
        当前依据 Magnitude 合成幅值进行停机/掉线检测:
        检测规则为「值 &lt; 中位数 − z × std × 0.3 持续 &ge; 最短时长」。
        </div>
        """, unsafe_allow_html=True)
    with c2:
        z = st.slider("z 阈值", 1.0, 5.0, 3.0, 0.1,
                      help="值越小越敏感, 默认 3.0")
    with c3:
        min_dur = st.slider("最短持续 (秒)", 1, 20, 3)

    events = detect_shutdown_events(s, z_threshold=z, min_duration=min_dur)

    # KPI
    section_title("事件汇总")
    k1, k2, k3, k4 = st.columns(4)
    total_events = len(events)
    total_duration = sum(e["duration_s"] for e in events)
    avg_duration = total_duration / max(total_events, 1)
    max_duration = max([e["duration_s"] for e in events], default=0)

    with k1:
        st.markdown(metric_card(
            "检测到事件", f"{total_events}", unit="次",
            delta=f"覆盖期 {(s.index[-1] - s.index[0]).total_seconds()/3600:.1f} 小时",
            delta_kind="neutral",
        ), unsafe_allow_html=True)
    with k2:
        st.markdown(metric_card(
            "累计停机时长", f"{total_duration}", unit="秒",
            delta=f"约 {total_duration/60:.1f} 分钟",
            delta_kind="neutral",
        ), unsafe_allow_html=True)
    with k3:
        st.markdown(metric_card(
            "平均单次时长", f"{avg_duration:.1f}", unit="秒",
        ), unsafe_allow_html=True)
    with k4:
        st.markdown(metric_card(
            "最长单次时长", f"{max_duration}", unit="秒",
        ), unsafe_allow_html=True)

    st.write("")

    # 时序 + 事件标注
    section_title("Magnitude 时序与异常区段")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, mode="lines",
        line=dict(color=COLORS["primary"], width=1.2),
        name="Magnitude",
        hovertemplate="%{x|%H:%M:%S}<br>%{y:.4f}<extra></extra>",
    ))
    for e in events:
        fig.add_vrect(
            x0=e["start_time"], x1=e["end_time"],
            fillcolor=COLORS["danger"], opacity=0.18,
            layer="below", line_width=0,
        )
    fig.update_layout(
        height=360,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Inter", size=12),
        xaxis=dict(gridcolor="#E5E9F2", title="时间"),
        yaxis=dict(gridcolor="#E5E9F2", title="Magnitude"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 事件列表
    section_title("事件明细")
    if not events:
        st.info("当前参数下未检测到异常事件")
        return

    rows = []
    for i, e in enumerate(events, 1):
        severity = "C" if e["duration_s"] > 10 else ("B" if e["duration_s"] > 5 else "A")
        rows.append({
            "#": i,
            "开始时间": e["start_time"].strftime("%H:%M:%S"),
            "结束时间": e["end_time"].strftime("%H:%M:%S"),
            "持续 (秒)": e["duration_s"],
            "最低值": round(e["min_value"], 4),
            "严重程度": severity,
        })
    ev_df = pd.DataFrame(rows)

    def _style_severity(val):
        if val == "A":
            return "background-color: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 600;"
        if val == "B":
            return "background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; font-weight: 600;"
        return "background-color: rgba(239, 68, 68, 0.15); color: #EF4444; font-weight: 600;"

    styled = ev_df.style.map(_style_severity, subset=["严重程度"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
