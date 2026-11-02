import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
"""Aggregate full-run results into one JSON used by the RDF builder and the graph page."""
import json, pickle, collections, re
from tests import ntext
U = pickle.load(open(ROOT + '/r3/units.pkl', 'rb'))
T = pickle.load(open(ROOT + '/r3/triplets.pkl', 'rb'))
D = {x['key']: x for x in json.load(open(ROOT + '/r3/datings_A.json')) + json.load(open(ROOT + '/r3/datings_B.json'))}
OPP = dict(key='Oppenheim_128', name_he='אופנהיימר 128', name_en='Bodleian MS. Oppenheim Add. 4° 128', date_from=1372, date_to=1400,
           date_he='1372–1400 (לפי המשתמש)', type='כתב יד', region='', sources=[])

def rel(x):
    if x['date_to'] < 1372: return 'before'
    if x['date_from'] > 1400: return 'after'
    return 'overlap'

def folio(pid): return pid.replace('Oppenheimer_128_', '').replace('fol_', 'fol ').replace('_', ' ')

# per-unit closeness tournament
wins = collections.defaultdict(collections.Counter); losses = collections.defaultdict(collections.Counter)
by_unit = collections.defaultdict(list)
for t in T:
    by_unit[t['uid']].append(t)
    if t['verdict'] == 'direct': wins[t['uid']][t['older']] += 1; losses[t['uid']][t['newer']] += 1
    elif t['verdict'] == 'via': wins[t['uid']][t['newer']] += 1; losses[t['uid']][t['older']] += 1

units = []
for u in U:
    ks = [k for k in u['wit'] if k in D]
    if len(ks) == 1: closest = ks
    else: closest = sorted(k for k in ks if wins[u['uid']][k] > 0 and losses[u['uid']][k] == 0)
    earliest = min(ks, key=lambda k: (D[k]['date_from'], D[k]['date_to']))
    units.append(dict(uid=u['uid'], pid=u['pid'], folio=folio(u['pid']), lo=u['lo'], hi=u['hi'],
                      text=' '.join(u['opp'][u['lo']:u['hi'] + 1]),
                      witnesses=[dict(work=k, w=u['wit'][k]['w'], S=round(u['wit'][k]['S'], 2),
                                      segments=[dict(ref=c['ref'], loc=c['loc'], eid=c['eid'], S=c['S']) for c in u['wit'][k]['cands']]) for k in ks],
                      closest=closest, earliest=earliest, n_wit=len(ks)))

def block_text(t, u, kind):
    W = {'opp_O_notM': None, 'opp_M_notO': None}
    out = []
    for b in t['blocks'].get(kind, [])[:3]:
        if kind == 'shared_omission':
            src = u['wit'][t['older']]['src']; out.append(' '.join(src[j] for j in b))
        else:
            out.append(' '.join(u['opp'][i] for i in b))
    return out
Uid = {u['uid']: u for u in U}
hyps = []
for t in T:
    u = Uid[t['uid']]
    hyps.append(dict(uid=t['uid'], older=t['older'], newer=t['newer'], verdict=t['verdict'], via=t['via'], direct=t['direct'],
                     ev={k: int(v) for k, v in t['ev'].items()}, order_certain=bool(t['order_certain']), newer_late=bool(t['newer_late']),
                     ex_O=block_text(t, u, 'opp_O_notM'), ex_M=block_text(t, u, 'opp_M_notO'), ex_om=block_text(t, u, 'shared_omission')))

# work-level
wk = {}
for k, x in D.items():
    xs = [u for u in units if k in [w['work'] for w in u['witnesses']]]
    if not xs: continue
    wk[k] = dict(key=k, name_he=x['name_he'], name_en=x['name_en'], type=x['type'], date_from=x['date_from'], date_to=x['date_to'],
                 date_he=x['date_he'], region=x['region'], region_note=x.get('region_note', ''), confidence=x['confidence'],
                 dispute=x.get('dispute', ''), sources=x['sources'], rel=rel(x),
                 n_units=len(xs), n_pairs=sum(len(w['segments']) for u in xs for w in u['witnesses'] if w['work'] == k),
                 n_only=sum(1 for u in xs if u['n_wit'] == 1),
                 n_closest=sum(1 for u in xs if k in u['closest']),
                 n_closest_sole=sum(1 for u in xs if u['closest'] == [k]),
                 n_earliest=sum(1 for u in xs if u['earliest'] == k and u['n_wit'] > 1),
                 files=sorted({w['w'] for u in xs for w in u['witnesses'] if w['work'] == k}))
pairs = collections.defaultdict(lambda: dict(units=0, via=0, direct=0, undetermined=0, uids=[]))
for h in hyps:
    p = pairs[(h['older'], h['newer'])]; p['units'] += 1; p[h['verdict']] += 1; p['uids'].append(h['uid'])
edges = [dict(older=o, newer=n, order_certain=D[o]['date_to'] < D[n]['date_from'], newer_late=D[n]['date_from'] > 1400, **v)
         for (o, n), v in sorted(pairs.items(), key=lambda kv: -kv[1]['units'])]
out = dict(opp=OPP, works=list(wk.values()), units=units, hypotheses=hyps, edges=edges,
           stats=dict(units=len(units), units_multi=sum(1 for u in units if u['n_wit'] > 1), units_3=sum(1 for u in units if u['n_wit'] > 2),
                      hyps=len(hyps), verdicts=dict(collections.Counter(h['verdict'] for h in hyps)), works=len(wk), edges=len(edges),
                      units_with_closest=sum(1 for u in units if u['n_wit'] > 1 and u['closest'])))
json.dump(out, open(ROOT + '/r3/matryoshka.json', 'w'), ensure_ascii=False)
print(out['stats'])
for w in sorted(wk.values(), key=lambda x: -x['n_units'])[:15]:
    print(f"{w['name_he'][:24]:24s} units {w['n_units']:3d} only {w['n_only']:3d} closest {w['n_closest']:3d} sole {w['n_closest_sole']:3d} earliest {w['n_earliest']:3d} {w['rel']}")
