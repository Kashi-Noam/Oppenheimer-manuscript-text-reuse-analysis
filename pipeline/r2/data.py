import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
import json,csv,sys,numpy as np,pandas as pd
sys.path.insert(0,ROOT + '/r2')
from feats import *
TIER={'אותו טקסט':'A','אותו טקסט · חלקי':'A','נוסח מקביל':'B','אותו חיבור · קטע אחר':'C','דרשה על המקור':'C','ציטוט פסוק מהמקור':'C','ציטוט משותף':'C','אין קשר':'D'}
def build():
    d=load()
    p1=json.load(open(ROOT + '/pairs.json')); p2=json.load(open(ROOT + '/r2/pairs2.json'))
    L={}
    for f in [ROOT + '/labels.tsv',ROOT + '/r2/labels2.tsv']:
        for r in csv.reader(open(f),delimiter='\t'): L[r[0]]=r
    rows=[]
    for rnd,P in ((1,p1),(2,p2)):
        for p in P:
            c=cands(d[p['pid']])[p['rank']]; m=metrics(c)
            lab=L[p['tid']]
            m.update(tid=p['tid'],pid=p['pid'],rank=p['rank'],eid=p['eid'],loc=p['loc'],round=rnd,rel=lab[1],conf=lab[2],note=lab[3],tier=TIER[lab[1]])
            rows.append(m)
    df=pd.DataFrame(rows)
    df['y']=(df.tier=='A').astype(int)
    df['tanakh']=df['loc'].str.startswith('Tanakh').astype(int)
    df['lN']=np.log1p(df.N); df['lscore']=np.log1p(df.score.astype(float)); df['lgroups']=np.log1p(df.groups)
    df['lplen']=np.log(df.p_len); df['lslen']=np.log(df.s_len); df['lLb']=np.log1p(df.L_both)
    df['N_per_group']=df.N/df.groups
    return df
if __name__=='__main__':
    df=build(); df.to_pickle(ROOT + '/r2/all.pkl'); print(df.shape, df.groupby('round').y.agg(['count','sum']))
