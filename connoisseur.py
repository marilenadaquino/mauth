# -*- coding: utf-8 -*-
import rdflib, urllib, utils , datetime , sys , re , os.path , logging , csv , json , uuid , time , hydra.tpf
from rdflib import Graph, Namespace, URIRef , XSD, Namespace , Literal
from rdflib.namespace import RDF, RDFS , OWL , DC
from rdflib.plugins.stores import sparqlstore 
from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE, RDF, N3 , URLENCODED
from pymantic import sparql
from collections import defaultdict


WHY = Namespace("http://purl.org/emmedi/mauth/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

attributions_graph = URIRef('http://purl.org/emmedi/mauth/attributions/')
settingFile = "settings/settings.json"
# ng = Graph(store, identifier=attributions_graph)
server = sparql.SPARQLServer('http://0.0.0.0:9999/blazegraph/sparql')
blaze = 'http://0.0.0.0:9999/blazegraph/sparql'

def findAttributions(inputURI, objProperty):
	""" given a URI as input, (1) query against the triplestore for equivalences
	(2) return a list of URIs, (3) open a mapping document, (4) fetch data about artist, sources etc. 
	(5) return a graph including all the information collected, grouped by observation/source"""
	
	# endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
	# store = sparqlstore.SPARQLUpdateStore()
	# store.open((endpoint, endpoint))
	
	try:
		get_artworks = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?b 
			WHERE { graph <http://purl.org/emmedi/mauth/artworks/> { {<"""+inputURI+"""> ?c ?b} UNION {?b ?c <"""+inputURI+""">} } }"""
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		sparqlW = SPARQLWrapper(blaze)
		sparqlW.setQuery(get_artworks)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		artworksList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
		artworksList.append(inputURI)
		if len(artworksList) == 0: # if there are no similar artworks (first perform the query again, otherwise give results only for the input uri), or inputURI does not represent an artwork
			print ("wrong input or no results") # TODO it should be done for the only URI if it is an artwork	
		else: # matches found in the linkset, create a new rdflib graph including artowrk-artist pairs and related observations
			time = str(datetime.datetime.now()).replace(' ', '').replace(':','').replace('.','').replace('-','')
			resultsGraph=rdflib.ConjunctiveGraph(identifier=URIRef(attributions_graph))
			resultsGraph.bind("dc", DC)
			resultsGraph.bind("rdfs", RDFS)
			resultsGraph.bind("mauth", WHY)
			resultsGraph.bind("prov", PROV)
			
			with open('settings/' + objProperty + '.json') as mapping:    # open the mapping document
				data = json.load(mapping)
				for artwork in artworksList:
					instance = artwork.rsplit('/', 1)[-1] # instance ID	
					URIbase = utils.splitURI(artwork) # extract URI base of each artworks
					if URIbase in data and len(artwork) > len(URIbase):	# call fetchData method, that open a settings file and rewrite queries outlined in mapping document		
						# artist
						if len(data[URIbase][objProperty]) != 0:
							singleResultsGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase][objProperty]), outputPattern=rdflib.term.URIRef(WHY.hasObservedArtist))
							for s, p, obj in singleResultsGraph.triples((URIRef(artwork), WHY.hasObservedArtist, None)):
								if len(obj) != 0 and 'http' in str(obj):
									instanceObj = obj.rsplit('/', 1)[-1]
									if ' ' in instanceObj:
										instanceObj = re.sub('\s', '-', instanceObj)
									resultsGraph.add(( URIRef(artwork), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
									resultsGraph.add(( URIRef(obj), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.atTime, Literal(datetime.datetime.now(),datatype=XSD.dateTime) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.wasAttributedTo, URIRef(WHY+'md') ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtist, URIRef(obj) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtwork, URIRef(artwork) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), RDFS.label, Literal( data[URIbase]['label'] + ' accepted attribution' ) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasType, URIRef(WHY+'accepted') ))
									# attribution text field
									if len(data[URIbase]['notes']) != 0:
										notesGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['notes']), outputPattern=rdflib.term.URIRef(DC.note))							
										for a, t, note in notesGraph.triples((URIRef(artwork), DC.note, None)):
											resultsGraph.add(( URIRef(artwork), DC.note, Literal(note) ))
									# artworkTitle
									if len(data[URIbase]['artworkTitle']) != 0:
										artworkTitleGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['artworkTitle']), outputPattern=rdflib.term.URIRef(RDFS.label))							
										for a, t, title in artworkTitleGraph.triples((URIRef(artwork), None, None)):
											resultsGraph.add(( URIRef(artwork), RDFS.label, Literal(title) ))
									# artistTitle
									if len(data[URIbase]['artistTitle']) != 0:
										artistTitleGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['artistTitle']), outputPattern=rdflib.term.URIRef(RDFS.label))							
										for aa, tt, titleA in artistTitleGraph.triples((None, None, None)):
											resultsGraph.add(( URIRef(aa), RDFS.label, Literal(titleA) ))
									# criterion
									if len(data[URIbase]['criterion']) != 0:
										singleCriterionGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['criterion']), outputPattern=rdflib.term.URIRef(WHY.hasObservedCriterion))
										for s, p, obj in singleCriterionGraph.triples((URIRef(artwork), WHY.hasObservedCriterion, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedCriterion, URIRef(obj) ))
									# source
									if len(data[URIbase]['source']) != 0:
										singleSourceGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['source']), outputPattern=rdflib.term.URIRef(WHY.hasSourceOfAttribution))
										for s, p, obj in singleSourceGraph.triples((URIRef(artwork), WHY.hasSourceOfAttribution, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasSourceOfAttribution, URIRef(obj) ))					
									# date
									if len(data[URIbase]['date']) != 0:
										singleDateGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['date']), outputPattern=rdflib.term.URIRef(WHY.hasAttributionDate))
										for s, p, obj in singleDateGraph.triples((URIRef(artwork), WHY.hasAttributionDate, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasAttributionDate, Literal(obj) ))
									# scholar
									if len(data[URIbase]['scholar']) != 0:
										singleSourceGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['scholar']), outputPattern=rdflib.term.URIRef(WHY.agreesWith))
										for s, p, obj in singleSourceGraph.triples((URIRef(artwork), WHY.agreesWith, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.agreesWith, URIRef(obj) ))
									# images
									if len(data[URIbase]['images']) != 0:
										singleSourceGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['images']), outputPattern=rdflib.term.URIRef(WHY.image))
										for s, p, obj in singleSourceGraph.triples((URIRef(artwork), WHY.image, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.image, URIRef(obj) ))
									
									# other artist
									if len(data[URIbase]['other_artist']) != 0:
										singleOtherResultsGraph = utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['other_artist']), outputPattern=rdflib.term.URIRef(DC.description))
										for s, p, obj in singleOtherResultsGraph.triples((URIRef(artwork), DC.description, None)):
											instanceObj = obj.rsplit('/', 1)[-1]
											if ' ' in instanceObj:
												instanceObj = re.sub('\s', '-', instanceObj)
											resultsGraph.add(( URIRef(artwork), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
											resultsGraph.add(( URIRef(obj), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.atTime, Literal(datetime.datetime.now(),datatype=XSD.dateTime) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.wasAttributedTo, URIRef(WHY+'md') ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtist, URIRef(obj) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtwork, URIRef(artwork) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), RDFS.label, Literal( data[URIbase]['label'] + ' discarded attribution' ) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasType, URIRef(WHY+'discarded') ))
									# other criterion (TODO double-check)
									if len(data[URIbase]['other_criterion']) != 0:
										singleOtherResultsGraph += utils.fetchData(uri=artwork, settingFile="settings/settings.json", inputPattern=str(data[URIbase]['other_criterion']), outputPattern=rdflib.term.URIRef(WHY.hasCriterion))
										for s, p, obj in singleOtherResultsGraph.triples((URIRef(artwork), WHY.hasCriterion, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedCriterion, URIRef(obj) ))
									
									
			
			return resultsGraph
	except Exception as error:
		print ('findAttributions error:', error)


def update_linksets():
	""" given a list of uris fetch data to find equivalences"""
	artworksGraph = rdflib.ConjunctiveGraph(identifier='http://purl.org/emmedi/mauth/artworks/')
	artistsGraph = rdflib.ConjunctiveGraph(identifier='http://purl.org/emmedi/mauth/artists/')
	historiansGraph = rdflib.ConjunctiveGraph(identifier='http://purl.org/emmedi/mauth/historians/')
	try:
		get_artists = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?b 
			FROM <http://purl.org/emmedi/mauth/artists/>
			WHERE {?a ?p ?b }"""
		# query the linkset of artists: look for equivalences and return a list of equivalences
		sparqlW1 = SPARQLWrapper(blaze)
		sparqlW1.setQuery(get_artists)
		sparqlW1.setReturnFormat(JSON)
		results = sparqlW1.query().convert()
		inputList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
		for inputURI in inputList:
			singleResultsGraph = utils.fetchData(uri=inputURI, settingFile="settings/settings.json", inputPattern='http://www.w3.org/2002/07/owl#sameAs', outputPattern=rdflib.term.URIRef(OWL.sameAs))
			artistsGraph += singleResultsGraph
		artistsGraph.serialize(destination='data/recursive_linkset_artists.nq', format='nquads')
	except:
		pass
	try:		
		get_artworks = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?b 
			FROM <http://purl.org/emmedi/mauth/artworks/>
			WHERE {?a (^owl:sameAs|owl:sameAs)* ?b }"""
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		sparqlW = SPARQLWrapper(blaze)
		sparqlW.setQuery(get_artworks)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		inputList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
		for inputURI in inputList:
			singleResultsGraph = utils.fetchData(uri=inputURI, settingFile="settings/settings.json", inputPattern='http://www.w3.org/2002/07/owl#sameAs', outputPattern=rdflib.term.URIRef(OWL.sameAs))
			artworksGraph += singleResultsGraph
		artworksGraph.serialize(destination='data/recursive_linkset_artworks.nq', format='nquads')
	except:
		pass	
	try:
		get_historians = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?b 
			FROM <http://purl.org/emmedi/mauth/historians/>
			WHERE {?a ?p ?b }"""
		# query the linkset of historians: look for equivalences and return a list of equivalences
		sparqlW2 = SPARQLWrapper(blaze)
		sparqlW2.setQuery(get_historians)
		sparqlW2.setReturnFormat(JSON)
		results = sparqlW2.query().convert()
		inputList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
		for inputURI in inputList:
			singleResultsGraph = utils.fetchData(uri=inputURI, settingFile="settings/settings.json", inputPattern='http://www.w3.org/2002/07/owl#sameAs', outputPattern=rdflib.term.URIRef(OWL.sameAs))
			historiansGraph += singleResultsGraph
		historiansGraph.serialize(destination='data/recursive_linkset_historians.nq', format='nquads')
	except:
		pass

#update_linksets()


def update_attributions():
	""" updates the graph attributions including reports (using findAttributions method) for each observed artwork in the named graph artworks """
	try:
		get_artworks = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?artwork
			FROM <http://purl.org/emmedi/mauth/artworks/>
			WHERE { ?a ?b ?artwork  }"""
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		sparqlW = SPARQLWrapper(blaze)
		#sparqlW.setRequestMethod(URLENCODED)
		sparqlW.setQuery(get_artworks)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		artworksList = list( result["artwork"]["value"] for result in (results["results"]["bindings"]))
		resultsGraph=rdflib.ConjunctiveGraph(identifier=URIRef(attributions_graph))
		for artwork in artworksList:
			URIbase = utils.splitURI(artwork)
			with open(settingFile) as settings:    
				data_source = json.load(settings)
				print ("Fetching data for URI:", artwork)
				if URIbase not in data_source:
					# artworksList.remove(artwork)
					print('NOT FOUND URIBASE', URIbase, '\n')
				else:
					artworkGraph = findAttributions(artwork, 'artist')
					print('here we are')
					if len(artworkGraph) > 0:
						resultsGraph += artworkGraph
		# update triples on blazegraph
		file_name = str(uuid.uuid4())
		time = str(datetime.datetime.now()).replace(' ', '').replace(':','').replace('.','').replace('-','')
		resultsGraph.serialize(destination='attributions/'+time+'-'+file_name+'.nq', format='nquads')
		server.update('load <file:///Users/marilena/Desktop/mauth/attributions/'+time+'-'+file_name+'.nq>')
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print('update_attributions', exc_type, fname, exc_tb.tb_lineno)
		pass

#update_attributions()


def rank(results):
	""" given a JSON reorganized by means of rebuildResults 
	adds the ranking value"""
	dates = []
	artists = []
	for x in results:
		# dates 
		# TODO take the most recent one when there are more than one for an attribution
		ymd = re.sub('none', '0001-01-01', str(x['date'][0]))
		ymd = re.sub('.000Z', '', str(x['date'][0]))
		dates.append(ymd)

		score = float()
		scorecriteria = float()
		scoreprovider = float()
		scoreagreement = float()
		scoredate = float()
		# artists
		for artist in x['artist']:
			artists.append(str(artist))
			
		# 1 domain expert
		if 'Zeri' in x['provider'] or 'I Tatti' in x['provider'] or 'Frick' in x['provider']:
			if 'discarded' in x['provider']:
				pass
			else:
				score += 1.00
				scoreprovider += 1.00
		x['scoreprovider'] = scoreprovider
		# 2 criterion
		for criterion in x['criteria']:
			rank = utils.rankCriteria(criterion) # look into the graph of criteria and sum the rank
			score += rank
			scorecriteria += rank
		
		# 3 scholar's authoritativeness
		# see h index, artist index and auth index in utils
		x['scorecriteria'] = scorecriteria			
		x['score'] = score
	
	# 4 date
	dateRank = utils.rankDates(dates)
	
	for x in results:
		for d,r in dateRank:
			if str(d) in x['date'][0]: # multiple dates? pick the highest date among the ones related to a single attr
				x['score'] += r
				scoredate += r
			if x['date'][0] == 'none':
				pass
		x['scoredate'] = scoredate
		for artist in x['artist']:
			
			# 5 attribution shared
			artistShared = utils.sharedAttribution(artist, artists) 

			x['score'] += artistShared
			x['agreement'] = int(artistShared)
			x['scoreagreement'] = int(artistShared)
	# rerank when a lower attribution agrees with the most authoritative one ?
	return results
