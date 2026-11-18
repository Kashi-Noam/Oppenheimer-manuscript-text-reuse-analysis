"""Build docs/explorer/tables.json: the main Excel tables of the project, with a link from each row to the matching item in the explorer."""
import json, os, datetime
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
XL = os.path.join(ROOT, 'outputs', 'excel')
OUT = os.path.join(ROOT, 'docs', 'explorer', 'tables.json')
GH = 'https://github.com/Kashi-Noam/Oppenheimer-manuscript-text-reuse-analysis/raw/main/outputs/excel/'
import statistics
C = json.load(open(os.path.join(ROOT, 'docs', 'explorer', 'core.json')))
CA = json.load(open(os.path.join(ROOT, 'docs', 'explorer', 'core_all.json')))  # matryoshka on every fully aligned candidate

W = {w['key']: w for w in C['works'] + CA['works']}
CANDS = {c['id']: c for c in C['cands']}
FOLIO = {p['folio']: p['pid'] for p in C['passages']}
WORK = {w['name_he']: w['key'] for w in C['works'] + CA['works']}
for c in C['cands']:
    if c['k'] in W: WORK.setdefault(c['work'], c['k'])
TID = {c['tid']: c['id'] for c in C['cands'] if c.get('tid')}
MAPS = {'thr': ({(c['uid'], c['o'], c['n']): i for i, c in enumerate(C['comps'])}, {u['uid'] for u in C['units']}),
        'all': ({(c['uid'], c['o'], c['n']): i for i, c in enumerate(CA['comps'])}, {u['uid'] for u in CA['units']})}
COMP, UNITS = MAPS['thr']

def clean(v):
    if v is None: return ''
    if isinstance(v, float): return round(v, 3)
    if isinstance(v, (datetime.date, datetime.datetime)): return v.isoformat()[:10]
    return v

def read(fname, sheet):
    ws = openpyxl.load_workbook(os.path.join(XL, fname), read_only=True)[sheet]
    rows = [[clean(v) for v in r] for r in ws.iter_rows(values_only=True)]
    head = [str(h) if h is not None else '' for h in rows[0]]
    keep = [i for i, h in enumerate(head) if h]
    body = [[r[i] if i < len(r) else '' for i in keep] for r in rows[1:] if any(v != '' for v in r)]
    return [head[i] for i in keep], body

def note(fname):
    try: h, rows = read(fname, 'הסבר')
    except KeyError: return []
    return [[str(r[0]), str(r[1])] for r in rows if len(r) > 1 and r[0]]

def col(head, *names):
    for n in names:
        if n in head: return head.index(n)
    return None

def pid_of(r, head):
    i = col(head, 'מזהה קטע', 'passage_id')
    if i is not None and r[i]: return r[i]
    i = col(head, 'קטע', 'דף')
    return FOLIO.get(r[i]) if i is not None else None

def go_passage(r, h):
    p = pid_of(r, h); return ['p', p] if p else None

def go_cand(r, h):
    p = pid_of(r, h); i = col(h, 'rank')
    if p and i is not None and f'{p}|{r[i]}' in CANDS: return ['c', f'{p}|{r[i]}']
    return go_passage(r, h)

def go_tid(r, h):
    i = col(h, 'מזהה')
    return ['c', TID[r[i]]] if i is not None and r[i] in TID else go_cand(r, h)

def go_work(r, h):
    i = col(h, 'חיבור'); k = WORK.get(r[i]) if i is not None else None
    return ['w', k] if k else None

def go_pair(r, h):
    o, n = WORK.get(r[col(h, 'חיבור ישן')]), WORK.get(r[col(h, 'חיבור חדש')])
    return ['vp', o, n] if o and n else None

def go_unit(r, h):
    u = r[col(h, 'יחידה')]
    return ['u', u] if u in UNITS else None

def go_comp(r, h):
    k = (r[col(h, 'יחידה')], WORK.get(r[col(h, 'עד ישן')]), WORK.get(r[col(h, 'עד חדש')]))
    return ['v', COMP[k]] if k in COMP else go_unit(r, h)

def go_pilot(r, h):
    return go_passage(r, h)

SRC, TAG, DAT, MAT, MATA, CAND = ('oppenheim128_sources_above_threshold.xlsx', 'oppenheim128_tagging_v3.xlsx', 'oppenheim128_datings_and_pilot.xlsx',
                                   'oppenheim128_matryoshka.xlsx', 'oppenheim128_matryoshka_all.xlsx', 'oppenheim128_all_aligned_candidates.xlsx')
TAG_COLS = ['מזהה', 'סבב', 'דף', 'rank', 'חיבור', 'מראה מקום', 'קשר', 'סמך', 'הערה', 'ציון משוכלל S', 'הסתברות p', 'מעל הסף', 'סיבה (מתחת לסף)']

# ---- every fully aligned candidate, no threshold: written to an Excel file so it can be downloaded like the others ----
P = {p['pid']: p for p in C['passages']}
def cand_sheets():
    cs = sorted(C['cands'], key=lambda c: (list(P).index(c['pid']), c['rank']))
    lst = [[P[c['pid']]['folio'], c['rank'], c['work'], c['ref'], c['S'], c['p'], 'כן' if c['above'] else 'לא', c['N'], c['C'], c['Cp'], c['score'], c['align'],
            c.get('rel', ''), c['pid']] for c in cs]
    by_w = {}
    for c in cs: by_w.setdefault(c['work'], []).append(c)
    wk = [[w, len({c['pid'] for c in g}), len(g), sum(c['above'] for c in g), round(statistics.median(c['S'] for c in g), 2), max(c['S'] for c in g),
           ', '.join(dict.fromkeys(P[c['pid']]['folio'] for c in g))] for w, g in sorted(by_w.items(), key=lambda kv: -len(kv[1]))]
    by_p = {}
    for c in cs: by_p.setdefault(c['pid'], []).append(c)
    ps = []
    for pid, g in by_p.items():
        g = sorted(g, key=lambda c: -c['S']); b = g[0]
        ps.append([P[pid]['folio'], pid, len(g), sum(c['above'] for c in g), ' | '.join(dict.fromkeys(c['work'] for c in g)), f"{b['work']} {b['ref']}", b['S']])
    return [('כל המועמדים', ['קטע', 'rank', 'חיבור', 'מראה מקום', 'S', 'p', 'מעל הסף', 'N', 'C', 'Cp', 'score', 'align', 'תיוג ידני', 'מזהה קטע'], lst),
            ('לפי חיבור', ['חיבור', 'קטעים', 'מועמדים', 'מתוכם מעל הסף', 'חציון S', 'S מרבי', 'קטעים (דפים)'], wk),
            ('לפי קטע', ['קטע', 'מזהה קטע', 'מועמדים מיושרים', 'מתוכם מעל הסף', 'חיבורים (לפי S יורד)', 'ההתאמה עם S הגבוה ביותר', 'S שלה'], ps)]
def write_cands_xlsx():
    wb = openpyxl.Workbook(); first = True
    ex = wb.active; ex.title = 'הסבר'; ex.sheet_view.rightToLeft = True
    for r in [['נושא', 'פירוט'], ['מה בקובץ', 'כל 2,650 המועמדים שדוח ACT החזיר וקיבלו יישור מלא, בלי סינון של הרגרסיה הלוגיסטית. העמודה "מעל הסף" מסמנת S ≥ 21.14.'],
              ['שימו לב', 'חלק גדול מהמועמדים מתחת לסף הם ציטוטי פסוקים, מימרות שגורות או רעש. זו הגרסה הגולמית לצורך עיון והשוואה.']]: ex.append(r)
    for title, head, rows in cand_sheets():
        ws = wb.create_sheet(title); ws.sheet_view.rightToLeft = True; ws.append(head)
        for r in rows: ws.append(r)
        ws.freeze_panes = 'A2'
    wb.save(os.path.join(XL, CAND))
write_cands_xlsx()

SPEC = [
    ('sources', 'המקורות מעל הסף', SRC, 'thr', [
        ('src_work', 'לפי חיבור', 'כל חיבור שיש לו לפחות התאמה אחת מעל הסף: בכמה קטעים, כמה התאמות, וחציון ומקסימום של הציון המשוכלל S.', go_work, None),
        ('src_pass', 'לפי קטע', 'כל קטע באופנהיימר: אילו חיבורים עברו את הסף, וההתאמה החזקה ביותר שלו.', go_passage, None),
        ('src_all', 'כל ההתאמות', 'כל ההתאמות מעל הסף (S ≥ 21.14), כולל מדדי ACT ותיוג ידני כשיש.', go_cand, None),
        ('src_near', 'קרובים לסף', 'התאמות קרובות לסף (0.2 ≤ p < 0.8), ואם עברו בכלל השלמה.', go_cand, None)]),
    ('cands_all', 'כל המועמדים המיושרים (בלי סף)', CAND, 'all', [
        ('cand_work_all', 'לפי חיבור', 'כל חיבור שיש לו מועמד מיושר: בכמה קטעים, כמה מועמדים, כמה מהם מעל הסף, וחציון ומקסימום של S.', go_work, None),
        ('cand_pass_all', 'לפי קטע', 'כל קטע באופנהיימר: כל החיבורים ש-ACT יישר אליו, וכמה מהם עברו את הסף.', go_passage, None),
        ('cand_list_all', 'כל המועמדים', 'כל 2,650 המועמדים המיושרים, מעל הסף ומתחתיו.', go_cand, None)]),
    ('tagging', 'התיוג והמודל', TAG, 'both', [
        ('tag_all', 'תיוג', '487 הזוגות המתויגים, עם הקשר, רמת הסמך, ההערה והציון המשוכלל. העמודות המלאות בקובץ ה-Excel.', go_tid, TAG_COLS),
        ('tag_below', 'זהים מתחת לסף', 'זוגות שתויגו כזהים אבל נפלו מתחת לסף, עם הסיבה ודרך התיקון.', go_tid, None),
        ('tag_sum', 'סיכום לפי קשר', 'חציוני המדדים לכל סוג קשר.', None, None),
        ('tag_model', 'ציון וסף', 'מקדמי הרגרסיה הלוגיסטית.', None, None)]),
    ('datings', 'תיארוכים', DAT, 'both', [
        ('dat_works', 'תיארוכים', 'תיארוך כל חיבור כטווח שנים, ודאות, אזור, מחלוקות ומקורות.', go_work, None),
        ('dat_pilot', 'פיילוט 20 שלשות', 'הפיילוט של בדיקות הקרבה על 20 שלישיות, מול קריאה ידנית.', go_pilot, None)]),
    ('matryoshka', 'מטריושקה (מעל הסף)', MAT, 'thr', [
        ('mat_works', 'חיבורים', 'לכל חיבור: בכמה יחידות הוא מעיד, בכמה הוא העד היחיד, הקרוב ביותר והמוקדם ביותר.', go_work, None),
        ('mat_pairs', 'זוגות חיבורים', 'לכל זוג חיבורים: כמה יחידות משותפות וכמה הכרעות מכל סוג.', go_pair, None),
        ('mat_units', 'יחידות', 'יחידות הטקסט והעדים שלהן.', go_unit, None),
        ('mat_comps', 'השוואות', 'כל ההשוואות בין עד ישן לעד חדש ביחידה, עם הראיות וההכרעה.', go_comp, None)]),
    ('matryoshka_all', 'מטריושקה (כל המיושרים)', MATA, 'all', [
        ('mat_works_all', 'חיבורים', 'אותה טבלה על כל המועמדים המיושרים, בלי סף.', go_work, None),
        ('mat_pairs_all', 'זוגות חיבורים', 'אותה טבלה על כל המועמדים המיושרים, בלי סף.', go_pair, None),
        ('mat_units_all', 'יחידות', 'אותה טבלה על כל המועמדים המיושרים, בלי סף.', go_unit, None),
        ('mat_comps_all', 'השוואות', 'אותה טבלה על כל המועמדים המיושרים, בלי סף.', go_comp, None)]),
]

groups, tables, stats = [], [], {}
for gid, gtitle, fname, mode, sheets in SPEC:
    COMP, UNITS = MAPS['all' if mode == 'all' else 'thr']
    groups.append(dict(id=gid, title=gtitle, file=fname, url=GH + fname, note=note(fname), mode=mode, tables=[s[0] for s in sheets]))
    for tid, sheet, desc, go, cols in sheets:
        head, body = read(fname, sheet)
        if tid.startswith('mat_comps'): body = [r for r in body if '#' in str(r[0])]
        gos = [go(r, head) if go else None for r in body]
        if cols:
            idx = [head.index(c) for c in cols if c in head]
            head, body = [head[i] for i in idx], [[r[i] for i in idx] for r in body]
        tables.append(dict(id=tid, group=gid, mode=mode, title=sheet, desc=desc, cols=head, rows=body, go=gos))
        stats[tid] = (len(body), sum(1 for g in gos if g))
json.dump(dict(groups=groups, tables=tables), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(round(os.path.getsize(OUT) / 1e6, 2), 'MB')
for k, (n, g) in stats.items(): print(f'{k:14s} rows {n:5d} linked {g:5d}')
