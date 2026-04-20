"""
多属性泛化性 — 报告复盘脚本
不重新训练 / 推理，直接基于 output/多属性泛化测试.csv 复算更科学的指标：
  - NRMSE = MAE / 趋势std   (比 MAE/|均值| 更能反映"任务难度")
  - 信噪比 SNR = 趋势std / 噪声std
  - 可用性判据（基于 ACF_lag16 + SNR）
产出：
  1) output/多属性泛化测试_v2.csv   — 带 NRMSE / SNR / 可用性列
  2) output/多属性_3_NRMSE对比.png — 真实难度对比图
  3) output/多属性_4_可用性象限.png — ACF vs SNR 可用性判据图
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = r"E:\timesfm_project\output"
SRC_CSV = os.path.join(OUTPUT_DIR, "多属性泛化测试.csv")


def classify(nrmse_tfm, acf16, snr):
    """可用性三级判据"""
    if nrmse_tfm < 0.20 and acf16 > 0.75 and snr > 1.5:
        return "A 可直接上线"
    if nrmse_tfm < 0.35 and acf16 > 0.55:
        return "B 可用/建议复核"
    return "C 不建议直接用"


def main():
    df = pd.read_csv(SRC_CSV)
    # 新指标
    df["信噪比_SNR"] = (df["趋势标准差"] / df["噪声标准差"]).round(3)
    df["NRMSE_LSTM"] = (df["LSTM_MAE"] / df["趋势标准差"]).round(3)
    df["NRMSE_TimesFM"] = (df["TimesFM_MAE"] / df["趋势标准差"]).round(3)
    df["TFM相对LSTM提升%"] = ((1 - df["TimesFM_MAE"] / df["LSTM_MAE"]) * 100).round(1)
    df["可用性"] = df.apply(
        lambda r: classify(r["NRMSE_TimesFM"], r["ACF_lag16"], r["信噪比_SNR"]),
        axis=1,
    )

    cols = ["属性", "原始均值", "趋势标准差", "噪声标准差", "信噪比_SNR",
            "ACF_lag1", "ACF_lag16",
            "LSTM_MAE", "TimesFM_MAE",
            "NRMSE_LSTM", "NRMSE_TimesFM",
            "LSTM_相对误差%", "TimesFM_相对误差%",
            "TFM相对LSTM提升%", "可用性"]
    df = df[cols]

    out_csv = os.path.join(OUTPUT_DIR, "多属性泛化测试_v2.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print("[OK] 新 CSV ->", out_csv)
    print("\n" + df.to_string(index=False))

    # ================== 图 3: NRMSE vs 伪相对误差 ==================
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    x = np.arange(len(df))
    w = 0.35

    # 左：旧的"相对误差%"（容易骗人）
    axes[0].bar(x - w/2, df["LSTM_相对误差%"], w, color="#e74c3c", label="LSTM", alpha=0.85)
    axes[0].bar(x + w/2, df["TimesFM_相对误差%"], w, color="#27ae60", label="TimesFM", alpha=0.85)
    for i, (l, t) in enumerate(zip(df["LSTM_相对误差%"], df["TimesFM_相对误差%"])):
        axes[0].text(i - w/2, l + 0.1, f"{l:.1f}%", ha="center", va="bottom", fontsize=9)
        axes[0].text(i + w/2, t + 0.1, f"{t:.1f}%", ha="center", va="bottom", fontsize=9)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df["属性"], fontsize=11)
    axes[0].set_ylabel("相对误差 % = MAE / |均值|", fontsize=11)
    axes[0].set_title("【旧指标】MAE/|均值| — ShockZ 被大均值稀释,看上去很好",
                      fontsize=11, color="#7f8c8d")
    axes[0].legend(fontsize=10); axes[0].grid(True, alpha=0.3, axis="y")
    axes[0].axhline(5, color="gray", linestyle=":", linewidth=0.8)

    # 右：NRMSE（科学指标）
    nlstm = df["NRMSE_LSTM"] * 100
    ntfm = df["NRMSE_TimesFM"] * 100
    axes[1].bar(x - w/2, nlstm, w, color="#e74c3c", label="LSTM", alpha=0.85)
    axes[1].bar(x + w/2, ntfm, w, color="#27ae60", label="TimesFM", alpha=0.85)
    for i, (l, t) in enumerate(zip(nlstm, ntfm)):
        axes[1].text(i - w/2, l + 0.5, f"{l:.1f}%", ha="center", va="bottom", fontsize=9)
        axes[1].text(i + w/2, t + 0.5, f"{t:.1f}%", ha="center", va="bottom", fontsize=9)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(df["属性"], fontsize=11)
    axes[1].set_ylabel("NRMSE % = MAE / 趋势std", fontsize=11)
    axes[1].set_title("【新指标】MAE/趋势std — ShockZ 真实水平暴露 (>35%)",
                      fontsize=11, color="#c0392b")
    axes[1].legend(fontsize=10); axes[1].grid(True, alpha=0.3, axis="y")
    axes[1].axhline(20, color="green", linestyle="--", linewidth=1.0, alpha=0.7,
                    label="_nolegend_")
    axes[1].axhline(35, color="red", linestyle="--", linewidth=1.0, alpha=0.7,
                    label="_nolegend_")
    axes[1].text(len(df)-0.5, 20, " 20% 可用线", color="green", fontsize=9, va="bottom")
    axes[1].text(len(df)-0.5, 35, " 35% 警戒线", color="red", fontsize=9, va="bottom")

    fig.suptitle("多属性泛化性 — 指标修正:从 MAE/|均值| 改为 NRMSE",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_png1 = os.path.join(OUTPUT_DIR, "多属性_3_NRMSE对比.png")
    plt.savefig(out_png1, dpi=140, bbox_inches="tight")
    plt.close()
    print("[OK] ->", out_png1)

    # ================== 图 4: 可用性象限 (ACF × SNR) ==================
    fig, ax = plt.subplots(figsize=(10, 7))
    acf16 = df["ACF_lag16"].values
    snr = df["信噪比_SNR"].values
    nrmse = df["NRMSE_TimesFM"].values
    names = df["属性"].tolist()

    # 背景分区着色
    ax.axvspan(0.75, 1.05, ymin=0.0, ymax=1.0, alpha=0.08, color="green")
    ax.axhspan(1.5, max(snr.max()*1.2, 3), alpha=0.08, color="green")
    ax.axvline(0.75, color="green", linestyle="--", linewidth=1, alpha=0.6)
    ax.axvline(0.55, color="orange", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(1.5, color="green", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(0.5, color="orange", linestyle="--", linewidth=1, alpha=0.6)

    # 按 NRMSE 着色,点大小
    sizes = 400 + nrmse * 1500
    colors = ["#27ae60" if n < 0.20 else ("#f39c12" if n < 0.35 else "#c0392b")
              for n in nrmse]
    ax.scatter(acf16, snr, s=sizes, c=colors, alpha=0.75, edgecolors="black", linewidth=1.2)

    for i, name in enumerate(names):
        ax.annotate(f"{name}\nNRMSE={nrmse[i]*100:.1f}%",
                    (acf16[i], snr[i]),
                    textcoords="offset points", xytext=(12, 8),
                    fontsize=10, fontweight="bold")

    ax.text(0.90, max(snr.max()*1.1, 2.5), "A 区:可直接上线",
            fontsize=11, color="#27ae60", fontweight="bold")
    ax.text(0.60, 1.0, "B 区:可用但需复核",
            fontsize=11, color="#f39c12", fontweight="bold")
    ax.text(0.35, 0.2, "C 区:不建议直接用",
            fontsize=11, color="#c0392b", fontweight="bold")

    ax.set_xlabel("ACF lag-16 (趋势的长程可预测性)", fontsize=12)
    ax.set_ylabel("信噪比 SNR = 趋势std / 噪声std  (对数坐标)", fontsize=12)
    ax.set_yscale("log")
    ax.set_xlim(0.3, 1.02)
    ax.set_title("可用性判据:ACF lag-16 × 信噪比  (气泡颜色=NRMSE 档位)",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)

    out_png2 = os.path.join(OUTPUT_DIR, "多属性_4_可用性象限.png")
    plt.savefig(out_png2, dpi=140, bbox_inches="tight")
    plt.close()
    print("[OK] ->", out_png2)


if __name__ == "__main__":
    main()
