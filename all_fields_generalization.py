"""
全字段泛化性测试 (11 字段, 验证 A/B/C 可用性判据)
Phase A: 用 d2l_env (CUDA)  跑 LSTM
Phase B: 用 env/     (CPU)  跑 TimesFM + 最终分析

用法:
  conda run -n d2l_env python all_fields_generalization.py      # phase_a
  .\env\python.exe all_fields_generalization.py                  # phase_b
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
CACHE_PATH = os.path.join(OUTPUT_DIR, "allfields_cache.npz")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HAS_CUDA = torch.cuda.is_available()

# 全部 11 个字段
FIELDS = [
    "Magnitude",
    "aRMSX", "aRMSY", "aRMSZ",
    "vRMSX", "vRMSY", "vRMSZ", "vRMSM",
    "ShockX", "ShockY", "ShockZ",
]

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
    return {"mae": mae, "train_time": time.time()-t0}


_tfm = None
def load_tfm():
    global _tfm
    import timesfm
    from timesfm.configs import ForecastConfig
    if _tfm is None:
        print("  [TFM] 加载模型(首次可能 1–2 分钟)...", flush=True)
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
    ap, aa = [], []
    n_windows = 0
    for s in range(0, len(test)-CONTEXT-HORIZON, stride):
        ctx = test[s:s+CONTEXT].astype(np.float64)
        fut = test[s+CONTEXT:s+CONTEXT+HORIZON]
        pf, _ = tfm.forecast(horizon=HORIZON, inputs=[ctx])
        p = pf[0][:len(fut)]
        ap.extend(p.tolist()); aa.extend(fut.tolist())
        n_windows += 1
        if n_windows >= n_eval: break
    mae = float(np.mean(np.abs(np.array(aa) - np.array(ap))))
    return {"mae": mae, "n_windows": n_windows}


def phase_a():
    print("=" * 60)
    print(f"  Phase A: 11 字段 LSTM (SavGol + h={HORIZON})")
    print(f"  Device: {DEVICE}")
    print("=" * 60)
    lstm_res = {}
    field_info = {}
    for i, f in enumerate(FIELDS, 1):
        print(f"\n[{i}/{len(FIELDS)}] {f} 加载 + 分解...", flush=True)
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
        print(f"  {f}: n={len(orig)}, 均值={orig.mean():.3f}, std={orig.std():.3f}, "
              f"趋势std={field_info[f]['trend_std']:.3f}, 噪声std={field_info[f]['noise_std']:.3f}, "
              f"ACF16={field_info[f]['acf_lag16']:.3f}")
        print(f"  LSTM 训练...", flush=True)
        r = train_lstm(trend, DEVICE)
        print(f"  MAE={r['mae']:.4f}  耗时={r['train_time']:.1f}s")
        lstm_res[f] = r

    np.savez(CACHE_PATH,
             lstm_results=json.dumps(lstm_res),
             field_info=json.dumps(field_info))
    print(f"\n[OK] Phase A 完成, 已缓存: {CACHE_PATH}")
    return lstm_res, field_info


def classify(nrmse_tfm, acf16, snr):
    if nrmse_tfm < 0.20 and acf16 > 0.75 and snr > 1.5:
        return "A 可直接上线"
    if nrmse_tfm < 0.35 and acf16 > 0.55:
        return "B 可用/建议复核"
    return "C 不建议直接用"


def phase_b():
    print("=" * 60)
    print(f"  Phase B: 11 字段 TimesFM + 分析")
    print("=" * 60)
    if not os.path.exists(CACHE_PATH):
        print("[ERR] 缺缓存, 先跑 Phase A"); return
    cache = np.load(CACHE_PATH, allow_pickle=True)
    lstm_res = json.loads(str(cache["lstm_results"]))
    field_info = json.loads(str(cache["field_info"]))

    tfm_res = {}
    for i, f in enumerate(FIELDS, 1):
        print(f"\n[{i}/{len(FIELDS)}] {f} TimesFM...", flush=True)
        orig = load_field(f)
        trend = savgol_trend(orig)
        t0 = time.time()
        r = run_tfm(trend)
        print(f"  MAE={r['mae']:.4f}  窗口数={r['n_windows']}  耗时={time.time()-t0:.1f}s")
        tfm_res[f] = r

    # 合并表 + NRMSE + 分类
    rows = []
    for f in FIELDS:
        fi = field_info[f]
        snr = fi["trend_std"] / max(fi["noise_std"], 1e-9)
        nrmse_l = lstm_res[f]["mae"] / max(fi["trend_std"], 1e-9)
        nrmse_t = tfm_res[f]["mae"] / max(fi["trend_std"], 1e-9)
        rows.append({
            "属性": f,
            "类别": ("冲击类" if f.startswith("Shock")
                     else "速度RMS" if f.startswith("vRMS")
                     else "加速度RMS" if f.startswith("aRMS")
                     else "合成幅值"),
            "均值": round(fi["mean"], 3),
            "趋势std": round(fi["trend_std"], 3),
            "噪声std": round(fi["noise_std"], 3),
            "SNR": round(snr, 3),
            "ACF_lag16": round(fi["acf_lag16"], 3),
            "LSTM_MAE": round(lstm_res[f]["mae"], 4),
            "TFM_MAE": round(tfm_res[f]["mae"], 4),
            "NRMSE_LSTM%": round(nrmse_l * 100, 2),
            "NRMSE_TFM%": round(nrmse_t * 100, 2),
            "TFM提升%": round((1 - tfm_res[f]["mae"] / max(lstm_res[f]["mae"], 1e-9)) * 100, 1),
            "可用性": classify(nrmse_t, fi["acf_lag16"], snr),
        })
    df = pd.DataFrame(rows)
    out_csv = os.path.join(OUTPUT_DIR, "全字段泛化测试.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print("\n[OK] 结果表 ->", out_csv)
    print("\n" + df.to_string(index=False))

    plot_all(df)


def plot_all(df):
    # 图 1: 11 字段 NRMSE 对比(按类别分色)
    fig, ax = plt.subplots(figsize=(14, 7))
    colors = {"合成幅值": "#3498db", "加速度RMS": "#1abc9c",
              "速度RMS": "#9b59b6", "冲击类": "#c0392b"}
    x = np.arange(len(df))
    w = 0.36
    cols_lstm = [colors[c] for c in df["类别"]]
    cols_tfm = [colors[c] for c in df["类别"]]
    ax.bar(x - w/2, df["NRMSE_LSTM%"], w, color=cols_lstm, alpha=0.55,
           edgecolor="black", label="LSTM", hatch="//")
    ax.bar(x + w/2, df["NRMSE_TFM%"], w, color=cols_tfm, alpha=0.95,
           edgecolor="black", label="TimesFM")
    for i, (l, t) in enumerate(zip(df["NRMSE_LSTM%"], df["NRMSE_TFM%"])):
        ax.text(i - w/2, l + 0.6, f"{l:.1f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + w/2, t + 0.6, f"{t:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.axhline(20, color="green", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.axhline(35, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.text(len(df)-0.3, 20, " A/B 界线 20%", color="green", fontsize=9, va="bottom")
    ax.text(len(df)-0.3, 35, " B/C 界线 35%", color="red", fontsize=9, va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels(df["属性"], fontsize=10, rotation=20)
    ax.set_ylabel("NRMSE % = MAE / 趋势std", fontsize=12)
    ax.set_title(f"11 字段 NRMSE (SavGol 趋势 + h={HORIZON}) — 颜色=物理量族", fontsize=13, fontweight="bold")
    # 族图例
    from matplotlib.patches import Patch
    legend_elems = [Patch(facecolor=v, label=k) for k, v in colors.items()]
    legend_elems += [Patch(facecolor="white", edgecolor="black", hatch="//", label="LSTM"),
                     Patch(facecolor="gray", edgecolor="black", label="TimesFM")]
    ax.legend(handles=legend_elems, fontsize=9, ncol=2, loc="upper left")
    ax.grid(True, alpha=0.3, axis="y")
    out1 = os.path.join(OUTPUT_DIR, "全字段_1_NRMSE对比.png")
    plt.tight_layout()
    plt.savefig(out1, dpi=140, bbox_inches="tight")
    plt.close()
    print("[OK] ->", out1)

    # 图 2: 判据象限图 (ACF × SNR, 气泡=NRMSE, 颜色=类别)
    fig, ax = plt.subplots(figsize=(12, 8))
    for cat, col in colors.items():
        sub = df[df["类别"] == cat]
        if len(sub) == 0: continue
        sizes = 300 + sub["NRMSE_TFM%"].values * 40
        ax.scatter(sub["ACF_lag16"], sub["SNR"], s=sizes, c=col, alpha=0.7,
                   edgecolors="black", linewidth=1.3, label=cat)
        for _, r in sub.iterrows():
            ax.annotate(f"{r['属性']}\n{r['NRMSE_TFM%']:.1f}%",
                        (r["ACF_lag16"], r["SNR"]),
                        textcoords="offset points", xytext=(10, 6),
                        fontsize=9, fontweight="bold")

    ax.axvline(0.75, color="green", linestyle="--", linewidth=1, alpha=0.6)
    ax.axvline(0.55, color="orange", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(1.5, color="green", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(0.5, color="orange", linestyle="--", linewidth=1, alpha=0.6)

    ax.set_xlabel("ACF lag-16  (趋势的长程可预测性)", fontsize=12)
    ax.set_ylabel("SNR = 趋势std / 噪声std  (对数)", fontsize=12)
    ax.set_yscale("log")
    ax.set_title("全字段可用性判据 — ACF × SNR (气泡大小=NRMSE_TFM)",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=11, title="物理量族", loc="lower right")
    ax.grid(True, alpha=0.3)

    out2 = os.path.join(OUTPUT_DIR, "全字段_2_判据象限.png")
    plt.tight_layout()
    plt.savefig(out2, dpi=140, bbox_inches="tight")
    plt.close()
    print("[OK] ->", out2)

    # 判据命中统计
    print("\n" + "=" * 60)
    print("  判据命中情况")
    print("=" * 60)
    print(df.groupby("可用性").size().to_string())
    print("\n按族看 NRMSE_TFM 均值:")
    print(df.groupby("类别")["NRMSE_TFM%"].agg(["mean", "std", "min", "max"]).round(2).to_string())


if __name__ == "__main__":
    print(f"环境: Python {sys.version.split()[0]}, CUDA={HAS_CUDA}")
    if HAS_CUDA:
        phase_a()
        print("\n[NEXT] 切到 CPU 环境跑 Phase B:")
        print("  .\\env\\python.exe all_fields_generalization.py")
    else:
        phase_b()
