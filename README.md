# Oppenheimer 128: text-reuse analysis

ניתוח שימוש חוזר בטקסט בכתב היד Bodleian MS. Oppenheim Add. 4° 128 (בערך 1372–1400). הניתוח בנוי בשרשרת: תעתיק eScriptorium HTR, השוואת שימוש חוזר בטקסט ב־ACT, ציון משוכלל שנלמד מתיוג ידני, ו"מטריושקה" של ציטוטים בין החיבורים.

**הממשק:** אחרי הפעלת GitHub Pages (ראו למטה) הוא זמין בכתובת
https://kashi-noam.github.io/Oppenheimer-manuscript-text-reuse-analysis/

## מבנה

| תיקייה | תוכן |
| --- | --- |
| `docs/` | האתר (GitHub Pages): `explorer/` סייר הנתונים, `graph/` גרף המטריושקה, `report/` דוח התיוג והרף |
| `pipeline/` | הקוד והנתונים בשלבי הביניים. `pipeline/` = סבב תיוג 1, `r2/` = סבב 2 והמודל, `r3/` = תיארוך, יחידות טקסט, השוואות, RDF |
| `data/raw/` | דוח ACT המקורי (`tr_report_288c1011….json.gz`, דחוס) |
| `outputs/excel/` | קובצי Excel: התיוג, המקורות מעל הסף, התיארוכים והפיילוט, המטריושקה |
| `outputs/rdf/` | RDF: המטריושקה (TTL, JSON-LD, SHACL) וההתאמות (`oppenheim128-matches.ttl`) |

## השלבים

1. **תיוג.** 487 זוגות (T001–T487) מ־80 קטעים. התוויות נמצאות ב־`pipeline/labels.tsv` וב־`pipeline/r2/labels2.tsv`, וההנחיות ב־`pipeline/r2/GUIDE.md`.
2. **ציון משוכלל.** רגרסיה לוגיסטית על מדדי ACT (`r2/data.py` → `r2/final.py` → `r2/diag.py` → `r2/feats2.py`). המקדמים נשמרים ב־`r2/model.json`. הרף הוא S ≥ 21.14 (p ≥ 0.8), עם דיוק 98.1% וכיסוי 85.8% באימות צולב לפי קטע.
3. **החלה על כל כתב היד** (`r3/build_list.py`): 1,272 מתוך 2,650 מועמדים עוברים את הרף.
4. **תיארוך.** 36 חיבורים, עם מקורות לכל תיארוך (`r3/datings_A.json`, `r3/datings_B.json`).
5. **מטריושקה.** `r3/units.py` → `r3/run_tests.py` → `r3/aggregate.py` מייצרים 538 יחידות טקסט ו־1,226 השוואות בין עדים.
6. **RDF והממשק.** `r3/build_rdf.py`, `r3/gui_data.py`, `r3/build_matches_rdf.py` (מריצים מתוך `r3/`).
7. **דוח התיוג.** `build_report2.py`.

### הרצה

```bash
pip install -r requirements.txt
cd pipeline/r3
python3 units.py && python3 run_tests.py && python3 aggregate.py && python3 build_rdf.py && python3 gui_data.py && python3 build_matches_rdf.py
```

- הסקריפטים מוצאים את הנתיבים לבד: `OPP_ROOT` = התיקייה `pipeline/`.
- את דוח ACT הם קוראים מ־`data/raw`. אפשר להחליף אותו בעזרת `OPP_ACT_REPORT`.
- קובצי הביניים (`*.pkl`) כלולים, כך שאפשר להריץ שלב בודד בלי לחזור על הקודמים.

**הערה:** כמה תוצרים נבנו בפקודות חד־פעמיות שלא נשמרו כסקריפט. אלה קובצי ה־Excel, `docs/graph/graph.json` ו־`pipeline/r2/allc_scored.pkl` (החלת המודל על כל 2,650 המועמדים). התוצרים עצמם כלולים.

## הפעלת האתר (GitHub Pages)

Settings → Pages → Build and deployment → Source: *Deploy from a branch* → Branch: `main`, תיקייה `/docs` → Save.

בלשונית "בדיקת השוואות" ההכרעות הידניות נשמרות בדפדפן (localStorage). לגיבוי או לשיתוף משתמשים בכפתור "ייצוא הבדיקות (CSV)".

## הסתייגויות

- הנתונים מבוססים על עד 30 מועמדים לקטע שקיבלו יישור מלא ב־ACT. היעדר עד אינו ראיה להיעדר הטקסט.
- הכרעות ההשוואה מצביעות על קרבה טקסטואלית, לא על העתקה מוכחת.
- מרחב השמות ב־RDF (`http://example.org/oppenheim128#`) הוא זמני.
- טקסטי המקורות מגיעים מקורפוס ACT וכפופים לרישיונות של המהדורות המקוריות.
