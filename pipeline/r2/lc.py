import numpy as np,pandas as pd,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
df=pd.read_pickle('all.pkl'); F=['lN','C','Cp','lscore','align','tanakh']
pids=df.pid.unique()
def fit(d): return make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000)).fit(d[F],d.y)
def thr_for(y,s,target=0.95):
    o=np.argsort(-s); ys=y[o]; prec=np.cumsum(ys)/np.arange(1,len(ys)+1); ok=np.where(prec>=target)[0]
    return s[o][ok.max()]
rs=np.random.RandomState(0)
for k in [15,25,35,45,55,65]:
    res=[]
    for rep in range(60):
        tr_p=rs.choice(pids,k,replace=False); tr=df[df.pid.isin(tr_p)]; te=df[~df.pid.isin(tr_p)]
        if tr.y.nunique()<2: continue
        m=fit(tr); ptr=m.predict_proba(tr[F])[:,1]; t=thr_for(tr.y.values,ptr)
        pte=m.predict_proba(te[F])[:,1]; sel=pte>=t
        prec=(te.y[sel]==1).mean() if sel.sum() else np.nan; rec=(sel&(te.y==1)).sum()/te.y.sum()
        res.append((roc_auc_score(te.y,pte),prec,rec,len(tr)))
    a=np.array(res)
    print(f'{k} passages (~{a[:,3].mean():.0f} pairs): AUC {a[:,0].mean():.3f}  held-out precision {np.nanmean(a[:,1]):.3f} (5th pct {np.nanpercentile(a[:,1],5):.3f})  recall {a[:,2].mean():.2f}')
