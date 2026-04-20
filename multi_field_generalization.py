"""
多属性泛化性测试: 验证 "SavGol 分解 + h=16" 在不同物理量上的表现
属性选择:
  - Magnitude (合成幅值, 基准, 量级 ~0.86)
  - aRMSX     (加速度 RMS, 与 Magnitude 同族, 量级 ~0.52)
  - vRMSM     (速度 RMS 合成, 不同物理量, 量级 ~3.63)
  - ShockZ    (冲击 Z 轴, 完全不同量级, 量级 ~-226)
"""
import os, sys, time, json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

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
CACHE_PATH = os.path.join(OUTPUT_DIR, "multifield_cache.npz")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HAS_CUDA = torch.cuda.is_available()

FIELDS = ["Magnitude", "aRMSX", "vRMSM", "ShockZ"]
CONTEXT = 256
HORIZON = 16
SAVGOL_WINDOW = 61
SAVGOL_POLY = 3
EPOCHS = 25


def load_field(field_name):
    df = pd.read_csv(CSV_PATH, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df = df[df["_field"] == field_name]
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])
    s = df.set_index("_time").sort_index()["_value"].resample("1s").mean().dropna()
    return s


def savgol_trend(s, window=SAVGOL_WINDOW, polyorder=SAVGOL_POLY):
    t = signal.savgol_filter(s.values, window_length=window, polyorder=polyorder)
    return pd.Series(t, index=s.index)


def autocorr_lag(x, lag):
    x = x - np.mean(x)
    return float(np.dot(x[:-lag], x[lag:]) / np.dot(x, x))


class TSD(Dataset):
    def __init__(self, data, context, horizon):
        self.data = data; self.context = context; self.horizon = horizon
        self.n = len(data) - context - horizon + 1

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        return (torch.FloatTensor(self.data[i:i+self.context]).unsqueeze(-1),
                torch.FloatTensor(self.data[i+self.context:i+self.context+self.horizon]))


class LSTM(nn.Module):
    def __init__(self, horizon=16, hidden=128):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, 2, batch_first=True, dropout=0.2)
        self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(),
                                   nn.Dropout(0.2), nn.Linear(hidden, horizon))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def train_lstm(series, device):
    v = series.values
    n = len(v); te = int(n*0.70); ve = int(n*0.85)
    scaler = MinMaxScaler()
    scaler.fit(v[:te].reshape(-1,1))
    scaled = scaler.transform(v.reshape(-1,1)).flatten()
    tr = TSD(scaled[:te], CONTEXT, HORIZON)
    vl = TSD(scaled[te-CONTEXT:ve], CONTEXT, HORIZON)
    ts = TSD(scaled[ve-CONTEXT:], CONTEXT, HORIZON)
    bs = min(64, max(1, len(tr)//4))
    trl = DataLoader(tr, batch_size=bs, shuffle=True, drop_last=len(tr)>bs)
    vll = DataLoader(vl, batch_size=bs, shuffle=False)
    tsl = DataLoader(ts, batch_size=bs, shuffle=False)

    m = LSTM(HORIZON).to(device)
    o = torch.optim.Adam(m.parameters(), lr=1e-3)
    s = torch.optim.lr_scheduler.ReduceLROnPlateau(o, factor=0.5, patience=3)
    c = nn.MSELoss()
    bv = float("inf"); bst = None; pc = 0
    t0 = time.time()
    for ep in range(EPOCHS):
        m.train()
        for x, y in trl:
            x, y = x.to(device), y.to(device)
            o.zero_grad(); c(m(x), y).backward()
            nn.utils.clip_grad_norm_(m.parameters(), 1.0); o.step()
        m.eval(); vloss, vb = 0., 0
        with torch.no_grad():
            for x, y in vll:
                x, y = x.to(device), y.to(device)
                vloss += c(m(x), y).item(); vb += 1
        vloss /= max(vb, 1); s.step(vloss)
        if vloss < bv:
            bv = vloss; bst = {k: v.cpu().clone() for k, v in m.state_dict().items()}; pc = 0
        else:
            pc += 1
            if pc >= 5: break

    m.load_state_dict(bst)
    m.eval()
    pr, ac = [], []
    with torch.no_grad():
        for x, y in tsl:
            pr.append(m(x.to(device)).cpu().numpy()); ac.append(y.numpy())
    pr = np.concatenate(pr); ac = np.concatenate(ac)
    pf = scaler.inverse_transform(pr.reshape(-1,1)).flatten()
    af = scaler.inverse_transform(ac.reshape(-1,1)).flatten()
    mae = float(np.mean(np.abs(af-pf)))

    n_show = min(60, len(pr))
    idx = np.linspace(0, len(pr)-1, n_show, dtype=int)
    p_show = scaler.inverse_transform(pr[idx].reshape(-1,1)).reshape(n_show, HORIZON)
    a_show = scaler.inverse_transform(ac[idx].reshape(-1,1)).reshape(n_show, HORIZON)
    return {"mae": mae, "train_time": time.time()-t0,
            "eval_preds": p_show.tolist(), "eval_actuals": a_show.tolist()}


_tfm = None
def load_tfm():
    global _tfm
    import timesfm
    from timesfm.configs import ForecastConfig
    if _tfm is None:
        print("  [TFM] 加载模型...", flush=True)
        _tfm = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch")
    _tfm.compile(ForecastConfig(
        max_context=min(1024, CONTEXT), max_horizon=min(256, HORIZON),
        normalize_inputs=True, use_continuous_quantile_head=True,
        force_flip_invariance=True, infer_is_positive=True, fix_quantile_crossing=True,
    ))
    return _tfm


def run_tfm(series, n_eval=60):
    tfm = load_tfm()
    v = series.values
    ve = int(len(v) * 0.85)
    test = v[ve-CONTEXT:]
    stride = max(1, (len(test)-CONTEXT-HORIZON) // n_eval)
    ap, aa, sp, sa = [], [], [], []
    for s in range(0, len(test)-CONTEXT-HORIZON, stride):
        ctx = test[s:s+CONTEXT].astype(np.float64)
        fut = test[s+CONTEXT:s+CONTEXT+HORIZON]
        pf, _ = tfm.forecast(horizon=HORIZON, inputs=[ctx])
        p = pf[0][:len(fut)]
        ap.extend(p.tolist()); aa.extend(fut.tolist())
        sp.append(p.tolist()); sa.append(fut.tolist())
        if len(sp) >= n_eval: break
    mae = float(np.mean(np.abs(np.array(aa) - np.array(ap))))
    return {"mae": mae, "eval_preds": sp, "eval_actuals": sa}


def phase_a():
    print("=" * 60)
    print(f"  Phase A: 多属性 LSTM (SavGol + h={HORIZON})")
    print("=" * 60)
    lstm_res = {}
    field_info = {}
    for f in FIELDS:
        print(f"\n[属性 {f}] 加载 + 分解...", flush=True)
        orig = load_field(f)
        trend = savgol_trend(orig)
        field_info[f] = {
            "mean": float(orig.mean()),
            "std": float(orig.std()),
            "trend_std": float(trend.std()),
            "noise_std": float((orig - trend).std()),
            "acf_lag1": autocorr_lag(trend.values, 1),
            "acf_lag16": autocorr_lag(trend.values, 16),
        }
        print(f"  {f}: 均值={orig.mean():.3f}, 标准差={orig.std():.3f}")
        print(f"  LSTM 训练...", flush=True)
        r = train_lstm(trend, DEVICE)
        print(f"  MAE={r['mae']:.4f}  耗时={r['train_time']:.1f}s")
        lstm_res[f] = r

    np.savez(CACHE_PATH,
             lstm_results=json.dumps(lstm_res),
             field_info=json.dumps(field_info))
    print(f"\n[OK] 已缓存")
    return lstm_res, field_info


def phase_b():
    print("=" * 60)
    print(f"  Phase B: 多属性 TimesFM + 对比图")
    print("=" * 60)
    if not os.path.exists(CACHE_PATH):
        print("[ERR] 缺缓存"); return
    cache = np.load(CACHE_PATH, allow_pickle=True)
    lstm_res = json.loads(str(cache["lstm_results"]))
    field_info = json.loads(str(cache["field_info"]))

    tfm_res = {}
    for f in FIELDS:
        print(f"\n[属性 {f}] TimesFM...", flush=True)
        orig = load_field(f)
        trend = savgol_trend(orig)
        r = run_tfm(trend)
        print(f"  MAE={r['mae']:.4f}")
        tfm_res[f] = r

    # 合并表
    rows = []
    for f in FIELDS:
        fi = field_info[f]
        rows.append({
            "属性": f,
            "原始均值": round(fi["mean"], 3),
            "原始标准差": round(fi["std"], 3),
            "趋势标准差": round(fi["trend_std"], 3),
            "噪声标准差": round(fi["noise_std"], 3),
            "ACF_lag1": round(fi["acf_lag1"], 3),
            "ACF_lag16": round(fi["acf_lag16"], 3),
            "LSTM_MAE": round(lstm_res[f]["mae"], 4),
            "TimesFM_MAE": round(tfm_res[f]["mae"], 4),
            "LSTM_相对误差%": round(lstm_res[f]["mae"] / (abs(fi["mean"])+1e-9) * 100, 2),
            "TimesFM_相对误差%": round(tfm_res[f]["mae"] / (abs(fi["mean"])+1e-9) * 100, 2),
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "多属性泛化测试.csv"),
              index=False, encoding="utf-8-sig")
    print("\n" + df.to_string(index=False))

    plot_comparison(df, lstm_res, tfm_res, field_info)


def plot_comparison(df, lstm_res, tfm_res, field_info):
    # 图1: 每个属性 2 列 (2个样例) 预测曲线
    n_fields = len(FIELDS)
    n_samples = 3
    fig, axes = plt.subplots(n_fields, n_samples, figsize=(20, 3.8*n_fields))

    for row, f in enumerate(FIELDS):
        lr = lstm_res[f]; tr = tfm_res[f]
        actuals_arr = np.array(lr["eval_actuals"])

        # 选方差大的正常样例 (避开零值)
        seg_mean = actuals_arr.mean(axis=1)
        seg_std = actuals_arr.std(axis=1)
        # 对 Shock 类: 绝对值均值大的算正常; 对其他: 均值>0.3*全局均值算正常
        mean_thr = 0.3 * abs(field_info[f]["mean"])
        ok = np.abs(seg_mean) > mean_thr
        idx_pool = np.where(ok)[0]
        if len(idx_pool) >= n_samples:
            sel = idx_pool[np.argsort(-seg_std[idx_pool])[:n_samples]]
        else:
            sel = np.argsort(-seg_std)[:n_samples]

        for col, si in enumerate(sel):
            ax = axes[row, col] if n_fields > 1 else axes[col]
            actual = actuals_arr[si]
            lstm_p = np.array(lr["eval_preds"][si])
            ta = np.array(tr["eval_actuals"])
            d = np.mean((ta - actual.reshape(1,-1))**2, axis=1)
            ti = int(np.argmin(d))
            tfm_p = np.array(tr["eval_preds"][ti])

            x = np.arange(len(actual))
            ax.plot(x, actual, color="#2c3e50", linewidth=2.2, label="真实值")
            ax.plot(x, lstm_p, "--", color="#e74c3c", linewidth=1.6, label="LSTM")
            if len(tfm_p) == len(actual):
                ax.plot(x, tfm_p, "-.", color="#27ae60", linewidth=1.6, label="TimesFM")
            ax.set_title(f"{f} - 样例{col+1} (std={actual.std():.3f})", fontsize=10)
            if col == 0:
                ax.set_ylabel(f, fontsize=12, fontweight="bold")
            if row == n_fields-1:
                ax.set_xlabel("预测步(秒)", fontsize=9)
            ax.legend(fontsize=8, loc="best")
            ax.grid(True, alpha=0.3)

    mae_line = "  |  ".join([
        f"{f}: LSTM={lstm_res[f]['mae']:.4f}, TFM={tfm_res[f]['mae']:.4f}"
        for f in FIELDS
    ])
    fig.suptitle(f"多属性泛化性测试 — SavGol 趋势 + horizon={HORIZON}\n{mae_line}",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(OUTPUT_DIR, "多属性_1_预测曲线.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("  [OK] 多属性_1_预测曲线.png")

    # 图2: MAE + 相对误差柱状图 + ACF
    fig, axes = plt.subplots(1, 3, figsize=(22, 6))

    x = np.arange(len(df))
    w = 0.35
    axes[0].bar(x - w/2, df["LSTM_MAE"], w, color="#e74c3c", label="LSTM", alpha=0.85)
    axes[0].bar(x + w/2, df["TimesFM_MAE"], w, color="#27ae60", label="TimesFM", alpha=0.85)
    for i, (l, t) in enumerate(zip(df["LSTM_MAE"], df["TimesFM_MAE"])):
        axes[0].text(i - w/2, l, f"{l:.3f}", ha="center", va="bottom", fontsize=9)
        axes[0].text(i + w/2, t, f"{t:.3f}", ha="center", va="bottom", fontsize=9)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df["属性"], fontsize=11)
    axes[0].set_ylabel("MAE", fontsize=11)
    axes[0].set_title(f"各属性 MAE 对比 (SavGol 趋势, h={HORIZON})", fontsize=12)
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3, axis="y")
    axes[0].set_yscale("log")

    axes[1].bar(x - w/2, df["LSTM_相对误差%"], w, color="#e74c3c", label="LSTM", alpha=0.85)
    axes[1].bar(x + w/2, df["TimesFM_相对误差%"], w, color="#27ae60", label="TimesFM", alpha=0.85)
    for i, (l, t) in enumerate(zip(df["LSTM_相对误差%"], df["TimesFM_相对误差%"])):
        axes[1].text(i - w/2, l, f"{l:.1f}", ha="center", va="bottom", fontsize=9)
        axes[1].text(i + w/2, t, f"{t:.1f}", ha="center", va="bottom", fontsize=9)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(df["属性"], fontsize=11)
    axes[1].set_ylabel("相对误差 (%)", fontsize=11)
    axes[1].set_title(f"各属性相对误差 MAE/|均值|×100%", fontsize=12)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3, axis="y")

    axes[2].bar(x - w/2, df["ACF_lag1"], w, color="#3498db", label="lag-1", alpha=0.85)
    axes[2].bar(x + w/2, df["ACF_lag16"], w, color="#9b59b6", label="lag-16", alpha=0.85)
    for i, (l1, l16) in enumerate(zip(df["ACF_lag1"], df["ACF_lag16"])):
        axes[2].text(i - w/2, l1, f"{l1:.2f}", ha="center", va="bottom", fontsize=9)
        axes[2].text(i + w/2, l16, f"{l16:.2f}", ha="center", va="bottom", fontsize=9)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(df["属性"], fontsize=11)
    axes[2].set_ylabel("自相关系数", fontsize=11)
    axes[2].set_title("趋势信号的自相关 (决定可预测性)", fontsize=12)
    axes[2].legend(fontsize=10)
    axes[2].grid(True, alpha=0.3, axis="y")
    axes[2].axhline(0.3, color="red", linestyle="--", linewidth=0.8, alpha=0.5)

    fig.suptitle(f"多属性泛化性 — SavGol 分解 + h={HORIZON} 的推广效果",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(OUTPUT_DIR, "多属性_2_指标对比.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("  [OK] 多属性_2_指标对比.png")


if __name__ == "__main__":
    print(f"环境: Python {sys.version.split()[0]}, CUDA={HAS_CUDA}")
    if HAS_CUDA:
        phase_a()
        print("\n[NEXT] 切到 py3.11 CPU 跑 Phase B")
    else:
        phase_b()
