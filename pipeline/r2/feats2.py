import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
import json,re,sys,numpy as np,pandas as pd
sys.path.insert(0,ROOT + '/r2'); from feats import *
def work_of(loc):
    if 'RAVKOOK_' in loc:
        m=re.match(r'(.*RAVKOOK_[A-Za-z]+)',loc); return m.group(1)
    return loc.split('_Sefaria_')[0].split('-Sefaria_')[0]
def passage_sets(d,pid):
    out=[]
    for r,c in enumerate(cands(d[pid])):
        if c.get('full_alignment_ind')!=1: continue
        ad=c['alignment_details']; seq=seq_of(ad)
        out.append(dict(rank=r,work=work_of(c.get('location','')),S={int(p[0]) for p in seq},p_len=len(ad['passage_text'].split())))
    return out
def extra(d,pid,rank):
    ps=passage_sets(d,pid); me=[x for x in ps if x['rank']==rank][0]
    U=set().union(*[x['S'] for x in ps if x['work']==me['work']])
    wit=set()
    for x in ps:
        if x['work']!=me['work'] and len(me['S']) and len(me['S']&x['S'])/len(me['S'])>=0.5: wit.add(x['work'])
    nseg=sum(1 for x in ps if x['work']==me['work'])
    return dict(N_work=len(U),Cp_work=len(U)/me['p_len'],n_wit=len(wit),nseg_work=nseg)
if __name__=='__main__':
    d=load(); df=pd.read_pickle(ROOT + '/r2/diag.pkl')
    ex=pd.DataFrame([extra(d,p,r) for p,r in zip(df.pid,df['rank'])],index=df.index)
    df=pd.concat([df.drop(columns=[c for c in ex.columns if c in df.columns]),ex],axis=1)
    df['lNw']=np.log1p(df.N_work); df['lwit']=np.log1p(df.n_wit)
    df.to_pickle(ROOT + '/r2/diag2.pkl')
    for g,name in [(df.y==1,'A'),(df.rel=='ציטוט משותף','shared quote'),(df.rel=='ציטוט פסוק מהמקור','verse'),(df.rel=='אין קשר','none')]:
        print(f'{name:12s} n_wit median {df[g].n_wit.median():.0f}  Cp_work median {df[g].Cp_work.median():.2f}  nseg_work median {df[g].nseg_work.median():.0f}')
    low=(df.y==1)&(df.p<0.8)
    print(df[low][['tid','N','N_work','Cp','Cp_work','n_wit','nseg_work']].to_string())
