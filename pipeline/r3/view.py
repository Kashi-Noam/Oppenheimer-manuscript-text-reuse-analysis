import pickle,sys
U={u['uid']:u for u in pickle.load(open('units.pkl','rb'))}
P=pickle.load(open('pilot.pkl','rb'))
from tests import wit_align
def snip(tokens,idxs,maxw=40):
    s=sorted(idxs); return ' '.join(tokens[i] for i in s[:maxw])+(' …' if len(s)>maxw else '')
for n in map(int,sys.argv[1:]):
    t=P[n-1]; u=U[t['uid']]; O=u['wit'][t['older']]; M=u['wit'][t['newer']]
    print(f"===== #{n} {t['uid']} OLD={t['older']} {O['cands'][0]['ref']} | NEW={t['newer']} {M['cands'][0]['ref']} | {t['verdict']} via={t['via']} direct={t['direct']} {t['ev']}")
    print('OPP unit:',' '.join(u['opp'][u['lo']:u['hi']+1])[:300])
    for k,lab in [('opp_O_notM','Opp+OLD, חסר ב-NEW'),('opp_M_notO','Opp+NEW, חסר ב-OLD')]:
        for b in t['blocks'].get(k,[])[:4]: print(f'  [{lab}]',snip(u['opp'],b))
    for b in t['blocks'].get('shared_omission',[])[:3]: print('  [OLD בלבד – חסר ב-Opp וב-NEW]',snip(O['src'],b,25))
