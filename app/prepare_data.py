"""
一次性预处理脚本: 把 28MB 的原始 InfluxDB CSV 压缩成 ~1MB parquet
运行: python -m app.prepare_data

产出: app/resources/fields.parquet
"""
import os
import sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "时序", "MPB01_6.11 08_18.csv")
OUT_DIR = os.path.join(ROOT, "app", "resources")
OUT_PATH = os.path.join(OUT_DIR, "fields.parquet")


ALL_FIELDS = [
    "Magnitude",
    "aRMSX", "aRMSY", "aRMSZ",
    "vRMSX", "vRMSY", "vRMSZ", "vRMSM",
    "ShockX", "ShockY", "ShockZ",
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        print(f"[ERR] 原始 CSV 不存在: {CSV_PATH}")
        sys.exit(1)

    print(f"读取原始 CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])

    print(f"总行数: {len(df):,}")

    frames = []
    for f in ALL_FIELDS:
        sub = df[df["_field"] == f]
        s = sub.set_index("_time").sort_index()["_value"].resample("1s").mean().dropna()
        fs = s.to_frame(name=f)
        frames.append(fs)
        print(f"  {f:12s} → {len(s):,} 点")

    merged = pd.concat(frames, axis=1)
    merged.to_parquet(OUT_PATH, compression="snappy")
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"\n[OK] 已保存: {OUT_PATH} ({size_kb:.1f} KB, {len(merged):,} 行)")


if __name__ == "__main__":
    main()
