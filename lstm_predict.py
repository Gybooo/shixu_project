"""
LSTM 振动预测与预防性自诊断系统
- 数据属性: MPB_01 设备振动幅值 (Magnitude)
- 模型: Encoder-Decoder LSTM + TimesFM 对比
- 功能: 预测 / 异常检测 / 三级告警 / 健康评分
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, r"E:\timesfm_project\timesfm\src")
os.environ["HF_HOME"] = r"E:\timesfm_project\hf_cache"

OUTPUT_DIR = r"E:\timesfm_project\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_PATH = r"E:\timesfm_project\时序\MPB01_6.11 08_18.csv"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.2
BATCH_SIZE = 64
LR = 1e-3

if torch.cuda.is_available():
    EPOCHS, PATIENCE = 50, 10
else:
    EPOCHS, PATIENCE = 20, 5

FIELD_CN = "振动幅值 (Magnitude)"
EQUIP_CN = "MPB_01 设备"

CACHE_PATH = os.path.join(OUTPUT_DIR, "_lstm_cache.npz")


# ================================================================
# 1. 数据加载
# ================================================================
def load_vibration_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, skiprows=[0, 1, 2], low_memory=False)
    meta_mask = df.iloc[:, 0].astype(str).str.startswith("#")
    header_mask = df["_time"].astype(str).eq("_time")
    default_mask = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta_mask | header_mask | default_mask)].copy()
    df = df[df["_field"] == "Magnitude"]
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])
    df = df[["_time", "_value"]].set_index("_time").sort_index()
    return df


def choose_resample_params(df: pd.DataFrame):
    n_raw = len(df)
    duration_sec = (df.index[-1] - df.index[0]).total_seconds()
    sample_rate = n_raw / duration_sec

    MIN_POINTS = 2000
    for freq, label in [("1s", "1秒"), ("5s", "5秒"), ("10s", "10秒"),
                         ("30s", "30秒"), ("1min", "1分钟")]:
        resampled = df["_value"].resample(freq).mean().dropna()
        if len(resampled) >= MIN_POINTS:
            break

    n = len(resampled)
    if n >= 5000:
        ctx, hor = 512, 64
    elif n >= 2000:
        ctx, hor = 256, 32
    elif n >= 800:
        ctx, hor = 128, 16
    else:
        ctx, hor = 64, 8

    print(f"  原始采样率: ~{sample_rate:.1f} Hz, 持续 {duration_sec/3600:.1f} 小时")
    print(f"  自动选择: 重采样={label}({freq}), 得到 {n} 点")
    print(f"  模型窗口: context={ctx}, horizon={hor}")
    return resampled, freq, label, ctx, hor


# ================================================================
# 2. 数据集
# ================================================================
class TimeSeriesDataset(Dataset):
    def __init__(self, data, context_len, horizon):
        self.data = data
        self.context_len = context_len
        self.horizon = horizon
        self.n_samples = len(data) - context_len - horizon + 1

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        x = self.data[idx: idx + self.context_len]
        y = self.data[idx + self.context_len: idx + self.context_len + self.horizon]
        return torch.FloatTensor(x).unsqueeze(-1), torch.FloatTensor(y).unsqueeze(-1)


def prepare_data(series, context_len, horizon):
    n = len(series)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    scaler = MinMaxScaler()
    scaler.fit(series[:train_end].reshape(-1, 1))
    scaled = scaler.transform(series.reshape(-1, 1)).flatten()

    train_ds = TimeSeriesDataset(scaled[:train_end], context_len, horizon)
    val_ds = TimeSeriesDataset(scaled[train_end - context_len: val_end], context_len, horizon)
    test_ds = TimeSeriesDataset(scaled[val_end - context_len:], context_len, horizon)

    bs = min(BATCH_SIZE, max(1, len(train_ds) // 4))
    train_ld = DataLoader(train_ds, batch_size=bs, shuffle=True,
                          drop_last=len(train_ds) > bs, num_workers=0)
    val_ld = DataLoader(val_ds, batch_size=bs, shuffle=False, num_workers=0)
    test_ld = DataLoader(test_ds, batch_size=bs, shuffle=False, num_workers=0)
    return scaler, train_ld, val_ld, test_ld, train_end, val_end


# ================================================================
# 3. LSTM 模型 — 直接多步输出（非自回归，避免预测退化成直线）
# ================================================================
class VibrationLSTM(nn.Module):
    """
    LSTM 编码上下文 → 全连接层直接输出 horizon 个预测值。
    每个预测点独立来自上下文隐藏状态，不存在误差累积。
    """
    def __init__(self, hidden_size=128, num_layers=2, dropout=0.2, horizon=64):
        super().__init__()
        self.horizon = horizon
        self.lstm = nn.LSTM(
            input_size=1, hidden_size=hidden_size, num_layers=num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, horizon),
        )

    def forward(self, x, target=None, teacher_forcing_ratio=0.0):
        out, (h_n, _) = self.lstm(x)
        last_hidden = out[:, -1, :]           # (batch, hidden)
        prediction = self.head(last_hidden)   # (batch, horizon)
        return prediction.unsqueeze(-1)       # (batch, horizon, 1)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ================================================================
# 4. 训练
# ================================================================
def train_model(model, train_loader, val_loader, epochs, lr, patience, device):
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5, min_lr=1e-6)

    best_val_loss = float("inf")
    patience_counter = 0
    train_losses, val_losses = [], []

    for epoch in range(epochs):
        model.train()
        epoch_loss, n_batches = 0.0, 0
        tf = max(0.0, 0.5 * (1 - epoch / epochs))

        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb, target=yb, teacher_forcing_ratio=tf)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        avg_train = epoch_loss / max(n_batches, 1)
        train_losses.append(avg_train)

        model.eval()
        val_loss, vb = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                loss = criterion(model(xb, teacher_forcing_ratio=0.0), yb)
                val_loss += loss.item()
                vb += 1
        avg_val = val_loss / max(vb, 1)
        val_losses.append(avg_val)
        scheduler.step(avg_val)

        cur_lr = optimizer.param_groups[0]["lr"]
        print(f"  轮次 {epoch+1:>3}/{epochs} | "
              f"训练: {avg_train:.6f} | 验证: {avg_val:.6f} | "
              f"学习率: {cur_lr:.2e}")

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            patience_counter = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  提前停止于第 {epoch+1} 轮")
                break

    model.load_state_dict(best_state)
    return train_losses, val_losses


# ================================================================
# 5. 评估 + 滚动预测
# ================================================================
def evaluate_on_loader(model, loader, scaler, device):
    model.eval()
    all_p, all_a = [], []
    with torch.no_grad():
        for xb, yb in loader:
            pred = model(xb.to(device), teacher_forcing_ratio=0.0)
            all_p.append(pred.cpu().numpy())
            all_a.append(yb.numpy())

    preds = np.concatenate(all_p)
    actuals = np.concatenate(all_a)
    pf = scaler.inverse_transform(preds.reshape(-1, 1)).flatten()
    af = scaler.inverse_transform(actuals.reshape(-1, 1)).flatten()

    mae = np.mean(np.abs(af - pf))
    rmse = np.sqrt(np.mean((af - pf) ** 2))
    mape = np.mean(np.abs((af - pf) / (af + 1e-8))) * 100
    rel = mae / np.mean(np.abs(af)) * 100

    return {"mae": mae, "rmse": rmse, "mape": mape, "rel_err": rel,
            "preds": preds, "actuals": actuals, "preds_real": pf, "actuals_real": af}


def rolling_predict(model, scaled_data, scaler, ctx_len, hor, step, device):
    model.eval()
    results = []
    with torch.no_grad():
        for s in range(0, len(scaled_data) - ctx_len - hor, step):
            ctx = scaled_data[s: s + ctx_len]
            fut = scaled_data[s + ctx_len: s + ctx_len + hor]
            if len(fut) < hor:
                break
            x = torch.FloatTensor(ctx).unsqueeze(0).unsqueeze(-1).to(device)
            p = model(x, teacher_forcing_ratio=0.0).cpu().numpy()[0, :, 0]
            pr = scaler.inverse_transform(p.reshape(-1, 1)).flatten()
            fr = scaler.inverse_transform(fut.reshape(-1, 1)).flatten()
            res = np.abs(fr - pr)
            results.append({
                "start_idx": s + ctx_len,
                "mean_residual": np.mean(res),
                "max_residual": np.max(res),
                "pred_real": pr, "actual_real": fr,
            })
    return results


# ================================================================
# 6. TimesFM 对比预测
# ================================================================
def run_timesfm_forecast(values, context_len, horizon, n_segments=5):
    """用 TimesFM 在同一数据段上做预测，返回结果列表。"""
    try:
        import timesfm
        from timesfm.configs import ForecastConfig

        print("  加载 TimesFM 2.5 模型...")
        torch.set_float32_matmul_precision("high")
        tfm = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch")
        tfm.compile(ForecastConfig(
            max_context=min(1024, context_len),
            max_horizon=min(256, horizon),
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        ))
        print("  TimesFM 模型就绪")

        results = []
        stride = max(1, (len(values) - context_len - horizon) // n_segments)
        for i in range(n_segments):
            start = i * stride
            if start + context_len + horizon > len(values):
                break
            ctx = values[start: start + context_len].astype(np.float64)
            actual = values[start + context_len: start + context_len + horizon]
            pf, qf = tfm.forecast(horizon=horizon, inputs=[ctx])
            pred = pf[0][:len(actual)]
            mae = np.mean(np.abs(actual[:len(pred)] - pred))
            results.append({
                "start": start, "context": ctx, "actual": actual,
                "pred": pred, "quantiles": qf[0] if qf is not None else None,
                "mae": mae,
            })
        overall_mae = np.mean([r["mae"] for r in results])
        return results, overall_mae

    except Exception as e:
        print(f"  TimesFM 不可用: {e}")
        return None, None


# ================================================================
# 7. 预防性自诊断
# ================================================================
class HealthDiagnostic:
    LEVELS = {0: "正常", 1: "关注", 2: "警告", 3: "危险"}
    COLORS = {0: "#2ecc71", 1: "#f1c40f", 2: "#e67e22", 3: "#e74c3c"}
    ACTIONS = {
        0: "继续正常运行",
        1: "加强监测频率，安排下次巡检",
        2: "尽快安排检修，准备备件",
        3: "立即停机检查，排除故障隐患",
    }

    def __init__(self, baseline_mean, baseline_std):
        self.baseline_mean = baseline_mean
        self.baseline_std = baseline_std
        self.thresholds = [
            baseline_mean + 1.5 * baseline_std,
            baseline_mean + 2.5 * baseline_std,
            baseline_mean + 3.5 * baseline_std,
        ]

    def classify(self, r):
        for lvl, thr in enumerate(self.thresholds):
            if r < thr:
                return lvl
        return 3

    def health_score(self, residuals):
        ratio = np.mean(residuals) / (self.baseline_mean + 3.5 * self.baseline_std)
        return max(0.0, min(100.0, 100.0 * (1 - ratio)))

    def detect_trend(self, residuals, window=20):
        if len(residuals) < window:
            return {"rising": False, "slope": 0.0}
        recent = residuals[-window:]
        slope = np.polyfit(np.arange(len(recent)), recent, 1)[0]
        return {"rising": slope > 0.5 * self.baseline_std / window, "slope": slope}

    def detect_frequency(self, levels, window=20):
        if len(levels) < window:
            return {"alarm_rate": 0.0, "frequent": False}
        rate = np.mean(levels[-window:] >= 1)
        return {"alarm_rate": rate, "frequent": rate > 0.4}

    def full_diagnosis(self, residuals):
        levels = np.array([self.classify(r) for r in residuals])
        hs = self.health_score(residuals)
        trend = self.detect_trend(residuals)
        freq = self.detect_frequency(levels)
        lc = {i: int(np.sum(levels == i)) for i in range(4)}
        ml = int(np.max(levels))
        if trend["rising"] and ml < 3:
            ml = min(ml + 1, 3)
        if freq["frequent"] and ml < 3:
            ml = min(ml + 1, 3)
        return {"levels": levels, "level_counts": lc, "health_score": hs,
                "trend": trend, "frequency": freq,
                "overall_level": ml, "overall_label": self.LEVELS[ml],
                "action": self.ACTIONS[ml]}


# ================================================================
# 8. 可视化（全中文 + 具体数据 + LSTM vs TimesFM 对比）
# ================================================================

def plot_1_training(train_losses, val_losses, save_path):
    """图1: 训练过程 — 损失曲线 + 超参数信息。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6),
                                    gridspec_kw={"width_ratios": [3, 1]})

    ep = range(1, len(train_losses) + 1)
    ax1.plot(ep, train_losses, "b-o", markersize=4, linewidth=1.5, label="训练损失")
    ax1.plot(ep, val_losses, "r-s", markersize=4, linewidth=1.5, label="验证损失")
    best_ep = np.argmin(val_losses) + 1
    best_v = min(val_losses)
    ax1.axvline(best_ep, color="gray", linestyle="--", alpha=0.5)
    ax1.scatter([best_ep], [best_v], s=120, c="red", zorder=5, marker="*")
    ax1.annotate(f"最佳: 第{best_ep}轮\n验证损失={best_v:.6f}",
                 xy=(best_ep, best_v), fontsize=10,
                 xytext=(best_ep + 1.5, best_v + (max(val_losses) - best_v) * 0.3),
                 arrowprops=dict(arrowstyle="->", color="gray"),
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
    ax1.set_xlabel("训练轮次", fontsize=12)
    ax1.set_ylabel("MSE 损失", fontsize=12)
    ax1.set_title(f"LSTM 模型训练过程 — {EQUIP_CN} {FIELD_CN}", fontsize=14)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    info = [
        ("数据属性", FIELD_CN),
        ("设备", "MPB_01"),
        ("模型", "Encoder-Decoder LSTM"),
        ("隐藏层大小", str(HIDDEN_SIZE)),
        ("层数", str(NUM_LAYERS)),
        ("Dropout", str(DROPOUT)),
        ("训练轮次", f"{len(train_losses)}/{EPOCHS}"),
        ("最佳轮次", str(best_ep)),
        ("最佳验证损失", f"{best_v:.6f}"),
    ]
    ax2.axis("off")
    ax2.set_title("模型参数", fontsize=13)
    for i, (k, v) in enumerate(info):
        y = 0.92 - i * 0.095
        ax2.text(0.05, y, f"{k}:", fontsize=10, fontweight="bold",
                 transform=ax2.transAxes, va="top")
        ax2.text(0.55, y, v, fontsize=10, transform=ax2.transAxes, va="top")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_2_comparison(times_index, values, scaler, lstm_results, tfm_results,
                      context_len, horizon, freq, save_path):
    """图2: LSTM vs TimesFM 预测对比 — 同一数据段上两个模型的预测。"""
    n_segments = min(3, len(lstm_results))
    fig, axes = plt.subplots(n_segments, 1, figsize=(20, 5.5 * n_segments))
    if n_segments == 1:
        axes = [axes]

    stride = max(1, len(lstm_results) // n_segments)

    for i, ax in enumerate(axes):
        lr = lstm_results[i * stride]
        seg_start = lr["start_idx"]
        ctx_start = max(0, seg_start - 60)

        ctx_times = times_index[ctx_start: seg_start]
        ctx_vals = values[ctx_start: seg_start]
        fut_times = times_index[seg_start: seg_start + horizon]
        actual = lr["actual_real"]
        lstm_pred = lr["pred_real"]

        ax.plot(ctx_times, ctx_vals, color="#3498db", linewidth=1, alpha=0.6,
                label="历史数据（上下文）")
        ax.plot(fut_times[:len(actual)], actual, color="#2c3e50", linewidth=1.8,
                label=f"真实值 (均值={np.mean(actual):.3f})")
        ax.plot(fut_times[:len(lstm_pred)], lstm_pred, color="#e74c3c",
                linewidth=1.8, linestyle="--",
                label=f"LSTM 预测 (MAE={np.mean(np.abs(actual-lstm_pred)):.4f})")

        if tfm_results is not None and i < len(tfm_results):
            tr = tfm_results[i]
            tfm_pred = tr["pred"]
            tfm_mae = tr["mae"]
            ax.plot(fut_times[:len(tfm_pred)], tfm_pred, color="#27ae60",
                    linewidth=1.8, linestyle="-.",
                    label=f"TimesFM 预测 (MAE={tfm_mae:.4f})")
            if tr["quantiles"] is not None and tr["quantiles"].shape[1] >= 2:
                q = tr["quantiles"]
                ax.fill_between(fut_times[:len(q)], q[:, 1], q[:, -2],
                                alpha=0.1, color="green", label="TimesFM 置信区间")

        ax.axvline(fut_times[0], color="gray", linestyle=":", alpha=0.5)
        ax.text(fut_times[0], ax.get_ylim()[1] * 0.98, " ← 预测起点",
                fontsize=9, color="gray", va="top")

        t0 = ctx_times[0] if len(ctx_times) > 0 else fut_times[0]
        ax.set_title(f"片段 {i+1}: {t0:%H:%M:%S} → {fut_times[-1]:%H:%M:%S}  "
                     f"(预测 {horizon} 步 ≈ {horizon}秒)",
                     fontsize=12)
        ax.set_ylabel(FIELD_CN, fontsize=11)
        ax.legend(fontsize=9, loc="upper right", ncol=2)
        ax.grid(True, alpha=0.2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    axes[-1].set_xlabel("时间 (2024-06-11)", fontsize=11)
    fig.suptitle(f"{EQUIP_CN} — LSTM vs TimesFM 预测效果对比\n"
                 f"预测属性: {FIELD_CN}  |  重采样: {freq}  |  "
                 f"上下文: {context_len}步  |  预测: {horizon}步",
                 fontsize=15, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_3_anomaly(times, residuals, diag_obj, diag, save_path):
    """图3: 异常检测 — 残差柱状图 + 滑动均值趋势 + 原始振动曲线。"""
    levels = diag["levels"]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(20, 14), sharex=True)

    # 上: 残差柱状图，按告警等级着色
    colors = [HealthDiagnostic.COLORS[l] for l in levels]
    bars = ax1.bar(times, residuals, width=0.015, color=colors, alpha=0.85,
                   edgecolor="none")
    for i, thr in enumerate(diag_obj.thresholds):
        lbl = f"阈值 L{i+1}-{HealthDiagnostic.LEVELS[i+1]}: {thr:.4f}"
        ax1.axhline(thr, color=HealthDiagnostic.COLORS[i+1],
                     linestyle="--", linewidth=1.2, alpha=0.7, label=lbl)
    ax1.set_title(f"预测残差 & 告警等级分布  (共 {len(residuals)} 个检测窗口)", fontsize=13)
    ax1.set_ylabel("平均绝对残差 |实际-预测|", fontsize=11)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(True, alpha=0.2)

    # 中: 残差滑动均值 + 趋势线
    w = min(10, len(residuals) // 3)
    if w >= 2:
        rm = pd.Series(residuals).rolling(w, min_periods=1).mean().values
        ax2.plot(times, rm, color="#2980b9", linewidth=2,
                 label=f"残差滑动均值 (窗口={w})")
    ax2.plot(times, residuals, color="#bdc3c7", linewidth=0.6, alpha=0.6,
             label="逐窗口残差")
    for i, thr in enumerate(diag_obj.thresholds):
        ax2.axhline(thr, color=HealthDiagnostic.COLORS[i+1],
                     linestyle="--", linewidth=0.8, alpha=0.4)

    trend = diag["trend"]
    if len(residuals) > 5:
        x_fit = np.arange(len(residuals))
        coef = np.polyfit(x_fit, residuals, 1)
        trend_line = np.polyval(coef, x_fit)
        direction = "↑ 上升" if trend["rising"] else "→ 平稳"
        ax2.plot(times, trend_line, "k--", linewidth=1.2, alpha=0.5,
                 label=f"趋势线 ({direction}, 斜率={coef[0]:.4f})")

    ax2.set_title("残差趋势分析", fontsize=13)
    ax2.set_ylabel("平均绝对残差", fontsize=11)
    ax2.legend(fontsize=9, loc="upper right")
    ax2.grid(True, alpha=0.2)

    # 下: 告警等级散点
    for lvl in range(4):
        mask = levels == lvl
        if np.any(mask):
            t_lvl = [times[j] for j in range(len(times)) if mask[j]]
            ax3.scatter(t_lvl, [lvl] * len(t_lvl),
                        c=HealthDiagnostic.COLORS[lvl], s=50, alpha=0.7,
                        label=f"{HealthDiagnostic.LEVELS[lvl]} ({np.sum(mask)}个)",
                        edgecolors="white", linewidths=0.3)
    ax3.set_yticks([0, 1, 2, 3])
    ax3.set_yticklabels(["L0-正常", "L1-关注", "L2-警告", "L3-危险"])
    ax3.set_title("各窗口告警等级", fontsize=13)
    ax3.set_ylabel("告警等级", fontsize=11)
    ax3.set_xlabel("时间 (2024-06-11)", fontsize=11)
    ax3.legend(fontsize=9, loc="upper right", ncol=4)
    ax3.grid(True, alpha=0.2)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    plt.xticks(rotation=30)

    fig.suptitle(f"{EQUIP_CN} — 基于{FIELD_CN}预测残差的异常检测",
                 fontsize=15, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_4_health(times, residuals, diag, diag_obj, lstm_mae, tfm_mae, save_path):
    """图4: 设备健康综合报告 — 健康评分 + 等级分布 + 方法对比 + 诊断结论。"""
    levels = diag["levels"]

    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    # (0,0): 健康评分时序
    ax1 = fig.add_subplot(gs[0, :])
    w = min(10, len(residuals) // 3)
    scores = []
    for i in range(len(residuals)):
        seg = residuals[max(0, i-w+1): i+1]
        scores.append(diag_obj.health_score(seg))
    scores = np.array(scores)

    ax1.fill_between(times, 0, scores, alpha=0.3, color="#3498db")
    ax1.plot(times, scores, color="#2c3e50", linewidth=1.8)
    ax1.axhline(80, color="#2ecc71", linestyle="--", alpha=0.6, label="健康线 (80分)")
    ax1.axhline(50, color="#f39c12", linestyle="--", alpha=0.6, label="关注线 (50分)")
    ax1.axhline(20, color="#e74c3c", linestyle="--", alpha=0.6, label="危险线 (20分)")
    ax1.set_ylim(-5, 105)
    ax1.set_title(f"{EQUIP_CN} — 健康评分时序曲线  "
                  f"(综合评分: {diag['health_score']:.1f}分)", fontsize=14)
    ax1.set_ylabel("健康评分 (0-100)", fontsize=11)
    ax1.legend(fontsize=10, loc="lower right")
    ax1.grid(True, alpha=0.2)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    # (1,0): 告警等级饼图
    ax2 = fig.add_subplot(gs[1, 0])
    lc = diag["level_counts"]
    pie_labels = []
    pie_sizes = []
    pie_colors = []
    for k in sorted(lc.keys()):
        if lc[k] > 0:
            pie_labels.append(f"L{k}-{HealthDiagnostic.LEVELS[k]}\n({lc[k]}个, {lc[k]/len(levels)*100:.1f}%)")
            pie_sizes.append(lc[k])
            pie_colors.append(HealthDiagnostic.COLORS[k])
    wedges, texts = ax2.pie(pie_sizes, labels=pie_labels, colors=pie_colors,
                             startangle=90, textprops={"fontsize": 10})
    ax2.set_title(f"告警等级分布 (共 {len(levels)} 个窗口)", fontsize=13)

    # (1,1): LSTM vs TimesFM 指标对比柱状图
    ax3 = fig.add_subplot(gs[1, 1])
    methods = ["LSTM"]
    mae_vals = [lstm_mae]
    bar_colors = ["#e74c3c"]
    if tfm_mae is not None:
        methods.append("TimesFM")
        mae_vals.append(tfm_mae)
        bar_colors.append("#27ae60")

    x_pos = np.arange(len(methods))
    bars = ax3.bar(x_pos, mae_vals, color=bar_colors, width=0.5,
                   edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, mae_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                 f"{val:.4f}", ha="center", fontsize=12, fontweight="bold")
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(methods, fontsize=12)
    ax3.set_ylabel("MAE (平均绝对误差)", fontsize=11)
    ax3.set_title(f"预测精度对比 — {FIELD_CN}", fontsize=13)
    ax3.grid(True, alpha=0.2, axis="y")

    # (2,:): 综合诊断结论面板
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis("off")

    trend = diag["trend"]
    freq = diag["frequency"]
    ov_level = diag["overall_level"]
    ov_color = HealthDiagnostic.COLORS[ov_level]

    lines = [
        f"╔══════════════════════════════════════════════════════════════════╗",
        f"║   {EQUIP_CN}  预防性维护自诊断报告",
        f"╠══════════════════════════════════════════════════════════════════╣",
        f"║  检测属性:  {FIELD_CN}",
        f"║  数据时段:  {times[0]:%Y-%m-%d %H:%M} ~ {times[-1]:%H:%M}",
        f"║  检测窗口:  {len(levels)} 个",
        f"║",
        f"║  健康评分:  {diag['health_score']:.1f} / 100",
        f"║  综合等级:  {diag['overall_label']}",
        f"║  残差趋势:  {'↑ 上升趋势' if trend['rising'] else '→ 平稳'}  (斜率={trend['slope']:.5f})",
        f"║  告警频率:  {freq['alarm_rate']*100:.1f}%  ({'偏高，需关注' if freq['frequent'] else '在正常范围内'})",
        f"║",
        f"║  LSTM 预测 MAE:    {lstm_mae:.4f}",
    ]
    if tfm_mae is not None:
        lines.append(f"║  TimesFM 预测 MAE: {tfm_mae:.4f}")
        better = "LSTM" if lstm_mae < tfm_mae else "TimesFM"
        lines.append(f"║  更优模型:         {better}")
    lines += [
        f"║",
        f"║  ▶ 建议动作:  {diag['action']}",
        f"╚══════════════════════════════════════════════════════════════════╝",
    ]

    report = "\n".join(lines)
    ax4.text(0.05, 0.95, report, fontsize=11, fontfamily="monospace",
             transform=ax4.transAxes, va="top",
             bbox=dict(boxstyle="round,pad=0.8", facecolor=ov_color, alpha=0.12))

    fig.suptitle(f"{EQUIP_CN} — 预防性维护健康诊断报告",
                 fontsize=16, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()


def P(*args, **kw):
    """带自动 flush 的 print。"""
    print(*args, **kw, flush=True)


# ================================================================
# 主流程：Phase 1 (LSTM) → 保存缓存 → Phase 2 (TimesFM + 出图)
# ================================================================
if __name__ == "__main__":

    P("=" * 60)
    P("  LSTM 振动预测与预防性自诊断系统")
    P(f"  设备: MPB_01  |  属性: Magnitude (振动幅值)")
    P("=" * 60)

    # --- 1. 数据 ---
    P("\n[1/7] 加载数据...")
    raw_df = load_vibration_data(CSV_PATH)
    P(f"  原始记录数: {len(raw_df)}")

    series, resample_freq, resample_label, CONTEXT_LEN, HORIZON = \
        choose_resample_params(raw_df)
    values = series.values
    times_index = series.index

    P(f"  时间范围: {times_index[0]} ~ {times_index[-1]}")
    P(f"  数值范围: [{values.min():.4f}, {values.max():.4f}]")
    P(f"  均值: {values.mean():.4f}, 标准差: {values.std():.4f}")

    scaler, train_ld, val_ld, test_ld, train_end, val_end = \
        prepare_data(values, CONTEXT_LEN, HORIZON)
    P(f"  训练/验证/测试: {len(train_ld.dataset)}/{len(val_ld.dataset)}/{len(test_ld.dataset)}")
    P(f"  计算设备: {DEVICE}")

    # --- 2/3. LSTM 训练（或从缓存加载） ---
    cache_ok = False
    if os.path.exists(CACHE_PATH):
        try:
            cache = np.load(CACHE_PATH, allow_pickle=True)
            if (int(cache["context_len"]) == CONTEXT_LEN
                    and int(cache["horizon"]) == HORIZON
                    and int(cache["n_values"]) == len(values)):
                P("\n[2/7] 从缓存加载 LSTM 结果...")
                train_losses = cache["train_losses"].tolist()
                val_losses = cache["val_losses"].tolist()
                lstm_mae = float(cache["lstm_mae"])
                lstm_rmse = float(cache["lstm_rmse"])
                lstm_rel = float(cache["lstm_rel"])
                rolling_residuals = cache["rolling_residuals"]
                rolling_start_idxs = cache["rolling_start_idxs"]
                rolling_pred_reals = list(cache["rolling_pred_reals"])
                rolling_actual_reals = list(cache["rolling_actual_reals"])
                cache_ok = True
                P(f"  缓存命中 (MAE={lstm_mae:.4f})")
        except Exception:
            pass

    if not cache_ok:
        P("\n[2/7] 构建 LSTM 模型...")
        model = VibrationLSTM(HIDDEN_SIZE, NUM_LAYERS, DROPOUT, HORIZON).to(DEVICE)
        P(f"  参数量: {model.count_parameters():,}")

        P(f"\n[3/7] 训练 (最多 {EPOCHS} 轮, 耐心值={PATIENCE})...")
        train_losses, val_losses = train_model(
            model, train_ld, val_ld, EPOCHS, LR, PATIENCE, DEVICE)

        P("\n[4/7] LSTM 测试集评估...")
        metrics = evaluate_on_loader(model, test_ld, scaler, DEVICE)
        lstm_mae = metrics["mae"]
        lstm_rmse = metrics["rmse"]
        lstm_rel = metrics["rel_err"]
        P(f"  MAE:  {lstm_mae:.4f}")
        P(f"  RMSE: {lstm_rmse:.4f}")
        P(f"  相对误差: {lstm_rel:.2f}%")

        P("\n  滑动窗口预测中...")
        scaled_all = scaler.transform(values.reshape(-1, 1)).flatten()
        rolling_results = rolling_predict(
            model, scaled_all, scaler, CONTEXT_LEN, HORIZON, HORIZON, DEVICE)
        P(f"  滑动窗口数: {len(rolling_results)}")

        rolling_residuals = np.array([r["mean_residual"] for r in rolling_results])
        rolling_start_idxs = np.array([r["start_idx"] for r in rolling_results])
        rolling_pred_reals = [r["pred_real"] for r in rolling_results]
        rolling_actual_reals = [r["actual_real"] for r in rolling_results]

        P("  保存 LSTM 缓存...")
        np.savez(CACHE_PATH,
                 context_len=CONTEXT_LEN, horizon=HORIZON, n_values=len(values),
                 train_losses=train_losses, val_losses=val_losses,
                 lstm_mae=lstm_mae, lstm_rmse=lstm_rmse, lstm_rel=lstm_rel,
                 rolling_residuals=rolling_residuals,
                 rolling_start_idxs=rolling_start_idxs,
                 rolling_pred_reals=np.array(rolling_pred_reals, dtype=object),
                 rolling_actual_reals=np.array(rolling_actual_reals, dtype=object))
        P("  缓存已保存")

    P(f"\n  LSTM MAE: {lstm_mae:.4f} | RMSE: {lstm_rmse:.4f} | 相对误差: {lstm_rel:.2f}%")

    # 重建 rolling_results 格式 (供绘图)
    rolling_results_rebuilt = []
    for i in range(len(rolling_residuals)):
        rolling_results_rebuilt.append({
            "start_idx": int(rolling_start_idxs[i]),
            "mean_residual": rolling_residuals[i],
            "pred_real": rolling_pred_reals[i],
            "actual_real": rolling_actual_reals[i],
        })

    # --- 5. TimesFM 对比 ---
    P("\n[5/7] TimesFM 对比预测...")
    tfm_segs = min(5, len(rolling_results_rebuilt))
    tfm_results_list, tfm_overall_mae = run_timesfm_forecast(
        values, CONTEXT_LEN, HORIZON, n_segments=tfm_segs)

    if tfm_overall_mae is not None:
        P(f"  TimesFM 平均 MAE: {tfm_overall_mae:.4f}")
        P(f"  LSTM    平均 MAE: {lstm_mae:.4f}")
        better = "LSTM" if lstm_mae < tfm_overall_mae else "TimesFM"
        P(f"  → 当前数据集上 {better} 更优")
    else:
        P("  TimesFM 跳过（环境不支持或加载失败）")

    # --- 6. 异常检测 + 诊断 ---
    P("\n[6/7] 异常检测与健康诊断...")
    rolling_times = []
    for r in rolling_results_rebuilt:
        idx = min(r["start_idx"] + HORIZON // 2, len(times_index) - 1)
        rolling_times.append(times_index[idx])

    bm, bs = np.mean(rolling_residuals), np.std(rolling_residuals)
    diag_obj = HealthDiagnostic(bm, bs)
    diag = diag_obj.full_diagnosis(rolling_residuals)

    P(f"  告警等级分布:")
    for lvl in range(4):
        cnt = diag["level_counts"][lvl]
        pct = cnt / len(rolling_residuals) * 100
        P(f"    L{lvl}-{HealthDiagnostic.LEVELS[lvl]}: {cnt} ({pct:.1f}%)")
    P(f"  健康评分: {diag['health_score']:.1f}/100")
    P(f"  综合判定: {diag['overall_label']} → {diag['action']}")

    # --- 7. 出图 ---
    P("\n[7/7] 生成图表...")

    plot_1_training(train_losses, val_losses,
                    os.path.join(OUTPUT_DIR, "lstm_1_训练过程.png"))
    P("  [OK] lstm_1_训练过程.png")

    plot_2_comparison(times_index, values, scaler,
                      rolling_results_rebuilt, tfm_results_list,
                      CONTEXT_LEN, HORIZON, resample_label,
                      os.path.join(OUTPUT_DIR, "lstm_2_LSTM与TimesFM预测对比.png"))
    P("  [OK] lstm_2_LSTM与TimesFM预测对比.png")

    plot_3_anomaly(rolling_times, rolling_residuals, diag_obj, diag,
                   os.path.join(OUTPUT_DIR, "lstm_3_异常检测.png"))
    P("  [OK] lstm_3_异常检测.png")

    plot_4_health(rolling_times, rolling_residuals, diag, diag_obj,
                  lstm_mae, tfm_overall_mae,
                  os.path.join(OUTPUT_DIR, "lstm_4_健康诊断报告.png"))
    P("  [OK] lstm_4_健康诊断报告.png")

    P("\n" + "=" * 60)
    P("  全部完成！")
    P("=" * 60)
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.startswith("lstm_"):
            sz = os.path.getsize(os.path.join(OUTPUT_DIR, f)) / 1024
            P(f"  {f}  ({sz:.0f} KB)")
