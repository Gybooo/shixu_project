"""数据加载层 - 复用现有 CSV / NPZ / 原始时序数据"""
import json
import os
from functools import lru_cache

import numpy as np
import pandas as pd
import streamlit as st
from scipy import signal

# 路径配置
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
CSV_PATH = os.path.join(ROOT, "时序", "MPB01_6.11 08_18.csv")

ALL_FIELDS = [
    "Magnitude",
    "aRMSX", "aRMSY", "aRMSZ",
    "vRMSX", "vRMSY", "vRMSZ", "vRMSM",
    "ShockX", "ShockY", "ShockZ",
]

FIELD_GROUPS = {
    "Magnitude": "合成幅值",
    "aRMSX": "加速度RMS", "aRMSY": "加速度RMS", "aRMSZ": "加速度RMS",
    "vRMSX": "速度RMS", "vRMSY": "速度RMS", "vRMSZ": "速度RMS", "vRMSM": "速度RMS",
    "ShockX": "冲击类", "ShockY": "冲击类", "ShockZ": "冲击类",
}

GROUP_COLORS = {
    "合成幅值": "#4F7CFF",
    "加速度RMS": "#10B981",
    "速度RMS": "#7C3AED",
    "冲击类": "#EF4444",
}

FIELD_UNITS = {
    "Magnitude": "g",
    "aRMSX": "g", "aRMSY": "g", "aRMSZ": "g",
    "vRMSX": "mm/s", "vRMSY": "mm/s", "vRMSZ": "mm/s", "vRMSM": "mm/s",
    "ShockX": "g", "ShockY": "g", "ShockZ": "g",
}

FIELDS_4 = ["Magnitude", "aRMSX", "vRMSM", "ShockZ"]  # 有详细预测缓存的 4 字段


@st.cache_data(show_spinner=False)
def load_summary_csv():
    """11 字段完整对比表"""
    path = os.path.join(OUTPUT_DIR, "全字段泛化测试.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df


@st.cache_data(show_spinner=False)
def load_allfields_cache():
    """11 字段 LSTM + field_info"""
    path = os.path.join(OUTPUT_DIR, "allfields_cache.npz")
    if not os.path.exists(path):
        return {}, {}
    c = np.load(path, allow_pickle=True)
    lstm = json.loads(str(c["lstm_results"]))
    fi = json.loads(str(c["field_info"]))
    return lstm, fi


@st.cache_data(show_spinner=False)
def load_multifield_cache():
    """4 字段详细预测 (eval_preds / eval_actuals)"""
    path = os.path.join(OUTPUT_DIR, "multifield_cache.npz")
    if not os.path.exists(path):
        return {}, {}
    c = np.load(path, allow_pickle=True)
    lstm = json.loads(str(c["lstm_results"]))
    fi = json.loads(str(c["field_info"]))
    return lstm, fi


PARQUET_PATH = os.path.join(ROOT, "app", "resources", "fields.parquet")


@st.cache_data(show_spinner=False)
def _load_all_fields_parquet():
    """优先加载预处理的 parquet (11 字段 × 8960 点)"""
    if os.path.exists(PARQUET_PATH):
        return pd.read_parquet(PARQUET_PATH)
    return None


@st.cache_data(show_spinner="加载原始时序数据...")
def load_raw_field(field):
    """加载单字段时序, 优先用 parquet, 回退到原始 CSV"""
    df_all = _load_all_fields_parquet()
    if df_all is not None and field in df_all.columns:
        return df_all[field].dropna()
    if not os.path.exists(CSV_PATH):
        return pd.Series(dtype=float)
    df = pd.read_csv(CSV_PATH, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df = df[df["_field"] == field]
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])
    s = df.set_index("_time").sort_index()["_value"].resample("1s").mean().dropna()
    return s


def savgol_trend(s, window=61, polyorder=3):
    """SavGol 趋势分解"""
    if len(s) < window:
        return s.copy()
    t = signal.savgol_filter(s.values, window_length=window, polyorder=polyorder)
    return pd.Series(t, index=s.index)


@st.cache_data(show_spinner="计算相关矩阵...")
def compute_correlation_matrix():
    """加载所有字段并计算 11×11 相关矩阵"""
    df_all = _load_all_fields_parquet()
    if df_all is not None:
        return df_all[ALL_FIELDS].dropna().corr()
    data = {}
    for f in ALL_FIELDS:
        try:
            s = load_raw_field(f)
            if len(s) > 0:
                data[f] = s
        except Exception:
            pass
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).dropna().corr()


def classify_usability(nrmse, acf16, snr):
    """可用性判据 v2 (命中率 11/11)"""
    if snr < 0.5:
        return "C", "不建议直接使用"
    if nrmse < 0.20 and acf16 > 0.75 and snr > 1.3:
        return "A", "可直接部署"
    if nrmse < 0.25 and acf16 > 0.70:
        return "B", "可用, 建议复核"
    return "C", "不建议直接使用"


def detect_shutdown_events(s, z_threshold=3.0, min_duration=3):
    """检测 Magnitude 骤降事件 (停机)"""
    if len(s) == 0:
        return []
    med = s.median()
    std = s.std()
    threshold = med - z_threshold * std * 0.3
    is_low = (s < threshold).values
    events = []
    in_event = False
    start = 0
    for i, low in enumerate(is_low):
        if low and not in_event:
            start = i
            in_event = True
        elif not low and in_event:
            duration = i - start
            if duration >= min_duration:
                events.append({
                    "start_idx": start,
                    "end_idx": i - 1,
                    "duration_s": duration,
                    "start_time": s.index[start],
                    "end_time": s.index[i - 1],
                    "min_value": float(s.iloc[start:i].min()),
                })
            in_event = False
    return events


def field_summary_row(field, field_info, lstm_mae=None, tfm_mae=None):
    """组装单字段摘要数据"""
    fi = field_info.get(field, {})
    if not fi:
        return None
    trend_std = fi.get("trend_std", 0)
    noise_std = fi.get("noise_std", 0)
    snr = trend_std / max(noise_std, 1e-9)
    nrmse_l = lstm_mae / max(trend_std, 1e-9) if lstm_mae else None
    nrmse_t = tfm_mae / max(trend_std, 1e-9) if tfm_mae else None
    grade = None
    grade_desc = None
    if nrmse_t is not None:
        grade, grade_desc = classify_usability(nrmse_t, fi.get("acf_lag16", 0), snr)
    return {
        "field": field,
        "group": FIELD_GROUPS.get(field, "其他"),
        "unit": FIELD_UNITS.get(field, ""),
        "mean": fi.get("mean", 0),
        "std": fi.get("std", 0),
        "trend_std": trend_std,
        "noise_std": noise_std,
        "snr": snr,
        "acf_lag1": fi.get("acf_lag1", 0),
        "acf_lag16": fi.get("acf_lag16", 0),
        "lstm_mae": lstm_mae,
        "tfm_mae": tfm_mae,
        "nrmse_lstm": nrmse_l,
        "nrmse_tfm": nrmse_t,
        "grade": grade,
        "grade_desc": grade_desc,
    }
