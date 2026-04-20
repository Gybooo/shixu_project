"""
MPB_01 振动预测与健康管理平台
Streamlit 应用主入口
"""
import streamlit as st
from streamlit_option_menu import option_menu

from app.style import inject_global_css, COLORS
from app.tabs import (
    dashboard, monitoring, alarms, forecast,
    root_cause, health, report,
)

st.set_page_config(
    page_title="MPB_01 振动预测平台",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "MPB_01 振动预测与健康管理平台 | 基于 TimesFM 的研究 Demo",
    },
)

inject_global_css()


# 侧栏
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">📡 SENSOR · AI</div>
            <div class="sidebar-brand-sub">MPB_01 振动预测与健康管理平台</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected = option_menu(
        menu_title=None,
        options=[
            "总览 Dashboard",
            "状态监控",
            "报警管理",
            "预警分析",
            "根因追溯",
            "健康管理",
            "研究报告",
        ],
        icons=[
            "grid-1x2-fill",
            "activity",
            "exclamation-triangle-fill",
            "graph-up-arrow",
            "diagram-3-fill",
            "heart-pulse-fill",
            "file-earmark-text-fill",
        ],
        default_index=0,
        styles={
            "container": {
                "padding": "0.5rem 0.4rem",
                "background-color": "transparent",
            },
            "icon": {
                "color": COLORS["text_mid"],
                "font-size": "1.0rem",
            },
            "nav-link": {
                "font-size": "0.92rem",
                "font-weight": "500",
                "color": COLORS["text_mid"],
                "text-align": "left",
                "margin": "2px 0",
                "padding": "0.6rem 0.9rem",
                "border-radius": "10px",
                "--hover-color": COLORS["bg_soft"],
            },
            "nav-link-selected": {
                "background": f"linear-gradient(135deg, {COLORS['gradient_start']}, {COLORS['gradient_end']})",
                "color": "white",
                "font-weight": "600",
                "box-shadow": "0 4px 12px rgba(79, 124, 255, 0.3)",
            },
        },
    )

    # 侧栏底部信息
    st.markdown(
        f"""
        <div style="position: absolute; bottom: 1.5rem; left: 1rem; right: 1rem;
                    padding-top: 1rem; border-top: 1px solid {COLORS["border"]};
                    font-size: 0.75rem; color: {COLORS["text_light"]};">
            <div style="margin-bottom: 0.5rem;">
                <b style="color: {COLORS["text_mid"]};">设备</b> &nbsp;MPB_01<br>
                <b style="color: {COLORS["text_mid"]};">字段</b> &nbsp;11 个物理量<br>
                <b style="color: {COLORS["text_mid"]};">采样</b> &nbsp;1 Hz (重采样)<br>
                <b style="color: {COLORS["text_mid"]};">模型</b> &nbsp;LSTM + TimesFM 2.5
            </div>
            <div style="opacity: 0.6; margin-top: 0.8rem;">
                研究原型 · 基于 SINOR 7 模块架构
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# 路由
ROUTES = {
    "总览 Dashboard": dashboard.render,
    "状态监控": monitoring.render,
    "报警管理": alarms.render,
    "预警分析": forecast.render,
    "根因追溯": root_cause.render,
    "健康管理": health.render,
    "研究报告": report.render,
}

render_fn = ROUTES.get(selected)
if render_fn:
    try:
        render_fn()
    except Exception as e:
        st.error(f"页面渲染失败: {e}")
        with st.expander("错误详情"):
            import traceback
            st.code(traceback.format_exc())
