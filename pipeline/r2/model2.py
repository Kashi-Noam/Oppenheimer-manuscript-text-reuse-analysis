import numpy as np,pandas as pd,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
df=pd.read_pickle('diag2.pkl'); y=df.y.values
BASE=['lN','C','Cp','lscore','align','tanakh']
SETS={'base':BASE,'+Cp_work':BASE+['Cp_work'],'+Cp_work,lNw':BASE+['Cp_work','lNw'],'+Cp_work,lNw,wit':BASE+['Cp_work','lNw','lwit'],'+Cp_work,oov':BASE+['Cp_work','oov'],'+Cp_work,Dloc':BASE+['Cp_work','Dloc']}
def oof(F,R=20):
    P=np.zeros(len(df))
    for r in range(R):
        g=df.pid.map({p:i for i,p in enumerate(np.random.RandomState(r).permutation(df.pid.unique()))})
        for tr,te in GroupKFold(10).split(df,y,g):
            P[te]+=make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000)).fit(df.iloc[tr][F],y[tr]).predict_proba(df.iloc[te][F])[:,1]
    return P/R
def at(p,t): s=p>=t; tp=(s&(y==1)).sum(); return tp/max(s.sum(),1),tp/y.sum()
for k,F in SETS.items():
    p=oof(F); 
    # threshold giving OOF precision>=0.98 max recall
    o=np.argsort(-p); prec=np.cumsum(y[o])/np.arange(1,len(y)+1); ok=np.where(prec>=0.98)[0]; t98=p[o][ok.max()]
    print(f'{k:22s} @0.8: prec {at(p,.8)[0]:.3f} rec {at(p,.8)[1]:.3f} | best rec at prec>=.98: {at(p,t98)[1]:.3f} (t={t98:.2f})')
