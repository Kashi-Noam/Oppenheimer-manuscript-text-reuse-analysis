import json,re,sys,collections,numpy as np,pandas as pd
sys.path.insert(0,'.'); from feats import *
d=load(); df=pd.read_pickle('scored.pkl')
# vocabulary from all source texts
voc=collections.Counter()
for pid,v in d.items():
    for c in cands(v):
        ad=c.get('alignment_details') or {}
        voc.update((ad.get('source_text') or '').split())
def oov(pid):
    c=cands(d[pid])[0]; pt=(c.get('alignment_details') or {}).get('passage_text','').split()
    return sum(1 for w in pt if voc[w]<3)/len(pt)
pass_oov={p:oov(p) for p in df.pid.unique()}
allp={p:oov(p) for p in d if cands(d[p]) and (cands(d[p])[0].get('alignment_details') or {}).get('passage_text')}
df['oov']=df.pid.map(pass_oov)
def geo(r):
    c=cands(d[r.pid])[r['rank']]; ad=c['alignment_details']; seq=seq_of(ad)
    pi=sorted({int(p[0]) for p in seq}); si=sorted({int(p[1]) for p in seq})
    s_len=len(ad['source_text'].split()); p_len=len(ad['passage_text'].split())
    return pd.Series(dict(s_first=si[0],s_last=si[-1],p_first=pi[0],p_last=pi[-1],
        edge_s=(si[0]<=3) or (si[-1]>=s_len-4), edge_p=(pi[0]<=3) or (pi[-1]>=p_len-4),
        sspan_frac=(si[-1]-si[0]+1)/s_len, pspan_frac=(pi[-1]-pi[0]+1)/p_len,
        Dloc=len(pi)/max(pi[-1]-pi[0]+1, si[-1]-si[0]+1)))
df=pd.concat([df,df.apply(geo,axis=1)],axis=1)
# sibling: another full candidate of the same work in same passage, labeled A
def work(loc): return re.sub(r'_\d+(_\d+)*$','',re.sub(r'(_Ot)?_\d+$','',loc))
df['work']=df['loc'].map(lambda l: re.split(r'_Sefaria_',l)[0])
sib=df[df.y==1].groupby(['pid','work']).size()
df['n_same_work_A']=[sib.get((p,w),0) for p,w in zip(df.pid,df.work)]
df.to_pickle('diag.pkl')
print('OOV: labeled passages median',np.median(list(pass_oov.values())).round(3),' all passages median',np.median(list(allp.values())).round(3), 'p90',np.percentile(list(allp.values()),90).round(3))
low=df[(df.y==1)&(df.p<0.8)]
hi=df[(df.y==1)&(df.p>=0.8)]
for k in ['oov','edge_s','edge_p','sspan_frac','pspan_frac','Dloc','exact','sim','s_len']:
    print(f'{k:10s} A-below {low[k].astype(float).median():.3f}   A-above {hi[k].astype(float).median():.3f}')
print(low.groupby('pid').size().sort_values(ascending=False).head(10))
print(df.groupby('pid').oov.first().sort_values(ascending=False).head(8))
