"""全局样式 - 现代风格 (浅色, 蓝紫主色, 卡片式) - 已针对部署优化"""
import streamlit as st


COLORS = {
    "primary": "#4F7CFF",
    "primary_dark": "#2B4FD0",
    "accent": "#FF8A4C",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "bg": "#FFFFFF",
    "bg_soft": "#F7F9FC",
    "bg_card": "#FFFFFF",
    "border": "#E5E9F2",
    "text": "#0F172A",
    "text_mid": "#475569",
    "text_light": "#94A3B8",
    "gradient_start": "#4F7CFF",
    "gradient_end": "#7C3AED",
}


def inject_global_css():
    """注入全局现代风格 CSS (纯系统字体, 不依赖外网 Google Fonts)"""
    st.markdown(
        f"""
        <style>
        /* === 全局字体 (纯系统栈, 不依赖外网) === */
        html, body, [class*="st-"], .main, .block-container,
        button, input, select, textarea {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
                         "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        /* 主容器收紧 padding */
        .main .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        /* 隐藏默认顶栏 & footer */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header[data-testid="stHeader"] {{
            background: transparent;
            height: 0;
        }}

        /* === 侧边栏 === */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F7F9FC 100%);
            border-right: 1px solid {COLORS["border"]};
        }}
        section[data-testid="stSidebar"] > div {{
            padding-top: 1.5rem;
        }}

        /* 侧边栏品牌区 */
        .sidebar-brand {{
            padding: 0 1rem 1.2rem 1rem;
            border-bottom: 1px solid {COLORS["border"]};
            margin-bottom: 0.8rem;
        }}
        .sidebar-brand-title {{
            font-size: 1.3rem;
            font-weight: 800;
            background: linear-gradient(90deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.01em;
            line-height: 1.2;
        }}
        .sidebar-brand-sub {{
            font-size: 0.75rem;
            color: {COLORS["text_light"]};
            margin-top: 0.3rem;
            font-weight: 500;
            line-height: 1.4;
        }}

        /* 侧边栏底部信息卡 (正常文档流, 不用 absolute 避免重叠) */
        .sidebar-footer {{
            margin-top: 2rem;
            padding: 1rem;
            border-top: 1px solid {COLORS["border"]};
            font-size: 0.74rem;
            color: {COLORS["text_light"]};
            line-height: 1.7;
        }}
        .sidebar-footer b {{
            color: {COLORS["text_mid"]};
            font-weight: 600;
        }}

        /* === Hero 顶部区 === */
        .hero {{
            background: linear-gradient(135deg, {COLORS["gradient_start"]} 0%, {COLORS["gradient_end"]} 100%);
            border-radius: 18px;
            padding: 1.6rem 1.9rem;
            color: white;
            margin-bottom: 1.3rem;
            box-shadow: 0 8px 24px rgba(79, 124, 255, 0.18);
            position: relative;
            overflow: hidden;
        }}
        .hero-title {{
            font-size: 1.6rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.01em;
            line-height: 1.3;
            color: white;
        }}
        .hero-sub {{
            font-size: 0.92rem;
            opacity: 0.88;
            margin-top: 0.4rem;
            font-weight: 400;
            line-height: 1.5;
        }}
        .hero-tag {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.18);
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-bottom: 0.55rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}

        /* === 指标卡 (固定最小高度防止对齐错乱) === */
        .metric-card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
            padding: 1rem 1.15rem;
            transition: all 0.2s ease;
            min-height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-sizing: border-box;
        }}
        .metric-card:hover {{
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
            border-color: {COLORS["primary"]};
        }}
        .metric-label {{
            font-size: 0.7rem;
            color: {COLORS["text_light"]};
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }}
        .metric-value {{
            font-size: 1.55rem;
            font-weight: 700;
            color: {COLORS["text"]};
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}
        .metric-unit {{
            font-size: 0.82rem;
            color: {COLORS["text_mid"]};
            font-weight: 500;
            margin-left: 0.3rem;
        }}
        .metric-delta {{
            font-size: 0.74rem;
            margin-top: 0.4rem;
            font-weight: 500;
            line-height: 1.4;
        }}
        .metric-delta-up {{ color: {COLORS["success"]}; }}
        .metric-delta-down {{ color: {COLORS["danger"]}; }}
        .metric-delta-neutral {{ color: {COLORS["text_light"]}; }}

        /* === 通用卡片 === */
        .card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
            padding: 1.15rem 1.3rem;
            box-sizing: border-box;
        }}
        .card-title {{
            font-size: 0.98rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 0 0 0.75rem 0;
            letter-spacing: -0.01em;
            line-height: 1.4;
        }}
        .card-sub {{
            font-size: 0.82rem;
            color: {COLORS["text_mid"]};
            margin: -0.3rem 0 0.9rem 0;
            line-height: 1.55;
        }}

        /* === 章节标题 === */
        .section-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 1.3rem 0 0.75rem 0;
            display: flex;
            align-items: center;
            letter-spacing: -0.01em;
            line-height: 1.4;
        }}
        .section-title::before {{
            content: "";
            width: 4px;
            height: 16px;
            background: linear-gradient(180deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
            border-radius: 3px;
            margin-right: 10px;
            flex-shrink: 0;
        }}

        /* === 状态徽章 === */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            line-height: 1.4;
        }}
        .badge-a {{ background: rgba(16, 185, 129, 0.12); color: {COLORS["success"]}; }}
        .badge-b {{ background: rgba(245, 158, 11, 0.12); color: {COLORS["warning"]}; }}
        .badge-c {{ background: rgba(239, 68, 68, 0.12); color: {COLORS["danger"]}; }}
        .badge-primary {{ background: rgba(79, 124, 255, 0.12); color: {COLORS["primary"]}; }}

        /* === 状态点 === */
        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }}
        .status-dot-a {{ background: {COLORS["success"]}; }}
        .status-dot-b {{ background: {COLORS["warning"]}; }}
        .status-dot-c {{ background: {COLORS["danger"]}; }}

        /* === 按钮美化 === */
        .stButton > button {{
            border-radius: 10px;
            border: 1px solid {COLORS["border"]};
            font-weight: 600;
            transition: all 0.18s;
        }}
        .stButton > button:hover {{
            border-color: {COLORS["primary"]};
            color: {COLORS["primary"]};
        }}
        .stDownloadButton > button {{
            background: linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
            color: white !important;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.5rem 1.2rem;
            transition: all 0.18s;
            box-shadow: 0 4px 12px rgba(79, 124, 255, 0.25);
        }}
        .stDownloadButton > button:hover {{
            box-shadow: 0 6px 18px rgba(79, 124, 255, 0.35);
            color: white !important;
        }}

        /* === 数据表 === */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {COLORS["border"]};
        }}

        hr {{
            border: none;
            border-top: 1px solid {COLORS["border"]};
            margin: 1.2rem 0;
        }}

        /* Tab */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {COLORS["bg_soft"]};
            padding: 4px;
            border-radius: 12px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            font-weight: 600;
            padding: 6px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            background: white !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
        }}

        code {{
            background: {COLORS["bg_soft"]};
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.85em;
            font-family: "Cascadia Code", "SF Mono", Consolas, Menlo, monospace;
        }}

        /* === 字段卡 (Dashboard Tab 1 专用) === */
        .field-card {{
            background: white;
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            padding: 0.9rem 1rem;
            min-height: 128px;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            transition: all 0.18s;
        }}
        .field-card:hover {{
            border-color: {COLORS["primary"]};
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        }}
        .field-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            font-size: 0.7rem;
            color: {COLORS["text_light"]};
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .field-card-name {{
            font-size: 1.05rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
            line-height: 1.3;
        }}
        .field-card-metric {{
            display: flex;
            justify-content: space-between;
            font-size: 0.78rem;
            color: {COLORS["text_mid"]};
            line-height: 1.5;
        }}
        .field-card-metric + .field-card-metric {{
            margin-top: 0.2rem;
        }}
        .field-card-metric-value {{
            font-weight: 600;
            color: {COLORS["text"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, unit="", delta=None, delta_kind="neutral"):
    """返回一个 metric 卡 HTML"""
    delta_html = ""
    if delta is not None:
        delta_html = f'<div class="metric-delta metric-delta-{delta_kind}">{delta}</div>'
    return f"""
    <div class="metric-card">
        <div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}<span class="metric-unit">{unit}</span></div>
        </div>
        {delta_html}
    </div>
    """


def hero(title, subtitle, tag=None):
    tag_html = f'<div class="hero-tag">{tag}</div>' if tag else ""
    st.markdown(
        f"""
        <div class="hero">
            {tag_html}
            <div class="hero-title">{title}</div>
            <div class="hero-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def badge(text, kind="a"):
    return f'<span class="badge badge-{kind}">{text}</span>'


def status_dot(kind="a"):
    return f'<span class="status-dot status-dot-{kind}"></span>'
