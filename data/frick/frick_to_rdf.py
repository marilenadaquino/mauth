# coding: utf-8
import requests , time , csv , sys , rdflib , hashlib, logging , json , urllib , re , string ,io
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS
from fuzzywuzzy import fuzz
import xml.etree.ElementTree as ET
from pymantic import sparql

CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
HICO = Namespace("http://purl.org/emmedi/hico/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

base = 'http://purl.org/emmedi/mauth/frick/'
criteriaBase = 'http://purl.org/emmedi/mauth/criteria/'
frick_graph = URIRef(base)
arthistorians_graph = URIRef('http://purl.org/emmedi/mauth/historians/')
artists_graph = URIRef('http://purl.org/emmedi/mauth/artists/')

def clean_criterion(crit):
	crit = re.sub(' ', '-', crit.strip())
	return crit.lower()

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
    uri = re.sub(' +', ' ', uri.strip())
    uri = re.sub(' ', '-', uri.strip())
    return uri


# 1. create rdf data 
def to_rdf(initial_csv,frick_rdf):
	""" extract data from xls file and transform artworks, creation, attributions and artists"""	
	g=rdflib.ConjunctiveGraph(identifier=URIRef(frick_graph))
	g.bind('owl', OWL)
	g.bind('crm', CIDOC)
	g.bind('hico', HICO)
	with open(initial_csv, 'r', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for sheetX in reader:
			artworkID = sheetX['RECORD #(BIBLIO)']
			artworkLabel = sheetX['TITLE']
			photoOnlineURN = 'https://digitalcollections.frick.org/digico/#/details/bibRecordNumber/'+artworkID+'/Photoarchive'
			photoID = sheetX['IMAGES']
			creationDateLabel = sheetX['EARLIEST DATE']+'-'+sheetX['LATEST DATE']
			artistLabel = sheetX['FRICK ARTIST NAME']
			attributionLabel = sheetX['ATTRIBUTION HISTORY']
			source = sheetX['SOURCES']
			alternateArtistLabels = sheetX['VARIANT ARTISTS']

			# artwork E28_Conceptual_Object
			if str(artworkID) != '':
				artworkID = str(artworkID)
				g.add(( URIRef(base+'artwork/'+artworkID) , RDF.type , URIRef(CIDOC.E28_Conceptual_Object) ))
				g.add(( URIRef(base+'artwork/'+artworkID) , DCTERMS.title , Literal(artworkLabel) ))
				#g.add(( URIRef(base+'artwork/'+artworkID) , FOAF.depiction , URIRef(photoOnlineURN) ))
				#g.add(( URIRef(photoOnlineURN) , DCTERMS.title , Literal(photoID) ))
				# creation E65_Creation
				g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation') ))	
				# artist
				if str(artistLabel) != '' and ';' not in str(artistLabel):
					artistID = clean_to_uri(artistLabel) # TO BE IMPROVED
					g.add(( URIRef(base+'artwork/'+artworkID+'/creation') , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+artistID) ))
					g.add(( URIRef(base+'artist/'+artistID) , DCTERMS.title , Literal(artistLabel) ))
				elif str(artistLabel) != '' and ';' in str(artistLabel):
					artists = str(artistLabel).split(';')
					for artist in artists:
						artist = artist.strip()
						artistID = clean_to_uri(artist) # TO BE IMPROVED
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation') , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+artistID) ))
						g.add(( URIRef(base+'artist/'+artistID) , DCTERMS.title , Literal(artist) ))
				else:
					g.add(( URIRef(base+'artwork/'+artworkID+'/creation') , CIDOC.P14_carried_out_by , URIRef(base+'artist/anonymous') ))
					g.add(( URIRef(base+'artist/anonymous') , DCTERMS.title , Literal('anonymous') ))
				
				# alternative attributions
	return g.serialize(destination=frick_rdf, format='nquads')



# 2. reconcile artists to VIAF and co. and manually double check DONE
def reconcile_artists_to_viaf(artists_frick_viaf, frick_rdf):
	""" parse the .nq file, get the artists, fuzzy string matching to VIAF, create a csv 'artists_frick_viaf.csv' to be manually double checked"""
	baseURL = 'http://viaf.org/viaf/search/viaf?query=local.personalNames+%3D+%22'
	f=csv.writer(open(artists_frick_viaf, 'w', encoding='utf-8'))
	f.writerow(['id']+['search']+['result']+['viaf']+['lc']+['isni']+['ratio']+['partialRatio']+['tokenSort']+['tokenSet']+['avg'])

	g=rdflib.ConjunctiveGraph(identifier=URIRef(frick_graph))
	g.parse(frick_rdf, format="nquads")
	g.bind('owl', OWL)
	names = set()
	for s,p,o in g.triples((None, CIDOC.P14_carried_out_by, None)):
		for o1, p1, name in g.triples((o, DCTERMS.title, None )):
			name = re.sub("([\(\[]).*?([\)\]])", "", name)
			name = re.sub("\d+", "", name)
			name = re.sub("artist", "", name)
			name = re.sub(", attributed to", "", name)
			names.add((name.strip(), o ))

	for name, idName in names:
		rowEdited = urllib.parse.quote(name.strip())
		url = baseURL+rowEdited+'%22+and+local.sources+%3D+%22lc%22&sortKeys=holdingscount&maximumRecords=1&httpAccept=application/rdf+json'		
		response = requests.get(url).content.decode('utf-8')
		try:
			response = response[response.index('<recordData xsi:type="ns1:stringOrXmlFragment">')+47:response.index('</recordData>')].replace('&quot;','"')
			response = json.loads(response)
			label = response['mainHeadings']['data'][0]['text']
			viafid = response['viafID']	
		except:
			label = ''
			viafid = ''
		ratio = fuzz.ratio(name, label)
		partialRatio = fuzz.partial_ratio(name, label)
		tokenSort = fuzz.token_sort_ratio(name, label)
		tokenSet = fuzz.token_set_ratio(name, label)
		avg = (ratio+partialRatio+tokenSort+tokenSet)/4

		if viafid != '':
			links = json.loads(requests.get('http://viaf.org/viaf/'+viafid+'/justlinks.json').text)
			viafid = 'http://viaf.org/viaf/'+viafid
			try:
				lc = 'http://id.loc.gov/authorities/names/'+json.dumps(links['LC'][0]).replace('"','')
			except:
				lc = ''
			try:
				isni = 'http://isni.org/isni/'+json.dumps(links['ISNI'][0]).replace('"','')
			except:
				isni = ''
		else:
			lc = ''
			isni = ''
		f.writerow([idName]+[name.strip()]+[label]+[viafid]+[lc]+[isni]+[ratio]+[partialRatio]+[tokenSort]+[tokenSet]+[avg])


# 3. create the linkset of artists
def artists_linkset(FINAL_artists_frick_viaf,linkset_artists_frick):
	""" read the csv manually double checked, renamed 'FINAL_artists_frick_viaf.csv', and create a linkset for artists."""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(artists_graph))
	g.bind('owl', OWL)
	with open(FINAL_artists_frick_viaf, 'r', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			uri = row['id'].strip()
			firstName = row['search'].strip()
			altName = row['result'].strip()
			viaf = row['viaf'].strip()
			lc = row['lc'].strip()
			isni = row['isni'].strip()
			if viaf != '':
				g.add(( URIRef(uri) , OWL.sameAs , URIRef(viaf) ))
			if lc != '':
				g.add(( URIRef(uri) , OWL.sameAs , URIRef(lc) ))
			if isni != '':
				g.add(( URIRef(uri) , OWL.sameAs , URIRef(isni) ))
	g.serialize(destination= linkset_artists_frick, format='nquads')


def export_attr(initial_csv, tb_revised_csv):
	""" extract attributions and create a csv to be reviewed manually"""
	f=csv.writer(open(tb_revised_csv, 'w', encoding='utf-8'))
	f.writerow(['artwork']+['artist_accepted']+['provenance']+['source']+['attribution_tbcleaned']+['accepted_attribution']+['accepted_criterion']+['discarded_attribution1']+['discarded_criterion1']+['discarded_attribution2']+['discarded_criterion2']+['discarded_attribution3']+['discarded_criterion3'])
	with open(initial_csv, 'r', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		attributions = set()
		for sheetX in reader:
			artworkID = sheetX['RECORD #(BIBLIO)']
			artistLabel = sheetX['FRICK ARTIST NAME']
			provenance = sheetX['PROVENANCE']
			source = sheetX['SOURCES']
			attributionLabel = sheetX['ATTRIBUTION HISTORY']
			f.writerow([artworkID]+[artistLabel]+[provenance]+[source]+[attributionLabel])

# 5. get the criteria underpinning the attribution
def methodology_frick(frick_rdf,attributions_revised):
	""" attributions extracted from the manually revised file"""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(frick_graph))
	g.parse(frick_rdf, format="nquads")
	g.bind('hico', HICO)
	g.bind('cito', CITO)
	g.bind('prov', PROV)

	with open(attributions_revised, encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader: 
			artworkID = (row['artwork'])
			artistLabel = row['artist_accepted']
			source = row['source']
			attributionLabel = row['attribution_tbcleaned']

			accepted_criterion = row['accepted_criterion']
			accepted_cited = row['accepted_cited']
			accepted_date = row['accepted_date']

			discarded_attribution1 = row['discarded_attribution1']
			discarded_criterion1 = row['discarded-criterion1']
			discarded_cited1 = row['discarded_cited1']
			discarded_date1 = row['discarded_date1']

			discarded_attribution2 = row['discarded_attribution2']
			discarded_criterion2 = row['discarded-criterion2']
			discarded_cited2 = row['discarded_cited2']
			discarded_date2 = row['discarded_date2']

			discarded_attribution3 = row['discarded_attribution3']
			discarded_criterion3 = row['discarded-criterion3']
			discarded_cited3 = row['discarded_cited3']
			discarded_date3 = row['discarded_date3']

			# accepted attribution 
			if str(accepted_criterion) != '':
				g.add(( URIRef(base+'artwork/'+artworkID+'/creation') , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution') ))
				g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
				g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationType , URIRef(base+'frick-preferred-attribution') ))
				if str(attributionLabel) != '':
					g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CIDOC.P3_has_note , Literal(attributionLabel) ))
				
				# criteria
				if '/' in accepted_criterion:
					criteria = accepted_criterion.split('/')
					for criterion in criteria:
						criterion = clean_criterion(criterion.strip())
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationCriterion , URIRef(criteriaBase+criterion) ))
				else:
					criterion = clean_criterion(accepted_criterion)
					if criterion == 'none':
						criterion = 'archival-classification'
					g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationCriterion , URIRef(criteriaBase+criterion) ))

				# cited entities
				if str(accepted_cited) != '':
					if '/' in accepted_cited:
						entities = accepted_cited.split('/')
						for entity in entities:
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CITO.agreesWith , URIRef(base+clean_to_uri(entity.strip())) ))
							g.add(( URIRef(base+clean_to_uri(entity.strip())), RDFS.label, Literal(entity.strip()) ))
					else:
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CITO.agreesWith , URIRef(base+clean_to_uri(accepted_cited.strip())) ))
						g.add(( URIRef(base+clean_to_uri(accepted_cited.strip())), RDFS.label, Literal(accepted_cited.strip()) ))
				
				# date
				if str(accepted_date) != '':
					if '/' in accepted_date:
						dates = accepted_date.split('/')
						for date in dates:
							date = date.strip()
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , PROV.startedAtTime , Literal(date+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
					else:
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , PROV.startedAtTime , Literal(accepted_date.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))

				# discarded 1
				if str(discarded_attribution1) != '':
					# multiple discarded 1 
					if '/' in discarded_attribution1:
						discarded_artists = discarded_attribution1.split('/')
						n = 0
						for discarded_artist in discarded_artists:
							n += 1
							discarded_artist = discarded_artist.strip()
							g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
							
							# criterion
							if str(discarded_criterion1) != '':
								if '/' in discarded_criterion1:
									discarded_criteria1 = discarded_criterion1.split('/')
									for discarded_criterion1 in discarded_criteria1:
										discarded_criterion1 = clean_criterion(discarded_criterion1.strip())
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion1) ))	
								else:	
									discarded_criterion1 = clean_criterion(discarded_criterion1.strip())
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion1) ))
							else:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
							
							# cited entities
							if str(discarded_cited1) != '':
								if '/' in discarded_cited1:
									discarded_citeds = discarded_cited1.split('/')
									for discarded_cited in discarded_citeds:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
										g.add(( URIRef(base+clean_to_uri(discarded_citeds.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
								else:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited1.strip())) ))
									g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited1.strip()) )) 

							# date:
							if str(discarded_date1) != '':
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date1.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
					
					# single discarded 1
					else:
						n = 1
						discarded_artist = discarded_attribution1
						g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
						
						# criterion
						if str(discarded_criterion1) != '':
							if '/' in discarded_criterion1:
								discarded_criteria1 = discarded_criterion1.split('/')
								for discarded_criterion1 in discarded_criteria1:
									discarded_criterion1 = clean_criterion(discarded_criterion1.strip())
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion1) ))
							else:
								discarded_criterion1 = clean_criterion(discarded_criterion1.strip())
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion1) ))	
						else:
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
						
						# cited entities
						if str(discarded_cited1) != '':
							if '/' in discarded_cited1:
								discarded_citeds = discarded_cited1.split('/')
								for discarded_cited in discarded_citeds:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
									g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
							else:
								discarded_cited = clean_to_uri(discarded_cited1.strip())
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
								g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) )) 

						# date:
						if str(discarded_date1) != '':
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date1.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))

				# discarded 2
				if str(discarded_attribution2) != '':
					# multiple discarded 2 
					if '/' in discarded_attribution2:
						discarded_artists = discarded_attribution2.split('/')
						n = 20
						for discarded_artist in discarded_artists:
							n += 1
							discarded_artist = discarded_artist.strip()
							g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
							
							# criterion
							if str(discarded_criterion2) != '':
								if '/' in discarded_criterion2:
									discarded_criteria2 = discarded_criterion2.split('/')
									for discarded_criterion2 in discarded_criteria2:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion2.strip() ) ))
								else:
									discarded_criterion2 = clean_criterion(discarded_criterion2.strip())
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion2) ))
							else:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
							
							# cited entities
							if str(discarded_cited2) != '':
								if '/' in discarded_cited2:
									discarded_citeds = discarded_cited2.split('/')
									for discarded_cited in discarded_citeds:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
										g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
								else:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited2.strip())) ))
									g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited2.strip()) )) 

							# date:
							if str(discarded_date2) != '':
								if '/' in discarded_date2:
									discarded_dates2 = discarded_date2.split('/')
									for discarded_date2 in discarded_dates2:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date2.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
								
								else:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date2.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
					
					# single discarded 2
					else:
						n = 2
						discarded_artist = discarded_attribution2
						g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
						
						# criterion
						if str(discarded_criterion2) != '':
							if '/' in discarded_criterion2:
								discarded_criteria2 = discarded_criterion2.split('/')
								for discarded_criterion2 in discarded_criteria2:
									discarded_criterion2 = clean_criterion(discarded_criterion2.strip())
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion2) ))	
							else:
								discarded_criterion2 = clean_criterion(discarded_criterion2.strip())
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion2) ))	
							
						else:	
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
						
						# cited entities
						if str(discarded_cited2) != '':
							if '/' in discarded_cited2:
								discarded_citeds = discarded_cited2.split('/')
								for discarded_cited in discarded_citeds:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
									g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
							else:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited2.strip())) ))
								g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited2.strip()) )) 

						# date:
						if str(discarded_date2) != '':
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date2.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
				
					# discarded 3
					if str(discarded_attribution3) != '':
						# multiple discarded 2 
						if '/' in discarded_attribution3:
							discarded_artists = discarded_attribution3.split('/')
							n = 30
							for discarded_artist in discarded_artists:
								n += 1
								discarded_artist = discarded_artist.strip()
								g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
								
								# criterion
								if str(discarded_criterion3) != '':
									if '/' in discarded_criterion3:
										discarded_criteria3 = discarded_criterion3.split('/')
										for discarded_criterion3 in discarded_criteria3:
											g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion3.strip() ) ))
									else:
										discarded_criterion3 = clean_criterion(discarded_criterion3.strip())
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion3) ))
								else:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
								
								# cited entities
								if str(discarded_cited3) != '':
									if '/' in discarded_cited3:
										discarded_citeds = discarded_cited3.split('/')
										for discarded_cited in discarded_citeds:
											g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
											g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
									else:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited3.strip())) ))
										g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited3.strip()) )) 

								# date:
								if str(discarded_date3) != '':
									if '/' in discarded_date3:
										discarded_dates3 = discarded_date3.split('/')
										for discarded_date3 in discarded_dates3:
											g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date3.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
									else:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date3.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
						
						# single discarded 2
						else:
							n = 3
							discarded_artist = discarded_attribution3
							g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(discarded_artist) ) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'frick-discarded-attribution') ))
							
							# criterion
							if str(discarded_criterion3) != '':
								if '/' in discarded_criterion3:
									discarded_criteria3 = discarded_criterion3.split('/')
									for discarded_criterion3 in discarded_criteria3:
										discarded_criterion3 = clean_criterion(discarded_criterion3.strip())
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion3) ))	
								else:	
									discarded_criterion3 = clean_criterion(discarded_criterion3.strip())
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+discarded_criterion3) ))
							
							else:	
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criteriaBase+'none') ))
							
							# cited entities
							if str(discarded_cited3) != '':
								if '/' in discarded_cited3:
									discarded_citeds = discarded_cited3.split('/')
									for discarded_cited in discarded_citeds:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited.strip())) ))
										g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited.strip()) ))
								else:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(discarded_cited3.strip())) ))
									g.add(( URIRef(base+clean_to_uri(discarded_cited.strip())), RDFS.label, Literal(discarded_cited3.strip()) )) 

							# date:
							if str(discarded_date3) != '':
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(discarded_date3.strip()+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))

	return g.serialize(destination=frick_rdf, format='nquads')	

