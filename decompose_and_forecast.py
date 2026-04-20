"""
方案 B: 信号分解 + 趋势预测
1. 对 Magnitude 做 3 种分解: 滑动均值 / Savitzky-Golay / 低通滤波
2. 展示分解效果
3. 测算趋势部分的可预测性 (ACF + 朴素基线)
4. 用 LSTM + TimesFM 预测趋势, 对比 MAE

运行:
  Phase A (CUDA): 训练 LSTM 预测各分解版本的趋势 → 保存
  Phase B (CPU+TFM): 跑 TimesFM + 合并 + 出图
"""

import os
import sys
import time
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import signal
from scipy.ndimage import uniform_filter1d

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, r"E:\timesfm_project\timesfm\src")
os.environ["HF_HOME"] = r"E:\timesfm_project\hf_cache"

CSV_PATH = r"E:\timesfm_project\时序\MPB01_6.11 08_18.csv"
OUTPUT_DIR = r"E:\timesfm_project\output"
CACHE_PATH = os.path.join(OUTPUT_DIR, "decompose_cache.npz")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HAS_CUDA = torch.cuda.is_available()

CONTEXT = 256
HORIZON = 32
TRAIN_EPOCHS = 25


# ============================================================
# 加载数据
# ============================================================
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
    s = df.set_index("_time").sort_index()["_value"]
    return s.resample("1s").mean().dropna()


# ============================================================
# 分解方法
# ============================================================
def decompose_moving_avg(s, window=30):
    """移动平均分解: 趋势 = 窗口滑动均值"""
    trend = pd.Series(uniform_filter1d(s.values, size=window, mode="nearest"),
                      index=s.index)
    noise = s - trend
    return trend, noise


def decompose_savgol(s, window=61, polyorder=3):
    """Savitzky-Golay 滤波分解"""
    trend_vals = signal.savgol_filter(s.values, window_length=window,
                                       polyorder=polyorder)
    trend = pd.Series(trend_vals, index=s.index)
    noise = s - trend
    return trend, noise


def decompose_butter(s, cutoff_hz=0.05, fs=1.0, order=4):
    """Butterworth 低通滤波分解"""
    b, a = signal.butter(order, cutoff_hz, btype="low", fs=fs)
    trend_vals = signal.filtfilt(b, a, s.values)
    trend = pd.Series(trend_vals, index=s.index)
    noise = s - trend
    return trend, noise


# ============================================================
# 朴素基线 (在任意序列上)
# ============================================================
def naive_last_value_mae(series, horizon):
    vals = series.values
    n = len(vals)
    errs = []
    for s in range(0, n - horizon, horizon):
        if s + horizon > n:
            break
        pred = vals[s] if s > 0 else vals[0]
        if s == 0:
            continue
        actual = vals[s: s + horizon]
        pred_arr = np.full(horizon, vals[s-1])
        errs.extend(np.abs(actual - pred_arr))
    return float(np.mean(errs)) if errs else None


def autocorr_lag(x, lag):
    x = x - np.mean(x)
    return float(np.dot(x[:-lag], x[lag:]) / np.dot(x, x))


# ============================================================
# LSTM (直接多步输出)
# ============================================================
class TSD(Dataset):
    def __init__(self, data, context, horizon):
        self.data, self.context, self.horizon = data, context, horizon
        self.n = len(data) - context - horizon + 1

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        return (torch.FloatTensor(self.data[i:i+self.context]).unsqueeze(-1),
                torch.FloatTensor(self.data[i+self.context:i+self.context+self.horizon]))


class LSTM(nn.Module):
    def __init__(self, hidden=128, horizon=32):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, 2, batch_first=True, dropout=0.2)
        self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(),
                                   nn.Dropout(0.2), nn.Linear(hidden, horizon))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def train_lstm_for(series, context, horizon, device, epochs=TRAIN_EPOCHS):
    v = series.values
    n = len(v)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    scaler = MinMaxScaler()
    scaler.fit(v[:train_end].reshape(-1, 1))
    scaled = scaler.transform(v.reshape(-1, 1)).flatten()

    train_ds = TSD(scaled[:train_end], context, horizon)
    val_ds = TSD(scaled[train_end-context:val_end], context, horizon)
    test_ds = TSD(scaled[val_end-context:], context, horizon)

    bs = min(64, max(1, len(train_ds) // 4))
    train_ld = DataLoader(train_ds, batch_size=bs, shuffle=True,
                          drop_last=len(train_ds) > bs)
    val_ld = DataLoader(val_ds, batch_size=bs, shuffle=False)
    test_ld = DataLoader(test_ds, batch_size=bs, shuffle=False)

    model = LSTM(128, horizon).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=3)
    crit = nn.MSELoss()

    best_val = float("inf")
    best_state = None
    pc = 0
    t0 = time.time()
    for ep in range(epochs):
        model.train()
        for xb, yb in train_ld:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

        model.eval()
        vl, vb = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_ld:
                xb, yb = xb.to(device), yb.to(device)
                vl += crit(model(xb), yb).item()
                vb += 1
        vl /= max(vb, 1)
        sched.step(vl)
        if vl < best_val:
            best_val = vl
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            pc = 0
        else:
            pc += 1
            if pc >= 5:
                break

    train_time = time.time() - t0
    model.load_state_dict(best_state)

    model.eval()
    preds, acts = [], []
    with torch.no_grad():
        for xb, yb in test_ld:
            preds.append(model(xb.to(device)).cpu().numpy())
            acts.append(yb.numpy())
    preds = np.concatenate(preds)
    acts = np.concatenate(acts)
    pf = scaler.inverse_transform(preds.reshape(-1, 1)).flatten()
    af = scaler.inverse_transform(acts.reshape(-1, 1)).flatten()
    mae = float(np.mean(np.abs(af - pf)))

    n_show = min(60, len(preds))
    idx = np.linspace(0, len(preds) - 1, n_show, dtype=int)
    p_show = scaler.inverse_transform(preds[idx].reshape(-1, 1)).reshape(n_show, horizon)
    a_show = scaler.inverse_transform(acts[idx].reshape(-1, 1)).reshape(n_show, horizon)
    return {"mae": mae, "train_time": train_time,
            "eval_preds": p_show.tolist(), "eval_actuals": a_show.tolist(),
            "eval_test_start_idx": int(val_end)}


# ============================================================
# TimesFM
# ============================================================
_tfm = None

def _load_tfm(context, horizon):
    global _tfm
    import timesfm
    from timesfm.configs import ForecastConfig
    if _tfm is None:
        print("  [TFM] 加载模型...", flush=True)
        _tfm = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch")
    _tfm.compile(ForecastConfig(
        max_context=min(1024, context), max_horizon=min(256, horizon),
        normalize_inputs=True, use_continuous_quantile_head=True,
        force_flip_invariance=True, infer_is_positive=True, fix_quantile_crossing=True,
    ))
    return _tfm


def run_tfm_on(series, context, horizon, n_eval=30):
    tfm = _load_tfm(context, horizon)
    v = series.values
    n = len(v)
    val_end = int(n * 0.85)
    test = v[val_end - context:]

    t0 = time.time()
    stride = max(1, (len(test) - context - horizon) // n_eval)
    all_p, all_a, seg_p, seg_a = [], [], [], []
    for s in range(0, len(test) - context - horizon, stride):
        ctx = test[s: s + context].astype(np.float64)
        fut = test[s + context: s + context + horizon]
        pf, _ = tfm.forecast(horizon=horizon, inputs=[ctx])
        p = pf[0][:len(fut)]
        all_p.extend(p.tolist())
        all_a.extend(fut.tolist())
        seg_p.append(p.tolist())
        seg_a.append(fut.tolist())
        if len(seg_p) >= n_eval:
            break

    pred_time = time.time() - t0
    mae = float(np.mean(np.abs(np.array(all_a) - np.array(all_p))))
    return {"mae": mae, "pred_time": pred_time,
            "eval_preds": seg_p, "eval_actuals": seg_a}


# ============================================================
# Phase A: LSTM
# ============================================================
def phase_a(mag, decomp):
    print("=" * 60)
    print("  Phase A: LSTM 训练 (设备=", DEVICE, ")")
    print("=" * 60)

    results = {"原始信号": {}, **{k: {} for k in decomp.keys()}}

    # 对原始信号
    print("\n[基线] 原始信号 LSTM...", flush=True)
    r = train_lstm_for(mag, CONTEXT, HORIZON, DEVICE)
    print(f"  MAE={r['mae']:.4f}  耗时={r['train_time']:.1f}s")
    results["原始信号"] = r

    # 对各趋势
    for i, (name, (trend, _)) in enumerate(decomp.items()):
        print(f"\n[{i+1}/{len(decomp)}] {name} 趋势信号 LSTM...", flush=True)
        r = train_lstm_for(trend, CONTEXT, HORIZON, DEVICE)
        print(f"  MAE={r['mae']:.4f}  耗时={r['train_time']:.1f}s")
        results[name] = r

    np.savez(CACHE_PATH, lstm_results=json.dumps(results))
    print(f"\n[OK] 已缓存: {CACHE_PATH}")
    return results


# ============================================================
# Phase B: TimesFM + 合并 + 图
# ============================================================
def phase_b(mag, decomp):
    print("=" * 60)
    print("  Phase B: TimesFM + 合并 + 出图")
    print("=" * 60)

    if not os.path.exists(CACHE_PATH):
        print("[ERR] 缺 LSTM 缓存")
        return
    cache = np.load(CACHE_PATH, allow_pickle=True)
    lstm_res = json.loads(str(cache["lstm_results"]))

    tfm_res = {}
    print("\n[基线] 原始信号 TimesFM...", flush=True)
    tfm_res["原始信号"] = run_tfm_on(mag, CONTEXT, HORIZON)
    print(f"  MAE={tfm_res['原始信号']['mae']:.4f}")

    for name, (trend, _) in decomp.items():
        print(f"\n[{name}] TimesFM...", flush=True)
        tfm_res[name] = run_tfm_on(trend, CONTEXT, HORIZON)
        print(f"  MAE={tfm_res[name]['mae']:.4f}")

    # ---------- 合并结果表 ----------
    rows = []
    for key in ["原始信号"] + list(decomp.keys()):
        if key == "原始信号":
            series = mag
        else:
            series = decomp[key][0]
        rows.append({
            "信号": key,
            "均值": round(series.mean(), 4),
            "标准差": round(series.std(), 4),
            "变异系数": round(series.std() / (abs(series.mean())+1e-9), 4),
            "ACF_lag1": round(autocorr_lag(series.values, 1), 4),
            "ACF_lag30": round(autocorr_lag(series.values, 30), 4),
            "朴素最后值MAE": round(naive_last_value_mae(series, HORIZON), 4),
            "LSTM_MAE": round(lstm_res[key]["mae"], 4),
            "TimesFM_MAE": round(tfm_res[key]["mae"], 4),
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "分解预测对比.csv"),
              index=False, encoding="utf-8-sig")
    print("\n" + df.to_string(index=False))

    # ---------- 绘图 ----------
    plot_decomposition(mag, decomp)
    plot_predictability(df)
    plot_prediction_curves(decomp, lstm_res, tfm_res)


def plot_decomposition(mag, decomp):
    """图1: 分解效果——原始 + 3 种趋势 + 3 种残差"""
    fig, axes = plt.subplots(4, 1, figsize=(20, 14), sharex=True)

    # 第一行: 原始 + 3 种趋势叠加
    axes[0].plot(mag.index, mag.values, color="#bdc3c7", linewidth=0.5,
                  alpha=0.8, label="原始信号")
    colors = ["#e74c3c", "#27ae60", "#2980b9"]
    for (name, (trend, _)), c in zip(decomp.items(), colors):
        axes[0].plot(trend.index, trend.values, color=c, linewidth=1.2,
                      alpha=0.9, label=f"{name} 趋势")
    axes[0].set_title("原始信号 + 3 种分解得到的趋势叠加",
                       fontsize=13)
    axes[0].set_ylabel("Magnitude")
    axes[0].legend(fontsize=10, loc="upper right", ncol=4)
    axes[0].grid(True, alpha=0.2)

    # 后 3 行: 每种分解的趋势 + 残差
    for i, ((name, (trend, noise)), c) in enumerate(zip(decomp.items(), colors)):
        ax = axes[i + 1]
        ax.plot(mag.index, mag.values, color="#95a5a6", linewidth=0.4,
                 alpha=0.5, label="原始")
        ax.plot(trend.index, trend.values, color=c, linewidth=1.5, label="趋势")
        ax2 = ax.twinx()
        ax2.plot(noise.index, noise.values, color="orange", linewidth=0.4,
                 alpha=0.5, label="残差 (右轴)")
        ax2.set_ylabel("残差", color="orange", fontsize=10)
        ax.set_title(f"{name}: 趋势 (std={trend.std():.3f}) + "
                      f"残差 (std={noise.std():.3f})",
                      fontsize=12)
        ax.set_ylabel("Magnitude")
        ax.legend(loc="upper left", fontsize=9)
        ax2.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.2)

    axes[-1].set_xlabel("时间", fontsize=11)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.suptitle("方案B — Magnitude 信号分解对比 (3 种方法)",
                 fontsize=15, fontweight="bold", y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(os.path.join(OUTPUT_DIR, "分解_1_信号分解对比.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("  [OK] 分解_1_信号分解对比.png")


def plot_predictability(df):
    """图2: 每种信号的可预测性 + MAE 对比"""
    fig, axes = plt.subplots(1, 2, figsize=(20, 7))

    # 左: ACF 对比
    x = np.arange(len(df))
    w = 0.4
    axes[0].bar(x - w/2, df["ACF_lag1"], w, color="#3498db",
                label="lag-1 自相关", alpha=0.85)
    axes[0].bar(x + w/2, df["ACF_lag30"], w, color="#9b59b6",
                label="lag-30 自相关", alpha=0.85)
    for i, v in enumerate(df["ACF_lag1"]):
        axes[0].text(i - w/2, v + 0.02, f"{v:.2f}", ha="center", fontsize=10)
    for i, v in enumerate(df["ACF_lag30"]):
        axes[0].text(i + w/2, v + 0.02, f"{v:.2f}", ha="center", fontsize=10)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df["信号"], rotation=15, ha="right", fontsize=11)
    axes[0].set_ylabel("自相关系数", fontsize=11)
    axes[0].set_title("信号的可预测性对比 (越接近 1 越可预测)",
                       fontsize=13)
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3, axis="y")
    axes[0].axhline(0.3, color="red", linestyle="--", linewidth=0.8,
                     alpha=0.5)

    # 右: MAE 对比 (朴素 vs LSTM vs TimesFM)
    x = np.arange(len(df))
    w = 0.27
    b1 = axes[1].bar(x - w, df["朴素最后值MAE"], w, color="#7f8c8d",
                     label="朴素-最后值", alpha=0.85)
    b2 = axes[1].bar(x, df["LSTM_MAE"], w, color="#e74c3c",
                     label="LSTM", alpha=0.85)
    b3 = axes[1].bar(x + w, df["TimesFM_MAE"], w, color="#27ae60",
                     label="TimesFM", alpha=0.85)
    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width()/2, h + 0.001,
                          f"{h:.3f}", ha="center", fontsize=9)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(df["信号"], rotation=15, ha="right", fontsize=11)
    axes[1].set_ylabel("MAE", fontsize=11)
    axes[1].set_title("预测方法对比 (MAE, 越低越好)", fontsize=13)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3, axis="y")

    fig.suptitle("方案B — 信号分解后的可预测性与预测精度",
                 fontsize=15, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(OUTPUT_DIR, "分解_2_可预测性对比.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("  [OK] 分解_2_可预测性对比.png")


def plot_prediction_curves(decomp, lstm_res, tfm_res):
    """图3: 各信号的预测曲线样例 - 展示 3 个正常样例 (避开异常时段)"""
    keys = ["原始信号"] + list(decomp.keys())
    n_samples = 3  # 每个信号选 3 个样例

    fig, axes = plt.subplots(len(keys), n_samples, figsize=(22, 3.5 * len(keys)))
    if len(keys) == 1:
        axes = np.array([axes]).reshape(1, n_samples)

    for row_i, key in enumerate(keys):
        if key not in lstm_res or key not in tfm_res:
            continue
        lr = lstm_res[key]
        tr = tfm_res[key]

        actuals_arr = np.array(lr["eval_actuals"])

        # 选择方差最大的前 N 个样例(可视化效果最好,能看波动)
        #   但先排除异常段(真实值几乎全零,均值<0.3 的样例)
        seg_means = actuals_arr.mean(axis=1)
        seg_stds = actuals_arr.std(axis=1)
        ok_mask = seg_means > 0.5
        candidate_idx = np.where(ok_mask)[0]
        if len(candidate_idx) >= n_samples:
            sorted_idx = candidate_idx[np.argsort(-seg_stds[candidate_idx])]
            sel_lstm = sorted_idx[:n_samples]
        else:
            sel_lstm = np.argsort(-seg_stds)[:n_samples]

        for col_j, lstm_idx in enumerate(sel_lstm):
            ax = axes[row_i, col_j]
            actual = actuals_arr[lstm_idx]
            lstm_p = np.array(lr["eval_preds"][lstm_idx])

            # 找 TimesFM 中最匹配的样例(按 actual 值最接近)
            tfm_actuals = np.array(tr["eval_actuals"])
            dists = np.mean((tfm_actuals - actual.reshape(1, -1)) ** 2, axis=1)
            tfm_idx = int(np.argmin(dists))
            tfm_p = np.array(tr["eval_preds"][tfm_idx])

            x = np.arange(len(actual))
            ax.plot(x, actual, color="#2c3e50", linewidth=2, label="真实值")
            ax.plot(x, lstm_p, "--", color="#e74c3c", linewidth=1.5,
                    label="LSTM")
            if len(tfm_p) == len(actual):
                ax.plot(x, tfm_p, "-.", color="#27ae60", linewidth=1.5,
                        label="TimesFM")
            ax.set_title(f"{key} - 样例{col_j+1}\n"
                          f"真实值均值={actual.mean():.3f}, std={actual.std():.3f}",
                          fontsize=10)
            ax.set_xlabel("预测步", fontsize=9)
            if col_j == 0:
                ax.set_ylabel(key, fontsize=10)
            ax.legend(fontsize=8, loc="upper right")
            ax.grid(True, alpha=0.3)

    # 最上方标注总体 MAE
    title = "方案B — 预测曲线样例 (正常运行时段, 每行一种信号, 每列一个样例)"
    mae_line = "  |  ".join([
        f"{k}: LSTM={lstm_res[k]['mae']:.3f}, TFM={tfm_res[k]['mae']:.3f}"
        for k in keys if k in lstm_res and k in tfm_res
    ])
    fig.suptitle(f"{title}\n{mae_line}",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(OUTPUT_DIR, "分解_3_预测曲线对比.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("  [OK] 分解_3_预测曲线对比.png")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    print(f"环境: Python {sys.version.split()[0]}, CUDA={HAS_CUDA}")

    print("\n加载 Magnitude 信号 (1s 重采样)...")
    mag = load_magnitude(CSV_PATH)
    print(f"  {len(mag)} 点, 均值={mag.mean():.3f}, 标准差={mag.std():.3f}")

    print("\n执行 3 种信号分解...")
    decomp = {
        "移动均值(30s)": decompose_moving_avg(mag, window=30),
        "SavGol(61,3)": decompose_savgol(mag, window=61, polyorder=3),
        "Butter低通(0.05Hz)": decompose_butter(mag, cutoff_hz=0.05),
    }
    for name, (tr, no) in decomp.items():
        print(f"  {name:<18} 趋势std={tr.std():.3f}  残差std={no.std():.3f}  "
              f"趋势占比={tr.std()**2/(tr.std()**2+no.std()**2)*100:.1f}%")

    if HAS_CUDA:
        phase_a(mag, decomp)
        print("\n[NEXT] 切到 py3.11 CPU 环境执行 Phase B")
    else:
        phase_b(mag, decomp)
