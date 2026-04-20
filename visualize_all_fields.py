"""
多属性时序数据可视化 (v2)
- 11 属性按量级分组画，避免混在一起
- 突出异常事件（振动骤降到0附近 = 停机/故障）
- 统计图用 log 轴避免被 Shock 压扁
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

CSV_PATH = r"E:\timesfm_project\时序\MPB01_6.11 08_18.csv"
OUTPUT_DIR = r"E:\timesfm_project\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FIELD_DESC = {
    "Magnitude": "振动合成幅值",
    "ShockX": "X轴冲击", "ShockY": "Y轴冲击", "ShockZ": "Z轴冲击",
    "aRMSX": "X轴加速度均方根", "aRMSY": "Y轴加速度均方根", "aRMSZ": "Z轴加速度均方根",
    "vRMSM": "合成速度均方根",
    "vRMSX": "X轴速度均方根", "vRMSY": "Y轴速度均方根", "vRMSZ": "Z轴速度均方根",
}

COLORS = {
    "Magnitude": "#c0392b",
    "ShockX": "#2980b9", "ShockY": "#27ae60", "ShockZ": "#8e44ad",
    "aRMSX": "#2980b9", "aRMSY": "#27ae60", "aRMSZ": "#8e44ad",
    "vRMSM": "#d35400",
    "vRMSX": "#2980b9", "vRMSY": "#27ae60", "vRMSZ": "#8e44ad",
}


def load_all_fields(csv_path):
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
        out[f] = s["_value"].resample("1s").mean().dropna()
    return out


def detect_anomaly_events(series, z_threshold=3.0, min_duration=3):
    """检测振动骤降（可能是停机/故障事件）。"""
    vals = series.values
    mean, std = np.median(vals), np.std(vals)
    low = vals < (mean - z_threshold * std * 0.3)
    events = []
    i = 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if j - i >= min_duration:
                events.append((series.index[i], series.index[j-1]))
            i = j
        else:
            i += 1
    return events


def plot_1_grouped_by_magnitude(fields, save_path):
    """
    按数值量级分 3 组画:
      - 组A: Magnitude (0~1)
      - 组B: aRMS/vRMS 系列 (0~5)
      - 组C: Shock 系列 (±1000+)
    每组一个面板，组内多条曲线。明显比单独 11 张子图易读。
    """
    events = detect_anomaly_events(fields["Magnitude"])

    group_a = ["Magnitude"]
    group_b = ["aRMSX", "aRMSY", "aRMSZ", "vRMSM", "vRMSX", "vRMSY", "vRMSZ"]
    group_c = ["ShockX", "ShockY", "ShockZ"]

    fig, axes = plt.subplots(3, 1, figsize=(22, 13), sharex=True,
                              gridspec_kw={"height_ratios": [1, 1.4, 1.2]})

    # ---------- A: Magnitude ----------
    ax = axes[0]
    s = fields["Magnitude"]
    ax.plot(s.index, s.values, color=COLORS["Magnitude"], linewidth=0.7)
    ax.fill_between(s.index, s.values, alpha=0.2, color=COLORS["Magnitude"])
    for (t0, t1) in events:
        ax.axvspan(t0, t1, color="orange", alpha=0.25)
    ax.axhline(s.median(), color="gray", linestyle="--", linewidth=0.6, alpha=0.6,
               label=f"中位数={s.median():.3f}")
    ax.set_ylabel("Magnitude\n振动合成幅值", fontsize=11)
    ax.set_title(f"【组A】合成幅值 (正常量级 0~1)  "
                 f"检测到 {len(events)} 个疑似异常事件（橙色带）",
                 fontsize=12)
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(True, alpha=0.25)

    # ---------- B: aRMS + vRMS ----------
    ax = axes[1]
    styles = {"aRMSX": "-", "aRMSY": "-", "aRMSZ": "-",
              "vRMSM": "-", "vRMSX": "--", "vRMSY": "--", "vRMSZ": "--"}
    for f in group_b:
        ss = fields[f]
        ax.plot(ss.index, ss.values, color=COLORS[f], linewidth=0.7,
                linestyle=styles[f], alpha=0.8,
                label=f"{f} ({FIELD_DESC[f]}, 均值={ss.mean():.2f})")
    for (t0, t1) in events:
        ax.axvspan(t0, t1, color="orange", alpha=0.15)
    ax.set_ylabel("RMS 值", fontsize=11)
    ax.set_title("【组B】加速度/速度 RMS (中等量级 0~5)",
                 fontsize=12)
    ax.legend(fontsize=8, loc="upper right", ncol=4)
    ax.grid(True, alpha=0.25)

    # ---------- C: Shock ----------
    ax = axes[2]
    for f in group_c:
        ss = fields[f]
        ax.plot(ss.index, ss.values, color=COLORS[f], linewidth=0.5, alpha=0.75,
                label=f"{f} ({FIELD_DESC[f]}, 均值={ss.mean():.0f}, 标准差={ss.std():.0f})")
    for (t0, t1) in events:
        ax.axvspan(t0, t1, color="orange", alpha=0.15)
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.5)
    ax.set_ylabel("Shock 值", fontsize=11)
    ax.set_title("【组C】三轴冲击 (大量级 ±1500)",
                 fontsize=12)
    ax.legend(fontsize=9, loc="upper right", ncol=3)
    ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("时间 (2024-06-11)", fontsize=12)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=30)

    fig.suptitle("MPB_01 设备 — 11 属性分量级可视化（橙色带 = 疑似停机/异常事件）",
                 fontsize=15, fontweight="bold", y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(save_path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {os.path.basename(save_path)}")
    return events


def plot_2_single_field_details(fields, save_path):
    """
    每个属性一张清晰的独立子图，4 列 × 3 行 布局。
    每张子图标题直接写属性名+描述+关键统计，不再挤在 y 轴。
    """
    order = ["Magnitude",
             "ShockX", "ShockY", "ShockZ",
             "aRMSX", "aRMSY", "aRMSZ",
             "vRMSM", "vRMSX", "vRMSY", "vRMSZ"]

    fig, axes = plt.subplots(3, 4, figsize=(24, 12), sharex=True)
    axes = axes.flatten()

    for i, f in enumerate(order):
        ax = axes[i]
        s = fields[f]
        ax.plot(s.index, s.values, color=COLORS[f], linewidth=0.5, alpha=0.8)
        ax.fill_between(s.index, s.values, alpha=0.15, color=COLORS[f])
        ax.axhline(s.mean(), color="red", linestyle="--", linewidth=0.8,
                   alpha=0.6, label=f"均值={s.mean():.3f}")
        ax.set_title(f"{f} — {FIELD_DESC[f]}\n"
                     f"范围 [{s.min():.2f}, {s.max():.2f}]  标准差 {s.std():.3f}",
                     fontsize=10)
        ax.tick_params(axis="y", labelsize=8)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, alpha=0.2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, fontsize=8)

    for j in range(len(order), len(axes)):
        axes[j].axis("off")

    fig.suptitle("MPB_01 设备 — 11 属性独立时序图 (各自独立量纲)",
                 fontsize=15, fontweight="bold", y=1.00)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    plt.savefig(save_path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {os.path.basename(save_path)}")


def plot_3_stats(fields, save_path):
    """
    统计概览：
      - 均值/范围柱状图用 symlog，解决 Shock 量级压扁其他属性的问题
      - 相关矩阵热图（优化可读性）
    """
    order = ["Magnitude",
             "ShockX", "ShockY", "ShockZ",
             "aRMSX", "aRMSY", "aRMSZ",
             "vRMSM", "vRMSX", "vRMSY", "vRMSZ"]
    stats = []
    aligned = {}
    for f in order:
        s = fields[f]
        stats.append({
            "属性": f, "描述": FIELD_DESC[f],
            "均值": s.mean(), "标准差": s.std(),
            "最小": s.min(), "最大": s.max(),
            "变异系数": s.std() / (abs(s.mean()) + 1e-9),
            "绝对值均值": np.abs(s).mean(),
        })
        aligned[f] = s
    stats_df = pd.DataFrame(stats)
    corr = pd.DataFrame(aligned).dropna().corr()

    fig = plt.figure(figsize=(22, 14))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.3], hspace=0.4, wspace=0.22)

    # 左上: 绝对值均值 (log 轴，避免 Shock 压扁其他)
    ax1 = fig.add_subplot(gs[0, 0])
    x_pos = np.arange(len(stats_df))
    bar_colors = [COLORS[f] for f in stats_df["属性"]]
    bars = ax1.bar(x_pos, stats_df["绝对值均值"], color=bar_colors,
                    alpha=0.85, edgecolor="white")
    ax1.set_yscale("log")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(stats_df["属性"], rotation=45, ha="right", fontsize=10)
    ax1.set_ylabel("绝对值均值 (对数轴)", fontsize=11)
    ax1.set_title("各属性数值量级对比 — log 轴揭示跨量级差异",
                  fontsize=13)
    ax1.grid(True, alpha=0.3, axis="y", which="both")
    for i, v in enumerate(stats_df["绝对值均值"]):
        ax1.text(i, v * 1.15, f"{v:.2f}" if v < 10 else f"{v:.0f}",
                 ha="center", va="bottom", fontsize=9)

    # 右上: 变异系数
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(x_pos, stats_df["变异系数"], color=bar_colors, alpha=0.85,
            edgecolor="white")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(stats_df["属性"], rotation=45, ha="right", fontsize=10)
    ax2.set_ylabel("变异系数 std/|mean|", fontsize=11)
    ax2.set_title("各属性相对波动性对比 — 越高越难预测", fontsize=13)
    ax2.grid(True, alpha=0.3, axis="y")
    for i, v in enumerate(stats_df["变异系数"]):
        color = "red" if v > 1 else "darkorange" if v > 0.5 else "green"
        ax2.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom",
                 fontsize=9, fontweight="bold", color=color)
    ax2.axhline(1.0, color="red", linestyle="--", linewidth=0.8, alpha=0.5,
                label="高难度阈值 (CV>1)")
    ax2.axhline(0.5, color="orange", linestyle="--", linewidth=0.8, alpha=0.5,
                label="中难度阈值 (CV>0.5)")
    ax2.legend(fontsize=9, loc="upper right")

    # 下: 相关矩阵热图
    ax3 = fig.add_subplot(gs[1, :])
    im = ax3.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax3.set_xticks(range(len(corr.columns)))
    ax3.set_yticks(range(len(corr.columns)))
    ax3.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=11)
    ax3.set_yticklabels(corr.columns, fontsize=11)
    ax3.set_title("各属性两两相关系数（皮尔逊）— 揭示同类属性高度相关、Shock 独立",
                  fontsize=13)
    for i in range(len(corr)):
        for j in range(len(corr)):
            v = corr.values[i, j]
            ax3.text(j, i, f"{v:.2f}",
                     ha="center", va="center",
                     color="white" if abs(v) > 0.5 else "black",
                     fontsize=9, fontweight="bold" if abs(v) > 0.7 else "normal")
    plt.colorbar(im, ax=ax3, shrink=0.8, label="相关系数")

    fig.suptitle("MPB_01 设备 — 多属性统计概览 (v2)",
                 fontsize=15, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(save_path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {os.path.basename(save_path)}")
    return stats_df, corr


def plot_4_anomaly_zoom(fields, events, save_path):
    """放大展示异常事件区域。"""
    if len(events) == 0:
        print("  (无异常事件，跳过)")
        return
    n_show = min(4, len(events))
    events_sel = events[:n_show]

    fig, axes = plt.subplots(n_show, 1, figsize=(20, 3 * n_show))
    if n_show == 1:
        axes = [axes]

    mag = fields["Magnitude"]
    for i, (t0, t1) in enumerate(events_sel):
        ax = axes[i]
        buf = pd.Timedelta(seconds=30)
        mask = (mag.index >= t0 - buf) & (mag.index <= t1 + buf)
        sub = mag[mask]
        ax.plot(sub.index, sub.values, color="#c0392b", linewidth=1)
        ax.axvspan(t0, t1, color="orange", alpha=0.3,
                   label=f"异常持续 {(t1-t0).total_seconds():.0f} 秒")
        ax.axhline(mag.median(), color="gray", linestyle="--", linewidth=0.6,
                   alpha=0.5, label=f"正常中位数={mag.median():.2f}")
        ax.set_title(f"事件 {i+1}: {t0:%H:%M:%S} → {t1:%H:%M:%S}",
                     fontsize=11)
        ax.set_ylabel("Magnitude", fontsize=10)
        ax.legend(fontsize=9, loc="lower right")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    axes[-1].set_xlabel("时间", fontsize=11)
    fig.suptitle(f"异常事件放大图 — 振动骤降可能表示设备停机/传感器故障 "
                 f"(共检测到 {len(events)} 次)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(save_path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {os.path.basename(save_path)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  多属性时序数据可视化 (v2)")
    print("=" * 60)

    print("\n[1/4] 加载数据...", flush=True)
    fields = load_all_fields(CSV_PATH)
    print(f"  加载 {len(fields)} 个属性，每个 {len(fields['Magnitude'])} 个 1 秒点")

    print("\n[2/4] 分量级可视化 + 异常事件标注...", flush=True)
    events = plot_1_grouped_by_magnitude(
        fields, os.path.join(OUTPUT_DIR, "属性总览_1_分量级时序.png"))
    print(f"  检测到 {len(events)} 个疑似异常事件:")
    for i, (t0, t1) in enumerate(events[:5]):
        print(f"    事件{i+1}: {t0:%H:%M:%S} ~ {t1:%H:%M:%S}  ({(t1-t0).total_seconds():.0f}秒)")
    if len(events) > 5:
        print(f"    ... 另 {len(events)-5} 个")

    print("\n[3/4] 独立子图详览...", flush=True)
    plot_2_single_field_details(
        fields, os.path.join(OUTPUT_DIR, "属性总览_2_独立子图.png"))

    print("\n[4/4] 统计概览 + 异常放大...", flush=True)
    stats_df, corr = plot_3_stats(
        fields, os.path.join(OUTPUT_DIR, "属性总览_3_统计与相关性.png"))
    plot_4_anomaly_zoom(
        fields, events, os.path.join(OUTPUT_DIR, "属性总览_4_异常事件放大.png"))

    stats_df.to_csv(os.path.join(OUTPUT_DIR, "属性统计.csv"),
                    index=False, encoding="utf-8-sig")
    corr.to_csv(os.path.join(OUTPUT_DIR, "属性相关系数.csv"),
                encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print("  统计摘要")
    print("=" * 60)
    print(stats_df.to_string(index=False))

    print("\n全部输出:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.startswith("属性"):
            sz = os.path.getsize(os.path.join(OUTPUT_DIR, f)) / 1024
            print(f"  {f}  ({sz:.0f} KB)")
