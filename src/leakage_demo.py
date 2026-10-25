"""Demonstratie leakage pe FD001: split aleator pe randuri vs split pe motoare.
Model foarte simplu (k-NN, k=5, numpy) ca sa nu depinda de sklearn; conteaza diferenta, nu valoarea absoluta.
Rulare: python src/leakage_demo.py --data data/raw"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from ingest import *

def knn_rmse(Xtr, ytr, Xva, yva, k=5, chunk=500):
    pred = np.empty(len(Xva)); n2 = (Xtr ** 2).sum(1)
    for i in range(0, len(Xva), chunk):
        q = Xva[i:i+chunk]
        d = (q ** 2).sum(1)[:, None] + n2[None, :] - 2 * q @ Xtr.T
        idx = np.argpartition(d, k, axis=1)[:, :k]
        pred[i:i+chunk] = ytr[idx].mean(1)
    return float(np.sqrt(((pred - yva) ** 2).mean()))

ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data/raw"); ap.add_argument("--subset", default="FD001")
a = ap.parse_args()
tr, te, rul = load_subset(a.data, a.subset)
tr = add_rul(tr, cap=125)
feats = [s for s in SENSORS if s not in flat_sensors(tr, 1)]
Z = regime_normalizer(tr, 1)(tr)
X, y, u = Z[feats].to_numpy(), Z["rul"].to_numpy(), Z["unit"].to_numpy()
res = {"random_rows": [], "by_engine": []}
for seed in range(5):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X)); cut = int(0.8 * len(X))
    tri, vai = perm[:cut], perm[cut:]
    res["random_rows"].append(knn_rmse(X[tri], y[tri], X[vai], y[vai]))
    folds = list(group_split(np.unique(u), 5, seed))
    tr_u, va_u = folds[0]
    m_tr, m_va = np.isin(u, tr_u), np.isin(u, va_u)
    res["by_engine"].append(knn_rmse(X[m_tr], y[m_tr], X[m_va], y[m_va]))
# --- ferestre glisante (W=30), aceleasi seed-uri: ferestrele vecine ale aceluiasi motor se suprapun 29/30 ---
Xw, yw, uw = make_windows(Z, feats, win=30, target="rul")
Xw = Xw.reshape(len(Xw), -1).astype(np.float64)
res["random_windows"], res["by_engine_windows"] = [], []
for seed in range(5):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(Xw)); cut = int(0.8 * len(Xw))
    tri, vai = perm[:cut], perm[cut:]
    res["random_windows"].append(knn_rmse(Xw[tri], yw[tri], Xw[vai], yw[vai]))
    tr_u, va_u = list(group_split(np.unique(uw), 5, seed))[0]
    m_tr, m_va = np.isin(uw, tr_u), np.isin(uw, va_u)
    res["by_engine_windows"].append(knn_rmse(Xw[m_tr], yw[m_tr], Xw[m_va], yw[m_va]))
out = {k: {"rmse_mean": round(float(np.mean(v)), 2), "rmse_std": round(float(np.std(v, ddof=1)), 2), "runs": [round(x, 2) for x in v]} for k, v in res.items()}
out["subset"] = a.subset; out["features"] = feats; out["rul_cap"] = 125; out["model"] = "kNN k=5"
print(json.dumps(out, indent=1))
Path(__file__).parent.parent.joinpath("docs", "leakage_demo.json").write_text(json.dumps(out, indent=1))
