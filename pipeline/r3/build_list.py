import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
import json,re,sys,collections,numpy as np,pandas as pd
sys.path.insert(0,ROOT + '/r2')
from feats import load,cands,seq_of
from feats2 import extra
d=load()
allc=pd.read_pickle(ROOT + '/r2/allc_scored.pkl')
lab=pd.read_pickle(ROOT + '/r2/diag2.pkl')[['pid','rank','tid','rel']]
allc=allc.merge(lab,on=['pid','rank'],how='left')
HE={'Pesikta_DRav_Kahanna':'פסיקתא דרב כהנא','Midrash_HaGadol':'מדרש הגדול','Yalkut_Shimoni_on_Nach':'ילקוט שמעוני נ"ך','Yalkut_Shimoni_on_Torah':'ילקוט שמעוני תורה',
'Pesikta_Rabbati':'פסיקתא רבתי','Midrash_Tanchuma_Buber':'תנחומא בובר','Otzar_Midrashim':'אוצר המדרשים','Tractate_Derekh_Eretz_Rabbah':'מסכת דרך ארץ רבה','Midrash_Tanchuma':'תנחומא',
'Bereshit_Rabbati':'בראשית רבתי','Eichah_Rabbah':'איכה רבה','Vayikra_Rabbah':'ויקרא רבה','Mishnat_Rabbi_Eliezer':"משנת ר' אליעזר",'Tractate_Derekh_Eretz_Zuta':'מסכת דרך ארץ זוטא',
'Ein_Yaakov_Glick_Edition':'עין יעקב','Bamidbar_Rabbah':'במדבר רבה','Shir_HaShirim_Rabbah':'שיר השירים רבה','Bereishit_Rabbah':'בראשית רבה','Kohelet_Rabbah':'קהלת רבה',
'Midrash_Tehillim':'מדרש תהלים','Sanhedrin':'בבלי סנהדרין','Tractate_Kutim':'מסכת כותים','Tractate_Semachot':'מסכת שמחות','Tractate_Gerim':'מסכת גרים','Midrash_Mishlei':'מדרש משלי',
'Midrash_Aggadah':'מדרש אגדה (בובר)','Gittin':'בבלי גיטין','Midrash_Lekach_Tov_on_Lamentations':'לקח טוב לאיכה','Ruth_Rabbah_Lerner':'רות רבה (מהד\' לרנר)','Taanit':'בבלי תענית',
'Midrash_Shmuel':'מדרש שמואל','Menachot':'בבלי מנחות','Midrash_Lekach_Tov':'לקח טוב','Shabbat':'בבלי שבת','Bava_Batra':'בבלי בבא בתרא','Jerusalem_Talmud_Taanit':'ירושלמי תענית',
'Arakhin':'בבלי ערכין','Midrash_Sekhel_Tov':'שכל טוב','Aggadat_Bereshit':'אגדת בראשית','Sukkah':'בבלי סוכה','Jerusalem_Talmud_Berakhot':'ירושלמי ברכות','Sifrei_Aggadah_on_Esther':'ספרי דאגדתא על אסתר',
'Esther_Rabbah':'אסתר רבה','Jerusalem_Talmud_Sheviit':'ירושלמי שביעית','Ruth_Rabbah':'רות רבה','Berakhot':'בבלי ברכות','Yevamot':'בבלי יבמות','Chagigah':'בבלי חגיגה','Yoma':'בבלי יומא',
'Pesachim':'בבלי פסחים','Ketubot':'בבלי כתובות','Jerusalem_Talmud_Shekalim':'ירושלמי שקלים','Jerusalem_Talmud_Peah':'ירושלמי פאה','Tanna_Debei_Eliyahu_Rabbah':'תנא דבי אליהו רבה','Makkot':'בבלי מכות'}
def parse(loc):
    a=loc.split('-',1)[1] if '-' in loc else loc
    if a.startswith('Midrash_HaGadol'):
        return 'Midrash_HaGadol', a.split('RAVKOOK_',1)[1].replace('_',' ')
    m=re.match(r'(.+?)(?:-[A-Z0-9]+)?_Sefaria_(.+)$',a) or re.match(r'(.+?)-Sefaria_(.+)$',a)
    w,ref=(m.group(1),m.group(2)) if m else (a,'')
    return re.sub(r'-[A-Z0-9]+$','',w), ref.replace('_',' ')
def genre(loc,w):
    if loc.startswith('Tanakh'): return 'תנ"ך'
    if w.startswith('Jerusalem_Talmud'): return 'ירושלמי'
    if loc.startswith('Talmud_Bavli'): return 'בבלי'
    if 'Yalkut' in w or w in('Midrash_HaGadol','Ein_Yaakov_Glick_Edition','Otzar_Midrashim','Bereshit_Rabbati','Midrash_Lekach_Tov','Midrash_Lekach_Tov_on_Lamentations','Midrash_Sekhel_Tov'): return 'ילקוטים ואוספים מאוחרים'
    if w.startswith('Tractate_'): return 'מסכתות קטנות'
    return 'מדרש'
def fkey(pid):
    m=re.match(r'Oppenheimer_128_fol_(\d+)([rv])_(\d+)$',pid)
    return (int(m.group(1)),m.group(2)=='v',int(m.group(3))) if m else (-1,False,0)
def folio(pid): return pid.replace('Oppenheimer_128_','').replace('fol_','fol ').replace('_',' ').replace('Upper cover','כריכה עליונה')
pw=allc['loc'].map(parse); allc['w']=[x[0] for x in pw]; allc['ref']=[x[1] for x in pw]
allc['work']=allc.w.map(lambda w: HE.get(w,w.replace('_',' '))); allc['genre']=[genre(l,w) for l,w in zip(allc['loc'],allc.w)]
allc['folio']=allc.pid.map(folio); allc['fk']=allc.pid.map(fkey)
M=json.load(open(ROOT + '/r2/model.json'))
allc['S']=sum(b*allc[f].astype(float) for f,b in zip(M['F'],M['b']))
up=allc[allc.p>=0.8].sort_values(['fk','S'],ascending=[True,False])
# per work
g=up.groupby('work')
byw=pd.DataFrame({'genre':g.genre.first(),'pages':g.pid.nunique(),'pairs':g.size(),'S_med':g.S.median().round(1),'S_max':g.S.max().round(1)})
byw['folios']=[', '.join(dict.fromkeys(up[up.work==w].sort_values('fk').folio)) for w in byw.index]
byw=byw.sort_values(['pages','pairs'],ascending=False)
# per page
allp=[p for p,v in d.items() if cands(v)]
pages=[]
for pid in sorted(allp,key=fkey):
    u=up[up.pid==pid]; a=allc[allc.pid==pid]
    nc=len(cands(d[pid]))
    if len(u):
        b=u.iloc[0]
        pages.append(dict(folio=folio(pid),pid=pid,n_up=len(u),works=' | '.join(dict.fromkeys(u.work)),best=f"{b.work} {b.ref}",best_S=round(b.S,1),n_full=len(a),n_cand=nc))
    else:
        b=a.sort_values('S',ascending=False).iloc[0] if len(a) else None
        pages.append(dict(folio=folio(pid),pid=pid,n_up=0,works='',best=(f"{b.work} {b.ref}" if b is not None else ''),best_S=(round(b.S,1) if b is not None else None),n_full=len(a),n_cand=nc))
pages=pd.DataFrame(pages)
# near threshold + rescue rules
near=allc[(allc.p>=0.2)&(allc.p<0.8)].copy()
ex=[extra(d,p,r) for p,r in zip(near.pid,near['rank'])]
near['Cp_work']=[e['Cp_work'] for e in ex]; near['nseg_work']=[e['nseg_work'] for e in ex]
voc=collections.Counter()
for v in d.values():
    for c in cands(v): voc.update(((c.get('alignment_details') or {}).get('source_text') or '').split())
def oov(pid):
    pt=(cands(d[pid])[0].get('alignment_details') or {}).get('passage_text','').split()
    return sum(1 for w in pt if voc[w]<3)/len(pt) if pt else 0
oo={p:oov(p) for p in near.pid.unique()}; near['oov']=near.pid.map(oo)
near['rule']=np.where(near.oov>=0.18,'HTR משובש','')+np.where((near.Cp_work>=0.4)&(near.nseg_work>=2),np.where(near.oov>=0.18,' + איחוד סגמנטים','איחוד סגמנטים'),'')
resc=near[near.rule!=''].sort_values(['fk','S'],ascending=[True,False])
pd.to_pickle(dict(up=up,byw=byw,pages=pages,resc=resc,allc=allc),ROOT + '/r3/lists.pkl')
print('passing pairs',len(up),'works',up.work.nunique(),'pages w/ pass',(pages.n_up>0).sum(),'of',len(pages))
print('pages no full cand',(pages.n_full==0).sum(),' pages with full but no pass',((pages.n_full>0)&(pages.n_up==0)).sum())
print('rescue candidates',len(resc),'new pages from rescue',len(set(resc.pid)-set(up.pid)))
print(byw.head(15)[['genre','pages','pairs','S_med']].to_string())
print(up.genre.value_counts().to_string())
print('tanakh passing',(up.genre=='תנ"ך').sum())
lab_up=up[up.rel.notna()]; print('labeled among passing',len(lab_up), lab_up.rel.value_counts().to_dict())
