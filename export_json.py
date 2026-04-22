"""
把 output/ 下的所有数据产物转成前端能直接读的 JSON
输出到 frontend/public/data/
"""
import json
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT, "output")
FRONTEND_DATA = os.path.join(ROOT, "frontend", "public", "data")
os.makedirs(FRONTEND_DATA, exist_ok=True)

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

FIELD_UNITS = {
    "Magnitude": "g",
    "aRMSX": "g", "aRMSY": "g", "aRMSZ": "g",
    "vRMSX": "mm/s", "vRMSY": "mm/s", "vRMSZ": "mm/s", "vRMSM": "mm/s",
    "ShockX": "g", "ShockY": "g", "ShockZ": "g",
}


def export_summary():
    """11 字段对比表"""
    df = pd.read_csv(os.path.join(OUTPUT_DIR, "全字段泛化测试.csv"))
    rows = []
    for _, r in df.iterrows():
        grade = r["可用性"][0]
        rows.append({
            "field": r["属性"],
            "group": r["类别"],
            "unit": FIELD_UNITS.get(r["属性"], ""),
            "mean": float(r["均值"]),
            "trendStd": float(r["趋势std"]),
            "noiseStd": float(r["噪声std"]),
            "snr": float(r["SNR"]),
            "acfLag16": float(r["ACF_lag16"]),
            "lstmMae": float(r["LSTM_MAE"]),
            "tfmMae": float(r["TFM_MAE"]),
            "nrmseLstm": float(r["NRMSE_LSTM%"]),
            "nrmseTfm": float(r["NRMSE_TFM%"]),
            "tfmImprove": float(r["TFM提升%"]),
            "grade": grade,
            "gradeText": r["可用性"],
        })
    out = os.path.join(FRONTEND_DATA, "summary.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"fields": rows}, f, ensure_ascii=False, indent=2)
    print(f"[OK] {out} ({len(rows)} fields)")


def export_timeseries():
    """11 字段时序, 下采样到 6s/点 (~1500 点) 减小文件大小"""
    parquet_path = os.path.join(ROOT, "app", "resources", "fields.parquet")
    if not os.path.exists(parquet_path):
        print(f"[SKIP] {parquet_path} 不存在")
        return
    df = pd.read_parquet(parquet_path)
    # 下采样 (原始 8960 点 / 1s → 1493 点 / 6s)
    df_down = df.resample("6s").mean().dropna(how="all")
    data = {
        "timestamps": [t.isoformat() for t in df_down.index],
        "samplingSeconds": 6,
        "fields": {},
    }
    for f in ALL_FIELDS:
        if f in df_down.columns:
            # 保留 4 位小数以控制大小
            data["fields"][f] = [round(float(v), 4) if pd.notna(v) else None
                                  for v in df_down[f].values]
    out = os.path.join(FRONTEND_DATA, "timeseries.json")
    with open(out, "w", encoding="utf-8") as f_out:
        json.dump(data, f_out, ensure_ascii=False)
    size_kb = os.path.getsize(out) / 1024
    print(f"[OK] {out} ({size_kb:.0f} KB, {len(df_down)} pts × {len(ALL_FIELDS)} fields)")


def export_forecast():
    """4 字段 × 60 窗口 × 16 步预测"""
    cache = np.load(os.path.join(OUTPUT_DIR, "multifield_cache.npz"), allow_pickle=True)
    lstm = json.loads(str(cache["lstm_results"]))
    out_data = {}
    for field, d in lstm.items():
        preds = np.array(d["eval_preds"])
        actuals = np.array(d["eval_actuals"])
        out_data[field] = {
            "mae": float(d["mae"]),
            "trainTime": float(d.get("train_time", 0)),
            "preds": preds.round(5).tolist(),
            "actuals": actuals.round(5).tolist(),
        }
    out = os.path.join(FRONTEND_DATA, "forecast.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False)
    size_kb = os.path.getsize(out) / 1024
    print(f"[OK] {out} ({size_kb:.0f} KB, {len(out_data)} fields × 60 windows × 16 steps)")


def export_correlation():
    """11×11 相关矩阵"""
    parquet_path = os.path.join(ROOT, "app", "resources", "fields.parquet")
    if not os.path.exists(parquet_path):
        print(f"[SKIP] correlation")
        return
    df = pd.read_parquet(parquet_path)
    corr = df[ALL_FIELDS].dropna().corr()
    out_data = {
        "fields": ALL_FIELDS,
        "matrix": corr.round(3).values.tolist(),
    }
    out = os.path.join(FRONTEND_DATA, "correlation.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] {out}")


def export_alarms():
    """Magnitude 的 18 次疑似停机事件"""
    parquet_path = os.path.join(ROOT, "app", "resources", "fields.parquet")
    if not os.path.exists(parquet_path):
        return
    df = pd.read_parquet(parquet_path)
    s = df["Magnitude"].dropna()
    med = s.median()
    std = s.std()
    threshold = med - 3.0 * std * 0.3
    is_low = (s < threshold).values
    events = []
    in_event, start = False, 0
    for i, low in enumerate(is_low):
        if low and not in_event:
            start = i; in_event = True
        elif not low and in_event:
            duration = i - start
            if duration >= 3:
                min_v = float(s.iloc[start:i].min())
                events.append({
                    "id": len(events) + 1,
                    "startTime": s.index[start].isoformat(),
                    "endTime": s.index[i - 1].isoformat(),
                    "durationSeconds": int(duration),
                    "minValue": round(min_v, 4),
                    "severity": "C" if duration > 10 else ("B" if duration > 5 else "A"),
                    "field": "Magnitude",
                    "type": "振动骤降",
                    "status": "已处理" if duration < 5 else "未处理",
                })
            in_event = False
    out = os.path.join(FRONTEND_DATA, "alarms.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, ensure_ascii=False, indent=2)
    print(f"[OK] {out} ({len(events)} events)")


def export_meta():
    """元数据 (设备/字段/族映射)"""
    meta = {
        "device": "MPB_01",
        "fields": ALL_FIELDS,
        "groups": FIELD_GROUPS,
        "units": FIELD_UNITS,
        "groupColors": {
            "合成幅值": "#4F7CFF",
            "加速度RMS": "#10B981",
            "速度RMS": "#7C3AED",
            "冲击类": "#EF4444",
        },
    }
    out = os.path.join(FRONTEND_DATA, "meta.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[OK] {out}")


if __name__ == "__main__":
    print("导出数据到 frontend/public/data/ ...")
    export_meta()
    export_summary()
    export_timeseries()
    export_forecast()
    export_correlation()
    export_alarms()
    print("\n完成")
