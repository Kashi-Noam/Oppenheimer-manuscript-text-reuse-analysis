import json, csv, re, glob, statistics as st

m = json.load(open('metrics.json'))
cap = {c['tid']: c for c in json.load(open('captured.json'))}
pairs = json.load(open('pairs.json'))
L = {r[0]: r for r in csv.reader(open('labels.tsv'), delimiter='\t')}

opp = {}
for f in sorted(glob.glob('tb_*.txt')):
    pid = None
    for line in open(f):
        if line.startswith('##### PASSAGE'):
            pid = line.split()[-1]
        elif line.startswith('OPP FULL:') and pid:
            opp[pid] = line[len('OPP FULL:'):].strip()

HE = {
 'Arakhin': 'בבלי ערכין', 'Avodah_Zarah': 'בבלי עבודה זרה', 'Bamidbar_Rabbah': 'במדבר רבה',
 'Bereshit_Rabbati': 'בראשית רבתי', 'Chagigah': 'בבלי חגיגה', 'Deuteronomy': 'דברים', 'Eichah_Rabbah': 'איכה רבה',
 'Ein_Yaakov_Glick_Edition': 'עין יעקב', 'Exodus': 'שמות', 'Ezekiel': 'יחזקאל', 'Genesis': 'בראשית', 'Hosea': 'הושע',
 'II_Chronicles': 'דברי הימים ב', 'II_Kings': 'מלכים ב', 'II_Samuel': 'שמואל ב', 'Isaiah': 'ישעיהו', 'Jeremiah': 'ירמיהו',
 'Joel': 'יואל', 'Kohelet_Rabbah': 'קהלת רבה', 'Lamentations': 'איכה', 'Leviticus': 'ויקרא', 'Midrash_HaGadol': 'מדרש הגדול',
 'Midrash_Lekach_Tov': 'לקח טוב', 'Midrash_Lekach_Tov_on_Lamentations': 'לקח טוב לאיכה',
 'Midrash_Lekach_Tov_on_Song_of_Songs': 'לקח טוב לשיר השירים', 'Midrash_Mishlei': 'מדרש משלי', 'Midrash_Tanchuma': 'תנחומא',
 'Midrash_Tanchuma_Buber': 'תנחומא בובר', 'Midrash_Tehillim': 'מדרש תהלים', 'Mishnat_Rabbi_Eliezer': "משנת ר' אליעזר",
 'Otzar_Midrashim': 'אוצר המדרשים', 'Pesikta_DRav_Kahanna': 'פסיקתא דרב כהנא', 'Pesikta_Rabbati': 'פסיקתא רבתי',
 'Pirkei_DeRabbi_Eliezer': "פרקי דר' אליעזר", 'Psalms': 'תהלים', 'Sanhedrin': 'בבלי סנהדרין',
 'Tanna_Debei_Eliyahu_Rabbah': 'תנא דבי אליהו רבה', 'Tractate_Derekh_Eretz_Rabbah': 'מסכת דרך ארץ רבה',
 'Tractate_Derekh_Eretz_Zuta': 'מסכת דרך ארץ זוטא', 'Tractate_Kallah_Rabbati': 'מסכת כלה רבתי', 'Vayikra_Rabbah': 'ויקרא רבה',
 'Yalkut_Shimoni_on_Nach': 'ילקוט שמעוני נ"ך', 'Yalkut_Shimoni_on_Torah': 'ילקוט שמעוני תורה', 'Zechariah': 'זכריה',
}

def parse_loc(loc):
    a = loc.split('-', 1)[1] if '-' in loc else loc
    if a.startswith('Midrash_HaGadol'):
        work = 'Midrash_HaGadol'; ref = a.split('RAVKOOK_', 1)[1]
    else:
        mm = re.match(r'(.+?)(?:-[A-Z0-9]+)?_Sefaria_(.+)$', a) or re.match(r'(.+?)-Sefaria_(.+)$', a)
        work, ref = (mm.group(1), mm.group(2)) if mm else (a, '')
        work = re.sub(r'-[A-Z0-9]+$', '', work)
    return HE.get(work, work.replace('_', ' ')), ref.replace('_', ' ')

TIER = {'אותו טקסט': 'A', 'אותו טקסט · חלקי': 'A', 'נוסח מקביל': 'B', 'אותו חיבור · קטע אחר': 'C',
        'דרשה על המקור': 'C', 'ציטוט פסוק מהמקור': 'C', 'ציטוט משותף': 'C', 'אין קשר': 'D'}

def folio(pid):
    return pid.replace('Oppenheimer_128_', '').replace('_', ' ')

out_pairs = []
for p in pairs:
    t = p['tid']; x = m[t]; c = cap[t]; lab = L[t]
    work, ref = parse_loc(p['loc'])
    out_pairs.append(dict(
        tid=t, pid=p['pid'], folio=folio(p['pid']), rank=p['rank'], eid=p['eid'], loc=p['loc'], work=work, ref=ref,
        ctitle=c.get('ctitle', ''), cref=c.get('cref', ''),
        score=round(x['score'], 2), norm=round(x['norm'], 4), align=round(x['align'], 4), full=x['full'],
        N=x['N'], L_p=x['L_p'], L_both=x['L_both'], groups=x['groups'], span=x['span'], D=round(x['D'], 3),
        C=round(x['C'], 3), Cp=round(x['Cp'], 3), sim=round(x['sim'], 3), exact=round(x['exact'], 3),
        p_len=x['p_len'], s_len=x['s_len'], rel=lab[1], conf=lab[2], note=lab[3], tier=TIER[lab[1]],
        shot=f'shots/{t}.jpg'))

passages = []
seen = []
for p in out_pairs:
    if p['pid'] not in seen: seen.append(p['pid'])
for pid in seen:
    passages.append(dict(pid=pid, folio=folio(pid), text=opp.get(pid, ''), n=sum(q['pid'] == pid for q in out_pairs)))

# summary
REL_ORDER = ['אותו טקסט', 'אותו טקסט · חלקי', 'נוסח מקביל', 'אותו חיבור · קטע אחר', 'דרשה על המקור',
             'ציטוט פסוק מהמקור', 'ציטוט משותף', 'אין קשר']
summ = []
for r in REL_ORDER:
    g = [p for p in out_pairs if p['rel'] == r]
    if not g: continue
    row = dict(rel=r, n=len(g), tier=TIER[r], conf={k: sum(p['conf'] == k for p in g) for k in ['גבוהה', 'בינונית', 'נמוכה']})
    for f in ['N', 'L_both', 'C', 'Cp', 'norm', 'align', 'score']:
        xs = sorted(p[f] for p in g)
        row[f] = [xs[0], st.median(xs), xs[-1]]
    summ.append(row)

thr = []
for f in ['N', 'C', 'Cp', 'score', 'align', 'groups', 'norm', 'L_both']:
    xs = [(p[f], p['tier'] == 'A') for p in out_pairs]
    best = None
    for t in sorted(set(v for v, _ in xs)):
        err = sum((v >= t) != y for v, y in xs)
        fp = sum((v >= t) and not y for v, y in xs); fn = sum((v < t) and y for v, y in xs)
        if best is None or err < best[0]: best = (err, t, fp, fn)
    thr.append(dict(metric=f, thr=best[1], err=best[0], fp=best[2], fn=best[3]))
thr.sort(key=lambda r: r['err'])

json.dump(dict(passages=passages, pairs=out_pairs, summary=summ, thresholds=thr, rel_order=REL_ORDER),
          open('report/data.json', 'w'), ensure_ascii=False)
json.dump(out_pairs, open('report_pairs_flat.json', 'w'), ensure_ascii=False)
print(len(passages), len(out_pairs)); print(thr[:4])
missing = [p['pid'] for p in passages if not p['text']]; print('missing text', missing)
print(sorted(set(p['work'] for p in out_pairs)))
