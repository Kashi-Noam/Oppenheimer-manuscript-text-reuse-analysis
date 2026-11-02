import os as _os; ROOT = _os.environ.get('OPP_ROOT', _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # = pipeline/
"""Build the Oppenheim-128 'matryoshka' graph as RDF (Turtle + JSON-LD) and SHACL shapes."""
import json, re, hashlib, datetime
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, SKOS, DCTERMS, OWL, PROV, DCAT, VOID, TIME

J = json.load(open(ROOT + '/r3/matryoshka.json'))
OPP = Namespace('http://example.org/oppenheim128#')
MDR = Namespace('http://example.org/midrash#')
BF = Namespace('http://id.loc.gov/ontologies/bibframe/')
OA = Namespace('http://www.w3.org/ns/oa#')
SCHEMA = Namespace('https://schema.org/')
SH = Namespace('http://www.w3.org/ns/shacl#')

g = Graph()
for p, n in [('opp', OPP), ('mdr', MDR), ('bf', BF), ('oa', OA), ('schema', SCHEMA), ('skos', SKOS), ('dcterms', DCTERMS), ('owl', OWL),
             ('prov', PROV), ('dcat', DCAT), ('void', VOID), ('time', TIME), ('xsd', XSD)]:
    g.bind(p, n)
he = lambda s: Literal(s, lang='he'); en = lambda s: Literal(s, lang='en')
def slug(s): return re.sub(r'[^A-Za-z0-9_]+', '_', s).strip('_')
def gyear(y): return Literal(f'{int(y):04d}', datatype=XSD.gYear)

# ---------------- ontology header + local vocabulary ----------------
ONT = URIRef('http://example.org/oppenheim128')
g.add((ONT, RDF.type, OWL.Ontology))
g.add((ONT, RDFS.label, he('מטריושקה של ציטוטים – אופנהיימר 128')))
g.add((ONT, RDFS.label, en('Citation matryoshka – MS Oppenheim 128')))
g.add((ONT, OWL.versionInfo, Literal('0.1')))
g.add((ONT, RDFS.comment, he('אוצר מונחים מקומי. מרחב השמות http://example.org/oppenheim128# הוא זמני ויש להחליפו לפני פרסום, כמו mdr: בפרויקט midrash-rdf.')))
CLASSES = {
 'DatingAssertion': ('טענת תיארוך', 'Dating assertion', 'צומת n-ary: טווח תיארוך לחיבור, עם מקור, ודאות ואזור.'),
 'Passage': ('קטע בכתב היד', 'Manuscript passage', 'קטע (דף או חלק מדף) של אופנהיימר 128 כפי שהוגדר בדוח ACT.'),
 'TextUnit': ('יחידת טקסט', 'Text unit', 'רצף מילים בקטע של אופנהיימר שכמה עדים מתיישרים אליו (חפיפה ≥50%).'),
 'TokenPositionSelector': ('בורר לפי מיקום מילים', 'Token position selector', 'בורר Web Annotation לפי מספרי מילים (0-based, end לא כולל).'),
 'SourceSegment': ('סגמנט מקור', 'Source segment', 'סגמנט בקורפוס של ACT (מזהה מיקום ו-elastic id).'),
 'Attestation': ('עדות', 'Attestation', 'צומת n-ary: חיבור מעיד על יחידת טקסט באופנהיימר דרך סגמנט אחד או יותר.'),
 'PathComparison': ('השוואת מסלולים', 'Path comparison', 'צומת n-ary: לשני עדים לאותה יחידה – תמיכה במסלול הישיר (ישן←אופנהיימר) ובמסלול דרך החדש (ישן←חדש←אופנהיימר).'),
 'SharedTextRelation': ('קשר טקסט משותף', 'Shared-text relation', 'קשת מסוכמת בין שני חיבורים: מספר יחידות משותפות וספירת ההכרעות.'),
 'WitnessSummary': ('סיכום עדות לאופנהיימר', 'Witness summary', 'קשת מסוכמת בין חיבור לאופנהיימר: מספר יחידות ובכמה מהן החיבור הוא העד הקרוב ביותר.'),
}
for c, (h, e, cm) in CLASSES.items():
    g.add((OPP[c], RDF.type, OWL.Class)); g.add((OPP[c], RDFS.label, he(h))); g.add((OPP[c], RDFS.label, en(e))); g.add((OPP[c], RDFS.comment, he(cm)))
g.add((OPP.TokenPositionSelector, RDFS.subClassOf, OA.Selector))
g.add((OPP.TextUnit, RDFS.subClassOf, OA.SpecificResource))
g.add((OPP.DatingAssertion, RDFS.subClassOf, TIME.ProperInterval))
PROPS = {
 'hasDating': ('תיארוך', OWL.ObjectProperty), 'confidence': ('ודאות', OWL.ObjectProperty), 'chronologyRelativeToOppenheim': ('ביחס לאופנהיימר', OWL.ObjectProperty),
 'ofUnit': ('של יחידה', OWL.ObjectProperty), 'byWork': ('על ידי חיבור', OWL.ObjectProperty), 'viaSegment': ('דרך סגמנט', OWL.ObjectProperty),
 'olderWitness': ('עד ישן', OWL.ObjectProperty), 'newerWitness': ('עד חדש', OWL.ObjectProperty), 'verdict': ('הכרעה', OWL.ObjectProperty),
 'closestWitness': ('העד הקרוב ביותר', OWL.ObjectProperty), 'earliestWitness': ('העד המוקדם ביותר', OWL.ObjectProperty),
 'olderWork': ('חיבור ישן', OWL.ObjectProperty), 'newerWork': ('חיבור חדש', OWL.ObjectProperty), 'work': ('חיבור', OWL.ObjectProperty), 'target': ('יעד', OWL.ObjectProperty),
 'actLocation': ('מזהה מיקום ב-ACT', OWL.DatatypeProperty), 'elasticId': ('elastic id', OWL.DatatypeProperty), 'ref': ('מראה מקום', OWL.DatatypeProperty),
 'actPassageId': ('מזהה קטע ב-ACT', OWL.DatatypeProperty), 'compositeScore': ('ציון משוכלל S', OWL.DatatypeProperty), 'segmentScore': ('S של סגמנט', OWL.DatatypeProperty),
 'directPathSupport': ('תמיכה במסלול הישיר', OWL.DatatypeProperty), 'viaPathSupport': ('תמיכה במסלול דרך החדש', OWL.DatatypeProperty),
 'evOppOlderNotNewer': ('מילים באופנהיימר ובישן, חסרות בחדש', OWL.DatatypeProperty), 'evOppNewerNotOlder': ('מילים באופנהיימר ובחדש, חסרות בישן', OWL.DatatypeProperty),
 'evSharedOmission': ('מילים בישן שחסרות באופנהיימר ובחדש', OWL.DatatypeProperty), 'evReadingOlder': ('נוסחאות כמו הישן', OWL.DatatypeProperty),
 'evReadingNewer': ('נוסחאות כמו החדש', OWL.DatatypeProperty), 'evOrderOlder': ('סדר כמו הישן', OWL.DatatypeProperty), 'evOrderNewer': ('סדר כמו החדש', OWL.DatatypeProperty),
 'evBoundaryOlder': ('גבולות כמו הישן', OWL.DatatypeProperty), 'evBoundaryNewer': ('גבולות כמו החדש', OWL.DatatypeProperty),
 'orderCertain': ('סדר התיארוך ודאי', OWL.DatatypeProperty), 'newerIsLate': ('החדש מאוחר לאופנהיימר', OWL.DatatypeProperty),
 'sharedUnits': ('יחידות משותפות', OWL.DatatypeProperty), 'viaCount': ('הכרעות "דרך החדש"', OWL.DatatypeProperty), 'directCount': ('הכרעות "ישיר"', OWL.DatatypeProperty),
 'undeterminedCount': ('הכרעות "לא מוכרע"', OWL.DatatypeProperty), 'units': ('יחידות', OWL.DatatypeProperty), 'soleWitnessUnits': ('יחידות שבהן הוא העד היחיד', OWL.DatatypeProperty),
 'closestAmongSeveralUnits': ('יחידות שבהן הוא הקרוב ביותר מבין כמה עדים', OWL.DatatypeProperty), 'earliestAmongSeveralUnits': ('יחידות שבהן הוא המוקדם מבין כמה עדים', OWL.DatatypeProperty),
}
for p, (h, t) in PROPS.items():
    g.add((OPP[p], RDF.type, t)); g.add((OPP[p], RDFS.label, he(h)))

def scheme(name, label, items):
    S = OPP[name]; g.add((S, RDF.type, SKOS.ConceptScheme)); g.add((S, SKOS.prefLabel, he(label)))
    for k, (h, e) in items.items():
        c = OPP[k]; g.add((c, RDF.type, SKOS.Concept)); g.add((c, SKOS.inScheme, S)); g.add((c, SKOS.prefLabel, he(h))); g.add((c, SKOS.prefLabel, en(e)))
scheme('GenreScheme', 'סוג חיבור', {'genre_midrash': ('מדרש', 'Midrash'), 'genre_anthology': ('ילקוט / אוסף', 'Anthology / compilation'),
                                     'genre_talmud': ('תלמוד', 'Talmud'), 'genre_minor_tractate': ('מסכת קטנה', 'Minor tractate'), 'genre_manuscript': ('כתב יד', 'Manuscript')})
scheme('ChronologyScheme', 'ביחס לאופנהיימר (1372–1400)', {'chron_before': ('קודם לאופנהיימר', 'Before Oppenheim 128'), 'chron_overlap': ('חופף לתקופת אופנהיימר', 'Overlapping'), 'chron_after': ('מאוחר לאופנהיימר', 'After Oppenheim 128 (implausible as a source)')})
scheme('ConfidenceScheme', 'ודאות התיארוך', {'conf_high': ('גבוהה', 'high'), 'conf_medium': ('בינונית', 'medium'), 'conf_low': ('נמוכה', 'low')})
scheme('VerdictScheme', 'הכרעת השוואת מסלולים', {'verdict_via': ('דרך החדש: אופנהיימר קרוב יותר לעד החדש', 'Via newer: Oppenheim closer to the newer witness'),
                                                 'verdict_direct': ('ישיר: אופנהיימר קרוב יותר לעד הישן', 'Direct: Oppenheim closer to the older witness'),
                                                 'verdict_undetermined': ('לא מוכרע', 'Undetermined')})
GEN = {'מדרש': 'genre_midrash', 'ילקוט / אוסף': 'genre_anthology', 'תלמוד': 'genre_talmud', 'מסכת קטנה': 'genre_minor_tractate', 'כתב יד': 'genre_manuscript'}
regions = sorted({w['region'] for w in J['works'] if w['region']})
REG = {r: f'region_{i:02d}' for i, r in enumerate(regions, 1)}
scheme('RegionScheme', 'אזור חיבור (מידע בלבד, לא פוסל קשרים)', {v: (k, k) for k, v in REG.items()})

def add_dating(node_key, x, srcs):
    dn = OPP[f'dating_{node_key}']
    g.add((dn, RDF.type, OPP.DatingAssertion)); g.add((dn, RDF.type, TIME.ProperInterval))
    for prop, y in ((TIME.hasBeginning, x['date_from']), (TIME.hasEnd, x['date_to'])):
        b = OPP[f'dating_{node_key}_{"begin" if prop == TIME.hasBeginning else "end"}']
        g.add((dn, prop, b)); g.add((b, RDF.type, TIME.Instant)); g.add((b, TIME.inXSDgYear, gyear(y)))
    g.add((dn, DCTERMS.date, Literal(f"{int(x['date_from']):04d}/{int(x['date_to']):04d}")))
    g.add((dn, RDFS.label, he(x['date_he'])))
    if x.get('confidence'): g.add((dn, OPP.confidence, OPP[f"conf_{x['confidence']}"]))
    if x.get('dispute'): g.add((dn, SKOS.note, he(x['dispute']) if re.search('[֐-׿]', x['dispute']) else en(x['dispute'])))
    if x.get('region'): g.add((dn, DCTERMS.spatial, OPP[REG[x['region']]]))
    if x.get('region_note'): g.add((dn, SKOS.scopeNote, Literal(x['region_note'])))
    for s in srcs:
        sid = OPP['source_' + hashlib.md5((s['title'] + s['url']).encode()).hexdigest()[:10]]
        g.add((sid, RDF.type, DCTERMS.BibliographicResource)); g.add((sid, DCTERMS.title, Literal(s['title'])))
        if s.get('url'): g.add((sid, SCHEMA.url, Literal(s['url'], datatype=XSD.anyURI)))
        g.add((dn, DCTERMS.source, sid))
        g.add((dn, SKOS.editorialNote, Literal(f"{s['title']}: {s['says']}")))
    return dn

# ---------------- manuscript ----------------
o = J['opp']; OW = OPP['work_Oppenheim_128']; MS = OPP['MS_Oppenheim_128']
g.add((OW, RDF.type, BF.Work)); g.add((OW, RDFS.label, he(o['name_he']))); g.add((OW, RDFS.label, en(o['name_en']))); g.add((OW, BF.genreForm, OPP.genre_manuscript))
g.add((OW, OPP.hasDating, add_dating('Oppenheim_128', dict(o, confidence='medium'), [])))
g.add((MS, RDF.type, BF.Item)); g.add((MS, BF.itemOf, OW)); g.add((MS, RDFS.label, en('Oxford, Bodleian Library, MS. Oppenheim Add. 4° 128')))

# ---------------- works ----------------
W = {}
for w in J['works']:
    n = OPP['work_' + slug(w['key'])]; W[w['key']] = n
    g.add((n, RDF.type, BF.Work)); g.add((n, RDF.type, MDR.Hibbur))
    g.add((n, RDFS.label, he(w['name_he']))); g.add((n, RDFS.label, en(w['name_en'])))
    g.add((n, BF.genreForm, OPP[GEN[w['type']]]))
    g.add((n, OPP.hasDating, add_dating(slug(w['key']), w, w['sources'])))
    g.add((n, OPP.chronologyRelativeToOppenheim, OPP[f"chron_{w['rel']}"]))
    for f in w['files']: g.add((n, SKOS.notation, Literal(f)))
    s = OPP['witnessSummary_' + slug(w['key'])]
    g.add((s, RDF.type, OPP.WitnessSummary)); g.add((s, OPP.work, n)); g.add((s, OPP.target, OW))
    g.add((s, OPP.units, Literal(w['n_units']))); g.add((s, OPP.soleWitnessUnits, Literal(w['n_only'])))
    g.add((s, OPP.closestAmongSeveralUnits, Literal(w['n_closest'] - w['n_only']))); g.add((s, OPP.earliestAmongSeveralUnits, Literal(w['n_earliest'])))

# ---------------- passages, units, attestations ----------------
seen_p = set()
for u in J['units']:
    p = OPP['passage_' + slug(u['pid'].replace('Oppenheimer_128_', ''))]
    if p not in seen_p:
        seen_p.add(p); g.add((p, RDF.type, OPP.Passage)); g.add((p, DCTERMS.isPartOf, MS)); g.add((p, RDFS.label, Literal(u['folio'])))
        g.add((p, OPP.actPassageId, Literal(u['pid'])))
    un = OPP['unit_' + slug(u['uid'])]
    g.add((un, RDF.type, OPP.TextUnit)); g.add((un, OA.hasSource, p)); g.add((un, RDFS.label, Literal(u['uid'])))
    sel = OPP['unit_' + slug(u['uid']) + '_selector']
    g.add((un, OA.hasSelector, sel)); g.add((sel, RDF.type, OPP.TokenPositionSelector))
    g.add((sel, OA.start, Literal(u['lo'], datatype=XSD.nonNegativeInteger))); g.add((sel, OA.end, Literal(u['hi'] + 1, datatype=XSD.nonNegativeInteger)))
    g.add((un, RDF.value, he(u['text'])))
    for k in u['closest']: g.add((un, OPP.closestWitness, W[k]))
    g.add((un, OPP.earliestWitness, W[u['earliest']]))
    for wt in u['witnesses']:
        a = OPP['att_' + slug(u['uid']) + '_' + slug(wt['work'])]
        g.add((a, RDF.type, OPP.Attestation)); g.add((a, OPP.ofUnit, un)); g.add((a, OPP.byWork, W[wt['work']])); g.add((a, OPP.compositeScore, Literal(wt['S'], datatype=XSD.decimal)))
        for sgm in wt['segments']:
            sn = OPP['segment_' + slug(sgm['eid'])]
            g.add((sn, RDF.type, OPP.SourceSegment)); g.add((sn, OPP.actLocation, Literal(sgm['loc']))); g.add((sn, OPP.elasticId, Literal(sgm['eid'])))
            g.add((sn, OPP.ref, Literal(sgm['ref']))); g.add((sn, DCTERMS.isPartOf, W[wt['work']])); g.add((sn, OPP.segmentScore, Literal(sgm['S'], datatype=XSD.decimal)))
            g.add((a, OPP.viaSegment, sn))

# ---------------- path comparisons ----------------
EV = {'opp_O_notM': 'evOppOlderNotNewer', 'opp_M_notO': 'evOppNewerNotOlder', 'shared_omission': 'evSharedOmission', 'reading_O': 'evReadingOlder',
      'reading_M': 'evReadingNewer', 'order_O': 'evOrderOlder', 'order_M': 'evOrderNewer', 'boundary_O': 'evBoundaryOlder', 'boundary_M': 'evBoundaryNewer'}
for h in J['hypotheses']:
    c = OPP[f"cmp_{slug(h['uid'])}_{slug(h['older'])}__{slug(h['newer'])}"]
    g.add((c, RDF.type, OPP.PathComparison)); g.add((c, OPP.ofUnit, OPP['unit_' + slug(h['uid'])]))
    g.add((c, OPP.olderWitness, W[h['older']])); g.add((c, OPP.newerWitness, W[h['newer']]))
    g.add((c, OPP.verdict, OPP['verdict_' + h['verdict']]))
    g.add((c, OPP.directPathSupport, Literal(h['direct'], datatype=XSD.decimal))); g.add((c, OPP.viaPathSupport, Literal(h['via'], datatype=XSD.decimal)))
    for k, p in EV.items(): g.add((c, OPP[p], Literal(int(h['ev'].get(k, 0)))))
    g.add((c, OPP.orderCertain, Literal(h['order_certain']))); g.add((c, OPP.newerIsLate, Literal(h['newer_late'])))

# ---------------- aggregated edges ----------------
for e in J['edges']:
    r = OPP[f"shared_{slug(e['older'])}__{slug(e['newer'])}"]
    g.add((r, RDF.type, OPP.SharedTextRelation)); g.add((r, OPP.olderWork, W[e['older']])); g.add((r, OPP.newerWork, W[e['newer']]))
    g.add((r, OPP.sharedUnits, Literal(e['units']))); g.add((r, OPP.viaCount, Literal(e['via']))); g.add((r, OPP.directCount, Literal(e['direct'])))
    g.add((r, OPP.undeterminedCount, Literal(e['undetermined']))); g.add((r, OPP.orderCertain, Literal(e['order_certain']))); g.add((r, OPP.newerIsLate, Literal(e['newer_late'])))

# ---------------- dataset + provenance ----------------
DS = OPP['dataset']; ACT = OPP['activity_matryoshka_2026_11']; SRC = OPP['act_report_288c1011']
g.add((DS, RDF.type, DCAT.Dataset)); g.add((DS, RDF.type, VOID.Dataset))
g.add((DS, DCTERMS.title, he('מטריושקה של ציטוטים באופנהיימר 128: חיבורים, תיארוכים ויחידות טקסט משותפות')))
g.add((DS, DCTERMS.created, Literal(datetime.date.today().isoformat(), datatype=XSD.date)))
g.add((DS, DCTERMS.description, he(
    'צמתים: חיבורים (bf:Work) עם טענות תיארוך (טווח OWL-Time, אזור, מקור, ודאות). קשתות: יחידות טקסט משותפות. '
    'לכל זוג עדים ליחידה יש צומת השוואה עם התמיכה בשני המסלולים: ישן←אופנהיימר, וישן←חדש←אופנהיימר. '
    'ההכרעה מבטאת קרבה טקסטואלית ולא הוכחת העתקה. חיבורים מאוחרים לאופנהיימר מסומנים ואינם נפסלים; האזור הוא מידע בלבד.')))
g.add((DS, SKOS.note, he(
    'הסתייגות: הנתונים מבוססים רק על מועמדים שדוח ACT החזיר (עד 30 לכל קטע), שקיבלו יישור מלא, ושעברו את הסף המשוכלל S ≥ 21.14 '
    '(דיוק 98% וכיסוי 86% על 487 זוגות מתויגים). היעדר עד אינו ראיה להיעדר הטקסט. נוסח כל חיבור הוא המהדורה שבספריא; '
    'קיצורי "וכו\'" עשויים להיות של המדפיס. התיארוכים נאספו ממקורות זמינים (בעיקר Encyclopaedia Judaica וויקיפדיה האנגלית), לא מ"מבוא למדרשים" של רייזל.')))
g.add((DS, PROV.wasGeneratedBy, ACT)); g.add((ACT, RDF.type, PROV.Activity)); g.add((ACT, PROV.used, SRC))
g.add((SRC, RDF.type, PROV.Entity)); g.add((SRC, RDFS.label, Literal('tr_report_288c1011-282d-4644-9959-2f1b093a6b33.json (ACT)')))
g.add((ACT, RDFS.comment, he('מבחנים: תוספות/השמטות, סדר יחידות סמוכות, הסכמה בנוסחאות, גבולות יחידה. ציון ישיר = מילים באופנהיימר ובישן שחסרות בחדש + 3×סדר + 2×גבולות + 0.5×נוסחאות. '
                           'ציון דרך החדש = מילים באופנהיימר ובחדש שחסרות בישן + 0.25×השמטה משותפת + 3×סדר + 2×גבולות + 0.5×נוסחאות. הכרעה: ציון ≥4, כפול מהשני, ולפחות ראיה חיובית אחת.')))
g.add((DS, VOID.triples, Literal(len(g) + 1)))
g.add((DS, DCTERMS.license, Literal('לא נקבע – להשלים לפני פרסום')))

g.serialize(ROOT + '/r3/oppenheim128-matryoshka.ttl', format='turtle')
g.serialize(ROOT + '/r3/oppenheim128-matryoshka.jsonld', format='json-ld', indent=1)
print('triples', len(g))

# ---------------- SHACL ----------------
S = Graph(); S.bind('sh', SH); S.bind('opp', OPP); S.bind('bf', BF); S.bind('oa', OA); S.bind('time', TIME); S.bind('xsd', XSD); S.bind('dcterms', DCTERMS)
def shape(name, target, props):
    sh = OPP[name + 'Shape']; S.add((sh, RDF.type, SH.NodeShape)); S.add((sh, SH.targetClass, target))
    for path, kw in props:
        b = BNode(); S.add((sh, SH.property, b)); S.add((b, SH.path, path))
        for k, v in kw.items(): S.add((b, SH[k], v))
one = lambda **k: dict(minCount=Literal(1), maxCount=Literal(1), **k)
shape('Work', BF.Work, [(OPP.hasDating, one(**{'class': OPP.DatingAssertion})), (RDFS.label, dict(minCount=Literal(1)))])
shape('Dating', OPP.DatingAssertion, [(TIME.hasBeginning, one()), (TIME.hasEnd, one()), (DCTERMS.date, one(datatype=XSD.string))])
shape('TextUnit', OPP.TextUnit, [(OA.hasSource, one(**{'class': OPP.Passage})), (OA.hasSelector, one(**{'class': OPP.TokenPositionSelector})), (OPP.earliestWitness, one(**{'class': BF.Work}))])
shape('Attestation', OPP.Attestation, [(OPP.ofUnit, one(**{'class': OPP.TextUnit})), (OPP.byWork, one(**{'class': BF.Work})), (OPP.viaSegment, dict(minCount=Literal(1)))])
shape('PathComparison', OPP.PathComparison, [(OPP.ofUnit, one()), (OPP.olderWitness, one(**{'class': BF.Work})), (OPP.newerWitness, one(**{'class': BF.Work})),
      (OPP.verdict, one()), (OPP.directPathSupport, one(datatype=XSD.decimal)), (OPP.viaPathSupport, one(datatype=XSD.decimal))])
shape('SharedText', OPP.SharedTextRelation, [(OPP.olderWork, one()), (OPP.newerWork, one()), (OPP.sharedUnits, one(datatype=XSD.integer))])
S.serialize(ROOT + '/r3/oppenheim128-matryoshka-shapes.ttl', format='turtle')
