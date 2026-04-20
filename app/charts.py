"""Plotly 图表工厂 - 现代极简风格"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .data import GROUP_COLORS
from .style import COLORS


# 统一 Plotly 默认风格
BASE_LAYOUT = dict(
    font=dict(family="Inter, Noto Sans SC, sans-serif", color=COLORS["text"], size=12),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(
        bgcolor="white",
        bordercolor=COLORS["border"],
        font_size=12,
        font_family="Inter",
    ),
    xaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        zerolinecolor=COLORS["border"],
        title_font=dict(size=12, color=COLORS["text_mid"]),
        tickfont=dict(size=11, color=COLORS["text_mid"]),
    ),
    yaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        zerolinecolor=COLORS["border"],
        title_font=dict(size=12, color=COLORS["text_mid"]),
        tickfont=dict(size=11, color=COLORS["text_mid"]),
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=COLORS["border"],
        borderwidth=1,
        font=dict(size=11),
    ),
)


def apply_layout(fig, **kwargs):
    """合并 BASE_LAYOUT 与自定义参数, 后者覆盖前者"""
    layout = {**BASE_LAYOUT, **kwargs}
    fig.update_layout(**layout)
    return fig


def plot_timeseries(s, title=None, color=None, height=320):
    """单字段时序曲线"""
    color = color or COLORS["primary"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, mode="lines",
        line=dict(color=color, width=1.5),
        hovertemplate="<b>%{x|%H:%M:%S}</b><br>值=%{y:.4f}<extra></extra>",
        name="",
    ))
    apply_layout(fig, title=title, height=height,
                 xaxis_title="时间", yaxis_title="数值")
    return fig


def plot_timeseries_with_trend(raw, trend, title=None, height=360):
    """原始 + 趋势 叠加"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=raw.index, y=raw.values, mode="lines",
        line=dict(color=COLORS["border"], width=1),
        name="原始", opacity=0.55,
        hovertemplate="%{y:.4f}<extra>原始</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=trend.index, y=trend.values, mode="lines",
        line=dict(color=COLORS["primary"], width=2.2),
        name="趋势 (SavGol)",
        hovertemplate="%{y:.4f}<extra>趋势</extra>",
    ))
    apply_layout(fig, title=title, height=height,
                 xaxis_title="时间", yaxis_title="数值",
                 hovermode="x unified")
    return fig


def plot_forecast_sample(actual, lstm_pred, tfm_pred, title=None, height=340):
    """单个预测窗口的对比曲线"""
    x = np.arange(len(actual))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=actual, mode="lines+markers",
        line=dict(color=COLORS["text"], width=2.2),
        marker=dict(size=5),
        name="真实值",
        hovertemplate="步%{x}: %{y:.4f}<extra>真实值</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=lstm_pred, mode="lines+markers",
        line=dict(color=COLORS["danger"], width=1.8, dash="dash"),
        marker=dict(size=4),
        name="LSTM",
        hovertemplate="步%{x}: %{y:.4f}<extra>LSTM</extra>",
    ))
    if tfm_pred is not None:
        fig.add_trace(go.Scatter(
            x=x, y=tfm_pred, mode="lines+markers",
            line=dict(color=COLORS["success"], width=1.8, dash="dot"),
            marker=dict(size=4),
            name="TimesFM",
            hovertemplate="步%{x}: %{y:.4f}<extra>TimesFM</extra>",
        ))
    apply_layout(fig, title=title, height=height,
                 xaxis_title="预测步 (秒)", yaxis_title="数值",
                 hovermode="x unified",
                 legend=dict(orientation="h", y=1.10, x=1, xanchor="right"))
    return fig


def plot_nrmse_bar(df, height=440):
    """11 字段 NRMSE 柱状图 (按族分色, LSTM vs TFM 并列)"""
    fig = go.Figure()
    colors = [GROUP_COLORS[g] for g in df["类别"]]
    fig.add_trace(go.Bar(
        name="LSTM",
        x=df["属性"], y=df["NRMSE_LSTM%"],
        marker=dict(color=colors, opacity=0.5,
                    pattern=dict(shape="/", size=6, solidity=0.2),
                    line=dict(color=colors, width=1.5)),
        hovertemplate="<b>%{x}</b><br>LSTM NRMSE: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="TimesFM",
        x=df["属性"], y=df["NRMSE_TFM%"],
        marker=dict(color=colors,
                    line=dict(color=colors, width=1)),
        hovertemplate="<b>%{x}</b><br>TFM NRMSE: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=20, line=dict(color=COLORS["success"], dash="dash", width=1.5),
                  annotation_text=" A档阈值 20%", annotation_position="right",
                  annotation_font=dict(size=10, color=COLORS["success"]))
    fig.add_hline(y=35, line=dict(color=COLORS["danger"], dash="dash", width=1.5),
                  annotation_text=" C档阈值 35%", annotation_position="right",
                  annotation_font=dict(size=10, color=COLORS["danger"]))
    apply_layout(fig, height=height,
                 barmode="group",
                 yaxis_title="NRMSE (%)",
                 xaxis_title="",
                 legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    fig.update_xaxes(tickangle=-20)
    return fig


def plot_quadrant(df, height=540):
    """ACF × SNR 可用性判据象限图"""
    fig = go.Figure()
    # 背景区域 - A 档绿色
    fig.add_shape(type="rect", x0=0.75, x1=1.0, y0=1.3, y1=10,
                  fillcolor="rgba(16, 185, 129, 0.06)", line=dict(width=0), layer="below")
    # B 档橙色
    fig.add_shape(type="rect", x0=0.55, x1=0.75, y0=0.5, y1=10,
                  fillcolor="rgba(245, 158, 11, 0.06)", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=0.75, x1=1.0, y0=0.5, y1=1.3,
                  fillcolor="rgba(245, 158, 11, 0.06)", line=dict(width=0), layer="below")
    # 网格线
    fig.add_vline(x=0.75, line=dict(color=COLORS["success"], dash="dash", width=1))
    fig.add_vline(x=0.55, line=dict(color=COLORS["warning"], dash="dash", width=1))
    fig.add_hline(y=1.3, line=dict(color=COLORS["success"], dash="dash", width=1))
    fig.add_hline(y=0.5, line=dict(color=COLORS["danger"], dash="dash", width=1))

    for group, color in GROUP_COLORS.items():
        sub = df[df["类别"] == group]
        if len(sub) == 0:
            continue
        sizes = 16 + sub["NRMSE_TFM%"].values * 1.2
        fig.add_trace(go.Scatter(
            x=sub["ACF_lag16"], y=sub["SNR"],
            mode="markers+text",
            marker=dict(size=sizes, color=color, opacity=0.75,
                        line=dict(color="white", width=2)),
            text=sub["属性"],
            textposition="top center",
            textfont=dict(size=10, color=COLORS["text"]),
            name=group,
            customdata=np.stack([sub["NRMSE_TFM%"], sub["可用性"]], axis=-1),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "ACF lag-16: %{x:.3f}<br>"
                "SNR: %{y:.3f}<br>"
                "NRMSE: %{customdata[0]:.1f}%<br>"
                "判定: %{customdata[1]}<extra></extra>"
            ),
        ))

    # 区域文字
    fig.add_annotation(x=0.93, y=5, text="<b>A 档 · 可直接部署</b>",
                       showarrow=False, font=dict(size=12, color=COLORS["success"]))
    fig.add_annotation(x=0.66, y=0.9, text="<b>B 档 · 可用需复核</b>",
                       showarrow=False, font=dict(size=11, color=COLORS["warning"]))
    fig.add_annotation(x=0.4, y=0.28, text="<b>C 档 · 不建议直接用</b>",
                       showarrow=False, font=dict(size=11, color=COLORS["danger"]))

    apply_layout(fig, height=height,
                 xaxis_title="ACF lag-16 (趋势长程可预测性)",
                 yaxis_title="SNR (信噪比, 对数)",
                 legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    fig.update_yaxes(type="log", range=[np.log10(0.15), np.log10(3)])
    fig.update_xaxes(range=[0.35, 1.0])
    return fig


def plot_correlation_heatmap(corr, height=540):
    """11×11 相关矩阵"""
    fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale=[[0, "#EF4444"], [0.5, "#FFFFFF"], [1, "#4F7CFF"]],
        zmid=0, zmin=-1, zmax=1,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10),
        hovertemplate="<b>%{x} × %{y}</b><br>r = %{z:.3f}<extra></extra>",
        colorbar=dict(title="r", thickness=14, len=0.75),
    ))
    apply_layout(fig, height=height, xaxis_title="", yaxis_title="")
    fig.update_xaxes(side="bottom", tickangle=-30)
    return fig


def plot_nrmse_by_group(df, height=340):
    """按族分组的 NRMSE 盒须图"""
    fig = go.Figure()
    for group, color in GROUP_COLORS.items():
        sub = df[df["类别"] == group]
        if len(sub) == 0:
            continue
        fig.add_trace(go.Box(
            y=sub["NRMSE_TFM%"],
            name=group,
            boxpoints="all",
            jitter=0.4,
            pointpos=0,
            marker=dict(color=color, size=8, line=dict(color="white", width=1)),
            line=dict(color=color, width=1.5),
            fillcolor=color,
            opacity=0.45,
            hovertemplate="%{y:.1f}%<extra>%{x}</extra>",
        ))
    apply_layout(fig, height=height,
                 yaxis_title="NRMSE TFM (%)",
                 showlegend=False)
    return fig


def plot_metric_gauge(value, label, max_val=50, thresholds=(20, 35), height=220):
    """仪表盘 - 用于单字段性能评估"""
    t1, t2 = thresholds
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(suffix="%", font=dict(size=26, color=COLORS["text"])),
        title=dict(text=label, font=dict(size=14, color=COLORS["text_mid"])),
        gauge=dict(
            axis=dict(range=[0, max_val], tickwidth=1, tickcolor=COLORS["text_light"]),
            bar=dict(color=COLORS["primary"], thickness=0.3),
            bgcolor="white",
            borderwidth=0,
            steps=[
                dict(range=[0, t1], color="rgba(16, 185, 129, 0.18)"),
                dict(range=[t1, t2], color="rgba(245, 158, 11, 0.18)"),
                dict(range=[t2, max_val], color="rgba(239, 68, 68, 0.18)"),
            ],
            threshold=dict(
                line=dict(color=COLORS["text"], width=3),
                thickness=0.75,
                value=value,
            ),
        ),
    ))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="white")
    return fig
