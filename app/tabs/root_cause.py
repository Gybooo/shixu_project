"""Tab 5 · 根因追溯 - 相关性分析"""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ..charts import plot_correlation_heatmap
from ..data import compute_correlation_matrix, ALL_FIELDS, GROUP_COLORS, FIELD_GROUPS
from ..style import hero, section_title, metric_card, COLORS


def render():
    hero(
        "根因追溯",
        "11×11 字段相关矩阵 · 物理量联动分析",
        tag="ROOT CAUSE · 根因追溯",
    )

    corr = compute_correlation_matrix()
    if corr.empty:
        st.error("无法计算相关矩阵")
        return

    # 顶部 KPI
    section_title("相关性总览")

    # 最强正相关 (排除对角)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    pairs = []
    for i in range(len(corr)):
        for j in range(i + 1, len(corr)):
            pairs.append({
                "a": corr.index[i], "b": corr.columns[j],
                "r": float(corr.iloc[i, j]),
            })
    pairs.sort(key=lambda x: -abs(x["r"]))

    strong_corr = [p for p in pairs if abs(p["r"]) > 0.7]
    weak_corr = [p for p in pairs if abs(p["r"]) < 0.3]
    strongest = pairs[0] if pairs else None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(metric_card(
            "字段对总数", f"{len(pairs)}", unit="对",
            delta="11 × 10 / 2", delta_kind="neutral",
        ), unsafe_allow_html=True)
    with k2:
        st.markdown(metric_card(
            "强相关对数", f"{len(strong_corr)}", unit="对",
            delta="|r| > 0.7", delta_kind="up",
        ), unsafe_allow_html=True)
    with k3:
        if strongest:
            st.markdown(metric_card(
                "最强关联",
                f"{strongest['r']:.3f}",
                delta=f"{strongest['a']} ↔ {strongest['b']}",
                delta_kind="up",
            ), unsafe_allow_html=True)
    with k4:
        st.markdown(metric_card(
            "无关字段对", f"{len(weak_corr)}", unit="对",
            delta="|r| < 0.3", delta_kind="neutral",
        ), unsafe_allow_html=True)

    # 热力图
    st.write("")
    section_title("相关矩阵热力图")
    fig = plot_correlation_heatmap(corr, height=580)
    st.plotly_chart(fig, use_container_width=True)

    # 强关联与独立关联对
    c1, c2 = st.columns(2)
    with c1:
        section_title("强关联 Top 5")
        top5 = pairs[:5]
        rows = []
        for i, p in enumerate(top5, 1):
            rows.append({"#": i, "字段 A": p["a"], "字段 B": p["b"],
                        "相关系数 r": round(p["r"], 3)})
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with c2:
        section_title("独立关联 Top 5")
        bottom5 = sorted(pairs, key=lambda x: abs(x["r"]))[:5]
        rows = []
        for i, p in enumerate(bottom5, 1):
            rows.append({"#": i, "字段 A": p["a"], "字段 B": p["b"],
                        "相关系数 r": round(p["r"], 3)})
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("""
    <div class="card" style="margin-top:1rem;">
        <div class="card-title">🔗 关键发现</div>
        <div style="color:#475569;font-size:0.88rem;line-height:1.7;">
        • <b>Magnitude 与 aRMS/vRMS 高度相关</b> (r ≈ 0.86 – 0.98): 说明这些属性本质源自同一物理量,
          可以互为冗余参考;<br>
        • <b>Shock 系列与其他字段弱相关</b> (r ≈ 0.05): 冲击类信号相对独立, 由瞬时撞击主导,
          需独立建模;<br>
        • <b>根因定位建议</b>: 当某个字段异常时, 可优先查看其强相关字段的历史走势,
          缩小故障范围。
        </div>
    </div>
    """, unsafe_allow_html=True)
