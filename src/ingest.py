"""Ingestie C-MAPSS (FD001-FD004) -- reproductibil, fara dependinte in afara de numpy/pandas.

Utilizare:
    python src/ingest.py --data data/raw            # ruleaza verificarile si tipareste un sumar
    from ingest import load_subset, add_rul, group_split, make_windows

Decizii de design (documentate in docs/data_card.md):
  * RUL de antrenare = (ultimul ciclu al motorului) - ciclu, cu plafon optional (piecewise-linear).
  * Split-ul de validare se face pe MOTOARE (GroupKFold), niciodata pe randuri.
  * Normalizarea se *potriveste* doar pe train (per regim de operare in FD002/FD004).
  * Setul de test oficial: doar ULTIMUL ciclu al fiecarui motor se evalueaza (RUL_FDxxx.txt).
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SETTINGS = ["os1", "os2", "os3"]
SENSORS = [f"s{i}" for i in range(1, 22)]
COLS = ["unit", "cycle"] + SETTINGS + SENSORS
SUBSETS = ["FD001", "FD002", "FD003", "FD004"]


def load_subset(data_dir: str | Path, fd: str):
    """Intoarce (train, test, rul_test). rul_test e indexat dupa unit (1..N)."""
    d = Path(data_dir)
    read = lambda name: pd.read_csv(d / name, sep=r"\s+", header=None, names=COLS)
    train, test = read(f"train_{fd}.txt"), read(f"test_{fd}.txt")
    rul = pd.read_csv(d / f"RUL_{fd}.txt", header=None, names=["rul"])
    rul.index = np.arange(1, len(rul) + 1)
    rul.index.name = "unit"
    return train, test, rul["rul"]


def add_rul(train: pd.DataFrame, cap: int | None = 125) -> pd.DataFrame:
    """Adauga RUL liniar (rul_lin) si, daca cap, RUL cu plafon (rul)."""
    df = train.copy()
    df["rul_lin"] = df.groupby("unit")["cycle"].transform("max") - df["cycle"]
    df["rul"] = df["rul_lin"].clip(upper=cap) if cap else df["rul_lin"]
    return df


def operating_regimes(df: pd.DataFrame, n_regimes: int) -> np.ndarray:
    """Eticheta de regim: 0 pentru conditie unica (FD001/FD003); k-means simplu pe setari altfel."""
    if n_regimes == 1:
        return np.zeros(len(df), dtype=int)
    key = df[SETTINGS].round(0).astype(int).astype(str).agg("_".join, axis=1)
    return pd.factorize(key, sort=True)[0]


def regime_normalizer(train: pd.DataFrame, n_regimes: int, sensors=SENSORS):
    """Potriveste media/std PER REGIM pe train; returneaza functie ce se aplica pe orice df."""
    reg_tr = pd.Series(operating_regimes(train, n_regimes), index=train.index)
    stats = train[sensors].groupby(reg_tr).agg(["mean", "std"])
    # Senzori cuantizati: <=2 valori distincte intr-un regim => z-score ar amplifica un singur salt
    # de cuantizare (ex. s10 in FD002, s16 in FD004: |z|~50). Ii punem pe 0 in acel regim.
    nuniq = train[sensors].groupby(reg_tr).nunique()
    for s in sensors:
        stats.loc[nuniq[s] <= 2, (s, "std")] = np.nan
    key_to_id = {}
    if n_regimes > 1:
        key = train[SETTINGS].round(0).astype(int).astype(str).agg("_".join, axis=1)
        key_to_id = dict(zip(key, reg_tr))

    def apply(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if n_regimes == 1:
            r = np.zeros(len(df), dtype=int)
        else:
            key = df[SETTINGS].round(0).astype(int).astype(str).agg("_".join, axis=1)
            r = key.map(key_to_id).to_numpy()
            if np.isnan(r.astype(float)).any():
                raise ValueError("Regim de operare nevazut la train")
        for s in sensors:
            mu = stats[(s, "mean")].reindex(r).to_numpy()
            sd = stats[(s, "std")].reindex(r).replace(0, np.nan).to_numpy()
            out[s] = (df[s].to_numpy() - mu) / sd
        out[sensors] = out[sensors].fillna(0.0)
        return out

    return apply


def flat_sensors(train: pd.DataFrame, n_regimes: int, tol: float = 1e-6):
    """Senzori fara variatie: global (1 regim) sau in interiorul fiecarui regim (6 regimuri)."""
    reg = operating_regimes(train, n_regimes)
    within = train[SENSORS].groupby(reg).std().max(axis=0)
    return [s for s in SENSORS if within[s] < tol]


def group_split(units: np.ndarray, n_splits: int = 5, seed: int = 0):
    """Fold-uri pe motoare (fara scurgere intre cicluri ale aceluiasi motor)."""
    rng = np.random.default_rng(seed)
    u = np.array(sorted(set(units)))
    rng.shuffle(u)
    folds = np.array_split(u, n_splits)
    for k in range(n_splits):
        va = set(folds[k])
        tr = set(u) - va
        yield sorted(tr), sorted(va)


def make_windows(df: pd.DataFrame, features, win: int = 30, target="rul", last_only=False):
    """Ferestre glisante pe motor. Motoarele mai scurte decat `win` sunt umplute cu primul rand.
    last_only=True -> o fereastra per motor (ultimul ciclu), ca la evaluarea oficiala de test."""
    X, y, u = [], [], []
    for unit, g in df.groupby("unit"):
        a = g[features].to_numpy(dtype=np.float32)
        t = g[target].to_numpy() if target in g else np.full(len(g), np.nan)
        if len(a) < win:
            a = np.vstack([np.repeat(a[:1], win - len(a), axis=0), a])
            t = np.concatenate([np.full(win - len(t), t[0]), t])
        rng = [len(a) - 1] if last_only else range(win - 1, len(a))
        for i in rng:
            X.append(a[i - win + 1 : i + 1]); y.append(t[i]); u.append(unit)
    return np.stack(X), np.asarray(y), np.asarray(u)


def checks(data_dir: str | Path):
    """Verificari de integritate + anti-leakage. Ridica AssertionError la orice problema."""
    rows = []
    for fd in SUBSETS:
        tr, te, rul = load_subset(data_dir, fd)
        assert tr.isna().sum().sum() == 0 and te.isna().sum().sum() == 0, f"{fd}: valori lipsa"
        assert not tr.duplicated().any() and not te.duplicated().any(), f"{fd}: duplicate"
        for name, d in (("train", tr), ("test", te)):
            assert d.groupby("unit")["cycle"].apply(lambda c: (c.values == np.arange(1, len(c) + 1)).all()).all(), \
                f"{fd} {name}: cicluri necontigue"
        assert len(rul) == te["unit"].nunique(), f"{fd}: RUL != nr. motoare test"
        assert set(rul.index) == set(te["unit"].unique()), f"{fd}: id-uri RUL != id-uri test"
        # motoarele train si test sunt flote distincte care se numeroteaza de la 1: id-ul NU e cheie comuna
        n_reg = 1 if fd in ("FD001", "FD003") else 6
        # leakage: normalizare potrivita doar pe train; fold-uri disjuncte pe motoare
        for a, b in group_split(tr["unit"].unique(), 5, 0):
            assert not set(a) & set(b)
        norm = regime_normalizer(tr, n_reg)
        z = norm(tr)
        flat = flat_sensors(tr, n_reg)
        rows.append(dict(subset=fd, train_units=tr.unit.nunique(), test_units=te.unit.nunique(),
                         train_rows=len(tr), test_rows=len(te), flat_sensors=",".join(flat) or "-",
                         max_abs_z=float(z[SENSORS].abs().max().max().round(1))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw")
    a = ap.parse_args()
    print(checks(a.data).to_string(index=False))
    print("OK: toate verificarile au trecut")
