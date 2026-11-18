"""Model report for the explorer's "המודל" tab: docs/explorer/model_report.json

Reproduces the evaluation of pipeline/r2/final.py without scikit-learn and without touching r2/model.json:
standardised logistic regression with an L2 penalty (C = 1, intercept not penalised), the same features, and
out-of-fold predictions from 20 repeats of 10-fold cross-validation grouped by passage (GroupKFold logic,
same seeds as final.py). The labelled pairs are rebuilt in memory with r2/data.py (the r2/all.pkl pickle no
longer loads in pandas 2.2).

Run from the repo root:  python3 pipeline/r4/model_report.py
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'r2'))
os.environ.setdefault('OPP_ROOT', ROOT)
from data import build  # noqa: E402

F = ['lN', 'C', 'Cp', 'lscore', 'align', 'tanakh']

def fit(X, y, C=1.0, iters=50):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    w = np.zeros(Z.shape[1]); R = np.eye(len(w)) / C; R[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Z @ w))
        g = Z.T @ (p - y) + R @ w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + R
        step = np.linalg.solve(H, g); w -= step
        if np.abs(step).max() < 1e-10: break
    return mu, sd, w

def predict(m, X):
    mu, sd, w = m; return 1 / (1 + np.exp(-(w[0] + ((X - mu) / sd) @ w[1:])))

def group_kfold(groups, k):
    """sklearn GroupKFold (balanced by sample count): largest groups first, each to the lightest fold."""
    uniq, inv = np.unique(groups, return_inverse=True)
    n = np.bincount(inv); order = np.argsort(n)[::-1]
    load = np.zeros(k); fold_of = np.zeros(len(uniq), int)
    for gi in order:
        f = int(np.argmin(load)); load[f] += n[gi]; fold_of[gi] = f
    folds = fold_of[inv]
    return [(np.where(folds != f)[0], np.where(folds == f)[0]) for f in range(k)]

df = build()
X = df[F].astype(float).values; y = df.y.values.astype(float)
P = np.zeros(len(df)); REP = 20
for r in range(REP):
    perm = np.random.RandomState(r).permutation(df.pid.unique())
    g = df.pid.map({p: i for i, p in enumerate(perm)}).values
    for tr, te in group_kfold(g, 10):
        P[te] += predict(fit(X[tr], y[tr]), X[te])
P /= REP
m = fit(X, y); mu, sd, w = m
b = w[1:] / sd; b0 = w[0] - np.sum(w[1:] * mu / sd)
ref = json.load(open(os.path.join(ROOT, 'r2', 'model.json')))
rows = []
for t in [0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]:
    s = P >= t; tp = int((s & (y == 1)).sum())
    rows.append(dict(t=t, n_above=int(s.sum()), tp=tp, precision=round(tp / max(int(s.sum()), 1), 4), recall=round(tp / int(y.sum()), 4)))
out = dict(
    source='pipeline/r4/model_report.py (reproduces pipeline/r2/final.py without scikit-learn)',
    n=int(len(df)), n_pos=int(y.sum()), n_passages=int(df.pid.nunique()),
    features=F, coef=[round(float(x), 4) for x in b], intercept=round(float(b0), 4), std_coef=[round(float(x), 4) for x in w[1:]],
    coef_published=[round(x, 4) for x in ref['b']], intercept_published=round(ref['b0'], 4),
    thr_p=0.8,
    oof=rows,
    labelled=[dict(tid=t, p_oof=round(float(p), 4), y=int(v), tier=tr) for t, p, v, tr in zip(df.tid, P, y, df.tier)],
)
# S at p = 0.8 with the published model: S - (-b0) = ln(4)
out['thr_S'] = round(-ref['b0'] + float(np.log(4)), 2)
json.dump(out, open(os.path.join(ROOT, '..', 'docs', 'explorer', 'model_report.json'), 'w'), ensure_ascii=False)
print('n', out['n'], 'pos', out['n_pos'], 'passages', out['n_passages'])
print('coef (this run)     ', out['coef'], out['intercept'])
print('coef (r2/model.json)', out['coef_published'], out['intercept_published'])
for r in rows: print(r)
