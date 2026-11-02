import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
import json,sys,re
sys.path.insert(0,ROOT + '/r2')
from feats import *
d=load()
pick=json.load(open('pick2.json'))
rows=json.load(open('full_cands.json'))
by={}
for r in rows: by.setdefault(r['pid'],[]).append(r)
pairs=[]; t=219
def mark(words,m,lo,hi):
    out=[]
    for i in range(lo,hi):
        w=words[i]
        if i in m: out.append(f'[{w}]' if m[i] else '{'+w+'}')
        else: out.append(w)
    return ' '.join(out)
for bi,pid in enumerate(pick):
    lines=[f'##### PASSAGE {pid}']
    cs=cands(d[pid]); first=True
    for r in sorted(by[pid],key=lambda x:x['rank']):
        c=cs[r['rank']]; ad=c['alignment_details']; seq=seq_of(ad)
        pt=ad['passage_text'].split(); st=ad['source_text'].split()
        if first: lines.append('OPP FULL: '+' '.join(pt)); lines.append(''); first=False
        pm={}; sm={}
        for p in seq:
            ex=len(p)>3 and str(p[3]).endswith('exact_match')
            pm[int(p[0])]=pm.get(int(p[0]),False) or ex; sm[int(p[1])]=sm.get(int(p[1]),False) or ex
        pi=sorted(pm); si=sorted(sm)
        plo,phi=max(0,pi[0]-8),min(len(pt),pi[-1]+9); slo,shi=max(0,si[0]-40),min(len(st),si[-1]+41)
        tid=f'T{t:03d}'; t+=1
        pairs.append(dict(tid=tid,pid=pid,rank=r['rank'],eid=r['eid'],loc=r['loc']))
        lines.append(f"### {tid} | rank {r['rank']} | {r['loc']}")
        lines.append('OPP: '+('… ' if plo>0 else '')+mark(pt,pm,plo,phi)+(' …' if phi<len(pt) else ''))
        lines.append('SRC: '+('… ' if slo>0 else '')+mark(st,sm,slo,shi)+(' …' if shi<len(st) else ''))
        lines.append('')
    open(f'tb2_{bi:02d}.txt','w').write('\n'.join(lines))
json.dump(pairs,open('pairs2.json','w'),ensure_ascii=False)
print(len(pairs), pairs[-1]['tid'])
