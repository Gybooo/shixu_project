"""全局样式 - 现代风格 (浅色, 蓝紫主色, 卡片式)"""
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
    """注入全局现代风格 CSS"""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

        /* 全局字体 */
        html, body, [class*="st-"], .main, .block-container {{
            font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }}

        /* 收紧主容器 padding */
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

        /* 侧边栏样式 */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F7F9FC 100%);
            border-right: 1px solid {COLORS["border"]};
        }}
        section[data-testid="stSidebar"] > div {{
            padding-top: 1.5rem;
        }}

        /* 侧边栏品牌区 */
        .sidebar-brand {{
            padding: 0 1rem 1.5rem 1rem;
            border-bottom: 1px solid {COLORS["border"]};
            margin-bottom: 1rem;
        }}
        .sidebar-brand-title {{
            font-size: 1.35rem;
            font-weight: 800;
            background: linear-gradient(90deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
            line-height: 1.15;
        }}
        .sidebar-brand-sub {{
            font-size: 0.78rem;
            color: {COLORS["text_light"]};
            margin-top: 0.3rem;
            font-weight: 500;
        }}

        /* Hero 顶部区 */
        .hero {{
            background: linear-gradient(135deg, {COLORS["gradient_start"]} 0%, {COLORS["gradient_end"]} 100%);
            border-radius: 20px;
            padding: 1.75rem 2rem;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(79, 124, 255, 0.2);
            position: relative;
            overflow: hidden;
        }}
        .hero::after {{
            content: "";
            position: absolute;
            right: -50px;
            top: -50px;
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.08);
        }}
        .hero::before {{
            content: "";
            position: absolute;
            right: 80px;
            bottom: -80px;
            width: 160px;
            height: 160px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.06);
        }}
        .hero-title {{
            font-size: 1.7rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .hero-sub {{
            font-size: 0.95rem;
            opacity: 0.88;
            margin-top: 0.35rem;
            font-weight: 400;
        }}
        .hero-tag {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(10px);
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        /* 指标卡 */
        .metric-card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 16px;
            padding: 1.1rem 1.25rem;
            transition: all 0.2s ease;
            height: 100%;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
            border-color: {COLORS["primary"]};
        }}
        .metric-label {{
            font-size: 0.72rem;
            color: {COLORS["text_light"]};
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }}
        .metric-value {{
            font-size: 1.7rem;
            font-weight: 700;
            color: {COLORS["text"]};
            line-height: 1;
            letter-spacing: -0.02em;
        }}
        .metric-unit {{
            font-size: 0.85rem;
            color: {COLORS["text_mid"]};
            font-weight: 500;
            margin-left: 0.3rem;
        }}
        .metric-delta {{
            font-size: 0.78rem;
            margin-top: 0.4rem;
            font-weight: 500;
        }}
        .metric-delta-up {{ color: {COLORS["success"]}; }}
        .metric-delta-down {{ color: {COLORS["danger"]}; }}
        .metric-delta-neutral {{ color: {COLORS["text_light"]}; }}

        /* 通用卡片 */
        .card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 16px;
            padding: 1.25rem 1.4rem;
        }}
        .card-title {{
            font-size: 1.0rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 0 0 0.75rem 0;
            letter-spacing: -0.01em;
        }}
        .card-sub {{
            font-size: 0.82rem;
            color: {COLORS["text_mid"]};
            margin: -0.5rem 0 1rem 0;
        }}

        /* 章节标题 */
        .section-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 1.5rem 0 0.85rem 0;
            display: flex;
            align-items: center;
            letter-spacing: -0.01em;
        }}
        .section-title::before {{
            content: "";
            width: 4px;
            height: 18px;
            background: linear-gradient(180deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
            border-radius: 3px;
            margin-right: 10px;
        }}

        /* 状态徽章 */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }}
        .badge-a {{ background: rgba(16, 185, 129, 0.12); color: {COLORS["success"]}; }}
        .badge-b {{ background: rgba(245, 158, 11, 0.12); color: {COLORS["warning"]}; }}
        .badge-c {{ background: rgba(239, 68, 68, 0.12); color: {COLORS["danger"]}; }}
        .badge-primary {{ background: rgba(79, 124, 255, 0.12); color: {COLORS["primary"]}; }}

        /* 状态点 */
        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18);
        }}
        .status-dot-a {{ background: {COLORS["success"]}; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2); }}
        .status-dot-b {{ background: {COLORS["warning"]}; box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2); }}
        .status-dot-c {{ background: {COLORS["danger"]}; box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2); }}

        /* 按钮美化 */
        .stButton > button {{
            border-radius: 10px;
            border: 1px solid {COLORS["border"]};
            font-weight: 600;
            transition: all 0.18s;
        }}
        .stButton > button:hover {{
            border-color: {COLORS["primary"]};
            color: {COLORS["primary"]};
            transform: translateY(-1px);
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
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(79, 124, 255, 0.35);
            color: white !important;
        }}

        /* 数据表 */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {COLORS["border"]};
        }}

        /* 分隔线 */
        hr {{
            border: none;
            border-top: 1px solid {COLORS["border"]};
            margin: 1.5rem 0;
        }}

        /* tab */
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

        /* 展开区 */
        details > summary {{
            cursor: pointer;
            font-weight: 600;
            color: {COLORS["primary"]};
        }}

        /* 代码块 */
        code {{
            background: {COLORS["bg_soft"]};
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.85em;
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
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}<span class="metric-unit">{unit}</span></div>
        {delta_html}
    </div>
    """


def hero(title, subtitle, tag=None):
    tag_html = f'<div class="hero-tag">{tag}</div>' if tag else ""
    st.markdown(
        f"""
        <div class="hero">
            {tag_html}
            <h1 class="hero-title">{title}</h1>
            <div class="hero-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def badge(text, kind="a"):
    """kind: a (绿) / b (橙) / c (红) / primary (蓝)"""
    return f'<span class="badge badge-{kind}">{text}</span>'


def status_dot(kind="a"):
    return f'<span class="status-dot status-dot-{kind}"></span>'
