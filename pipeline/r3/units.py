import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
"""Build text units (clusters of above-threshold witnesses aligned to the same Oppenheim tokens)."""
import json, re, sys, pickle, collections
import pandas as pd
sys.path.insert(0, ROOT + '/r2')
from feats import load, cands, seq_of

DATE_KEY = {'Ruth_Rabbah_Lerner': 'Ruth_Rabbah'}
BAVLI = {'Sanhedrin', 'Gittin', 'Taanit', 'Menachot', 'Shabbat', 'Bava_Batra', 'Arakhin', 'Sukkah', 'Berakhot', 'Yevamot',
         'Chagigah', 'Yoma', 'Pesachim', 'Ketubot', 'Makkot'}

def date_key(w, loc):
    if w.startswith('Jerusalem_Talmud'): return 'Jerusalem_Talmud'
    if w in BAVLI or loc.startswith('Talmud_Bavli'): return 'Babylonian_Talmud'
    return DATE_KEY.get(w, w)

def ref_tuple(w, ref):
    words = tuple(x for x in ref.split() if not x.isdigit())
    nums = tuple(int(x) for x in re.findall(r'\d+', ref))
    return (w,) + words, nums

def build():
    d = load()
    L = pd.read_pickle(ROOT + '/r3/lists.pkl'); up = L['up']
    units = []
    for pid, g in sorted(up.groupby('pid'), key=lambda x: x[1].fk.iloc[0]):
        pt = cands(d[pid])[0]['alignment_details']['passage_text'].split()
        items = []
        for r in g.itertuples():
            c = cands(d[pid])[r.rank]; ad = c['alignment_details']; seq = seq_of(ad)
            amap = {}
            for p in seq:
                i, j = int(p[0]), int(p[1]); ex = len(p) > 3 and str(p[3]).endswith('exact_match')
                if i not in amap or (ex and not amap[i][1]): amap[i] = (j, ex)
            items.append(dict(rank=r.rank, w=r.w, dk=date_key(r.w, r.loc), work=r.work, loc=r.loc, ref=r.ref, S=float(r.S), eid=r.eid,
                              src=ad['source_text'].split(), amap=amap, O=set(amap)))
        clusters = []
        for it in sorted(items, key=lambda x: -len(x['O'])):
            for cl in clusters:
                if len(it['O'] & cl['O']) / min(len(it['O']), len(cl['O'])) >= 0.5:
                    cl['items'].append(it); cl['O'] |= it['O']; break
            else:
                clusters.append(dict(items=[it], O=set(it['O'])))
        clusters.sort(key=lambda c: min(c['O']))
        for k, cl in enumerate(clusters, 1):
            wit = {}
            by = collections.defaultdict(list)
            for it in cl['items']: by[it['dk']].append(it)
            for dk, its in by.items():
                # several editions/tractates of one dated work: keep the variant (w) with the best S; merge segments of that w
                bestw = max(its, key=lambda x: x['S'])['w']
                segs = sorted([x for x in its if x['w'] == bestw], key=lambda x: ref_tuple(x['w'], x['ref']))
                src, amap, off, refs = [], {}, 0, []
                for s in segs:
                    for i, (j, ex) in s['amap'].items():
                        if i not in amap or (ex and not amap[i][1]): amap[i] = (j + off, ex)
                    src += s['src']; off += len(s['src']); refs.append(ref_tuple(s['w'], s['ref']))
                wit[dk] = dict(w=bestw, work=segs[0]['work'], cands=[dict(rank=s['rank'], loc=s['loc'], ref=s['ref'], S=round(s['S'], 2), eid=s['eid']) for s in segs],
                               src=src, amap=amap, refs=refs, S=max(s['S'] for s in segs))
            units.append(dict(uid=f"{pid.replace('Oppenheimer_128_', '')}#u{k}", pid=pid, fk=g.fk.iloc[0], opp=pt,
                              lo=min(cl['O']), hi=max(cl['O']), O=sorted(cl['O']), wit=wit))
    return units

if __name__ == '__main__':
    U = build()
    pickle.dump(U, open(ROOT + '/r3/units.pkl', 'wb'))
    n = collections.Counter(min(len(u['wit']), 5) for u in U)
    print('units', len(U), sorted(n.items()))
