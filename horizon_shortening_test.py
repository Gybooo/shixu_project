"""
缩短预测窗口测试: horizon=4, 8, 16, 32 分别跑 SavGol 趋势预测
观察预测曲线视觉上能否跟上真实值
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
CACHE_PATH = os.path.join(OUTPUT_DIR, "horizon_cache.npz")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HAS_CUDA = torch.cuda.is_available()

CONTEXT = 256
HORIZONS = [4, 8, 16, 32]
EPOCHS = 25


def load_savgol_trend():
    df = pd.read_csv(CSV_PATH, skiprows=[0, 1, 2], low_memory=False)
    meta = df.iloc[:, 0].astype(str).str.startswith("#")
    hdr = df["_time"].astype(str).eq("_time")
    dflt = df.iloc[:, 0].astype(str).eq("#default")
    df = df[~(meta | hdr | dflt)].copy()
    df = df[df["_field"] == "Magnitude"]
    df["_time"] = pd.to_datetime(df["_time"], format="ISO8601", utc=True).dt.tz_localize(None)
    df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
    df = df.dropna(subset=["_time", "_value"])
    mag = df.set_index("_time").sort_index()["_value"].resample("1s").mean().dropna()
    trend = signal.savgol_filter(mag.values, window_length=61, polyorder=3)
    return pd.Series(trend, index=mag.index), mag


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
    def __init__(self, hidden=128, horizon=8):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden, 2, batch_first=True, dropout=0.2)
        self.head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(),
                                   nn.Dropout(0.2), nn.Linear(hidden, horizon))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :])


def train_lstm(series, context, horizon, device):
    v = series.values
    n = len(v)
    te = int(n*0.70); ve = int(n*0.85)
    scaler = MinMaxScaler()
    scaler.fit(v[:te].reshape(-1,1))
    scaled = scaler.transform(v.reshape(-1,1)).flatten()
    tr = TSD(scaled[:te], context, horizon)
    vl = TSD(scaled[te-context:ve], context, horizon)
    ts = TSD(scaled[ve-context:], context, horizon)
    bs = min(64, max(1, len(tr)//4))
    trl = DataLoader(tr, batch_size=bs, shuffle=True, drop_last=len(tr)>bs)
    vll = DataLoader(vl, batch_size=bs, shuffle=False)
    tsl = DataLoader(ts, batch_size=bs, shuffle=False)

    m = LSTM(128, horizon).to(device)
    o = torch.optim.Adam(m.parameters(), lr=1e-3)
    s = torch.optim.lr_scheduler.ReduceLROnPlateau(o, factor=0.5, patience=3)
    c = nn.MSELoss()
    bv = float("inf"); bs_state = None; pc = 0
    for ep in range(EPOCHS):
        m.train()
        for x,y in trl:
            x,y = x.to(device), y.to(device)
            o.zero_grad()
            c(m(x), y).backward()
            nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            o.step()
        m.eval()
        vll_loss, vb = 0., 0
        with torch.no_grad():
            for x,y in vll:
                x,y = x.to(device), y.to(device)
                vll_loss += c(m(x), y).item(); vb += 1
        vll_loss /= max(vb, 1); s.step(vll_loss)
        if vll_loss < bv:
            bv = vll_loss; bs_state = {k: v.cpu().clone() for k,v in m.state_dict().items()}; pc = 0
        else:
            pc += 1
            if pc >= 5: break
    m.load_state_dict(bs_state)

    m.eval()
    pr, ac = [], []
    with torch.no_grad():
        for x,y in tsl:
            pr.append(m(x.to(device)).cpu().numpy()); ac.append(y.numpy())
    pr = np.concatenate(pr); ac = np.concatenate(ac)
    pf = scaler.inverse_transform(pr.reshape(-1,1)).flatten()
    af = scaler.inverse_transform(ac.reshape(-1,1)).flatten()
    mae = float(np.mean(np.abs(af-pf)))

    n_show = min(60, len(pr))
    idx = np.linspace(0, len(pr)-1, n_show, dtype=int)
    p_show = scaler.inverse_transform(pr[idx].reshape(-1,1)).reshape(n_show, horizon)
    a_show = scaler.inverse_transform(ac[idx].reshape(-1,1)).reshape(n_show, horizon)
    return {"mae": mae, "eval_preds": p_show.tolist(), "eval_actuals": a_show.tolist()}


_tfm = None
def load_tfm(context, horizon):
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


def run_tfm(series, context, horizon, n_eval=60):
    tfm = load_tfm(context, horizon)
    v = series.values
    ve = int(len(v) * 0.85)
    test = v[ve-context:]
    stride = max(1, (len(test)-context-horizon) // n_eval)
    ap, aa, sp, sa = [], [], [], []
    for s in range(0, len(test)-context-horizon, stride):
        ctx = test[s:s+context].astype(np.float64)
        fut = test[s+context:s+context+horizon]
        pf, _ = tfm.forecast(horizon=horizon, inputs=[ctx])
        p = pf[0][:len(fut)]
        ap.extend(p.tolist()); aa.extend(fut.tolist())
        sp.append(p.tolist()); sa.append(fut.tolist())
        if len(sp) >= n_eval: break
    mae = float(np.mean(np.abs(np.array(aa) - np.array(ap))))
    return {"mae": mae, "eval_preds": sp, "eval_actuals": sa}


def phase_a(trend):
    print("=" * 60)
    print("  Phase A: 不同 horizon 下的 LSTM 训练")
    print("=" * 60)
    results = {}
    for h in HORIZONS:
        print(f"\nhorizon={h} LSTM 训练...", flush=True)
        t0 = time.time()
        r = train_lstm(trend, CONTEXT, h, DEVICE)
        print(f"  MAE={r['mae']:.4f}  耗时={time.time()-t0:.1f}s")
        results[h] = r
    np.savez(CACHE_PATH, results=json.dumps({str(k): v for k,v in results.items()}))
    return results


def phase_b(trend):
    print("=" * 60)
    print("  Phase B: TimesFM + 出图")
    print("=" * 60)
    if not os.path.exists(CACHE_PATH):
        print("[ERR] 缺缓存"); return
    cache = np.load(CACHE_PATH, allow_pickle=True)
    lstm_res = {int(k): v for k,v in json.loads(str(cache["results"])).items()}

    tfm_res = {}
    for h in HORIZONS:
        print(f"\nhorizon={h} TimesFM...", flush=True)
        tfm_res[h] = run_tfm(trend, CONTEXT, h)
        print(f"  MAE={tfm_res[h]['mae']:.4f}")

    # 合并结果表
    rows = []
    for h in HORIZONS:
        rows.append({
            "horizon": h, "实际秒数": f"{h}秒",
            "LSTM_MAE": round(lstm_res[h]["mae"], 4),
            "TimesFM_MAE": round(tfm_res[h]["mae"], 4),
        })
    df = pd.DataFrame(rows)
    print("\n" + df.to_string(index=False))
    df.to_csv(os.path.join(OUTPUT_DIR, "horizon缩短测试.csv"),
              index=False, encoding="utf-8-sig")

    # ---------- 图: horizon vs 预测效果 ----------
    fig, axes = plt.subplots(len(HORIZONS), 4, figsize=(22, 3.3*len(HORIZONS)))

    for row, h in enumerate(HORIZONS):
        lr = lstm_res[h]
        tr = tfm_res[h]
        actuals = np.array(lr["eval_actuals"])
        # 选 4 个方差最大的正常样例
        seg_mean = actuals.mean(axis=1)
        seg_std = actuals.std(axis=1)
        ok_mask = seg_mean > 0.5
        idx_pool = np.where(ok_mask)[0]
        if len(idx_pool) >= 4:
            sel = idx_pool[np.argsort(-seg_std[idx_pool])[:4]]
        else:
            sel = np.argsort(-seg_std)[:4]

        for col, si in enumerate(sel):
            ax = axes[row, col]
            actual = actuals[si]
            lstm_p = np.array(lr["eval_preds"][si])

            # TFM 最匹配
            ta = np.array(tr["eval_actuals"])
            d = np.mean((ta - actual.reshape(1,-1))**2, axis=1)
            ti = int(np.argmin(d))
            tfm_p = np.array(tr["eval_preds"][ti])

            x = np.arange(len(actual))
            ax.plot(x, actual, color="#2c3e50", linewidth=2.2, label="真实值")
            ax.plot(x, lstm_p, "--", color="#e74c3c", linewidth=1.6, label=f"LSTM")
            if len(tfm_p) == len(actual):
                ax.plot(x, tfm_p, "-.", color="#27ae60", linewidth=1.6, label=f"TFM")
            ax.set_title(f"horizon={h} 样例{col+1}\n真实std={actual.std():.3f}",
                         fontsize=10)
            if col == 0:
                ax.set_ylabel(f"h={h}", fontsize=11, fontweight="bold")
            if row == len(HORIZONS)-1:
                ax.set_xlabel("预测步(秒)", fontsize=9)
            ax.legend(fontsize=8, loc="best")
            ax.grid(True, alpha=0.3)

    mae_line = "  |  ".join([
        f"h={h}: LSTM={lstm_res[h]['mae']:.4f}, TFM={tfm_res[h]['mae']:.4f}"
        for h in HORIZONS
    ])
    fig.suptitle(f"缩短预测窗口测试 (SavGol 趋势信号)\n"
                 f"每行一个 horizon, 每列一个样例 — {mae_line}",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(OUTPUT_DIR, "horizon_1_缩短窗口对比.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("\n[OK] horizon_1_缩短窗口对比.png")

    # MAE vs horizon 曲线
    fig, ax = plt.subplots(figsize=(12, 6))
    lstm_maes = [lstm_res[h]["mae"] for h in HORIZONS]
    tfm_maes = [tfm_res[h]["mae"] for h in HORIZONS]
    ax.plot(HORIZONS, lstm_maes, "-o", color="#e74c3c", linewidth=2,
            markersize=10, label="LSTM")
    ax.plot(HORIZONS, tfm_maes, "-s", color="#27ae60", linewidth=2,
            markersize=10, label="TimesFM")
    for h, m in zip(HORIZONS, lstm_maes):
        ax.text(h, m + 0.003, f"{m:.4f}", ha="center", fontsize=10, color="#c0392b")
    for h, m in zip(HORIZONS, tfm_maes):
        ax.text(h, m - 0.005, f"{m:.4f}", ha="center", fontsize=10, color="#229954")
    ax.set_xlabel("预测窗口 horizon (秒)", fontsize=12)
    ax.set_ylabel("MAE", fontsize=12)
    ax.set_title("预测窗口 vs 预测精度 (SavGol 趋势)\n"
                  "窗口越短，预测越准，但业务价值也越小",
                  fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(HORIZONS)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "horizon_2_MAE曲线.png"),
                dpi=140, bbox_inches="tight")
    plt.close()
    print("[OK] horizon_2_MAE曲线.png")


if __name__ == "__main__":
    print(f"环境: Python {sys.version.split()[0]}, CUDA={HAS_CUDA}")
    trend, mag = load_savgol_trend()
    print(f"SavGol 趋势: {len(trend)} 点, std={trend.std():.3f}")
    print(f"测试 horizons: {HORIZONS}")

    if HAS_CUDA:
        phase_a(trend)
        print("\n[NEXT] 切 py3.11 CPU 跑 Phase B")
    else:
        phase_b(trend)
