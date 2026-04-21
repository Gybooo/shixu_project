"""Tab 1 · 平台架构总览 (对标 SINOR 7 模块控制层)"""
import base64
import os
import streamlit as st

from ..data import ROOT, load_summary_csv
from ..style import COLORS


THUMB_DIR = os.path.join(ROOT, "app", "resources", "thumbs")


def _img_b64(filename):
    path = os.path.join(THUMB_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# 7 模块定义 (对标 SINOR)
MODULES = [
    {
        "num": "1",
        "name": "Dashboard",
        "thumb": "01_dashboard.jpg",
        "desc": "设备监测总览界面，以大屏形式展示 11 个物理量的核心指标、NRMSE 性能对比、A/B/C 档位分布，是整个平台的数据入口。",
    },
    {
        "num": "2",
        "name": "状态监控",
        "thumb": "02_monitoring.jpg",
        "desc": "按字段查看实时时序曲线，叠加 SavGol 趋势分解，提供数值分布与滚动标准差分析，反映设备当前运行状态。",
    },
    {
        "num": "3",
        "name": "报警管理",
        "thumb": "03_alarms.jpg",
        "desc": "针对 Magnitude 骤降事件进行自动检测，已识别 18 次疑似停机。支持阈值调节、事件分级告警与历史事件追溯。",
    },
    {
        "num": "4",
        "name": "预警分析",
        "thumb": "04_forecast.jpg",
        "desc": "基于 LSTM 与 TimesFM 两种模型进行 16 步未来窗口预测，零样本 TFM 在 10/11 字段上优于本地训练的 LSTM。",
    },
    {
        "num": "5",
        "name": "根因追溯",
        "thumb": "05_root_cause.jpg",
        "desc": "通过 11×11 皮尔逊相关矩阵定位关联字段。Magnitude 与 aRMS/vRMS 族相关 0.86–0.98，Shock 族相对独立。",
    },
    {
        "num": "6",
        "name": "剩余寿命",
        "thumb": "06_lifetime.jpg",
        "desc": "基于 horizon 扩展的误差演化趋势推断设备剩余可监控时长。当前版本为方法学演示，完整寿命模型待后续补充。",
    },
    {
        "num": "7",
        "name": "健康管理",
        "thumb": "07_health.jpg",
        "desc": "ACF × SNR × NRMSE 三维可用性判据体系，对新接入字段实现秒级评估，对 MPB_01 的 11 字段命中率 100%。",
    },
]


def _inject_sinor_css():
    st.markdown(
        f"""
        <style>
        /* SINOR 风格架构图 */
        .sinor-wrap {{
            margin: 1rem 0 0.5rem 0;
        }}
        .sinor-title-bar {{
            background: linear-gradient(90deg, #1E3A8A 0%, #2B4FD0 100%);
            color: white;
            padding: 0.7rem 1.3rem;
            border-radius: 8px;
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            margin-bottom: 0.6rem;
            display: inline-block;
        }}
        .sinor-sub {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 0.8rem 0 1.5rem 0;
            letter-spacing: -0.01em;
        }}

        /* 7 卡片网格 */
        .sinor-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin: 0 0 1.5rem 0;
        }}
        /* 小屏幕时降到 4 或 2 列 */
        @media (max-width: 1400px) {{
            .sinor-grid {{
                grid-template-columns: repeat(4, 1fr);
            }}
        }}
        @media (max-width: 900px) {{
            .sinor-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        .sinor-card {{
            border: 1.5px solid #B8C7E0;
            border-radius: 10px;
            padding: 10px 10px 14px 10px;
            background: white;
            display: flex;
            flex-direction: column;
            transition: all 0.18s ease;
        }}
        .sinor-card:hover {{
            border-color: {COLORS["primary"]};
            box-shadow: 0 6px 20px rgba(31, 58, 138, 0.12);
            transform: translateY(-2px);
        }}

        .sinor-card-title {{
            font-size: 0.92rem;
            font-weight: 700;
            color: #1E3A8A;
            margin: 0 0 8px 2px;
            letter-spacing: -0.01em;
            line-height: 1.25;
        }}
        .sinor-card-num {{
            color: {COLORS["accent"]};
            margin-right: 4px;
        }}

        .sinor-card-img {{
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: cover;
            border-radius: 6px;
            border: 1px solid {COLORS["border"]};
            background: {COLORS["bg_soft"]};
            display: block;
        }}
        .sinor-card-img-placeholder {{
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 6px;
            background: linear-gradient(135deg, {COLORS["bg_soft"]}, #E2E8F0);
            border: 1px solid {COLORS["border"]};
            display: flex;
            align-items: center;
            justify-content: center;
            color: {COLORS["text_light"]};
            font-size: 0.78rem;
        }}

        .sinor-card-desc {{
            margin-top: 10px;
            padding: 0 2px;
            font-size: 0.76rem;
            color: {COLORS["text_mid"]};
            line-height: 1.55;
            letter-spacing: 0.005em;
            text-align: justify;
        }}

        /* 底部产品理念 */
        .sinor-philosophy {{
            background: {COLORS["bg_soft"]};
            border-left: 4px solid {COLORS["primary"]};
            padding: 0.85rem 1.2rem;
            border-radius: 0 10px 10px 0;
            margin-top: 1rem;
            font-size: 0.88rem;
            color: {COLORS["text_mid"]};
            line-height: 1.65;
        }}
        .sinor-philosophy b {{
            color: {COLORS["text"]};
            font-weight: 700;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_module_cards_html():
    cards_html = ""
    for mod in MODULES:
        b64 = _img_b64(mod["thumb"])
        if b64:
            img_html = f'<img class="sinor-card-img" src="data:image/jpeg;base64,{b64}" alt="{mod["name"]}" />'
        else:
            img_html = '<div class="sinor-card-img-placeholder">图示</div>'

        cards_html += f"""
        <div class="sinor-card">
            {img_html}
            <div class="sinor-card-title">
                <span class="sinor-card-num">{mod["num"]}.</span>{mod["name"]}
            </div>
            <div class="sinor-card-desc">{mod["desc"]}</div>
        </div>
        """
    return f'<div class="sinor-grid">{cards_html}</div>'


def render():
    _inject_sinor_css()

    # SINOR 风格顶部标题栏
    st.markdown(
        """
        <div class="sinor-wrap">
            <div class="sinor-title-bar">MPB_01 · 振动预测 AI 平台</div>
            <div class="sinor-sub">具身 AI 运维软件平台控制层</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 7 模块卡片
    st.markdown(_render_module_cards_html(), unsafe_allow_html=True)

    # 产品理念
    st.markdown(
        """
        <div class="sinor-philosophy">
            <b>产品理念：</b>以上七项内容先期设置，形成 v1 版本的软件；
            内容根据客户工艺工程师交流修正，现场工艺调试优化软件功能，
            直至形成一个具备自主知识工艺库的平台型运维软件。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 数据覆盖概览 (折叠, 默认展开)
    df = load_summary_csv()
    with st.expander("📊 当前数据覆盖与验证指标", expanded=True):
        if len(df) == 0:
            st.info("未加载到字段数据")
            return

        n_a = int((df["可用性"] == "A 可直接上线").sum())
        n_b = int((df["可用性"] == "B 可用/建议复核").sum())
        n_c = int((df["可用性"] == "C 不建议直接用").sum())
        best_nrmse = float(df["NRMSE_TFM%"].min())

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("监测字段总数", f"{len(df)}", delta="4 个物理量族")
        with c2:
            st.metric("A 档字段 (可直接部署)", f"{n_a}",
                      delta=f"{n_a / len(df):.0%}")
        with c3:
            st.metric("最佳 NRMSE", f"{best_nrmse:.1f}%",
                      delta="低于 20% 可用线", delta_color="inverse")
        with c4:
            st.metric("研究设备", "MPB_01", delta="1 台 × 2.6 小时")

        st.caption(
            f"字段档位分布: **A 档 {n_a}** · **B 档 {n_b}** · **C 档 {n_c}** "
            f"— 按 ACF × SNR × NRMSE 三指标自动归档, 判据命中率 11/11"
        )
