# -*- coding: utf-8 -*-
import utils , config , rdflib , urllib, datetime , sys , re , os.path , logging , csv , json , uuid , time , hydra.tpf
from rdflib import Graph, Namespace, URIRef , XSD, Namespace , Literal
from rdflib.namespace import RDF, RDFS , OWL , DC
from rdflib.plugins.stores import sparqlstore 
from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE, RDF, N3 , URLENCODED
from pymantic import sparql
from collections import defaultdict

logging.basicConfig()
currPath = os.path.dirname(os.path.abspath(__file__))
time = str(datetime.datetime.now()).replace(' ', '').replace(':','').replace('.','').replace('-','')

# namespaces
WHY = Namespace("http://purl.org/emmedi/mauth/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

class Connoisseur(object):
	""" given a collection of URIs identifying artworks, a list of trusted providers, a mapping document, and a settings file,
	the crawling process retrieves authorship attributions and uploads results on the triplestore in the Observation Graph

	Attributes:

	"""
	def __init__(self, uris, graph):
		""" Returns a Connoisseur object for the input URI"""
		self.uris = uris
		self.graph = config.attributions_graph

	def updateLinksets(self, linkset, settingFile, fileName):
		""" given a linkset fetches data to find equivalences and updates the graph with the new found equivalneces"""
		try:
			get_artists = """
				PREFIX owl: <http://www.w3.org/2002/07/owl#>
				SELECT DISTINCT ?b 
				FROM <"""+linkset+""">
				WHERE { ?a (^owl:sameAs|owl:sameAs)* ?b }"""
			# query the linkset of artists: look for equivalences and return a list of equivalences
			sparqlW1 = SPARQLWrapper(config.SPARQLendpoint)
			sparqlW1.setQuery(get_artists)
			sparqlW1.setReturnFormat(JSON)
			results = sparqlW1.query().convert()
			inputList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
			for inputURI in inputList:
				singleResultsGraph = utils.fetchData(uri=inputURI, settingFile=settingFile, inputPattern='http://www.w3.org/2002/07/owl#sameAs', outputPattern=rdflib.term.URIRef(OWL.sameAs))
				artistsGraph += singleResultsGraph
			artistsGraph.serialize(destination='data/recursive_linkset_'+fileName+'.nq', format='nquads')
			config.server.update('load <'+currPath+'/data/recursive_linkset_'+fileName+'.nq>')
		except:
			pass

	# usage
	# updateLinksets(config.artworks_linkset, 'settings/settings.json', 'artworks')
	# updateLinksets(config.artists_linkset, 'settings/settings.json', 'artists')
	# updateLinksets(config.historians_linkset, 'settings/settings.json', 'historians')
	

	def findAttributions(self, artwork):
		""" given an inputURI identifying an artwork, looks for all the equivalent URIs in the linkset of artworks and fetches attributions """
		try:
			# prepare the graph to store attributions
			time = str(datetime.datetime.now()).replace(' ', '').replace(':','').replace('.','').replace('-','')
			resultsGraph=rdflib.ConjunctiveGraph(identifier=URIRef(config.attributions_graph))
			resultsGraph.bind("dc", DC)
			resultsGraph.bind("rdfs", RDFS)
			resultsGraph.bind("mauth", WHY)
			resultsGraph.bind("prov", PROV)

			# open the mapping document
			with open(config.mappingDocument) as mapping:
				data = json.load(mapping)
				objProperty = config.objProperty
				settings = config.settingsFile

				instance = artwork.rsplit('/', 1)[-1]
				URIbase = utils.splitURI(artwork) 
				
				# call fetchData method for each property included in the mapping document
				if URIbase in data and len(artwork) > len(URIbase):
					# artist
					if len(data[URIbase]['artist']) != 0:
						singleResultsGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['artist']), outputPattern=URIRef(WHY.hasObservedArtist), outputGraph=URIRef(config.attributions_graph) )
						if len(singleResultsGraph) > 0:
							for s, p, obj in singleResultsGraph.triples((URIRef(artwork), None, None)):
								if len(obj) != 0 and 'http' in str(obj):
									instanceObj = utils.subSpace(obj.rsplit('/', 1)[-1])
									resultsGraph.add(( URIRef(artwork), WHY.isSubjectOfObservation, URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
									resultsGraph.add(( URIRef(obj), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.atTime, Literal(datetime.datetime.now(),datatype=XSD.dateTime) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.wasAttributedTo, URIRef(WHY+'md') ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtist, URIRef(obj) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtwork, URIRef(artwork) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), RDFS.label, Literal( data[URIbase]['label'] + ' accepted attribution' ) ))
									resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasType, URIRef(WHY+'accepted') ))
									# artistTitle
									if len(data[URIbase]['artistTitle']) != 0:
										artistTitleGraph = utils.fetchData(uri=str(obj), settingFile=settings, inputPattern=str(data[URIbase]['artistTitle']), outputPattern=rdflib.term.URIRef(RDFS.label), outputGraph=URIRef(config.attributions_graph))							
										for aa, tt, titleA in artistTitleGraph.triples((None, None, None)):
											resultsGraph.add(( URIRef(obj), RDFS.label, titleA ))
									# attribution text field
									if len(data[URIbase]['notes']) != 0:
										notesGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['notes']), outputPattern=rdflib.term.URIRef(DC.note), outputGraph=URIRef(config.attributions_graph))							
										for a, t, note in notesGraph.triples((URIRef(artwork), DC.note, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), DC.note, note ))
									# artworkTitle
									if len(data[URIbase]['artworkTitle']) != 0:
										artworkTitleGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['artworkTitle']), outputPattern=rdflib.term.URIRef(RDFS.label), outputGraph=URIRef(config.attributions_graph))							
										for a, t, title in artworkTitleGraph.triples((URIRef(artwork), None, None)):
											resultsGraph.add(( URIRef(artwork), RDFS.label, title ))
									
									# criterion
									if len(data[URIbase]['criterion']) != 0:
										singleCriterionGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['criterion']), outputPattern=rdflib.term.URIRef(WHY.hasObservedCriterion), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleCriterionGraph.triples((URIRef(artwork), WHY.hasObservedCriterion, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedCriterion, URIRef(obj) ))
									# source
									if len(data[URIbase]['source']) != 0:
										singleSourceGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['source']), outputPattern=rdflib.term.URIRef(WHY.hasSourceOfAttribution), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleSourceGraph.triples((URIRef(artwork), WHY.hasSourceOfAttribution, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasSourceOfAttribution, URIRef(obj) ))					
									# biblio
									if len(data[URIbase]['biblio']) != 0:
										singleBiblioGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['biblio']), outputPattern=rdflib.term.URIRef(WHY.citesAsEvidence), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleBiblioGraph.triples((URIRef(artwork), WHY.citesAsEvidence, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.citesAsEvidence, Literal(obj) ))					
									
									# date
									if len(data[URIbase]['date']) != 0:
										singleDateGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['date']), outputPattern=rdflib.term.URIRef(WHY.hasAttributionDate), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleDateGraph.triples((URIRef(artwork), WHY.hasAttributionDate, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasAttributionDate, rdflib.term.Literal(obj) ))
									# scholar
									if len(data[URIbase]['scholar']) != 0:
										singleSGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['scholar']), outputPattern=rdflib.term.URIRef(WHY.agreesWith), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleSGraph.triples((URIRef(artwork), WHY.agreesWith, None)):
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.agreesWith, URIRef(obj) ))
									# images
									if len(data[URIbase]['images']) != 0:
										singleDGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['images']), outputPattern=rdflib.term.URIRef(WHY.image), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleDGraph.triples((URIRef(artwork), WHY.image, None)):
											if "\\" not in str(obj):
												resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.image, URIRef(obj ) ))
									
									# other artist
									if len(data[URIbase]['other_artist']) != 0:
										nother = 0
										singleOtherResultsGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['other_artist']), outputPattern=rdflib.term.URIRef(DC.description), outputGraph=URIRef(config.attributions_graph))
										for s, p, obj in singleOtherResultsGraph.triples((URIRef(artwork), DC.description, None)):
											instanceObj = utils.subSpace(obj.rsplit('/', 1)[-1]) 
											nother += 1
											resultsGraph.add(( URIRef(artwork), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
											resultsGraph.add(( URIRef(obj), WHY.isSubjectOfObservation, rdflib.term.URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs')))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.atTime, rdflib.term.Literal(datetime.datetime.now(),datatype=XSD.dateTime) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), PROV.wasAttributedTo, URIRef(WHY+'md') ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtist, URIRef(obj) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedArtwork, URIRef(artwork) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), RDFS.label, rdflib.term.Literal( data[URIbase]['label'] + ' discarded attribution ('+str(nother)+')' ) ))
											resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasType, URIRef(WHY+'discarded') ))
											# bind to the artist
											# other criterion
											if len(data[URIbase]['other_criterion']) != 0:
												singleOtherResultsGraph = utils.fetchBindingsData(uri=artwork, uriBind=obj, settingFile=settings, inputPattern=str(data[URIbase]['other_artist']), inputPattern2=str(data[URIbase]['other_criterion']), outputPattern=rdflib.term.URIRef(WHY.hasCriterion), outputGraph=URIRef(config.attributions_graph))
												for s, p, o in singleOtherResultsGraph.triples((URIRef(artwork), WHY.hasCriterion, None)):
													resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasObservedCriterion, URIRef(o) ))
											if len(data[URIbase]['other_date']) != 0:
												singleOtherResultsDateGraph = utils.fetchBindingsData(uri=artwork, uriBind=obj, settingFile=settings, inputPattern=str(data[URIbase]['other_artist']), inputPattern2=str(data[URIbase]['other_date']), outputPattern=rdflib.term.URIRef(WHY.hasAttributionDate), outputGraph=URIRef(config.attributions_graph))
												for s, p, o in singleOtherResultsDateGraph.triples((URIRef(artwork), WHY.hasAttributionDate, None)):
													resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasAttributionDate, rdflib.term.Literal(o) ))
											# scholar
											if len(data[URIbase]['other_scholar']) != 0:
												singleOtherResultsScholarGraph = utils.fetchBindingsData(uri=artwork, uriBind=obj, settingFile=settings, inputPattern=str(data[URIbase]['other_artist']), inputPattern2=str(data[URIbase]['other_scholar']), outputPattern=rdflib.term.URIRef(WHY.agreesWith), outputGraph=URIRef(config.attributions_graph))
												for s, p, o in singleOtherResultsScholarGraph.triples((URIRef(artwork), WHY.agreesWith, None)):
													resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.agreesWith, URIRef(o) ))
											# biblio
											if len(data[URIbase]['other_biblio']) != 0:
												singleOtherResultsBiblioGraph = utils.fetchBindingsData(uri=artwork, uriBind=obj, settingFile=settings, inputPattern=str(data[URIbase]['other_artist']), inputPattern2=str(data[URIbase]['other_biblio']), outputPattern=rdflib.term.URIRef(WHY.citesAsEvidence), outputGraph=URIRef(config.attributions_graph))
												for s, p, o in singleOtherResultsBiblioGraph.triples((URIRef(artwork), WHY.citesAsEvidence, None)):
													resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.citesAsEvidence, Literal(o) ))
											# source
											if len(data[URIbase]['source']) != 0:
												singleSourceGraph = utils.fetchData(uri=artwork, settingFile=settings, inputPattern=str(data[URIbase]['source']), outputPattern=rdflib.term.URIRef(WHY.hasSourceOfAttribution), outputGraph=URIRef(config.attributions_graph))
												for s, p, o in singleSourceGraph.triples((URIRef(artwork), WHY.hasSourceOfAttribution, None)):
													resultsGraph.add(( URIRef(WHY+instance+'-'+objProperty+'-'+instanceObj+'-obs'), WHY.hasSourceOfAttribution, URIRef(o) ))					
									
			return resultsGraph					

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print('findAttributions', exc_type, fname, exc_tb.tb_lineno, e)


	def updateAttributions(self):
		""" updates the graph attributions including reports (using findAttributions method) 
		for each observed artwork in the named graph artworks """
		resultsGraph=rdflib.ConjunctiveGraph(identifier=URIRef(config.attributions_graph))
		resultsGraph.bind("dc", DC)
		resultsGraph.bind("rdfs", RDFS)
		resultsGraph.bind("mauth", WHY)
		resultsGraph.bind("prov", PROV)
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		try:
			n = 0
			for artwork in self.uris:
				n += 1
				URIbase = utils.splitURI(artwork)
				with open(config.settingsFile) as settings:    
					data_source = json.load(settings)
					print str(n), ": Fetching data for URI:", artwork.encode('utf-8')
					if URIbase not in data_source:
						print 'NOT FOUND', artwork.encode('utf-8')
					else:
						artworkGraph = self.findAttributions(artwork)
						print 'YEE FOUND', artwork.encode('utf-8')
						if artworkGraph is not None:
								resultsGraph += artworkGraph
						
			
			# update triples on blazegraph
			resultsGraph.serialize('observations/observations-'+time+'.nq', format='nquads')
			config.server.update('load <'+currPath+'/observations/observations-'+time+'.nq>')
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print('updateAttributions', exc_type, fname, exc_tb.tb_lineno, e)

	# usage
	# get_artworks = """
	# 	PREFIX owl: <http://www.w3.org/2002/07/owl#>
	# 	SELECT DISTINCT ?artwork
	# 	FROM <"""+config.artworks_linkset+""">
	# 	WHERE { {?a ?b ?artwork } UNION {?artwork ?b ?c } }"""
	# # query the linkset of artworks: look for equivalences and return a list of equivalences
	# sparqlW = SPARQLWrapper(config.SPARQLendpoint)
	# sparqlW.setQuery(get_artworks)
	# sparqlW.setReturnFormat(JSON)
	# results = sparqlW.query().convert()
	# artworkList = list( result["artwork"]["value"] for result in (results["results"]["bindings"]))
				
	# kb = Connoisseur(artworkList, config.attributions_graph)
	# kb.updateAttributions()


