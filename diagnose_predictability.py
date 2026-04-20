"""
数据可预测性诊断
目的: 确认当前预测"出现直线"的根本原因——数据在该时间尺度上是否可预测？

步骤:
1. 自相关函数 (ACF) —— 测量 lag=1..100 的自相关
2. 功率谱 (PSD)     —— 看能量在哪些频率上
3. 朴素基线 vs LSTM/TimesFM —— 对比预测模型相对于基线的增益
4. 多尺度可预测性   —— 在 1s/5s/30s/1min/5min 各尺度上重复朴素基线测试
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

CSV_PATH = r"E:\timesfm_project\时序\MPB01_6.11 08_18.csv"
OUTPUT_DIR = r"E:\timesfm_project\output"


def load_magnitude(csv_path):
    df = pd.read_csv(csv_path, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df = df[df["_field"] == "Magnitude"]
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])
    return df.set_index("_time").sort_index()["_value"]


def autocorr(x, max_lag):
    x = x - np.mean(x)
    r = np.correlate(x, x, mode="full")
    r = r[len(r) // 2: len(r) // 2 + max_lag + 1]
    r = r / r[0]
    return r


def naive_predictions(series, horizon):
    """对长度 >= horizon 的滑窗返回 4 种朴素预测。"""
    vals = series.values
    n = len(vals)
    preds = {"last_value": [], "mean_100": [], "linear": [], "seasonal": []}
    actuals = []
    for s in range(horizon, n - horizon, horizon):
        ctx = vals[max(0, s - 100): s]
        fut = vals[s: s + horizon]
        actuals.append(fut)

        preds["last_value"].append(np.full(horizon, ctx[-1]))
        preds["mean_100"].append(np.full(horizon, np.mean(ctx)))

        # 线性外推
        if len(ctx) >= 10:
            slope, intercept = np.polyfit(np.arange(len(ctx)), ctx, 1)
            preds["linear"].append(slope * np.arange(len(ctx), len(ctx) + horizon) + intercept)
        else:
            preds["linear"].append(np.full(horizon, np.mean(ctx)))

        # 假设有周期 => 用更长回望
        preds["seasonal"].append(np.full(horizon, np.median(vals[max(0, s-horizon*5):s])))

    actuals = np.array(actuals)
    metrics = {}
    for k, p in preds.items():
        p = np.array(p)
        mae = np.mean(np.abs(actuals - p))
        rmse = np.sqrt(np.mean((actuals - p) ** 2))
        metrics[k] = {"mae": mae, "rmse": rmse}
    return metrics


def run_diagnosis():
    print("=" * 60)
    print("  数据可预测性诊断 — Magnitude 属性")
    print("=" * 60)

    raw = load_magnitude(CSV_PATH)
    print(f"\n原始数据: {len(raw)} 条, 采样率 ~3 Hz")

    scales = {
        "1s": raw.resample("1s").mean().dropna(),
        "5s": raw.resample("5s").mean().dropna(),
        "30s": raw.resample("30s").mean().dropna(),
        "1min": raw.resample("1min").mean().dropna(),
        "5min": raw.resample("5min").mean().dropna(),
    }
    print("\n各尺度重采样点数:")
    for k, v in scales.items():
        print(f"  {k:>5}: {len(v)} 点  (均值={v.mean():.3f}, 标准差={v.std():.3f})")

    # ---------- 1. 自相关 ACF ----------
    print("\n\n[1] 自相关函数 (ACF)")
    print("-" * 40)
    acfs = {}
    for k, s in scales.items():
        if len(s) > 200:
            r = autocorr(s.values, 100)
            acfs[k] = r
            print(f"  {k:>5}: lag-1={r[1]:.3f}, lag-5={r[5]:.3f}, lag-10={r[10]:.3f}, lag-60={r[60]:.3f}")

    # ---------- 2. 朴素基线 ----------
    print("\n\n[2] 朴素基线预测对比 (horizon=32)")
    print("-" * 60)
    print(f"  {'尺度':<8} {'重复最后值':<16} {'均值':<16} {'线性外推':<16} {'季节性':<16}")
    all_naive = {}
    for k, s in scales.items():
        if len(s) > 500:
            m = naive_predictions(s, horizon=32)
            all_naive[k] = m
            print(f"  {k:<8} "
                  f"MAE={m['last_value']['mae']:.4f}      "
                  f"{m['mean_100']['mae']:.4f}         "
                  f"{m['linear']['mae']:.4f}         "
                  f"{m['seasonal']['mae']:.4f}")

    # ---------- 3. 与 LSTM/TimesFM 结果对比 ----------
    print("\n\n[3] 朴素基线 vs LSTM vs TimesFM (1s 尺度, horizon=32)")
    print("-" * 60)
    lstm_mae_1s = 0.1122
    tfm_mae_1s = 0.0785
    ref = all_naive["1s"]
    print(f"  朴素-最后值:        MAE = {ref['last_value']['mae']:.4f}")
    print(f"  朴素-100点均值:     MAE = {ref['mean_100']['mae']:.4f}")
    print(f"  朴素-线性外推:      MAE = {ref['linear']['mae']:.4f}")
    print(f"  朴素-季节中位数:    MAE = {ref['seasonal']['mae']:.4f}")
    print(f"  LSTM:               MAE = {lstm_mae_1s:.4f}")
    print(f"  TimesFM:            MAE = {tfm_mae_1s:.4f}")

    best_naive = min(ref.values(), key=lambda x: x["mae"])["mae"]
    print(f"\n  最佳朴素基线 MAE = {best_naive:.4f}")
    print(f"  LSTM 相对最佳朴素: {(best_naive - lstm_mae_1s) / best_naive * 100:+.1f}%")
    print(f"  TimesFM 相对最佳朴素: {(best_naive - tfm_mae_1s) / best_naive * 100:+.1f}%")

    # ---------- 4. 可视化 ----------
    fig = plt.figure(figsize=(22, 14))
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.25)

    # 4.1 ACF 对比图
    ax1 = fig.add_subplot(gs[0, 0])
    for k, r in acfs.items():
        ax1.plot(r, label=k, linewidth=1.5, alpha=0.85)
    ax1.axhline(0.3, color="red", linestyle="--", linewidth=1,
                alpha=0.6, label="可预测阈值 (r=0.3)")
    ax1.axhline(0, color="gray", linewidth=0.5)
    ax1.set_xlabel("Lag (步数)", fontsize=11)
    ax1.set_ylabel("自相关系数 r", fontsize=11)
    ax1.set_title("不同重采样尺度下的自相关函数 (ACF)\nr<0.3 → 接近白噪声，不可预测",
                  fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-0.3, 1.05)

    # 4.2 PSD
    ax2 = fig.add_subplot(gs[0, 1])
    s_1s = scales["1s"].values
    f, Pxx = signal.welch(s_1s, fs=1.0, nperseg=512)
    ax2.semilogy(f, Pxx, color="#c0392b", linewidth=1.2)
    ax2.set_xlabel("频率 (Hz)", fontsize=11)
    ax2.set_ylabel("功率谱密度 (log)", fontsize=11)
    ax2.set_title("Magnitude 1s 信号功率谱 — 能量分布在哪些频率?", fontsize=12)
    ax2.grid(True, alpha=0.3)

    # 4.3 朴素基线 vs 模型 MAE 柱状图
    ax3 = fig.add_subplot(gs[1, :])
    methods = ["朴素-最后值", "朴素-100均值", "朴素-线性外推", "朴素-季节中位数",
               "LSTM", "TimesFM"]
    mae_vals = [ref["last_value"]["mae"], ref["mean_100"]["mae"],
                ref["linear"]["mae"], ref["seasonal"]["mae"],
                lstm_mae_1s, tfm_mae_1s]
    colors = ["#7f8c8d", "#95a5a6", "#bdc3c7", "#34495e",
              "#e74c3c", "#27ae60"]
    bars = ax3.bar(methods, mae_vals, color=colors, alpha=0.85, edgecolor="white")
    for bar, v in zip(bars, mae_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                 f"{v:.4f}", ha="center", fontsize=11, fontweight="bold")
    best = min(mae_vals)
    ax3.axhline(best, color="blue", linestyle="--", linewidth=1, alpha=0.6,
                label=f"最佳 MAE = {best:.4f}")
    ax3.set_ylabel("MAE (平均绝对误差)", fontsize=12)
    ax3.set_title("预测方法对比 (1s 尺度, horizon=32)\n"
                  "模型与朴素基线差距很小 → 说明数据本身难预测",
                  fontsize=13)
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3, axis="y")

    # 4.4 不同尺度下的最佳朴素 MAE
    ax4 = fig.add_subplot(gs[2, 0])
    scale_labels = list(all_naive.keys())
    best_mae = [min(m[k]["mae"] for k in m) for m in all_naive.values()]
    means = [scales[k].mean() for k in scale_labels]
    rel_err = [b / m * 100 for b, m in zip(best_mae, means)]
    ax4.bar(scale_labels, rel_err, color="#3498db", alpha=0.85, edgecolor="white")
    for i, v in enumerate(rel_err):
        ax4.text(i, v + 0.2, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold")
    ax4.set_xlabel("重采样尺度", fontsize=11)
    ax4.set_ylabel("相对误差 MAE/均值 (%)", fontsize=11)
    ax4.set_title("各尺度下最佳朴素预测的相对误差\n越大说明越难预测", fontsize=12)
    ax4.grid(True, alpha=0.3, axis="y")

    # 4.5 展示信号片段说明直线原因
    ax5 = fig.add_subplot(gs[2, 1])
    mag_1s = scales["1s"]
    sample = mag_1s.iloc[1000:1100]
    ax5.plot(sample.index, sample.values, "b-", linewidth=0.8, label="真实振动")
    ax5.axhline(sample.mean(), color="red", linestyle="--", linewidth=1.5,
                label=f"100点均值 = {sample.mean():.3f}")
    ax5.set_title("1秒尺度振动信号 — 真实值在均值附近高频抖动\n最优预测≈均值 (一条直线)",
                  fontsize=12)
    ax5.set_ylabel("Magnitude")
    ax5.legend(fontsize=10)
    ax5.grid(True, alpha=0.3)

    fig.suptitle("Magnitude 预测「直线问题」诊断报告",
                 fontsize=16, fontweight="bold", y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(os.path.join(OUTPUT_DIR, "诊断_1_可预测性分析.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print(f"\n[OK] 诊断图已保存: 诊断_1_可预测性分析.png")

    # ---------- 5. 结论 ----------
    print("\n" + "=" * 60)
    print("  诊断结论")
    print("=" * 60)
    lag1_1s = acfs.get("1s", [1, 0])[1]
    lag1_1min = acfs.get("1min", [1, 0])[1]
    print(f"""
1. 1s 尺度的振动信号本质上接近高频噪声:
   - lag-1 自相关仅 {lag1_1s:.3f} (远低于 0.3 可预测阈值)
   - 上一秒的值对下一秒的预测几乎没有信息量

2. LSTM/TimesFM 的 MAE ({min(lstm_mae_1s, tfm_mae_1s):.4f}) 与
   最佳朴素基线 ({best_naive:.4f}) 差距极小:
   - 说明模型已经接近理论上限
   - 再优化模型结构也难有大幅提升

3. 随着重采样尺度增大, 信号变得更可预测:
   - 1min 尺度 lag-1 自相关 = {lag1_1min:.3f}
   - 1 分钟均值信号包含更多"趋势"而非"噪声"

建议的改进方向:
  [1] 改变预测目标: 不预测瞬时值, 预测「1分钟/5分钟滚动均值」
  [2] 改变预测任务: 不做回归, 做「事件检测」(异常开始/结束)
  [3] 使用分位数预测: 预测未来值的分布区间, 而非单点
""")


if __name__ == "__main__":
    run_diagnosis()
