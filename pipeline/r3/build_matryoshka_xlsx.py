"""Build outputs/excel/oppenheim128_matryoshka.xlsx from matryoshka.json (explanation, works, work pairs, units, comparisons)."""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'outputs', 'excel', 'oppenheim128_matryoshka.xlsx')
J = json.load(open(os.path.join(HERE, 'matryoshka.json')))
W = {w['key']: w for w in J['works']}
name = lambda k: W[k]['name_he'] if k in W else k
REL = {'before': 'קודם', 'overlap': 'חופף', 'after': 'מאוחר'}
VER = {'direct': 'ישיר', 'via': 'דרך החדש', 'undetermined': 'לא מוכרע'}
yn = lambda b: 'כן' if b else 'לא'
st = J['stats']; vc = st['verdicts']

wb = Workbook()
def sheet(title, header, rows, widths=None, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title; ws.sheet_view.rightToLeft = True
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill('solid', fgColor='E3ECF5'); c.alignment = Alignment(wrap_text=True, vertical='top')
    for r in rows: ws.append(r)
    ws.freeze_panes = 'A2'
    if rows: ws.auto_filter.ref = f'A1:{get_column_letter(len(header))}{len(rows) + 1}'
    for i, w in enumerate(widths or [], 1): ws.column_dimensions[get_column_letter(i)].width = w
    return ws

sheet('הסבר', ['נושא', 'פירוט'], [
    ['מה בקובץ', 'ההרצה המלאה של בדיקת ה"מטריושקה": חיבורים, זוגות חיבורים, יחידות טקסט והשוואות בין עדים. אותם נתונים שבקובץ ה-RDF ובגרף, בפורמט שנוח לבדיקה ידנית.'],
    ['יחידת טקסט', 'התאמות מעל הסף (S ≥ 21.14) שמכסות לפחות 50% מאותן מילים באופנהיימר אוחדו ליחידה אחת; סגמנטים של אותו חיבור חוברו לעד אחד.'],
    ['הכרעות', 'ישיר = אופנהיימר קרוב יותר לעד הישן (תומך בישן←אופנהיימר). דרך החדש = קרוב יותר לעד החדש (תומך בישן←חדש←אופנהיימר). לא מוכרע = ראיות חסרות או סותרות. זו קרבה טקסטואלית, לא הוכחת העתקה.'],
    ['ציונים', 'דרך החדש = מילים באופנהיימר ובחדש בלבד + ¼·השמטה משותפת + 3·סדר + 2·גבולות + ½·נוסחאות. ישיר = מילים באופנהיימר ובישן בלבד + 3·סדר + 2·גבולות + ½·נוסחאות. הכרעה רק כשציון ≥ 4, לפחות פי 2 מהשני, ויש ראיה חיובית.'],
    ['הסתייגות', 'רק מועמדים שדוח ACT החזיר (עד 30 לקטע), שקיבלו יישור מלא ועברו את הסף. היעדר עד אינו ראיה להיעדר הטקסט. נוסח המקורות הוא המהדורה שבספריא.'],
    ['סטטיסטיקה', f"{st['units']} יחידות, {st['units_multi']} עם כמה עדים, {st['hyps']} השוואות: ישיר {vc.get('direct', 0)}, דרך החדש {vc.get('via', 0)}, לא מוכרע {vc.get('undetermined', 0)}."],
], [16, 120], first=True)

sheet('חיבורים', ['חיבור', 'משנה', 'עד', 'ביחס לאופנהיימר', 'סוג', 'אזור', 'ודאות', 'יחידות', 'עד יחיד', 'הקרוב מבין כמה', 'המוקדם מבין כמה'],
      [[w['name_he'], w['date_from'], w['date_to'], REL[w['rel']], w['type'], w['region'], w['confidence'], w['n_units'], w['n_only'],
        w['n_closest'] - w['n_only'], w['n_earliest']] for w in sorted(J['works'], key=lambda w: -w['n_units'])],
      [34, 8, 8, 14, 14, 16, 10, 9, 9, 13, 13])

sheet('זוגות חיבורים', ['חיבור ישן', 'חיבור חדש', 'יחידות משותפות', 'ישיר', 'דרך החדש', 'לא מוכרע', 'סדר תיארוך ודאי', 'החדש מאוחר לאופנהיימר'],
      [[name(e['older']), name(e['newer']), e['units'], e['direct'], e['via'], e['undetermined'], yn(e['order_certain']), yn(e['newer_late'])] for e in J['edges']],
      [34, 34, 12, 8, 10, 10, 14, 16])

sheet('יחידות', ['יחידה', 'קטע', 'עדים', 'מספר עדים', 'הקרוב ביותר', 'המוקדם ביותר', 'טקסט באופנהיימר'],
      [[u['uid'], u['folio'], ' | '.join(f"{name(w['work'])}: {', '.join(s['ref'] for s in w['segments'])}" for w in u['witnesses']),
        u['n_wit'], ', '.join(name(k) for k in u['closest']), name(u['earliest']), u['text'][:500]] for u in J['units']],
      [20, 14, 60, 9, 26, 26, 80])

ev = lambda h, k: h['ev'].get(k, 0)
sheet('השוואות', ['יחידה', 'עד ישן', 'עד חדש', 'הכרעה', 'ציון ישיר', 'ציון דרך החדש', 'באופנהיימר ובישן, חסר בחדש', 'באופנהיימר ובחדש, חסר בישן',
                  'השמטה משותפת', 'נוסחאות כמו הישן', 'נוסחאות כמו החדש', 'סדר כמו הישן', 'סדר כמו החדש', 'סדר תיארוך ודאי', 'החדש מאוחר',
                  'דוגמה: באופנהיימר ובישן בלבד', 'דוגמה: באופנהיימר ובחדש בלבד', 'בדיקה ידנית', 'הערה'],
      [[h['uid'], name(h['older']), name(h['newer']), VER[h['verdict']], h['direct'], h['via'], ev(h, 'opp_O_notM'), ev(h, 'opp_M_notO'),
        ev(h, 'shared_omission'), ev(h, 'reading_O'), ev(h, 'reading_M'), ev(h, 'order_O'), ev(h, 'order_M'), yn(h['order_certain']), yn(h['newer_late']),
        (h['ex_O'] or [''])[0], (h['ex_M'] or [''])[0], '', ''] for h in J['hypotheses']],
      [20, 26, 26, 11, 9, 11, 12, 12, 10, 10, 10, 9, 9, 10, 9, 40, 40, 12, 30])

os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print('saved', OUT, [ws.title for ws in wb.worksheets], len(J['hypotheses']), 'comparisons')
