"""
LSTM vs TimesFM 多参数对比实验
实验设计: 3 维度 × 3 取值 = 7 组 (共享中心点 1s/32/256)

运行流程:
  Phase A (CUDA env, d2l_env): 训练所有 LSTM 变体 → 保存到 compare_cache.npz
  Phase B (CPU env, env):       跑 TimesFM → 合并 → 出图

自动检测环境并执行对应阶段。
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
CACHE_PATH = os.path.join(OUTPUT_DIR, "compare_cache.npz")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "对比实验结果.csv")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HAS_CUDA = torch.cuda.is_available()

# ---------- 实验配置 ----------
# 中心点
CENTER = {"resample": "1s", "horizon": 32, "context": 256}

EXPERIMENTS = [
    # 变重采样
    {"id": "A1", "label": "重采样=1s (中心点)",   "resample": "1s",   "horizon": 32, "context": 256, "dim": "重采样"},
    {"id": "A2", "label": "重采样=5s",            "resample": "5s",   "horizon": 32, "context": 256, "dim": "重采样"},
    {"id": "A3", "label": "重采样=30s",           "resample": "30s",  "horizon": 32, "context": 256, "dim": "重采样"},
    # 变 horizon
    {"id": "B1", "label": "horizon=8",            "resample": "1s",   "horizon": 8,  "context": 256, "dim": "预测长度"},
    {"id": "B2", "label": "horizon=64",           "resample": "1s",   "horizon": 64, "context": 256, "dim": "预测长度"},
    # 变 context
    {"id": "C1", "label": "context=128",          "resample": "1s",   "horizon": 32, "context": 128, "dim": "上下文长度"},
    {"id": "C2", "label": "context=512",          "resample": "1s",   "horizon": 32, "context": 512, "dim": "上下文长度"},
]

TRAIN_EPOCHS = 20
BATCH_SIZE = 64
LR = 1e-3
HIDDEN = 128
N_EVAL_SEGMENTS = 50   # 每组实验用多少滑动窗口计算 MAE


# ============================================================
# 数据加载
# ============================================================
def load_magnitude(csv_path: str) -> pd.Series:
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


def resample_series(series, freq):
    return series.resample(freq).mean().dropna()


# ============================================================
# LSTM (直接多步输出)
# ============================================================
class TimeSeriesDataset(Dataset):
    def __init__(self, data, context, horizon):
        self.data = data
        self.context = context
        self.horizon = horizon
        self.n = len(data) - context - horizon + 1

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        x = self.data[idx: idx + self.context]
        y = self.data[idx + self.context: idx + self.context + self.horizon]
        return torch.FloatTensor(x).unsqueeze(-1), torch.FloatTensor(y)


class DirectLSTM(nn.Module):
    def __init__(self, hidden=128, horizon=32, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, num_layers=2, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, horizon),
        )

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def run_lstm_experiment(values_1d, context, horizon, device, epochs=TRAIN_EPOCHS):
    """训练 LSTM, 返回 (mae, rmse, train_time, eval_segments)"""
    n = len(values_1d)
    if n < context + horizon + 100:
        return None

    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    scaler = MinMaxScaler()
    scaler.fit(values_1d[:train_end].reshape(-1, 1))
    scaled = scaler.transform(values_1d.reshape(-1, 1)).flatten()

    train_ds = TimeSeriesDataset(scaled[:train_end], context, horizon)
    val_ds = TimeSeriesDataset(scaled[train_end - context: val_end], context, horizon)
    test_ds = TimeSeriesDataset(scaled[val_end - context:], context, horizon)

    bs = min(BATCH_SIZE, max(1, len(train_ds) // 4))
    train_ld = DataLoader(train_ds, batch_size=bs, shuffle=True,
                          drop_last=len(train_ds) > bs)
    val_ld = DataLoader(val_ds, batch_size=bs, shuffle=False)
    test_ld = DataLoader(test_ds, batch_size=bs, shuffle=False)

    model = DirectLSTM(HIDDEN, horizon).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=3)
    crit = nn.MSELoss()

    best_val = float("inf")
    patience_cnt = 0
    best_state = None
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
        vl = vl / max(vb, 1)
        sched.step(vl)

        if vl < best_val:
            best_val = vl
            patience_cnt = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_cnt += 1
            if patience_cnt >= 5:
                break

    train_time = time.time() - t0
    model.load_state_dict(best_state)

    model.eval()
    preds, acts = [], []
    with torch.no_grad():
        for xb, yb in test_ld:
            p = model(xb.to(device)).cpu().numpy()
            preds.append(p)
            acts.append(yb.numpy())
    preds = np.concatenate(preds)
    acts = np.concatenate(acts)

    pf = scaler.inverse_transform(preds.reshape(-1, 1)).flatten()
    af = scaler.inverse_transform(acts.reshape(-1, 1)).flatten()
    mae = float(np.mean(np.abs(af - pf)))
    rmse = float(np.sqrt(np.mean((af - pf) ** 2)))

    # 采样若干段保存用于画图
    n_show = min(N_EVAL_SEGMENTS, len(preds))
    idx_show = np.linspace(0, len(preds) - 1, n_show, dtype=int)
    preds_show = preds[idx_show]
    acts_show = acts[idx_show]
    preds_show_real = scaler.inverse_transform(preds_show.reshape(-1, 1)).reshape(preds_show.shape)
    acts_show_real = scaler.inverse_transform(acts_show.reshape(-1, 1)).reshape(acts_show.shape)

    return {
        "mae": mae, "rmse": rmse, "train_time": train_time,
        "eval_preds": preds_show_real.tolist(),
        "eval_actuals": acts_show_real.tolist(),
    }


# ============================================================
# TimesFM
# ============================================================
_tfm_model = None

def _load_tfm(max_context, max_horizon):
    global _tfm_model
    try:
        import timesfm
        from timesfm.configs import ForecastConfig
        if _tfm_model is None:
            print("  [TimesFM] 加载模型...", flush=True)
            _tfm_model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                "google/timesfm-2.5-200m-pytorch")
        _tfm_model.compile(ForecastConfig(
            max_context=min(1024, max_context),
            max_horizon=min(256, max_horizon),
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        ))
        return _tfm_model
    except Exception as e:
        print(f"  [TimesFM] 加载失败: {e}")
        return None


def run_timesfm_experiment(values_1d, context, horizon, n_eval=N_EVAL_SEGMENTS):
    """在滑动窗口上跑 TimesFM, 返回统计"""
    tfm = _load_tfm(context, horizon)
    if tfm is None:
        return None

    n = len(values_1d)
    if n < context + horizon + 100:
        return None

    val_end = int(n * 0.85)
    test_data = values_1d[val_end - context:]

    all_preds, all_acts = [], []
    t0 = time.time()
    stride = max(1, (len(test_data) - context - horizon) // n_eval)
    seg_preds, seg_acts = [], []

    for s in range(0, len(test_data) - context - horizon, stride):
        ctx = test_data[s: s + context].astype(np.float64)
        fut = test_data[s + context: s + context + horizon]
        pf, _ = tfm.forecast(horizon=horizon, inputs=[ctx])
        p = pf[0][:len(fut)]
        all_preds.extend(p.tolist())
        all_acts.extend(fut.tolist())
        seg_preds.append(p.tolist())
        seg_acts.append(fut.tolist())
        if len(seg_preds) >= n_eval:
            break

    pred_time = time.time() - t0
    pf = np.array(all_preds)
    af = np.array(all_acts)
    mae = float(np.mean(np.abs(af - pf)))
    rmse = float(np.sqrt(np.mean((af - pf) ** 2)))

    return {
        "mae": mae, "rmse": rmse, "pred_time": pred_time,
        "eval_preds": seg_preds, "eval_actuals": seg_acts,
    }


# ============================================================
# Phase A: 跑 LSTM 并保存 (CUDA 环境执行)
# ============================================================
def phase_a_lstm(values_by_freq):
    print("=" * 60)
    print(f"  Phase A: 训练 LSTM  (设备={DEVICE})")
    print("=" * 60)

    all_results = {}
    for i, exp in enumerate(EXPERIMENTS):
        print(f"\n[{i+1}/{len(EXPERIMENTS)}] 实验 {exp['id']}: {exp['label']}", flush=True)
        print(f"  resample={exp['resample']}, context={exp['context']}, horizon={exp['horizon']}", flush=True)

        v = values_by_freq[exp["resample"]]
        print(f"  数据点数: {len(v)}", flush=True)

        r = run_lstm_experiment(v, exp["context"], exp["horizon"], DEVICE)
        if r is None:
            print(f"  [跳过] 数据不足", flush=True)
            continue
        print(f"  [LSTM] MAE={r['mae']:.4f}  RMSE={r['rmse']:.4f}  训练耗时={r['train_time']:.1f}s", flush=True)
        all_results[exp["id"]] = r

    np.savez(CACHE_PATH, lstm_results=json.dumps(all_results))
    print(f"\n[OK] LSTM 结果已缓存: {CACHE_PATH}", flush=True)
    return all_results


# ============================================================
# Phase B: 跑 TimesFM + 合并 + 出图 (CPU 环境, 加载 LSTM 缓存)
# ============================================================
def phase_b_tfm(values_by_freq):
    print("=" * 60)
    print(f"  Phase B: 跑 TimesFM + 合并 + 出图")
    print("=" * 60)

    if not os.path.exists(CACHE_PATH):
        print(f"[ERR] 缺 LSTM 缓存，请先在 CUDA 环境跑 Phase A")
        return
    cache = np.load(CACHE_PATH, allow_pickle=True)
    lstm_results = json.loads(str(cache["lstm_results"]))

    tfm_results = {}
    for i, exp in enumerate(EXPERIMENTS):
        print(f"\n[{i+1}/{len(EXPERIMENTS)}] 实验 {exp['id']}: {exp['label']}")
        v = values_by_freq[exp["resample"]]
        r = run_timesfm_experiment(v, exp["context"], exp["horizon"])
        if r is None:
            continue
        print(f"  [TFM] MAE={r['mae']:.4f}  RMSE={r['rmse']:.4f}  推理耗时={r['pred_time']:.1f}s")
        tfm_results[exp["id"]] = r

    # 合并结果表
    rows = []
    for exp in EXPERIMENTS:
        row = {
            "实验ID": exp["id"],
            "对比维度": exp["dim"],
            "配置描述": exp["label"],
            "重采样": exp["resample"],
            "上下文": exp["context"],
            "预测步长": exp["horizon"],
        }
        lr = lstm_results.get(exp["id"])
        tr = tfm_results.get(exp["id"])
        if lr:
            row["LSTM_MAE"] = round(lr["mae"], 4)
            row["LSTM_RMSE"] = round(lr["rmse"], 4)
            row["LSTM_训练耗时秒"] = round(lr["train_time"], 1)
        if tr:
            row["TimesFM_MAE"] = round(tr["mae"], 4)
            row["TimesFM_RMSE"] = round(tr["rmse"], 4)
            row["TimesFM_推理耗时秒"] = round(tr["pred_time"], 1)
        if lr and tr:
            row["胜者"] = "LSTM" if lr["mae"] < tr["mae"] else "TimesFM"
            row["MAE差距%"] = round((max(lr["mae"], tr["mae"]) / min(lr["mae"], tr["mae"]) - 1) * 100, 1)
        rows.append(row)

    results_df = pd.DataFrame(rows)
    results_df.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[OK] 结果表: {RESULTS_CSV}")
    print("\n" + results_df.to_string(index=False))

    # 可视化
    plot_comparison_results(results_df, lstm_results, tfm_results)
    return results_df


def plot_comparison_results(df, lstm_results, tfm_results):
    """
    图1: 每个对比维度 (重采样/horizon/context) 的 MAE 柱状对比
    图2: 选几组典型实验的预测曲线对比
    """
    # ---------- 图1: 分维度对比柱状图 ----------
    dims = ["重采样", "预测长度", "上下文长度"]
    fig, axes = plt.subplots(1, 3, figsize=(22, 7))

    for ax, dim in zip(axes, dims):
        sub = df[df["对比维度"] == dim]
        x = np.arange(len(sub))
        w = 0.35
        lstm_v = sub.get("LSTM_MAE", pd.Series([np.nan]*len(sub))).values
        tfm_v = sub.get("TimesFM_MAE", pd.Series([np.nan]*len(sub))).values
        b1 = ax.bar(x - w/2, lstm_v, w, color="#e74c3c", label="LSTM", alpha=0.85, edgecolor="white")
        b2 = ax.bar(x + w/2, tfm_v, w, color="#27ae60", label="TimesFM", alpha=0.85, edgecolor="white")
        for bar, val in zip(b1, lstm_v):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                        f"{val:.3f}", ha="center", fontsize=9, color="#c0392b", fontweight="bold")
        for bar, val in zip(b2, tfm_v):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                        f"{val:.3f}", ha="center", fontsize=9, color="#229954", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(sub["配置描述"].values, rotation=15, ha="right", fontsize=10)
        ax.set_ylabel("MAE (平均绝对误差)", fontsize=11)
        ax.set_title(f"维度: {dim}", fontsize=13)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle("LSTM vs TimesFM — 分维度参数对比 (属性=Magnitude)",
                 fontsize=15, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(OUTPUT_DIR, "对比_1_分维度柱状图.png"), dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] 对比_1_分维度柱状图.png")

    # ---------- 图2: 预测曲线典型样例 ----------
    sample_ids = ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]
    sample_ids = [sid for sid in sample_ids if sid in lstm_results and sid in tfm_results]
    n = len(sample_ids)
    if n == 0:
        return
    fig, axes = plt.subplots(n, 1, figsize=(20, 3.5 * n))
    if n == 1:
        axes = [axes]
    for ax, sid in zip(axes, sample_ids):
        exp = next(e for e in EXPERIMENTS if e["id"] == sid)
        lr = lstm_results[sid]
        tr = tfm_results[sid]
        mid = len(lr["eval_preds"]) // 2
        actual = np.array(lr["eval_actuals"][mid])
        lstm_p = np.array(lr["eval_preds"][mid])
        tfm_mid = min(mid, len(tr["eval_preds"]) - 1)
        tfm_p = np.array(tr["eval_preds"][tfm_mid])

        x = np.arange(len(actual))
        ax.plot(x, actual, "-", color="#2c3e50", linewidth=2, label="真实值")
        ax.plot(x, lstm_p, "--", color="#e74c3c", linewidth=1.5,
                label=f"LSTM (MAE={lr['mae']:.4f})")
        if len(tfm_p) == len(actual):
            ax.plot(x, tfm_p, "-.", color="#27ae60", linewidth=1.5,
                    label=f"TimesFM (MAE={tr['mae']:.4f})")
        winner = "LSTM" if lr["mae"] < tr["mae"] else "TimesFM"
        ax.set_title(f"实验 {sid}: {exp['label']}  |  胜者: {winner}",
                     fontsize=12)
        ax.set_xlabel("预测步")
        ax.set_ylabel("振动幅值")
        ax.legend(fontsize=10, loc="upper right")
        ax.grid(True, alpha=0.3)
    fig.suptitle("LSTM vs TimesFM — 各实验预测曲线样例 (属性=Magnitude)",
                 fontsize=15, fontweight="bold", y=1.00)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    plt.savefig(os.path.join(OUTPUT_DIR, "对比_2_预测曲线样例.png"), dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] 对比_2_预测曲线样例.png")

    # ---------- 图3: 胜率汇总 ----------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    winners = df["胜者"].dropna().value_counts()
    colors = {"LSTM": "#e74c3c", "TimesFM": "#27ae60"}
    ax1.pie(winners.values, labels=[f"{k}\n({v}/{len(df)} 组)" for k, v in winners.items()],
            colors=[colors[k] for k in winners.index], autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 12})
    ax1.set_title("LSTM vs TimesFM 胜率 (按 MAE)", fontsize=13)

    dims_order = dims
    ax2.set_xlabel("MAE 差距 (%)", fontsize=11)
    ax2.set_ylabel("实验")
    pos = np.arange(len(df))
    gaps = df["MAE差距%"].fillna(0).values
    winner_colors = [colors.get(w, "gray") for w in df["胜者"].fillna("").values]
    bars = ax2.barh(pos, gaps, color=winner_colors, alpha=0.85)
    ax2.set_yticks(pos)
    ax2.set_yticklabels([f"{r['实验ID']}: {r['配置描述']}" for _, r in df.iterrows()], fontsize=9)
    for bar, v, w in zip(bars, gaps, df["胜者"].fillna("").values):
        ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                 f"{w} 领先 {v:.1f}%", va="center", fontsize=9)
    ax2.set_title("每组实验 — MAE 相对差距 (条形越长差距越大)", fontsize=13)
    ax2.grid(True, alpha=0.3, axis="x")
    ax2.invert_yaxis()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "对比_3_胜率汇总.png"), dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  [OK] 对比_3_胜率汇总.png")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    print(f"运行环境: Python {sys.version.split()[0]}, CUDA={HAS_CUDA}")
    print(f"CACHE_PATH = {CACHE_PATH}")

    # 加载数据 & 预先重采样 (所有实验用到)
    print("\n加载数据...", flush=True)
    raw = load_magnitude(CSV_PATH)
    print(f"  原始 {len(raw)} 条")

    freqs_needed = sorted(set(e["resample"] for e in EXPERIMENTS))
    values_by_freq = {}
    for f in freqs_needed:
        s = resample_series(raw, f)
        values_by_freq[f] = s.values
        print(f"  重采样 {f}: {len(s)} 点")

    # 基础阶段选择: CUDA 优先跑 Phase A, 否则 Phase B
    if HAS_CUDA:
        print("\n→ CUDA 环境，执行 Phase A (LSTM 训练)")
        phase_a_lstm(values_by_freq)
        print("\n[NEXT] 请切换到 py3.11 CPU 环境运行本脚本执行 Phase B (TimesFM + 出图)")
    else:
        print("\n→ CPU 环境，执行 Phase B (TimesFM + 合并 + 出图)")
        phase_b_tfm(values_by_freq)
