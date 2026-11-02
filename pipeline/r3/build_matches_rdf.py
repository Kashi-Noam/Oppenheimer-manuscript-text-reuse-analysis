import json,re
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, SKOS, DCTERMS, OWL
C=json.load(open('gui/core.json'))
OPP=Namespace('http://example.org/oppenheim128#')
g=Graph(); g.bind('opp',OPP); g.bind('skos',SKOS); g.bind('dcterms',DCTERMS); g.bind('xsd',XSD); g.bind('owl',OWL)
he=lambda s: Literal(s,lang='he')
slug=lambda s: re.sub(r'[^A-Za-z0-9_]+','_',s).strip('_')
g.add((OPP.Match,RDF.type,OWL.Class)); g.add((OPP.Match,RDFS.label,he('התאמה של ACT (יישור מלא)')))
g.add((OPP.Match,RDFS.comment,he('מועמד שדוח ACT יישר במלואו מול קטע באופנהיימר, עם ציוני ACT, הציון המשוכלל S וההסתברות p (סף: p ≥ 0.8, כלומר S ≥ 21.14), ותיוג ידני אם קיים.')))
for p,t in [('inPassage',OWL.ObjectProperty),('byWork',OWL.ObjectProperty),('viaSegment',OWL.ObjectProperty),('manualRelation',OWL.ObjectProperty),('labelConfidence',OWL.DatatypeProperty),
            ('labelId',OWL.DatatypeProperty),('actRank',OWL.DatatypeProperty),('actScore',OWL.DatatypeProperty),('normScore',OWL.DatatypeProperty),('alignScore',OWL.DatatypeProperty),
            ('alignedTokens',OWL.DatatypeProperty),('coverageSource',OWL.DatatypeProperty),('coveragePassage',OWL.DatatypeProperty),('probability',OWL.DatatypeProperty),('aboveThreshold',OWL.DatatypeProperty)]:
    g.add((OPP[p],RDF.type,t))
REL={'אותו טקסט':'rel_same','אותו טקסט · חלקי':'rel_same_partial','נוסח מקביל':'rel_parallel','אותו חיבור · קטע אחר':'rel_same_work_other','דרשה על המקור':'rel_homily',
     'ציטוט פסוק מהמקור':'rel_verse','ציטוט משותף':'rel_shared_quote','אין קשר':'rel_none'}
S=OPP.RelationScheme; g.add((S,RDF.type,SKOS.ConceptScheme)); g.add((S,SKOS.prefLabel,he('אופי הקשר (תיוג ידני)')))
for k,v in REL.items(): g.add((OPP[v],RDF.type,SKOS.Concept)); g.add((OPP[v],SKOS.inScheme,S)); g.add((OPP[v],SKOS.prefLabel,he(k)))
MS=OPP['MS_Oppenheim_128']
for p in C['passages']:
    n=OPP['passage_'+slug(p['pid'].replace('Oppenheimer_128_',''))]
    g.add((n,RDF.type,OPP.Passage)); g.add((n,DCTERMS.isPartOf,MS)); g.add((n,RDFS.label,Literal(p['folio']))); g.add((n,OPP.actPassageId,Literal(p['pid'])))
for c in C['cands']:
    m=OPP['match_'+slug(c['pid'].replace('Oppenheimer_128_',''))+'_'+str(c['rank'])]
    g.add((m,RDF.type,OPP.Match)); g.add((m,OPP.inPassage,OPP['passage_'+slug(c['pid'].replace('Oppenheimer_128_',''))]))
    g.add((m,OPP.byWork,OPP['work_'+slug(c['k'])])); sg=OPP['segment_'+slug(c['eid'])]; g.add((m,OPP.viaSegment,sg))
    g.add((sg,RDF.type,OPP.SourceSegment)); g.add((sg,OPP.actLocation,Literal(c['loc']))); g.add((sg,OPP.elasticId,Literal(c['eid']))); g.add((sg,OPP.ref,Literal(c['ref'])))
    for p,v,dt in [('actRank',c['rank'],XSD.integer),('actScore',c['score'],XSD.decimal),('normScore',c['norm'],XSD.decimal),('alignScore',c['align'],XSD.decimal),('alignedTokens',c['N'],XSD.integer),
                   ('coverageSource',c['C'],XSD.decimal),('coveragePassage',c['Cp'],XSD.decimal),('compositeScore',c['S'],XSD.decimal),('probability',c['p'],XSD.decimal)]:
        g.add((m,OPP[p],Literal(v,datatype=dt)))
    g.add((m,OPP.aboveThreshold,Literal(c['above'])))
    if 'tid' in c:
        g.add((m,OPP.labelId,Literal(c['tid']))); g.add((m,OPP.manualRelation,OPP[REL[c['rel']]])); g.add((m,OPP.labelConfidence,he(c['conf']))); g.add((m,RDFS.comment,he(c['note'])))
BF=Namespace('http://id.loc.gov/ontologies/bibframe/'); g.bind('bf',BF)
works={w['key'] for w in C['works']}
g.add((OPP.genre_tanakh,RDF.type,SKOS.Concept)); g.add((OPP.genre_tanakh,SKOS.prefLabel,he('תנ"ך'))); g.add((OPP.genre_tanakh,SKOS.inScheme,OPP.GenreScheme))
done=set()
for c in C['cands']:
    if c['k'] in works or c['k'] in done: continue
    done.add(c['k']); n=OPP['work_'+slug(c['k'])]
    g.add((n,RDF.type,BF.Work)); g.add((n,RDFS.label,he(c['work']))); g.add((n,RDFS.label,Literal(c['k'].replace('_',' '),lang='en')))
    if c['loc'].startswith('Tanakh'): g.add((n,BF.genreForm,OPP.genre_tanakh))
    g.add((n,SKOS.note,he('חיבור שמופיע רק בהתאמות מתחת לסף או בתנ"ך; לא תוארך בשלב הזה.')))
g.serialize('gui/oppenheim128-matches.ttl',format='turtle'); print(len(g))
# works not in matryoshka (dk used by below-threshold matches) -> check
miss={c['k'] for c in C['cands']}-works; print('works without node',len(miss),sorted(miss)[:20])
