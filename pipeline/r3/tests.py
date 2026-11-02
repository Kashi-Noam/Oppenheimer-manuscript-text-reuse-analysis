"""Four closeness tests for each (older, newer) witness pair of a text unit, relative to Oppenheim."""
import json, re, pickle, itertools, difflib, collections
from rapidfuzz.fuzz import ratio, partial_ratio

FIN = str.maketrans('ךםןףץ', 'כמנפצ')
ABBR = {'יי': 'ה', 'ייי': 'ה', 'אמ': 'אמר', 'שנ': 'שנאמר', 'שנא': 'שנאמר', 'הקבה': 'הקבה', 'דכת': 'דכתיב', 'כת': 'כתיב', 'אר': 'אמר', 'וגו': 'וגומר', 'וג': 'וגומר'}
def norm(t):
    t = re.sub(r'[^א-ת]', '', t).translate(FIN)
    t = ABBR.get(t, t)
    if len(t) > 2: t = t[0] + re.sub('[וי]', '', t[1:])
    return t
def sim(a, b):
    a, b = norm(a), norm(b)
    if a == b: return 1.0
    if not a or not b: return 0.0
    return ratio(a, b) / 100

def runs(idx, gap=1, minlen=3):
    out, cur = [], []
    for i in sorted(idx):
        if cur and i - cur[-1] <= gap + 1: cur.append(i)
        else:
            if len(cur) >= minlen: out.append(cur)
            cur = [i]
    if len(cur) >= minlen: out.append(cur)
    return out

def ntext(tokens):
    return ' '.join(norm(t) for t in tokens if norm(t))
def present(block_tokens, hay_text, thr):
    b = ntext(block_tokens)
    return bool(b) and partial_ratio(b, hay_text) >= thr

def wit_align(a, b):
    """align two clean witness texts (token lists) -> dict a_idx->b_idx"""
    sm = difflib.SequenceMatcher(None, [norm(x) for x in a], [norm(x) for x in b], autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): m[blk.a + k] = blk.b + k
    return m

def near(refsA, refsB):
    for (pa, na) in refsA:
        for (pb, nb) in refsB:
            if pa == pb and na == nb: return True
            if pa == pb and len(na) == len(nb) and na[:-1] == nb[:-1] and abs(na[-1] - nb[-1]) <= 1: return True
    return False

def compare(u, O, M, nbrs):
    """O = older witness dict, M = newer witness dict (as in units.pkl). nbrs = list of neighbour units."""
    aO, aM = O['amap'], M['amap']
    oO, oM = set(aO), set(aM)
    lo, hi = max(min(oO), min(oM)), min(max(oO), max(oM))
    inter = lambda s: {i for i in s if lo <= i <= hi}
    om = wit_align(O['src'], M['src'])            # O idx -> M idx
    mo = {v: k for k, v in om.items()}
    ev = collections.Counter(); blocks = collections.defaultdict(list)
    # Test 1a: Oppenheim shares with O material that M lacks
    Mtxt, Otxt = ntext(M['src']), ntext(O['src'])
    win = u['opp'][max(0, u['lo'] - 20): u['hi'] + 21]; Wtxt = ntext(u['opp'])
    for r in runs(inter(oO - oM)):
        src = [aO[i][0] for i in r]
        if sum(1 for j in src if j in om) <= len(src) / 3 and not present([u['opp'][i] for i in r], Mtxt, 70):
            ev['opp_O_notM'] += len(r); blocks['opp_O_notM'].append(r)
    # Test 1b: Oppenheim shares with M material that O lacks
    for r in runs(inter(oM - oO)):
        src = [aM[i][0] for i in r]
        if sum(1 for j in src if j in mo) <= len(src) / 3 and not present([u['opp'][i] for i in r], Otxt, 70):
            ev['opp_M_notO'] += len(r); blocks['opp_M_notO'].append(r)
    # Test 1c: shared omission – O material (inside O's aligned stretch, inside M's coverage) absent from both Oppenheim and M
    Osrc_al = {aO[i][0] for i in oO if lo <= i <= hi}
    if Osrc_al and om:
        s0, s1 = min(Osrc_al), max(Osrc_al)
        mcov = [k for k in om if s0 <= k <= s1]
        if mcov:
            c0, c1 = min(mcov), max(mcov)
            free = [j for j in range(max(s0, c0), min(s1, c1) + 1) if j not in Osrc_al]
            for r in runs(free):
                if sum(1 for j in r if j in om) > len(r) / 3: continue
                for k in range(0, len(r), 5):
                    ch = r[k:k + 5]
                    if len(ch) < 3: continue
                    toks = [O['src'][j] for j in ch]
                    if not present(toks, Wtxt, 70) and not present(toks, Mtxt, 70):
                        ev['shared_omission'] += len(ch); blocks['shared_omission'].append(ch)
    # Test 3: readings – where O and M differ, whom does Oppenheim follow
    for i in sorted(inter(oO & oM)):
        o, m, q = O['src'][aO[i][0]], M['src'][aM[i][0]], u['opp'][i]
        if sim(o, m) >= 0.9: continue
        so, sm_ = sim(q, o), sim(q, m)
        if sm_ - so >= 0.2: ev['reading_M'] += 1
        elif so - sm_ >= 0.2: ev['reading_O'] += 1
    # Test 2: order – neighbouring units juxtaposed in M (or O) as in Oppenheim
    dk = (O['_dk'], M['_dk'])
    for v in nbrs:
        inO = v['wit'].get(dk[0]); inM = v['wit'].get(dk[1])
        nO = bool(inO) and near(O['refs'], inO['refs']); nM = bool(inM) and near(M['refs'], inM['refs'])
        if nM and not nO: ev['order_M'] += 1
        if nO and not nM: ev['order_O'] += 1
    # Test 4: boundaries – M's excerpt starts where Oppenheim's unit starts, while O continues earlier
    first = lambda W: min(j for j, _ in W['amap'].values())
    if u['lo'] >= 6:
        if first(M) <= 3 and first(O) >= 10: ev['boundary_M'] += 1
        if first(O) <= 3 and first(M) >= 10: ev['boundary_O'] += 1
    via = ev['opp_M_notO'] + 0.25 * ev['shared_omission'] + 3 * ev['order_M'] + 2 * ev['boundary_M'] + 0.5 * ev['reading_M']
    direct = ev['opp_O_notM'] + 3 * ev['order_O'] + 2 * ev['boundary_O'] + 0.5 * ev['reading_O']
    pos_via = ev['opp_M_notO'] >= 3 or ev['order_M'] or ev['boundary_M'] or ev['reading_M'] >= 3
    pos_dir = ev['opp_O_notM'] >= 3 or ev['order_O'] or ev['boundary_O'] or ev['reading_O'] >= 3
    if via >= 4 and via >= 2 * direct and pos_via: verdict = 'via'
    elif direct >= 4 and direct >= 2 * via and pos_dir: verdict = 'direct'
    else: verdict = 'undetermined'
    return dict(ev=dict(ev), via=round(via, 1), direct=round(direct, 1), verdict=verdict, blocks={k: v for k, v in blocks.items()})

def all_triplets(units, dates):
    by_pid = collections.defaultdict(list)
    for u in units: by_pid[u['pid']].append(u)
    pids = sorted(by_pid, key=lambda p: by_pid[p][0]['fk'])
    neigh = {}
    for k, p in enumerate(pids):
        us = by_pid[p]
        for i, u in enumerate(us):
            nb = []
            if i > 0: nb.append(us[i - 1])
            if i < len(us) - 1: nb.append(us[i + 1])
            if i == 0 and k > 0: nb.append(by_pid[pids[k - 1]][-1])
            if i == len(us) - 1 and k < len(pids) - 1: nb.append(by_pid[pids[k + 1]][0])
            neigh[u['uid']] = nb
    out = []
    for u in units:
        ks = [k for k in u['wit'] if k in dates]
        for a, b in itertools.combinations(ks, 2):
            da, db = dates[a], dates[b]
            mid = lambda x: (x['date_from'] + x['date_to']) / 2
            O, M = (a, b) if mid(da) <= mid(db) else (b, a)
            Wo, Wm = dict(u['wit'][O], _dk=O), dict(u['wit'][M], _dk=M)
            r = compare(u, Wo, Wm, neigh[u['uid']])
            r.update(uid=u['uid'], pid=u['pid'], older=O, newer=M,
                     order_certain=dates[O]['date_to'] < dates[M]['date_from'],
                     older_late=dates[O]['date_from'] > 1400, newer_late=dates[M]['date_from'] > 1400)
            out.append(r)
    return out
