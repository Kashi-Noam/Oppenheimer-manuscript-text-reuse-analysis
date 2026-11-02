import json, gzip, os
# ACT text-reuse report. Default: the gzipped copy in data/raw (override with OPP_ACT_REPORT).
REP = os.environ.get('OPP_ACT_REPORT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'raw',
                     'tr_report_288c1011-282d-4644-9959-2f1b093a6b33.json.gz'))
_CACHE = None
def load():
    global _CACHE
    if _CACHE is None:
        op = gzip.open if REP.endswith('.gz') else open
        with op(REP, 'rt', encoding='utf-8') as fh: _CACHE = json.load(fh)
    return _CACHE
def seq_of(ad):
    seq=ad.get('alignment_sequence')
    if isinstance(seq,str):
        try: seq=json.loads(seq)
        except Exception: seq=[]
    seq=seq or []
    if seq and isinstance(seq[0],list) and seq[0] and isinstance(seq[0][0],list): seq=[p for b in seq for p in b]
    return seq
def cands(v):
    c=v.get('candidates') or []
    if isinstance(c,str):
        import ast; c=ast.literal_eval(c)
    return c
def metrics(c):
    ad=c.get('alignment_details') or {}
    seq=seq_of(ad)
    pt=(ad.get('passage_text') or '').split(); st=(ad.get('source_text') or '').split()
    pairs=sorted({(int(p[0]),int(p[1])) for p in seq})
    pidx=sorted({p for p,_ in pairs}); sidx=sorted({s for _,s in pairs})
    # passage-side run
    run=best=0; prev=None
    for i in pidx:
        run=run+1 if prev is not None and i==prev+1 else 1; best=max(best,run); prev=i
    # both-side run & groups (consecutive in both)
    bb=0; r=0; prev=None; groups=0
    for (a,b) in pairs:
        if prev is not None and a==prev[0]+1 and b==prev[1]+1: r+=1
        else: r=1; groups+=1
        bb=max(bb,r); prev=(a,b)
    span=(pidx[-1]-pidx[0]+1) if pidx else 0
    sims=[float(p[2]) for p in seq]
    return dict(score=ad.get('score'),norm=c.get('norm_score'),align=c.get('alignment_score'),full=c.get('full_alignment_ind'),
        N=len(pidx),L_p=best,L_both=bb,groups=groups,span=span,D=len(pidx)/span if span else 0,
        C=len(sidx)/len(st) if st else 0,Cp=len(pidx)/len(pt) if pt else 0,
        sim=sum(sims)/len(sims) if sims else 0,exact=sum(1 for p in seq if len(p)>3 and str(p[3]).endswith('exact_match'))/len(seq) if seq else 0,
        p_len=len(pt),s_len=len(st))
