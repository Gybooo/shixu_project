"""
生成 CSV 字段 → 图表对照 Excel，便于展示时用。
"""

import os
import numpy as np
import pandas as pd

CSV_PATH = r"E:\timesfm_project\时序\MPB01_6.11 08_18.csv"
OUTPUT_DIR = r"E:\timesfm_project\output"
XLSX_PATH = os.path.join(OUTPUT_DIR, "CSV字段对照表.xlsx")


FIELD_META = [
    # (原_field, 中文描述, 物理类别, 量纲/单位, 图中位置)
    ("Magnitude", "振动合成幅值", "合成幅值", "g (标准化)", "图1-组A / 图2-左上 / 图3 / 图4"),
    ("ShockX", "X轴冲击峰值", "三轴冲击", "冲击强度 (量级 ±1500)", "图1-组C / 图2"),
    ("ShockY", "Y轴冲击峰值", "三轴冲击", "冲击强度 (量级 ±500)", "图1-组C / 图2"),
    ("ShockZ", "Z轴冲击峰值", "三轴冲击", "冲击强度 (量级 ±800)", "图1-组C / 图2"),
    ("aRMSX", "X轴加速度均方根", "加速度 RMS", "g", "图1-组B / 图2"),
    ("aRMSY", "Y轴加速度均方根", "加速度 RMS", "g", "图1-组B / 图2"),
    ("aRMSZ", "Z轴加速度均方根", "加速度 RMS", "g", "图1-组B / 图2"),
    ("vRMSM", "合成速度均方根", "速度 RMS", "mm/s", "图1-组B / 图2"),
    ("vRMSX", "X轴速度均方根", "速度 RMS", "mm/s", "图1-组B / 图2"),
    ("vRMSY", "Y轴速度均方根", "速度 RMS", "mm/s", "图1-组B / 图2"),
    ("vRMSZ", "Z轴速度均方根", "速度 RMS", "mm/s", "图1-组B / 图2"),
]


def load_fields(csv_path):
    df = pd.read_csv(csv_path, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])

    out = {}
    for f in df["_field"].unique():
        s = df[df["_field"] == f][["_time", "_value"]].set_index("_time").sort_index()
        out[f] = s["_value"]
    return out, df


def main():
    print("读取 CSV 原始数据...", flush=True)
    fields, raw_df = load_fields(CSV_PATH)
    print(f"  _measurement = {raw_df['_measurement'].unique().tolist()}")
    print(f"  _field 共 {raw_df['_field'].nunique()} 种")
    print(f"  总行数 = {len(raw_df)}")
    print(f"  时间范围 = {raw_df['_time'].min()} ~ {raw_df['_time'].max()}")

    # ---------- Sheet 1: CSV 字段对照表 ----------
    sheet1_rows = []
    for _field, desc, cat, unit, figloc in FIELD_META:
        s_raw = fields[_field]
        s_1s = s_raw.resample("1s").mean().dropna()
        sheet1_rows.append({
            "CSV 字段 (_field)": _field,
            "中文含义": desc,
            "物理类别": cat,
            "单位/量纲": unit,
            "原始记录数": len(s_raw),
            "1秒重采样点数": len(s_1s),
            "均值": round(s_1s.mean(), 4),
            "标准差": round(s_1s.std(), 4),
            "最小值": round(s_1s.min(), 4),
            "最大值": round(s_1s.max(), 4),
            "变异系数 CV": round(s_1s.std() / (abs(s_1s.mean()) + 1e-9), 4),
            "预测难度": ("高" if s_1s.std()/(abs(s_1s.mean())+1e-9) > 1
                     else "中" if s_1s.std()/(abs(s_1s.mean())+1e-9) > 0.5
                     else "低"),
            "出现在图": figloc,
        })
    sheet1_df = pd.DataFrame(sheet1_rows)

    # ---------- Sheet 2: CSV 原始格式说明 ----------
    sheet2_df = pd.DataFrame([
        {"列名": "result", "含义": "查询结果名 (InfluxDB 保留字段)",
         "示例值": "_result"},
        {"列名": "table", "含义": "表编号 (每个 _field 一张子表)",
         "示例值": "0-10 (对应 11 个属性)"},
        {"列名": "_start", "含义": "查询起始时间 (InfluxDB 元数据)",
         "示例值": "2024-06-11T00:00:00Z"},
        {"列名": "_stop", "含义": "查询截止时间 (InfluxDB 元数据)",
         "示例值": "2024-06-11T10:00:00Z"},
        {"列名": "_time", "含义": "**时间戳 (RFC3339 UTC)**",
         "示例值": "2024-06-11T07:23:04.061Z"},
        {"列名": "_value", "含义": "**测量值 (数值)**",
         "示例值": "0.811319923"},
        {"列名": "_field", "含义": "**属性名 (11 种，见 Sheet 1)**",
         "示例值": "Magnitude / ShockX / aRMSY / vRMSM 等"},
        {"列名": "_measurement", "含义": "**设备标识**",
         "示例值": "MPB_01"},
    ])

    # ---------- Sheet 3: 图文件说明 ----------
    sheet3_df = pd.DataFrame([
        {"文件名": "属性总览_1_分量级时序.png",
         "内容": "11 属性分 3 组 (A合成幅值/B RMS/C 冲击) 时序对照",
         "对应 CSV 字段": "全部 11 个 _field"},
        {"文件名": "属性总览_2_独立子图.png",
         "内容": "11 属性独立子图，每个一个面板",
         "对应 CSV 字段": "全部 11 个 _field"},
        {"文件名": "属性总览_3_统计与相关性.png",
         "内容": "数值量级 log 柱图 + 变异系数 + 两两相关矩阵",
         "对应 CSV 字段": "全部 11 个 _field"},
        {"文件名": "属性总览_4_异常事件放大.png",
         "内容": "Magnitude 骤降事件放大，疑似停机/故障时段",
         "对应 CSV 字段": "_field=Magnitude"},
    ])

    # ---------- Sheet 4: 异常事件列表 ----------
    mag = fields["Magnitude"].resample("1s").mean().dropna()
    med = mag.median()
    std = mag.std()
    low = mag.values < (med - 3.0 * std * 0.3)
    events = []
    i = 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if j - i >= 3:
                events.append({
                    "事件编号": f"E{len(events)+1:02d}",
                    "开始时间": mag.index[i].strftime("%Y-%m-%d %H:%M:%S"),
                    "结束时间": mag.index[j-1].strftime("%Y-%m-%d %H:%M:%S"),
                    "持续秒数": (mag.index[j-1] - mag.index[i]).total_seconds() + 1,
                    "最低值": round(mag.values[i:j].min(), 4),
                    "判定": "振动骤降 (疑似停机/故障)",
                })
            i = j
        else:
            i += 1
    sheet4_df = pd.DataFrame(events)

    # ---------- Sheet 5: 相关矩阵 ----------
    order = [m[0] for m in FIELD_META]
    aligned = pd.DataFrame({f: fields[f].resample("1s").mean() for f in order}).dropna()
    corr_df = aligned.corr().round(4)

    # 写入 Excel
    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        sheet1_df.to_excel(writer, sheet_name="1_字段对照表", index=False)
        sheet2_df.to_excel(writer, sheet_name="2_CSV列说明", index=False)
        sheet3_df.to_excel(writer, sheet_name="3_图文件说明", index=False)
        sheet4_df.to_excel(writer, sheet_name="4_异常事件", index=False)
        corr_df.to_excel(writer, sheet_name="5_相关矩阵")

        wb = writer.book
        for sn in wb.sheetnames:
            ws = wb[sn]
            for col_cells in ws.columns:
                max_len = max(
                    (len(str(c.value)) if c.value is not None else 0
                     for c in col_cells), default=8)
                w = min(max(12, max_len + 2), 60)
                ws.column_dimensions[col_cells[0].column_letter].width = w
            ws.freeze_panes = "A2"

    print(f"\n[OK] 对照表已生成: {XLSX_PATH}")
    print(f"\n包含 5 个 Sheet:")
    print(f"  Sheet 1 — 字段对照表 ({len(sheet1_df)} 行)")
    print(f"  Sheet 2 — CSV 列说明 ({len(sheet2_df)} 行)")
    print(f"  Sheet 3 — 图文件说明 ({len(sheet3_df)} 行)")
    print(f"  Sheet 4 — 异常事件 ({len(sheet4_df)} 个)")
    print(f"  Sheet 5 — 相关矩阵 ({len(corr_df)}×{len(corr_df)})")


if __name__ == "__main__":
    main()
