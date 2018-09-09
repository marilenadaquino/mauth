import rdflib
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS

HICO = Namespace("http://purl.org/emmedi/hico/")
DBO = Namespace("http://dbpedia.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")
base = 'http://purl.org/emmedi/mauth/criteria/'

g=rdflib.ConjunctiveGraph(identifier=URIRef(base))
g.bind('hico', HICO)

g.add(( URIRef(base+'documentation'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'documentation'), RDFS.label, Literal('documentation') ))
g.add(( URIRef(base+'documentation'), DBO.rating, Literal('10.0', datatype=XSD.float) ))

g.add(( URIRef(base+'artist-signature'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'artist-signature'), RDFS.label, Literal('artist\'s signature') ))
g.add(( URIRef(base+'artist-signature'), DBO.rating, Literal('10.0', datatype=XSD.float) ))

g.add(( URIRef(base+'archival-creator-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'archival-creator-attribution'), RDFS.label, Literal('archival creator\'s attribution') ))
g.add(( URIRef(base+'archival-creator-attribution'), DBO.rating, Literal('9.0', datatype=XSD.float) ))

g.add(( URIRef(base+'archival-creator-bibliography'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'archival-creator-bibliography'), RDFS.label, Literal('archival creator\'s bibliography') ))
g.add(( URIRef(base+'archival-creator-bibliography'), DBO.rating, Literal('8.0', datatype=XSD.float) ))

g.add(( URIRef(base+'bibliography'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'bibliography'), RDFS.label, Literal('bibliography') ))
g.add(( URIRef(base+'bibliography'), DBO.rating, Literal('7.0', datatype=XSD.float) ))

g.add(( URIRef(base+'archival-classification'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'archival-classification'), RDFS.label, Literal('archival classification') ))
g.add(( URIRef(base+'archival-classification'), DBO.rating, Literal('7.0', datatype=XSD.float) ))

g.add(( URIRef(base+'archival-creator-note-on-photo'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'archival-creator-note-on-photo'), RDFS.label, Literal('archival creator\'s note on the photograph') ))
g.add(( URIRef(base+'archival-creator-note-on-photo'), DBO.rating, Literal('7.0', datatype=XSD.float) ))

g.add(( URIRef(base+'scholar-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'scholar-attribution'), RDFS.label, Literal('scholar\'s attribution') ))
g.add(( URIRef(base+'scholar-attribution'), DBO.rating, Literal('6.0', datatype=XSD.float) ))

g.add(( URIRef(base+'museum-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'museum-attribution'), RDFS.label, Literal('museum attribution') ))
g.add(( URIRef(base+'museum-attribution'), DBO.rating, Literal('5.0', datatype=XSD.float) ))

g.add(( URIRef(base+'scholar-note-on-photo'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'scholar-note-on-photo'), RDFS.label, Literal('scholar\'s note on the photograph') ))
g.add(( URIRef(base+'scholar-note-on-photo'), DBO.rating, Literal('5.0', datatype=XSD.float) ))

g.add(( URIRef(base+'inscription'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'inscription'), RDFS.label, Literal('inscription') ))
g.add(( URIRef(base+'inscription'), DBO.rating, Literal('5.0', datatype=XSD.float) ))

g.add(( URIRef(base+'sigla'), RDF.type, URIRef(HICO.InterpretationCriterion) )) # includes monogram
g.add(( URIRef(base+'sigla'), RDFS.label, Literal('sigla') ))
g.add(( URIRef(base+'sigla'), DBO.rating, Literal('5.0', datatype=XSD.float) ))

g.add(( URIRef(base+'auction-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'auction-attribution'), RDFS.label, Literal('auction attribution') ))
g.add(( URIRef(base+'auction-attribution'), DBO.rating, Literal('4.0', datatype=XSD.float) ))

g.add(( URIRef(base+'collection-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'collection-attribution'), RDFS.label, Literal('collection attribution') ))
g.add(( URIRef(base+'collection-attribution'), DBO.rating, Literal('4.0', datatype=XSD.float) ))

g.add(( URIRef(base+'market-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'market-attribution'), RDFS.label, Literal('market attribution') ))
g.add(( URIRef(base+'market-attribution'), DBO.rating, Literal('4.0', datatype=XSD.float) ))

g.add(( URIRef(base+'traditional-attribution'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'traditional-attribution'), RDFS.label, Literal('traditional attribution') ))
g.add(( URIRef(base+'traditional-attribution'), DBO.rating, Literal('4.0', datatype=XSD.float) ))

g.add(( URIRef(base+'stylistic-analysis'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'stylistic-analysis'), RDFS.label, Literal('stylistic analysis') ))
g.add(( URIRef(base+'stylistic-analysis'), DBO.rating, Literal('3.0', datatype=XSD.float) ))

g.add(( URIRef(base+'anonymous-note-on-photo'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'anonymous-note-on-photo'), RDFS.label, Literal('anonymous note on the photograph') ))
g.add(( URIRef(base+'anonymous-note-on-photo'), DBO.rating, Literal('3.0', datatype=XSD.float) ))

g.add(( URIRef(base+'false-signature'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'false-signature'), RDFS.label, Literal('false signature') ))
g.add(( URIRef(base+'false-signature'), DBO.rating, Literal('2.0', datatype=XSD.float) ))

g.add(( URIRef(base+'caption-on-photo'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'caption-on-photo'), RDFS.label, Literal('caption on the photograph') ))
g.add(( URIRef(base+'caption-on-photo'), DBO.rating, Literal('2.0', datatype=XSD.float) ))

g.add(( URIRef(base+'other'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'other'), RDFS.label, Literal('other') ))
g.add(( URIRef(base+'other'), DBO.rating, Literal('2.0', datatype=XSD.float) ))

g.add(( URIRef(base+'none'), RDF.type, URIRef(HICO.InterpretationCriterion) ))
g.add(( URIRef(base+'none'), RDFS.label, Literal('none') ))
g.add(( URIRef(base+'none'), DBO.rating, Literal('1.0', datatype=XSD.float) ))

g.add(( URIRef(base), PROV.wasAttributedTo, URIRef('https://w3id.org/zericatalog/organization/federico-zeri-foundation') ))

g.serialize(destination='vocabulary-criteria.nq', format='nquads')