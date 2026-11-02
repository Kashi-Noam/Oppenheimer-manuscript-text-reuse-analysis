import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
import json, pickle, re, sys, collections, os
import pandas as pd
sys.path.insert(0, ROOT + '/r2'); sys.path.insert(0, ROOT + '/r3')
from feats import load, cands, seq_of
from units import date_key, ref_tuple
OUT = ROOT + '/r3/gui'; os.makedirs(OUT, exist_ok=True)
d = load()
L = pd.read_pickle(ROOT + '/r3/lists.pkl'); allc = L['allc']
lab = pd.read_pickle(ROOT + '/r2/diag2.pkl')[['pid', 'rank', 'tid', 'rel', 'conf', 'note', 'tier']]
allc = allc.drop(columns=[c for c in ['tid', 'rel'] if c in allc.columns]).merge(lab, on=['pid', 'rank'], how='left')
J = json.load(open(ROOT + '/r3/matryoshka.json'))
U = pickle.load(open(ROOT + '/r3/units.pkl', 'rb')); T = pickle.load(open(ROOT + '/r3/triplets.pkl', 'rb'))
M = json.load(open(ROOT + '/r2/model.json'))

def fkey(pid):
    m = re.match(r'Oppenheimer_128_fol_(\d+)([rv])_(\d+)$', pid)
    return (int(m.group(1)), m.group(2) == 'v', int(m.group(3))) if m else (-1, False, 0)
def folio(pid): return pid.replace('Oppenheimer_128_', '').replace('fol_', 'fol ').replace('_', ' ').replace('Upper cover', 'כריכה עליונה')

pids = sorted([p for p in d if cands(d[p])], key=fkey) + sorted([p for p in d if not cands(d[p])], key=fkey)
passages, ptext = [], {}
for p in pids:
    cs = cands(d[p]); tok = ''
    for c in cs:
        ad = c.get('alignment_details') or {}
        if ad.get('passage_text'): tok = ad['passage_text']; break
    ptext[p] = tok
    passages.append(dict(pid=p, folio=folio(p), n_cand=len(cs), n_full=int(sum(1 for c in cs if c.get('full_alignment_ind') == 1))))

cand_meta, ctext = [], {}
for r in allc.sort_values(['fk', 'rank']).itertuples():
    cid = f'{r.pid}|{r.rank}'
    c = cands(d[r.pid])[r.rank]; ad = c['alignment_details']; seq = seq_of(ad)
    al = {}
    for q in seq:
        i, j = int(q[0]), int(q[1]); ex = 1 if (len(q) > 3 and str(q[3]).endswith('exact_match')) else 0
        if i not in al or (ex and not al[i][2]): al[i] = [i, j, ex]
    ctext[cid] = dict(src=ad['source_text'], al=sorted(al.values()))
    m = dict(id=cid, pid=r.pid, rank=int(r.rank), w=r.w, k=date_key(r.w, r.loc), work=r.work, ref=r.ref, loc=r.loc, eid=r.eid,
             S=round(float(r.S), 2), p=round(float(r.p), 3), above=bool(r.p >= 0.8), N=int(r.N), C=round(float(r.C), 3), Cp=round(float(r.Cp), 3),
             score=round(float(r.score), 1), align=round(float(r.align), 3), norm=round(float(r.norm), 3))
    if isinstance(r.tid, str): m.update(tid=r.tid, rel=r.rel, conf=r.conf, note=r.note, tier=r.tier)
    cand_meta.append(m)

# units with ordered candidate ids per witness
units = []
for u in U:
    wit = []
    for k, w in u['wit'].items():
        ids = [f"{u['pid']}|{c['rank']}" for c in w['cands']]
        wit.append(dict(k=k, ids=ids, S=round(w['S'], 2)))
    ju = next(x for x in J['units'] if x['uid'] == u['uid'])
    units.append(dict(uid=u['uid'], pid=u['pid'], lo=u['lo'], hi=u['hi'], wit=wit, closest=ju['closest'], earliest=ju['earliest']))
comps = []
for t in T:
    comps.append(dict(uid=t['uid'], o=t['older'], n=t['newer'], v=t['verdict'], sv=t['via'], sd=t['direct'],
                      ev={k: int(v) for k, v in t['ev'].items()}, oc=bool(t['order_certain']), nl=bool(t['newer_late']),
                      b={k: v for k, v in t['blocks'].items()}))
works = []
for w in J['works']:
    works.append({k: w[k] for k in ['key', 'name_he', 'name_en', 'type', 'date_from', 'date_to', 'date_he', 'region', 'region_note', 'confidence', 'dispute', 'rel', 'n_units', 'n_only', 'n_closest', 'n_earliest', 'files', 'sources']})
core = dict(model=dict(F=M['F'], b=M['b'], b0=M['b0'], thr_S=21.14), stats=J['stats'], works=works, edges=J['edges'], units=units, comps=comps,
            passages=passages, cands=cand_meta, opp=J['opp'])
json.dump(core, open(f'{OUT}/core.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(dict(p=ptext, c=ctext), open(f'{OUT}/texts.json', 'w'), ensure_ascii=False, separators=(',', ':'))
for f in ['core.json', 'texts.json']: print(f, round(os.path.getsize(f'{OUT}/{f}') / 1e6, 2), 'MB')
print(len(passages), 'passages', len(cand_meta), 'cands', len(units), 'units', len(comps), 'comps', sum(1 for c in cand_meta if 'tid' in c), 'labeled')
