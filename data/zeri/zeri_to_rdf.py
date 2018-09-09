#!/usr/bin/python
# -*- coding: UTF-8
import requests , time , csv , sys , rdflib , hashlib, logging , json , urllib , re , string ,io , codecs , uuid
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS , DCTERMS
from fuzzywuzzy import fuzz
import xml.etree.ElementTree as ET
from pymantic import sparql

CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
HICO = Namespace("http://purl.org/emmedi/hico/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

base = 'http://purl.org/emmedi/mauth/zeri/'
criterion = 'http://purl.org/emmedi/mauth/criteria/'
zeri_graph = URIRef(base)
arthistorians_graph = URIRef('http://purl.org/emmedi/mauth/historians/')
artists_graph = URIRef('http://purl.org/emmedi/mauth/artists/')
artworks_graph = URIRef('http://purl.org/emmedi/mauth/artworks/')
criterion = 'http://purl.org/emmedi/mauth/criteria/'

# utils
def clean_to_uri(stringa):
    """ given a string return a partial URI"""
    uri = re.sub('ä', 'a', stringa.strip().lower())
    uri = re.sub('à', 'a', uri)
    uri = re.sub('è', 'e', uri)
    uri = re.sub('é', 'e', uri)
    uri = re.sub('ì', 'i', uri)
    uri = re.sub('ò', 'o', uri)
    uri = re.sub('ù', 'u', uri)
    uri = re.sub('[^a-zA-Z\s]', '', uri)
    uri = re.sub('\s', '-', uri)
    return uri


def get_criteria(text):
	""" given a string returns the keyword representing the criterion"""
	criteria = set()
	if 'Analisi' in text:
		criteria.add('stylistic-analysis')
	if 'Bibliografia' in text and 'Zeri' not in text:
		criteria.add('bibliography')
	if 'Bibliografia' in text and 'Zeri' in text:
		criteria.add('archival-creator-bibliography')
	if 'Documentazione' in text or 'documentazione' in text or 'Perizi' in text or 'perizi' in text:
		criteria.add('documentation')
	if 'Classificazione' in text:
		criteria.add('archival-creator-attribution')
	if 'Iscrizione' in text:
		criteria.add('inscription')
	if 'Firma' in text and 'falsa' not in text:
		criteria.add('artist-signature')
	if 'Firma' in text and 'falsa' in text:
		criteria.add('false-signature')
	if 'Sigla' in text or 'Monogramma' in text:
		criteria.add('sigla')
	if 'Asta' in text or 'Vendita' in text:
		criteria.add('auction-attribution')
	if 'ota anonima' in text or 'Nota sul retro' in text:
		criteria.add('anonymous-note-on-photo')
	if 'dattiloscr' in text and 'Zeri' not in text and 'museo' not in text:
		criteria.add('anonymous-note-on-photo')
	if 'dattiloscr' in text and 'Zeri' in text:
		criteria.add('archival-creator-note-on-photo')
	if 'ota autografa di' in text and 'ota autografa di F. Zeri' not in text:
		criteria.add('scholar-note-on-photo')
	if 'ota autografa di F. Zeri' in text:
		criteria.add('archival-creator-note-on-photo')
	if 'ercato antiq' in text:
		criteria.add('market-attribution')
	if 'collezione' in text:
		criteria.add('collection-attribution')
	if 'museo' in text or 'Galleria Vangelisti' == text or 'Royal Academy, 1871' == text:
		criteria.add('museum-attribution')
	if 'tradizionale' in text:
		criteria.add('traditional-attribution')
	if 'idascalia' in text:
		criteria.add('caption-on-photo')
	if ('Parere' in text or 'Attribuzione' in text or 'P. Della Pergola' == text) and ('Attribuzione F. Zeri' not in text and 'mercato' not in text and 'collezione' not in text and 'museo' not in text and 'tradizionale' not in text):
		criteria.add('scholar-attribution')
	if 'Vedi Osservazioni' == text:
		criteria.add('other')
	if '-' == text or 'n.r.' == text:
		criteria.add('none')
	return criteria


def get_cited_entity(text):
	""" given a string returns the keyword representing the criterion"""
	criteria = set()
	
	if 'Asta' in text or 'Vendita' in text:
		if re.match('^Asta (.*) \(?', text) is not None: 
			critic = re.sub("\s?[\(\[].*?[\)\]]\s?", "", text) # remove parenthesis
			auth = critic
			criteria.add(auth)
	
	if 'museo' in text :
		# tree = ET.parse('fzeri_OA_2015_11_26_175351.xml')
		# root = tree.getroot()
		# for scheda in root.findall('./SCHEDA'):	
		# 	sercd = scheda.get('sercdoa')
		# 	if sercd == sercdInput:
		# 		auth = scheda.find('./PARAGRAFO[@etichetta="LOCATION"]/LDCN')
		# 		if auth is not None:
		# 			criteria.add(auth.text)
		# 		else:
		# 			pass
		pass
	if 'Bibliografia' in text:
		if re.match('^Bibliografia \((.*)\-(.*)\,(.*)\)', text) is not None:
			auth = re.match('^Bibliografia \((.*)\-(.*)\,(.*)\)', text)
			auth1 = auth.group(2)
			auth2 = auth.group(1)
			criteria.add(auth1) 
			criteria.add(auth2) 
		if re.match('^Bibliografia \((.*)\/(.*)\,(.*)\)', text) is not None:
			auth = re.match('^Bibliografia \((.*)\/(.*)\,(.*)\)', text)
			auth1 = auth.group(2).strip()
			auth2 = auth.group(1)
			criteria.add(auth1) 
			criteria.add(auth2)
		if re.match('^Bibliografia\s\(((?:(?!/)(?!-).)*),\s(\d{4})\)$', text) is not None:
			auth = re.match('^Bibliografia\s\(((?:(?!/)(?!-).)*),\s(\d{4})\)$', text)
			auth1 = auth.group(1)
			criteria.add(auth1)
		if re.match('^Bibliografia\s\(((?:(?!/)(?!-)(?!,).)*)\)$',text) is not None:
			auth = re.match('^Bibliografia\s\(((?:(?!/)(?!-)(?!,).)*)\)$',text)
			criteria.add(auth.group(1))
	
	if re.match('^Nota autografa di (.*) sul', text) is not None:
		auth = re.match('^Nota autografa di (.*) sul', text)
		criteria.add(auth.group(1))
	if re.match('^Nota dattiloscritta di (.*) sul', text) is not None:
		auth = re.match('^Nota dattiloscritta di (.*) sul', text)
		criteria.add(auth.group(1))
	if re.match('^Nota dattiloscrita di (.*) sul', text) is not None:
		auth = re.match('^Nota dattiloscrita di (.*) sul', text)
		criteria.add(auth.group(1))
	# e.g. Nota autografa di F. Zeri
	if re.match('^Nota autografa di ((?:(?!\ssul).)*)$', text) is not None:
		auth = re.match('^Nota autografa di ((?:(?!\ssul).)*)$', text)
		criteria.add(auth.group(1))

	if (re.match('^Attribuzione (.*)', text) is not None) and ('Attribuzione F. Zeri' not in text and 'mercato' not in text and 'collezione' not in text and 'museo' not in text and 'tradizionale' not in text): 
		if '(' in text: # includes 'collezione'
			critic = re.sub("\s?[\(\[].*?[\)\]]\s?", "", text) 
		else:
			critic = text
		auth = re.match('^Attribuzione (.*)', critic)
		criteria.add(auth.group(1))
	if (re.match('^Parere (.*)', text) is not None):
		if '(' in text: # includes 'collezione'
			critic = re.sub("\s?[\(\[].*?[\)\]]\s?", "", text) 
		else:
			critic = text
		auth = re.match('^Parere (.*)', critic)
		criteria.add(auth.group(1))
		
	# exceptions
	if 'P. Della Pergola' == text:
		criteria.add('Della Pergola')
	if 'Galleria Vangelisti' == text:
		criteria.add('Asta Galleria Vangelisti')
	if 'Royal Academy, 1871' == text:
		criteria.add('Royal Academy of Arts')
	if 'Zeri' in text:
		criteria.add('F. Zeri')
	return criteria


def get_year(text):
	""" match four digits in the string if lower that 2018 and attributes default value to others"""
	criteria = set()
	rg = re.compile('.*([\[\(]?((?:19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
	match = rg.search(text)
	if match:
		criteria.add(match.group(1))
	if 'Classificazione' in text:
		criteria.add('1990')
	return criteria


def reconcile_two(graph_name, file_name, final_file_name, field_one, field_check, field_two):
    """given a csv, double-check, and return a rdf file including equivalences between two fields"""
    g = rdflib.ConjunctiveGraph(identifier=URIRef(graph_name))
    g.bind("owl", OWL)
    with open(file_name, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            subject = row[field_one]
            objectURI = row[field_two]
            if ('Y' in row[field_check]) and 'http' in objectURI:
                g.add((URIRef(subject), OWL.sameAs, URIRef(objectURI)))
                g.add((URIRef(objectURI), OWL.sameAs, URIRef(subject)))
            elif (row[field_check] is None) and 'http' in objectURI:
                g.add((URIRef(subject), OWL.sameAs, URIRef(objectURI)))
                g.add((URIRef(objectURI), OWL.sameAs, URIRef(subject)))
    return g.serialize(destination=final_file_name + '.nq', format='nquads')

# 1. create rdf data
def zeri_to_rdf():
	""" extract data from xls file and transform artworks, creation, attributions and artists"""	
	# prepare graph
	g=rdflib.ConjunctiveGraph(identifier=base)
	g.bind('owl', OWL)
	g.bind('crm', CIDOC)
	g.bind('hico', HICO)

	# open XML dump
	tree = ET.parse('fzeri_OA_2015_11_26_175351.xml')
	root = tree.getroot()

	autmSet = set()
	aatmSet = set()
	for scheda in root.findall('./SCHEDA'):	
		# variables
		oaBase = "http://purl.org/emmedi/mauth/zeri/artwork/"
		sercd = scheda.get('sercdoa')
		artworkLabel = scheda.get('intestazione')
		artworkURI = oaBase+sercd

		# artwork
		g.add(( URIRef(artworkURI) , RDF.type , URIRef(CIDOC.E28_Conceptual_Object) ))
		g.add(( URIRef(artworkURI) , DCTERMS.title , Literal(artworkLabel) ))		
		for photo in scheda.findall('ALLEGATI/FOTO'):
			# e.g. http://catalogo.fondazionezeri.unibo.it/foto/160000/132800/132513.jpg
			g.add(( URIRef(artworkURI) , FOAF.depiction , URIRef('http://catalogo.fondazionezeri.unibo.it/foto'+photo.text) ))
			
		# creation E65_Creation
		g.add(( URIRef(artworkURI) , CIDOC.P94i_was_created_by , URIRef(artworkURI+'/creation') ))
		# http://catalogo.fondazionezeri.unibo.it/scheda.v2.jsp?locale=it&decorator=layout_resp&apply=true&tipo_scheda=OA&id=16742
		g.add(( URIRef(artworkURI) , URIRef('http://purl.org/emmedi/oaentry/isDescribedBy'), URIRef('http://catalogo.fondazionezeri.unibo.it/scheda.v2.jsp?locale=it&decorator=layout_resp&apply=true&tipo_scheda=OA&id='+sercd) ))
		# accepted attributions
		for paragraph in scheda.findall('PARAGRAFO[@etichetta="AUTHOR"]/RIPETIZIONE'): # multiple artists
			autn = paragraph.find('AUTN')
			# artist
			g.add(( URIRef(artworkURI+'/creation'),  CIDOC.P14_carried_out_by , URIRef(base+clean_to_uri(autn.text)) ))
			g.add(( URIRef(base+clean_to_uri(autn.text)), DCTERMS.title , Literal(autn.text) ))
			#attribution
			artworkAttributionURI = artworkURI+'/authorship/'+clean_to_uri(autn.text)
			g.add(( URIRef(artworkURI+'/creation'), PROV.wasGeneratedBy, URIRef(artworkAttributionURI) ))
			g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationType, URIRef(HICO+'authorship-attribution') ))
			g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationType, URIRef(base+'zeri-preferred-attribution') ))
			# motivation: get criteria, dates and cited entities
			autms = paragraph.findall('AUTM')
			for autm in autms:
				g.add(( URIRef(artworkAttributionURI), CIDOC.P3_has_note, Literal(autm.text) ))
				if '//' in autm.text:
					autmList = autm.text.split('//')
					for autmSingle in autmList:
						autmSet.add(autmSingle.strip())
						crits = get_criteria(autmSingle)
						if len(crits) >= 1:
							for crit in crits: # criteria
								g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationCriterion, URIRef(criterion+crit) ))
						authsCited = get_cited_entity(autmSingle.strip()) # cited entities
						if len(authsCited) >= 1:
							for authCited in authsCited:
								g.add(( URIRef(artworkAttributionURI), CITO.agreesWith, URIRef(base+clean_to_uri(authCited)) ))
						year = get_year(autmSingle.strip())
						if len(year) >= 1:
							for yearOne in year:
								g.add(( URIRef(artworkAttributionURI), PROV.startedAtTime , Literal(yearOne+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
				else:	
					autmSet.add(autm.text)
					crits = get_criteria(autm.text)
					if len(crits) >= 1:
						for crit in crits:
							g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationCriterion, URIRef(criterion+crit) ))
					authsCited = get_cited_entity(autm.text) # cited entities
					if len(authsCited) >= 1:
						for authCited in authsCited:
							g.add(( URIRef(artworkAttributionURI), CITO.agreesWith, URIRef(base+clean_to_uri(authCited)) ))
					year = get_year(autm.text)
					if len(year) >= 1:
						for yearOne in year:
							g.add(( URIRef(artworkAttributionURI), PROV.startedAtTime , Literal(yearOne+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
				for paragraph in scheda.findall('PARAGRAFO[@etichetta="DIFFERENT ATTRIBUTIONS"]/RIPETIZIONE'): # multiple artists
					aat = paragraph.find('AAT')
					if aat is not None and 'Zeri' not in aat.text:
						g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationCriterion, URIRef(criterion+'archival-classification') ))
						g.add(( URIRef(artworkAttributionURI), PROV.startedAtTime , Literal('1990-01-01T00:00:01Z', datatype=XSD.dateTime) ))		
			for bibl in scheda.findall('PARAGRAFO[@etichetta="BIBLIOGRAPHY"]/RIPETIZIONE'): # multiple artists
				brid = str(uuid.uuid4())
				br = " ".join(bibl.itertext()).encode('utf-8')
				g.add(( URIRef(artworkAttributionURI), CITO.citesAsEvidence, URIRef(base+'br/'+brid ) ))
				g.add(( URIRef(base+'br/'+brid ), RDFS.label, Literal(br) ))
				print br
		# discarded attributions
		naat= 0
		for paragraph in scheda.findall('PARAGRAFO[@etichetta="DIFFERENT ATTRIBUTIONS"]/RIPETIZIONE'): # multiple artists
			naat += 1
			aat = paragraph.find('AAT')
			if aat is not None:		
				aats = paragraph.find('AATS')
				if aats is not None:
					autnURI = clean_to_uri(aat.text)+'/'+clean_to_uri(aats.text)
					autnLabel = aat.text+' '+aats.text
				else:
					autnURI = clean_to_uri(aat.text)
					autnLabel = aat.text
				# artist
				g.add(( URIRef(artworkURI+'/creation'+str(naat)), CIDOC.P14_carried_out_by , URIRef(base+autnURI) ))
				g.add(( URIRef(base+autnURI), DCTERMS.title , Literal(autnLabel) ))
				#attribution
				artworkAttributionURI = artworkURI+'/authorship/'+autnURI
				g.add(( URIRef(artworkURI) , CIDOC.P94i_was_created_by , URIRef(artworkURI+'/creation'+str(naat)) ))
				g.add(( URIRef(artworkURI+'/creation'+str(naat)), PROV.wasGeneratedBy, URIRef(artworkAttributionURI) ))
				g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationType, URIRef(HICO+'authorship-attribution') ))
				g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationType, URIRef(base+'zeri-discarded-attribution') ))
				# motivation
				aatms = paragraph.findall('AATM')
				for aatm in aatms:
					if '//' in aatm.text:
						aatmList = aatm.text.split('//')
						for aatmSingle in aatmList:
							aatmSet.add(aatmSingle.strip())
							crits = get_criteria(aatmSingle)
							if len(crits) >= 1:
								for crit in crits:
									g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationCriterion, URIRef(criterion+crit) ))
							authsCited = get_cited_entity(aatmSingle.strip()) # cited entities
							if len(authsCited) >= 1:
								for authCited in authsCited:
									g.add(( URIRef(artworkAttributionURI), CITO.agreesWith, URIRef(base+clean_to_uri(authCited)) ))
							year = get_year(aatmSingle.strip())
							if len(year) >= 1:
								for yearOne in year:
									g.add(( URIRef(artworkAttributionURI), PROV.startedAtTime , Literal(yearOne+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
					else:	
						aatmSet.add(aatm.text)
						crits = get_criteria(aatm.text)
						if len(crits) >= 1:
							for crit in crits:
								g.add(( URIRef(artworkAttributionURI), HICO.hasInterpretationCriterion, URIRef(criterion+crit) ))
						authsCited = get_cited_entity(aatm.text) # cited entities
						if len(authsCited) >= 1:
							for authCited in authsCited:
								g.add(( URIRef(artworkAttributionURI), CITO.agreesWith, URIRef(base+clean_to_uri(authCited)) ))
						year = get_year(aatm.text)
						if len(year) >= 1:
							for yearOne in year:
								g.add(( URIRef(artworkAttributionURI), PROV.startedAtTime , Literal(yearOne+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
	
	return g.serialize(destination='FINAL_zeri.nq', format='nquads')

zeri_to_rdf()

# 2. create the linkset of artists
def zeri_artists_linkset():
	""" read the authority file, including links to ULAN, WD, DBPedia, and VIAF, and reconciled artists to Sandrart, and create a linkset for artists."""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(artists_graph))
	g.bind('owl', OWL)
	auth = ET.parse('Authority-Artist-updated.xml')
	authRoot = auth.getroot()
	# VIAF, DB, WD, ULAN
	for row in authRoot.findall('./ROW'):	
		artist = row.find('AUTN')
		uri = base+clean_to_uri(artist.text)	
		ulan = row.find('ULAN')
		if ulan is not None:
			g.add(( URIRef(uri) , OWL.sameAs , URIRef(ulan.text) ))
			g.add(( URIRef(ulan.text) , OWL.sameAs , URIRef(uri) ))
		wd = row.find('WIKIDATA')
		if wd is not None and wd.text is not None:
			g.add(( URIRef(uri) , OWL.sameAs , URIRef(wd.text) ))
			g.add(( URIRef(wd.text) , OWL.sameAs , URIRef(uri) ))
		db = row.find('DBPEDIA')
		if db is not None:
			g.add(( URIRef(uri) , OWL.sameAs , URIRef(db.text) ))
			g.add(( URIRef(db.text) , OWL.sameAs , URIRef(uri) ))
		viaf = row.find('VIAF')
		if viaf is not None:
			g.add(( URIRef(uri) , OWL.sameAs , URIRef(viaf.text) ))
			g.add(( URIRef(viaf.text) , OWL.sameAs , URIRef(uri) ))
	# Sandrart
	sandrart = rdflib.Graph()
	sandrart = sandrart.parse('FINAL_artists_sandrart_reconciled.rdf', format="n3")
	for s,p,o in sandrart.triples(( None, OWL.sameAs, None )):
		g.add(( URIRef(s) , OWL.sameAs , URIRef(o) ))
		g.add(( URIRef(o) , OWL.sameAs , URIRef(s) ))
	return g.serialize(destination='linkset_artists_zeri.nq', format='nquads')

#zeri_artists_linkset()

def reconcile_zeri_artworks_to_all():
	"""call the utils method for all the final csv with data reconciled"""
	reconcile_two(artworks_graph, 'FINAL_artworks_db_reconciled.csv', 'linkset_artworks_zeri_dbpedia', 'zeriArtwork', 'include', 'dbArtwork')
	reconcile_two(artworks_graph, 'FINAL_artworks_sandrart_reconciled.csv', 'linkset_artworks_zeri_sandrart', 'zeriArtwork','include', 'sandrartArtwork')
	reconcile_two(artworks_graph, 'FINAL_artworks_viaf_reconciled.csv', 'linkset_artworks_zeri_viaf', 'zeriArtwork', 'include', 'viafArtwork')
	reconcile_two(artworks_graph, 'FINAL_artworks_wd_reconciled.csv', 'linkset_artworks_zeri_wikidata', 'zeriArtwork', 'include', 'wdArtwork')

#reconcile_zeri_artworks_to_all()


def zeri_historians_linkset():
	""" given a csv with art historians already reconciled to VIAF creates the linkset"""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(arthistorians_graph))
	g.bind('owl', OWL)
	with open('FINAL_critics_all_reconciled.csv', 'rb') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			uri = 'http://purl.org/emmedi/mauth/zeri/'+clean_to_uri(row['name'].strip())
			firstName = row['name'].strip()
			altName = row['label'].strip()
			viaf = row['viaf'].strip()
			lc = row['lc'].strip()
			isni = row['isni'].strip()
			bnf = row['bnf'].strip()
			dnb = row['dnb'].strip()
			wd = row['wd'].strip()
			# if altName != '':
			#  	g.add(( URIRef(uri.decode('utf-8')) , RDFS.label , Literal( altName.decode('utf-8') ) ))
			if firstName != '':
				g.add(( URIRef(uri.encode('utf-8')) , RDFS.label , Literal( firstName ) ))
			if viaf != '':
				g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(viaf.encode('utf-8')) ))
				g.add(( URIRef(viaf.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
			if lc != '':
				g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(lc.encode('utf-8')) ))
				g.add(( URIRef(lc.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
			if isni != '':
				g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(isni.encode('utf-8')) ))
				g.add(( URIRef(isni.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
			if bnf != '':
				if 'http' in bnf :
					g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(bnf.encode('utf-8')) ))
					g.add(( URIRef(bnf.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
				else: 
					g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef('http://data.bnf.fr/ark:/'+bnf.encode('utf-8')) ))
					g.add(( URIRef('http://data.bnf.fr/ark:/'+bnf.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
			if dnb != '':
				g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(dnb.encode('utf-8')) ))
				g.add(( URIRef(dnb.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
			if wd != '':
				g.add(( URIRef(uri.encode('utf-8')) , OWL.sameAs , URIRef(wd.encode('utf-8')) ))
				g.add(( URIRef(wd.encode('utf-8')) , OWL.sameAs , URIRef(uri.encode('utf-8')) ))
	return g.serialize(destination='linkset_arthistorians_zeri.nq', format='nquads')

#zeri_historians_linkset()
