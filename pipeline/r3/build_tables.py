"""Build docs/explorer/tables.json: the main Excel tables of the project, with a link from each row to the matching item in the explorer."""
import json, os, datetime
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
XL = os.path.join(ROOT, 'outputs', 'excel')
OUT = os.path.join(ROOT, 'docs', 'explorer', 'tables.json')
GH = 'https://github.com/Kashi-Noam/Oppenheimer-manuscript-text-reuse-analysis/raw/main/outputs/excel/'
C = json.load(open(os.path.join(ROOT, 'docs', 'explorer', 'core.json')))

W = {w['key']: w for w in C['works']}
CANDS = {c['id']: c for c in C['cands']}
FOLIO = {p['folio']: p['pid'] for p in C['passages']}
WORK = {w['name_he']: w['key'] for w in C['works']}
for c in C['cands']:
    if c['k'] in W: WORK.setdefault(c['work'], c['k'])
TID = {c['tid']: c['id'] for c in C['cands'] if c.get('tid')}
COMP = {(c['uid'], c['o'], c['n']): i for i, c in enumerate(C['comps'])}
UNITS = {u['uid'] for u in C['units']}

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

SRC, TAG, DAT, MAT = ('oppenheim128_sources_above_threshold.xlsx', 'oppenheim128_tagging_v3.xlsx',
                      'oppenheim128_datings_and_pilot.xlsx', 'oppenheim128_matryoshka.xlsx')
TAG_COLS = ['מזהה', 'סבב', 'דף', 'rank', 'חיבור', 'מראה מקום', 'קשר', 'סמך', 'הערה', 'ציון משוכלל S', 'הסתברות p', 'מעל הסף', 'סיבה (מתחת לסף)']
SPEC = [
    ('sources', 'המקורות מעל הסף', SRC, [
        ('src_work', 'לפי חיבור', 'כל חיבור שיש לו לפחות התאמה אחת מעל הסף: בכמה קטעים, כמה התאמות, וחציון ומקסימום של הציון המשוכלל S.', go_work, None),
        ('src_pass', 'לפי קטע', 'כל קטע באופנהיימר: אילו חיבורים עברו את הסף, וההתאמה החזקה ביותר שלו.', go_passage, None),
        ('src_all', 'כל ההתאמות', 'כל ההתאמות מעל הסף (S ≥ 21.14), כולל מדדי ACT ותיוג ידני כשיש.', go_cand, None),
        ('src_near', 'קרובים לסף', 'התאמות קרובות לסף (0.2 ≤ p < 0.8), ואם עברו בכלל השלמה.', go_cand, None)]),
    ('tagging', 'התיוג והמודל', TAG, [
        ('tag_all', 'תיוג', '487 הזוגות המתויגים, עם הקשר, רמת הסמך, ההערה והציון המשוכלל. העמודות המלאות בקובץ ה-Excel.', go_tid, TAG_COLS),
        ('tag_below', 'זהים מתחת לסף', 'זוגות שתויגו כזהים אבל נפלו מתחת לסף, עם הסיבה ודרך התיקון.', go_tid, None),
        ('tag_sum', 'סיכום לפי קשר', 'חציוני המדדים לכל סוג קשר.', None, None),
        ('tag_model', 'ציון וסף', 'מקדמי הרגרסיה הלוגיסטית.', None, None)]),
    ('datings', 'תיארוכים', DAT, [
        ('dat_works', 'תיארוכים', 'תיארוך כל חיבור כטווח שנים, ודאות, אזור, מחלוקות ומקורות.', go_work, None),
        ('dat_pilot', 'פיילוט 20 שלשות', 'הפיילוט של בדיקות הקרבה על 20 שלישיות, מול קריאה ידנית.', go_pilot, None)]),
    ('matryoshka', 'מטריושקה', MAT, [
        ('mat_works', 'חיבורים', 'לכל חיבור: בכמה יחידות הוא מעיד, בכמה הוא העד היחיד, הקרוב ביותר והמוקדם ביותר.', go_work, None),
        ('mat_pairs', 'זוגות חיבורים', 'לכל זוג חיבורים: כמה יחידות משותפות וכמה הכרעות מכל סוג.', go_pair, None),
        ('mat_units', 'יחידות', 'יחידות הטקסט והעדים שלהן.', go_unit, None),
        ('mat_comps', 'השוואות', 'כל ההשוואות בין עד ישן לעד חדש ביחידה, עם הראיות וההכרעה.', go_comp, None)]),
]

groups, tables, stats = [], [], {}
for gid, gtitle, fname, sheets in SPEC:
    groups.append(dict(id=gid, title=gtitle, file=fname, url=GH + fname, note=note(fname), tables=[s[0] for s in sheets]))
    for tid, sheet, desc, go, cols in sheets:
        head, body = read(fname, sheet)
        if tid == 'mat_comps': body = [r for r in body if '#' in str(r[0])]
        gos = [go(r, head) if go else None for r in body]
        if cols:
            idx = [head.index(c) for c in cols if c in head]
            head, body = [head[i] for i in idx], [[r[i] for i in idx] for r in body]
        tables.append(dict(id=tid, group=gid, title=sheet, desc=desc, cols=head, rows=body, go=gos))
        stats[tid] = (len(body), sum(1 for g in gos if g))
json.dump(dict(groups=groups, tables=tables), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(round(os.path.getsize(OUT) / 1e6, 2), 'MB')
for k, (n, g) in stats.items(): print(f'{k:10s} rows {n:5d} linked {g:5d}')
