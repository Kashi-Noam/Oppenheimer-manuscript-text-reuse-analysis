"""Raw ACT data for the explorer: docs/explorer/act_raw.json

Every candidate ACT returned for every passage (up to 30 each), as ACT gave it, in ACT's order:
rank, location, elastic id, ACT score, norm_score, alignment_score, full_alignment_ind, collection, search
field, and the first words of the source window. The explorer otherwise shows only the 2,650 candidates with
a full alignment. Run from the repo root:  python3 pipeline/r4/act_raw.py
"""
import os, sys, json, ast
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'r2'))
from feats import load, cands  # noqa: E402

def f(x):
    try: return None if x in (None, 'None', '') else round(float(x), 4)
    except (TypeError, ValueError): return None

R = load()
order = [p['pid'] for p in json.load(open(os.path.join(ROOT, '..', 'docs', 'explorer', 'core.json')))['passages']]
cols = ['rank', 'loc', 'eid', 'score', 'norm', 'align', 'full', 'snippet', 'words']
out = {'source': 'data/raw/tr_report_288c1011-282d-4644-9959-2f1b093a6b33.json.gz', 'cols': cols, 'p': {}, 'meta': {}}
n = 0
for pid in order:
    e = R[pid]; rows = []
    for i, c in enumerate(cands(e)):
        ad = c.get('alignment_details') or {}
        if isinstance(ad, str): ad = ast.literal_eval(ad)
        src = (ad.get('source_text') or '').split()
        rows.append([i, c.get('location') or ad.get('location'), c.get('elastic_id'), f(ad.get('score')), f(c.get('norm_score')),
                     f(c.get('alignment_score')), int(c.get('full_alignment_ind') in (1, '1')), ' '.join(src[:14]), len(src)])
        n += 1
    out['p'][pid] = rows
    ad0 = next(((cc.get('alignment_details') or {}) for cc in cands(e)), {})
    if isinstance(ad0, str): ad0 = ast.literal_eval(ad0)
    out['meta'][pid] = {'job_id': e.get('job_id'), 'Location': e.get('Location'), 'collection': ad0.get('collection'),
                        'search_index': ad0.get('search_index'), 'search_fields': ad0.get('search_fields'), 'alignment_field': ad0.get('alignment_field')}
path = os.path.join(ROOT, '..', 'docs', 'explorer', 'act_raw.json')
json.dump(out, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
print(n, 'candidates in', len(order), 'passages ->', path, round(os.path.getsize(path) / 1e6, 2), 'MB')
