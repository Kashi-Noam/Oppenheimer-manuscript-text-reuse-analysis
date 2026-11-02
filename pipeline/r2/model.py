import numpy as np,pandas as pd,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score,average_precision_score
df=pd.read_pickle('all.pkl')
SETS={
 'C only':['C'],'N only':['lN'],
 'small: N,C,Cp':['lN','C','Cp'],
 'mid: N,C,Cp,score,align,tanakh':['lN','C','Cp','lscore','align','tanakh'],
 'full':['lN','C','Cp','lscore','align','tanakh','lLb','lgroups','D','sim','exact','norm','rank','lplen','lslen'],
}
def oof(feats,Cr=1.0,reps=10):
    P=np.zeros(len(df))
    for r in range(reps):
        g=df.pid.map({p:i for i,p in enumerate(np.random.RandomState(r).permutation(df.pid.unique()))})
        for tr,te in GroupKFold(10).split(df,df.y,g):
            m=make_pipeline(StandardScaler(),LogisticRegression(C=Cr,max_iter=2000)).fit(df.iloc[tr][feats],df.y.iloc[tr])
            P[te]+=m.predict_proba(df.iloc[te][feats])[:,1]
    return P/reps
def recall_at_prec(y,s,target):
    o=np.argsort(-s); ys=y[o]; tp=np.cumsum(ys); prec=tp/np.arange(1,len(ys)+1)
    ok=np.where(prec>=target)[0]
    return (tp[ok.max()]/ys.sum(), s[o][ok.max()]) if len(ok) else (0,None)
y=df.y.values
for name,f in SETS.items():
    p=oof(f)
    r95,_=recall_at_prec(y,p,0.95); r98,_=recall_at_prec(y,p,0.98)
    print(f'{name:35s} AUC {roc_auc_score(y,p):.3f} AP {average_precision_score(y,p):.3f} recall@95%prec {r95:.2f} @98% {r98:.2f}')
# round1 -> round2 test
for name,f in SETS.items():
    tr=df[df['round']==1]; te=df[df['round']==2]
    m=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000)).fit(tr[f],tr.y)
    p=m.predict_proba(te[f])[:,1]
    print(f'R1->R2 {name:30s} AUC {roc_auc_score(te.y,p):.3f}')
te=df[df['round']==2]
for f,t in [('C',0.252),('lN',np.log1p(33)),('Cp',0.18)]:
    pr=te[f]>=t; tp=(pr&(te.y==1)).sum()
    print(f'R1 single threshold {f}>={t:.3f} on R2: precision {tp/pr.sum():.2f} recall {tp/te.y.sum():.2f}')
