import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.abspath(__file__)))  # = pipeline/
import json, csv, re, glob, sys, statistics as st, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + '/r2')
from below import CAUSES, BELOW
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

exec(open(ROOT + '/build_report_data.py').read().split('out_pairs = []')[0]
     .replace("m = json.load(open('metrics.json'))", "").replace("cap = {c['tid']: c for c in json.load(open('captured.json'))}", "")
     .replace("pairs = json.load(open('pairs.json'))", "").replace("L = {r[0]: r for r in csv.reader(open('labels.tsv'), delimiter='\\t')}", ""))

df = pd.read_pickle(ROOT + '/r2/diag2.pkl')
M = json.load(open(ROOT + '/r2/model.json'))
cap = {c['tid']: c for c in json.load(open(ROOT + '/captured.json')) + json.load(open(ROOT + '/r2/captured2.json'))}
for f in sorted(glob.glob(ROOT + '/r2/tb2_*.txt')):
    pid = None
    for line in open(f):
        if line.startswith('##### PASSAGE'): pid = line.split()[-1]
        elif line.startswith('OPP FULL:') and pid: opp[pid] = line[len('OPP FULL:'):].strip()

THR_P = 0.8; THR_S = float(np.log(THR_P / (1 - THR_P)) - M['b0'])
def S_of(r):
    return sum(b * float(r[f]) for f, b in zip(M['F'], M['b']))

def fkey(pid):
    m = re.match(r'Oppenheimer_128_fol_(\d+)([rv])_(\d+)$', pid); return (int(m.group(1)), m.group(2) == 'v', int(m.group(3)))

out_pairs = []
for _, r in df.sort_values(['pid', 'rank'], key=lambda s: s.map(fkey) if s.name == 'pid' else s).iterrows():
    t = r['tid']; work, ref = parse_loc(r['loc'])
    S = S_of(r); p = float(r['p'])
    rescue_htr = bool(0.2 <= p < THR_P and r['oov'] >= 0.18)
    rescue_split = bool(0.2 <= p < THR_P and r['Cp_work'] >= 0.4 and r['nseg_work'] >= 2)
    b = BELOW.get(t)
    out_pairs.append(dict(
        tid=t, rnd=int(r['round']), pid=r['pid'], folio=folio(r['pid']), rank=int(r['rank']), eid=r['eid'], loc=r['loc'], work=work, ref=ref,
        score=round(float(r['score']), 2), norm=round(float(r['norm']), 4), align=round(float(r['align']), 4), full=int(r['full']),
        N=int(r['N']), L_p=int(r['L_p']), L_both=int(r['L_both']), groups=int(r['groups']), span=int(r['span']), D=round(float(r['D']), 3),
        C=round(float(r['C']), 3), Cp=round(float(r['Cp']), 3), sim=round(float(r['sim']), 3), exact=round(float(r['exact']), 3),
        p_len=int(r['p_len']), s_len=int(r['s_len']), oov=round(float(r['oov']), 3), Cp_work=round(float(r['Cp_work']), 3), nseg_work=int(r['nseg_work']),
        S=round(S, 2), p=round(p, 3), above=p >= THR_P, rescue=('HTR' if rescue_htr else '') + ('+' if rescue_htr and rescue_split else '') + ('איחוד' if rescue_split else ''),
        rel=r['rel'], conf=r['conf'], note=r['note'], tier=r['tier'],
        cause=(dict(main=b[0], second=b[1], text=b[2]) if b else None),
        shot=f'shots/{t}.jpg'))

seen = []
for p in out_pairs:
    if p['pid'] not in seen: seen.append(p['pid'])
passages = [dict(pid=pid, folio=folio(pid), text=opp.get(pid, ''), n=sum(q['pid'] == pid for q in out_pairs),
                 rnd=next(q['rnd'] for q in out_pairs if q['pid'] == pid)) for pid in seen]

REL_ORDER = ['אותו טקסט', 'אותו טקסט · חלקי', 'נוסח מקביל', 'אותו חיבור · קטע אחר', 'דרשה על המקור',
             'ציטוט פסוק מהמקור', 'ציטוט משותף', 'אין קשר']
summ = []
for rl in REL_ORDER:
    g = [p for p in out_pairs if p['rel'] == rl]
    if not g: continue
    row = dict(rel=rl, n=len(g), tier=TIER[rl], conf={k: sum(p['conf'] == k for p in g) for k in ['גבוהה', 'בינונית', 'נמוכה']},
               above=sum(p['above'] for p in g))
    for f in ['N', 'C', 'Cp', 'score', 'align', 'S', 'p']:
        xs = sorted(p[f] for p in g); row[f] = [xs[0], st.median(xs), xs[-1]]
    summ.append(row)

# performance (out-of-fold, grouped by passage)
y = df.y.values; po = df.p_oof.values
perf = []
rs = np.random.RandomState(1); pids = df.pid.unique()
idxs = [np.where(df.pid.values == q)[0] for q in pids]
for t in [0.5, 0.7, 0.8, 0.9]:
    s = po >= t; tp = (s & (y == 1)).sum()
    B = []
    for _ in range(2000):
        ii = np.concatenate([idxs[k] for k in rs.randint(0, len(pids), len(pids))]); ss = po[ii] >= t; yy = y[ii]
        B.append(((ss & (yy == 1)).sum() / max(ss.sum(), 1), (ss & (yy == 1)).sum() / yy.sum()))
    B = np.array(B)
    perf.append(dict(t=t, S=round(float(np.log(t / (1 - t)) - M['b0']), 2), prec=round(tp / s.sum(), 3), rec=round(tp / y.sum(), 3),
                     prec_ci=[round(float(np.percentile(B[:, 0], 2.5)), 3), round(float(np.percentile(B[:, 0], 97.5)), 3)],
                     rec_ci=[round(float(np.percentile(B[:, 1], 2.5)), 3), round(float(np.percentile(B[:, 1], 97.5)), 3)], n=int(s.sum())))
# R1 -> R2
F = M['F']; tr = df[df['round'] == 1]; te = df[df['round'] == 2]
m1 = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(tr[F], tr.y); p2 = m1.predict_proba(te[F])[:, 1]
s = p2 >= THR_P; tp = (s & (te.y == 1)).sum()
r1r2 = dict(prec=round(tp / s.sum(), 3), rec=round(tp / te.y.sum(), 3), n=int(s.sum()), A=int(te.y.sum()))
# rescue effect
base = po >= THR_P
resc = (po >= 0.2) & (po < THR_P) & ((df.oov.values >= 0.18) | ((df.Cp_work.values >= 0.4) & (df.nseg_work.values >= 2)))
def pr(sel): tp = (sel & (y == 1)).sum(); return dict(prec=round(tp / sel.sum(), 3), rec=round(tp / y.sum(), 3), n=int(sel.sum()))
rescue = dict(base=pr(base), plus=pr(base | resc))
# all candidates in the report
allc = pd.read_pickle(ROOT + '/r2/allc_scored.pkl')
population = dict(full=int(len(allc)), above=int((allc.p >= THR_P).sum()), passages_above=int(allc[allc.p >= THR_P].pid.nunique()), passages=505)

model = dict(F=F, b=[round(v, 3) for v in M['b']], b0=round(M['b0'], 3), std=[round(v, 2) for v in M['std_coef']], thr_p=THR_P, thr_S=round(THR_S, 2))
lc = [dict(k=15, n=90, prec=0.906, p5=0.686, rec=0.93), dict(k=25, n=150, prec=0.924, p5=0.744, rec=0.93), dict(k=35, n=211, prec=0.940, p5=0.859, rec=0.93),
      dict(k=45, n=276, prec=0.946, p5=0.846, rec=0.92), dict(k=55, n=334, prec=0.935, p5=0.830, rec=0.93), dict(k=65, n=397, prec=0.945, p5=0.830, rec=0.95)]
causes = {k: dict(name=v[0], why=v[1], fix=v[2], n=sum(1 for b in BELOW.values() if b[0] == k)) for k, v in CAUSES.items()}
fp = [dict(tid=p['tid'], rel=p['rel'], p=p['p'], note=p['note']) for p in out_pairs if p['above'] and p['tier'] != 'A']

json.dump(dict(passages=passages, pairs=out_pairs, summary=summ, rel_order=REL_ORDER, model=model, perf=perf, r1r2=r1r2,
               rescue=rescue, population=population, lc=lc, causes=causes, fp=fp),
          open(ROOT + '/report/data.json', 'w'), ensure_ascii=False)
print(len(passages), len(out_pairs), 'thr_S', round(THR_S, 2)); print(perf); print(r1r2, rescue, population)
print('below A', sum(1 for p in out_pairs if p['tier'] == 'A' and not p['above']), 'explained', len(BELOW))
print('missing text', [p['pid'] for p in passages if not p['text']])
