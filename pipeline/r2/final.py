import numpy as np,pandas as pd,json,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
df=pd.read_pickle('all.pkl'); F=['lN','C','Cp','lscore','align','tanakh']
mk=lambda: make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000))
P=np.zeros(len(df)); R=20
for r in range(R):
    g=df.pid.map({p:i for i,p in enumerate(np.random.RandomState(r).permutation(df.pid.unique()))})
    for tr,te in GroupKFold(10).split(df,df.y,g):
        P[te]+=mk().fit(df.iloc[tr][F],df.y.iloc[tr]).predict_proba(df.iloc[te][F])[:,1]
df['p_oof']=P/R
m=mk().fit(df[F],df.y); df['p']=m.predict_proba(df[F])[:,1]
sc=m[0]; lr=m[1]; b=lr.coef_[0]/sc.scale_; b0=lr.intercept_[0]-np.sum(lr.coef_[0]*sc.mean_/sc.scale_)
print('raw coefs:',dict(zip(F,b.round(3))),'b0',round(b0,3))
print('std coefs:',dict(zip(F,lr.coef_[0].round(2))))
y=df.y.values
def stats(t,col='p_oof'):
    s=df[col]>=t; tp=(s&(df.y==1)).sum(); return tp/max(s.sum(),1), tp/df.y.sum(), s.sum()
for t in [0.3,0.5,0.6,0.7,0.8,0.85,0.9,0.95]:
    pr,rc,n=stats(t); print(f't={t:.2f} OOF precision {pr:.3f} recall {rc:.3f} n_above {n}')
# bootstrap by passage for chosen thresholds
pids=df.pid.unique(); rs=np.random.RandomState(1)
for t in [0.5,0.7,0.8,0.9]:
    B=[]
    for _ in range(2000):
        sp=rs.choice(pids,len(pids)); d=pd.concat([df[df.pid==p] for p in sp]) if False else None
        idx=np.concatenate([np.where(df.pid.values==p)[0] for p in sp])
        s=df.p_oof.values[idx]>=t; yy=y[idx]; B.append(((s&(yy==1)).sum()/max(s.sum(),1),(s&(yy==1)).sum()/yy.sum()))
    B=np.array(B); print(f't={t} precision 95%CI [{np.percentile(B[:,0],2.5):.3f},{np.percentile(B[:,0],97.5):.3f}] recall CI [{np.percentile(B[:,1],2.5):.3f},{np.percentile(B[:,1],97.5):.3f}]')
df.to_pickle('scored.pkl')
json.dump(dict(F=F,b=list(b),b0=b0,mean=list(sc.mean_),scale=list(sc.scale_),std_coef=list(lr.coef_[0])),open('model.json','w'))
