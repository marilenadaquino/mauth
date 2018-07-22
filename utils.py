import rdflib , hydra.tpf , SPARQLWrapper , logging , datetime , time , uuid , random , json , re , sys , os.path , csv
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import OWL, DC , RDF , RDFS
from SPARQLWrapper import SPARQLWrapper, JSON 
from pymantic import sparql


logging.basicConfig(level=logging.INFO)
server = sparql.SPARQLServer('http://127.0.0.1:9999/blazegraph/sparql')

WHY = Namespace("http://purl.org/emmedi/mauth/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

def lists_overlap(a, b):
	""" given two lists return true if there is an overlap """
	return bool(set(a) & set(b)) 


def splitURI(string):
    """Return URIbase, string truncated at the n occurrence of the delimiter d"""
    d = str('/')
    if re.findall(r"w3id", string):
    	n=5
    elif re.findall(r"mauth", string):
    	n=7
    elif re.findall(r"^http:\/\/www.idref", string):
    	n=3
    else:
    	n=4
    return str(d.join(string.split(d)[:n])) + '/'


def fetchData(uri, settingFile, inputPattern, outputPattern):
	'''uses a method detailed in a setting file 
	to fetch data having as subject the input URI (subject)
	and as BGP the specified input pattern.
	Finally it returns a new graph containing subject and object linked by a outputPattern '''
	
	# TODO clean instance matching
	# exceptions to match URI base 
	if re.findall(r"^http:\/\/d-nb.info", uri) or re.findall(r"^http:\/\/www.idref", uri):
		instance = uri.encode('utf-8').rsplit('/', 1)[-2]
	else:
		instance = uri.encode('utf-8').rsplit('/', 1)[-1]
	URIbase = splitURI(uri.encode('utf-8'))
	attributions_graph = 'http://purl.org/emmedi/mauth/attributions/'
	URIGraph = rdflib.ConjunctiveGraph(identifier=URIRef(attributions_graph))
	URIGraph.bind("owl", OWL)
	URIGraph.bind("dc", DC)
	URIGraph.bind("prov", PROV)

	URImatchPatterns = re.findall(r"https?:\/\/[^\s]*", inputPattern) # match URIs in *.json file and wrap into <> to rewrite the SPARQL query
	for URImatchPattern in URImatchPatterns:
		inputPattern = re.sub(URImatchPattern, r'<'+URImatchPattern+'>', inputPattern)
		inputPattern = re.sub(r'<<', r'<', inputPattern)
		inputPattern = re.sub(r'>>', r'>', inputPattern)

	# TODO query to be changed 
	query="""
			SELECT DISTINCT ?b 
			WHERE { <"""+uri.encode('utf-8')+"""> """+inputPattern+""" ?b }""" # rewrite SPARQL query

	with open(settingFile) as settings:    
		data_source = json.load(settings)
		print ("Fetching data for URI BASE:", URIbase, '\n')
		if URIbase in data_source:
			if data_source[URIbase].has_key("endpoint"):
				SPARQLendpoint = data_source[URIbase]["endpoint"]
				try:
					sparql = SPARQLWrapper(SPARQLendpoint) # prepare the SPARQL query
					sparql.setTimeout(15)
					sparql.setQuery(query)
					print(query)
					sparql.setReturnFormat(JSON)
					results = sparql.query().convert()
					resultsList = list(result["b"]["value"] for result in (results["results"]["bindings"]) if result["b"]["value"] != [])		
					for result in resultsList:
						print (result, '\n'	)
						URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(u'%s')% result.encode('utf-8') ))
					if str(URImatchPattern) == 'http://www.w3.org/2002/07/owl#sameAs':
						URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(uri)))
					else:
						pass
					print (URIbase.encode('utf-8'), "URI found at SPARQL endpoint ", SPARQLendpoint)
				except Exception as error:
					print (URIbase.encode('utf-8'), "no results for this SPARQL query at ", SPARQLendpoint , '\n', error)
			elif data_source[URIbase].has_key("content-negotiation"):
				try:
					for src, dst in data_source[URIbase]["content-negotiation"].items():
							graphTBL = re.sub(src, dst, uri.encode('utf-8'))
					tempGraph = rdflib.Graph()
					tempGraph.load(URIRef(graphTBL))
					# TODO change query
					q = """
						SELECT DISTINCT ?b 
						WHERE { ?a """+inputPattern+""" ?b }"""
					print (q)
					results = tempGraph.query(q)
					for result in results:
						print (result, '\n')
						URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(u'%s')% result.encode('utf-8') ))
					if str(URImatchPattern) == 'http://www.w3.org/2002/07/owl#sameAs':
						URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(uri)))
					else:
						pass
					print (URIbase.encode('utf-8'), "URI content-negotiation", URIRef(uri))
				except:
				  	print ("No content-negotiation supported")
			elif data_source[URIbase].has_key("linkeddatafragments"):
				try:
					if len(sys.argv) > 1:
						LDF = sys.argv[1]
					LDFGraph=rdflib.Graph("TPFStore")
					LDF = data_source[URIbase]["linkeddatafragments"]
					try:
						LDFGraph.open(LDF)
						results = LDFGraph.query(query)
						for result in results:
							print (result, '\n')
							URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(u'%s')% result.encode('utf-8') ))
						if str(URImatchPattern) == 'http://www.w3.org/2002/07/owl#sameAs':
							URIGraph.add((URIRef(uri), rdflib.term.URIRef(outputPattern), URIRef(uri))) # ???
						else:
							pass
						print (uri.encode('utf-8'), "Linked Data Fragment", URIRef(LDF)	)
					except Exception as error:
						print (uri.encode('utf-8'), error)	
				except Exception as error:
				  	print ("ehm...", query , error)
			else:
				print ("this URI has not settings")
		else:
			print (URIbase, "this URIbase is not in the mapping document")
	
	return URIGraph


def rebuildResults(results):
	""" given the results of a SPARQL query (against mauth) in JSON assings rebuilds the JSON"""
	providers = set()
	for attribution in results["results"]["bindings"]:
		providers.add(attribution["obsLabel"]["value"])
	
	attributions = []
	for provider in providers:
		attrib = dict()
		artists = set()
		artistsTitle = set()
		criteria = set()
		criteriaLabel = set()
		date = set()
		scholars = set()
		images = set()
		
		for attribution in results["results"]["bindings"]:
			if attribution["obsLabel"]["value"] == provider:
				attrib['provider'] = re.sub(' accepted attribution','',provider)
				# artwork
				if attribution["obsLabel"]["value"] == provider and 'artwork' in attribution.keys() and 'other' not in attribution.keys():
					attrib['artwork'] = attribution["artwork"]["value"]
				if attribution["obsLabel"]["value"] == provider and 'artworkTitle' in attribution.keys() and 'other' not in attribution.keys():
					attrib['artworkTitle'] = attribution["artworkTitle"]["value"]
				# other artworks
				if  attribution["obsLabel"]["value"] == provider and 'other' in attribution.keys():
					attrib['artwork'] = attribution["other"]["value"]
				if  attribution["obsLabel"]["value"] == provider and 'other' in attribution.keys() and 'artworkTitle' in attribution.keys():
					attrib['artworkTitle'] = attribution["artworkTitle"]["value"]
				# artists
				if  attribution["obsLabel"]["value"] == provider and 'artist' in attribution.keys():
					artists.add(attribution["artist"]["value"])
				if  attribution["obsLabel"]["value"] == provider and 'artistTitle' in attribution.keys():
					artistsTitle.add(attribution["artistTitle"]["value"])
				# date
				if  attribution["obsLabel"]["value"] == provider and 'date' in attribution.keys():
					date.add(attribution["date"]["value"])	
				if  attribution["obsLabel"]["value"] == provider and 'date' not in attribution.keys():
					date.add('none')
				# criteria
				if  attribution["obsLabel"]["value"] == provider and 'criterion' in attribution.keys():
					criteria.add(attribution["criterion"]["value"])								
				if  attribution["obsLabel"]["value"] == provider and 'criterion' not in attribution.keys():
					criteria.add('http://purl.org/emmedi/mauth/criteria/none')	

				if  attribution["obsLabel"]["value"] == provider and 'criterionLabel' in attribution.keys():
					criteriaLabel.add(attribution["criterionLabel"]["value"])								
				
				if  attribution["obsLabel"]["value"] == provider and 'criterionLabel' not in attribution.keys():
					criteriaLabel.add('none')	
				
				# scholar
				if  attribution["obsLabel"]["value"] == provider and 'scholar' in attribution.keys():
					scholars.add(attribution["scholar"]["value"])	
					if 'h_index' in attribution.keys():
						attrib[attribution["scholar"]["value"]] = [{'h_index': attribution["h_index"]["value"]}]
					else: 
						attrib[attribution["scholar"]["value"]] = [{'h_index': 0.0}]
					if 'a_index' in attribution.keys():
						attrib[attribution["scholar"]["value"]][0]['a_index'] = attribution["a_index"]["value"]
					else: 
						pass
				if  attribution["obsLabel"]["value"] == provider and 'scholar' not in attribution.keys():
					scholars.add('none')
				
				# images
				if  attribution["obsLabel"]["value"] == provider and 'image' in attribution.keys():
					images.add(attribution["image"]["value"])
				if  attribution["obsLabel"]["value"] == provider and 'image' not in attribution.keys():
					images.add('none')
		
		attrib['artist'] = list(artists)
		attrib['artistTitle'] = list(artistsTitle) 
		attrib['date'] = list(date) 
		attrib['criteria'] = list(criteria) 
		attrib['criterionLabel'] = list(criteriaLabel) 
		attrib['scholar'] = list(scholars) 
		attrib['images'] = list(images) 
		
		# for attribution in results["results"]["bindings"]:
		# 	if attribution["obsLabel"]["value"] == provider:
		# 		for schol in scholars:
		# 			indexes = list()
		# 			for attribution in results["results"]["bindings"]:
		# 				if 'h_index' in attribution.keys():
		# 					indexes.append({'h_index': attribution["h_index"]["value"]})
		# 				if 'a_index' in attribution.keys():
		# 					indexes.append({'a_index': attribution["a_index"]["value"]})
		# 			attrib[schol] = list(indexes)
				
	
		attributions.append(attrib)
	
	return attributions	


def rankDates(dates):
	""" given a list of dates, sorts them by them (desc) and attributes a score"""
	
	sortedDates = sorted(dates, reverse=True)
	current_date = datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')
	current_date = datetime.datetime.strptime(current_date, '%Y-%m-%dT%H:%M:%S' )
	datesRank = []
	normDatesRank = []
	for datestr in sortedDates:
		# timeliness
		if datestr == 'none':
			datestr = '0001-01-01T00:00:00'
		if datestr.endswith('Z'):
			datestr = datestr[:-1]
		updated_on = datetime.datetime.strptime(datestr, '%Y-%m-%dT%H:%M:%S')
		delta = (current_date - updated_on).days
		rank = max(0, 100000 - delta)
		datesRank.append((datestr, rank))
	sumRanks = sum([pair[1] for pair in datesRank])

	# normalize ranking
	for d,r in datesRank:
		if sumRanks != float(0.00):
			ra = float(r)/sumRanks
		else:
			ra = float(0.00)
		normDatesRank.append((d,round(ra, 2)))
	return normDatesRank	


def rankCriteria(criterion):
	""" given a named graph including criteria and related score
	returns score"""
	criteriaGraph = rdflib.ConjunctiveGraph(identifier=URIRef('http://purl.org/emmedi/mauth/criteria/'))
	criteriaGraph.parse('vocabulary-criteria.nq', format="nquads")
	for s,p,o in criteriaGraph.triples(( URIRef(criterion), URIRef('http://dbpedia.org/ontology/rating'), None )):
		if 'none' in criterion:
			return float(0.00)
		elif o is not None:
			return float(o)


def sharedAttribution(inputArtist, listOfArtists):
	""" given a list of artists returns, for each artist returns the number of occurrences in the list, 
	either of the same uri or of equivalent uris, that are deduced by the linkset of artists"""
	sparql = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
	# query the linkset for equivalences to the input artist uri
	try:
		score = float(0.00)
		get_artists = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			SELECT DISTINCT ?b 
			FROM <http://purl.org/emmedi/mauth/artists/>
			WHERE { {<"""+str(inputArtist)+"""> owl:sameAs ?b } UNION {?b owl:sameAs <"""+str(inputArtist)+""">}}"""
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		
		sparql.setQuery(get_artists)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		# create a list of equivalences for the input artist uri
		inputArtistEquivalenceList = list(str(result["b"]["value"]) for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
		inputArtistEquivalenceList.append(inputArtist)
	except:
		pass
	
	# query the linkset of artists for each artist in the given list. 
	for artist in listOfArtists:
		try:
			get_artistsOfList = """
				PREFIX owl: <http://www.w3.org/2002/07/owl#>
				SELECT DISTINCT ?b 
				FROM <http://purl.org/emmedi/mauth/artists/>
				WHERE { {<"""+artist+"""> owl:sameAs ?b } UNION {?b owl:sameAs <"""+artist+""">}}"""
			# query the linkset of artworks: look for equivalences and return a list of equivalences
			sparql.setQuery(get_artistsOfList)
			sparql.setReturnFormat(JSON)
			results = sparql.query().convert()
			# create a list of equivalences for each artist
			artistEquivalenceList = list(str(result["b"]["value"]) for result in (results["results"]["bindings"]) if result["b"]["value"] != [])
			artistEquivalenceList.append(artist)
			if lists_overlap(inputArtistEquivalenceList, artistEquivalenceList):
				score += 1.00	
		except:
			pass
	score = score - 1.00 # naive way to remove the equivalence to itself
	return score


def hindex(citationsArray):
	n = len(citationsArray);
	count = [0] * (n + 1)
	for x in citationsArray:
		if x >= n:
			count[n] += 1
		else:
			count[x] += 1
	h = 0
	for i in reversed(xrange(0, n + 1)):
		h += count[i]
		if h >= i:
			return i
	return h


def rankHistorianByArtist(historian, artist):
	""" given the uri of a historian, look into domain experts' datasets 
	to see how many times s/he is cited wrt the specified artist and calculate the h-index for an artist. 
	ATM only Itatti and Zeri are considered """
	
	number_of_artworks = """
		SELECT (count(distinct ?artwork) as ?count)
		WHERE { {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> 
                   <"""+str(artist)+"""> .} UNION
		       {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> ?artist . 
		        	?artist (^owl:sameAs|owl:sameAs)* <"""+str(artist)+"""> .} .
		       
		       ?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?attribution .
		       ?attribution <http://purl.org/emmedi/hico/hasInterpretationType> ?accepted.
		       FILTER regex(str(?accepted),'preferred','i')
				?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .      
		      }"""

	number_of_agreements = """
		SELECT (count(distinct ?artwork) as ?count)
		WHERE { {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> 
               <"""+str(artist)+"""> .} UNION
	       {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> ?artist . 
	        	?artist owl:sameAs ?common . <"""+str(artist)+"""> owl:sameAs ?common .} .
	       
	       ?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?attribution .
	       ?attribution <http://purl.org/emmedi/hico/hasInterpretationType> ?accepted . 
	       { ?attribution <http://purl.org/spar/cito/agreesWith> <"""+str(historian)+"""> .} UNION
	       { ?attribution <http://purl.org/spar/cito/agreesWith> ?historian . 
	        	?historian owl:sameAs ?commonH . <"""+str(historian)+"""> owl:sameAs ?commonH .} 
	       FILTER regex(str(?accepted),'preferred','i')
			?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .      
	      }"""
	try:
		# exception: fondazione zeri reduced to federico zeri
		sparql = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		sparql.setQuery(number_of_artworks)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		for result in (results["results"]["bindings"]): 
			if result["count"]["value"] != '':
				numberArtworks = result["count"]["value"]
	except:
		pass
	
	try:
		sparqlW = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		sparqlW.setQuery(number_of_agreements)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		for result in (results["results"]["bindings"]): 
			if result["count"]["value"] != '':
				numberAgreements = result["count"]["value"]
		a_index = float(numberAgreements) / float(numberArtworks)
		return float(round(a_index, 2))
	except:
		pass


def rankHistorianBias(historian, artist):
	""" """
	
	#the number of times a historian's attribution is chosen regardless the choice is motivated or not wrt a specific artist - in a photo archive
	number_of_citations = """
		SELECT (count(distinct ?artwork) as ?count)
		WHERE { {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> 
	               <"""+str(artist)+"""> .} UNION
		       {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> ?artist . 
		        	?artist (^owl:sameAs|owl:sameAs)+ <"""+str(artist)+"""> .} .
		       
		       ?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?attribution .
		       ?attribution <http://purl.org/emmedi/hico/hasInterpretationType> ?accepted . 
		       { ?attribution <http://purl.org/spar/cito/agreesWith> <"""+historian+"""> .} UNION
		       { ?attribution <http://purl.org/spar/cito/agreesWith> ?historian . 
		        	?historian (^owl:sameAs|owl:sameAs)+ <"""+historian+"""> .} 
				?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .      
		      }"""
	try:
		sparqlW = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		sparqlW.setQuery(number_of_citations)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		for result in (results["results"]["bindings"]): 
			if result["count"]["value"] != '':
				numberCitations = result["count"]["value"]
			else:
				numberCitations = 1.0
	except:
		pass
	
	# the number of times a historian's attribution is preferred over other listed attributions wrt a specific artist
	number_of_motivated_agreements = """
			SELECT (count(distinct ?artwork) as ?count)
			WHERE { {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> 
		               <"""+str(artist)+"""> .} UNION
			       {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> ?artist . 
			        	?artist (^owl:sameAs|owl:sameAs)+ <"""+str(artist)+"""> .} .
			       
			       ?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?attribution ; 
			       			 <http://www.w3.org/ns/prov#wasGeneratedBy> ?attributionDisc .
			       ?attribution <http://purl.org/emmedi/hico/hasInterpretationType> ?accepted .
			       ?attributionDisc <http://purl.org/emmedi/hico/hasInterpretationType> ?discarded . 
			       { ?attribution <http://purl.org/spar/cito/agreesWith> <"""+historian+"""> .} UNION
			       { ?attribution <http://purl.org/spar/cito/agreesWith> ?historian . 
			        	?historian (^owl:sameAs|owl:sameAs)+ <"""+historian+"""> .} 
			       FILTER regex(str(?accepted),'preferred','i')
			       FILTER regex(str(?discarded),'discarded','i')
					?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .      
			      }"""
	
	try:
		sparqlW = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		sparqlW.setQuery(number_of_motivated_agreements)
		sparqlW.setReturnFormat(JSON)
		results = sparqlW.query().convert()
		for result in (results["results"]["bindings"]): 
			if result["count"]["value"] != '':
				numberMotivatedAgreements = result["count"]["value"]
			else:
				numberMotivatedAgreements = 1.0
		auth_index = float(numberMotivatedAgreements) / float(numberCitations)
		if auth_index is not None:
			return float(round(auth_index, 2))
		else:
			return float(0.0)
	except:
		pass


def rankHistorian():
	""" given the uri of a historian, look into domain experts' datasets 
	to see how many times s/he is cited wrt the specified artist and calculate the h-index for an artist. 
	ATM only Itatti and Zeri are considered. Load triples on a named graph """
	historiansIndexesGraph = rdflib.ConjunctiveGraph(identifier='http://purl.org/emmedi/mauth/h_index/')
	
	# exception: fondazione zeri to be reduced to federico zeri
	get_historians = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			PREFIX cito: <http://purl.org/spar/cito/>
			SELECT DISTINCT ?h
			WHERE { ?attr cito:agreesWith ?h }"""
	try:
		sparql = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		sparql.setQuery(get_historians)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		historians = list(result["h"]["value"] for result in (results["results"]["bindings"]) if result["h"]["value"] != [])
	except:
		pass

	for historian in historians:
		print historian
		get_artists = """
			PREFIX owl: <http://www.w3.org/2002/07/owl#>
			PREFIX mauth: <http://purl.org/emmedi/mauth/>
			SELECT DISTINCT ?a
			WHERE { ?obs mauth:hasObservedArtist ?a ; 
					mauth:agreesWith <"""+historian+""">}"""
		try:
			sparqlw = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
			sparqlw.setQuery(get_artists)
			sparqlw.setReturnFormat(JSON)
			results = sparqlw.query().convert()
			artists = list(result["a"]["value"] for result in (results["results"]["bindings"]) if result["a"]["value"] != [])
		except:
			pass
		
		# H_index (done)
		# citations = """
		# SELECT (count(distinct ?artwork) as ?count) ?artist 
		# WHERE { {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> 
		#                ?artist .} UNION
		# 	   {?creation <http://www.cidoc-crm.org/cidoc-crm/P14_carried_out_by> ?artist . 
		# 	    	?artist (^owl:sameAs|owl:sameAs)* ?artist .}
			   
		# 	  	?creation <http://www.w3.org/ns/prov#wasGeneratedBy> ?attribution .
		# 		       ?attribution <http://purl.org/emmedi/hico/hasInterpretationType> ?accepted . 
		# 		       { ?attribution <http://purl.org/spar/cito/agreesWith> <"""+str(historian)+"""> . } UNION
		# 	   			{ ?attribution <http://purl.org/spar/cito/agreesWith> ?same. ?same (^owl:sameAs|owl:sameAs)* <"""+str(historian)+"""> .}
		# 		       FILTER regex(str(?accepted),'preferred','i')
		# 				?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .
		# 		?artwork <http://www.cidoc-crm.org/cidoc-crm/P94i_was_created_by> ?creation .      
		# 	  }
		# GROUP BY ?artist
		# """
		# try:
		# 	sparql1 = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		# 	sparql1.setQuery(citations)
		# 	sparql1.setReturnFormat(JSON)
		# 	results = sparql1.query().convert()

		# 	citationsArray = list(int(result["count"]["value"]) for result in (results["results"]["bindings"]) if result["count"]["value"] != [])
		# 	print citationsArray
		# 	# h index
		# 	h = hindex(citationsArray)
		# 	print 'h index:', h
		# 	historiansIndexesGraph.add(( URIRef(historian), WHY.hasHIndex, Literal(h, datatype=XSD.float) ))
		# except:
		# 	pass
		
		# Artist_Index
		for artist in artists:
			print artist
			a_index = rankHistorianByArtist(historian, artist)
			print 'a index:', a_index
			historiansIndexesGraph.add(( URIRef(historian), WHY.hasArtistIndex, URIRef(historian+'/'+artist) ))
			historiansIndexesGraph.add(( URIRef(historian+'/'+artist), WHY.hasArtistIndex, Literal(a_index, datatype=XSD.float) ))
			historiansIndexesGraph.add(( URIRef(historian+'/'+artist), WHY.hasIndexedHistorian, URIRef(historian) ))
			historiansIndexesGraph.add(( URIRef(historian+'/'+artist), WHY.hasIndexedArtist, URIRef(artist) ))
			#auth_index = rankHistorianBias(historian, artist)
			#print 'auth index:', auth_index
			# if auth_index is not None:
			# 	historiansIndexesGraph.add(( URIRef(historian), WHY.hasAuthoritativenessIndex, Literal(auth_index, datatype=XSD.float) ))
			# else:
			# 	historiansIndexesGraph.add(( URIRef(historian), WHY.hasAuthoritativenessIndex, Literal(0.0, datatype=XSD.float) ))
			
	historiansIndexesGraph.serialize(destination='data/statistics_by_artist.nq', format='nquads')
	server.update('load <file:///Users/marilena/Desktop/mauth/data/statistics_by_artist.nq>')

#rankHistorian()


def getLabel(uri):
	""" given a uri retrns the label"""
	label = """
		PREFIX dcterms: <http://purl.org/dc/terms/>
		SELECT ?label
		WHERE { {<"""+uri+"""> rdfs:label ?label .} UNION {<"""+uri+"""> dcterms:title ?label .}}"""
	try:
		# exception: fondazione zeri reduced to federico zeri
		sparql = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
		# query the linkset of artworks: look for equivalences and return a list of equivalences
		sparql.setQuery(label)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()
		for result in (results["results"]["bindings"]): 
			if result["label"]["value"] != '':
				urilabel = result["label"]["value"]
			else:
				urilabel = 'unknown'
		return urilabel
	except:
		pass
	

def getURI(inputURL):
	""" given the URL of an online cataloguing record returns the URI of the artwork"""
	# zeri
	if 'tipo_scheda=OA&id=' in inputURL:
		oa = re.compile('OA&id=(.*)&titolo=', re.IGNORECASE|re.DOTALL)
		match = oa.search(inputURL)
		if match:
			iri = 'http://purl.org/emmedi/mauth/zeri/artwork/'+match.group(1)
			return iri
	
	# i tatti
	elif 'HVD_IMAGES&imageId=urn-3:VIT.BB:10593338&adaptor=Local%20' in inputURL:
		oa = re.compile('HVD_IMAGES&imageId=(.*)&adaptor=', re.IGNORECASE|re.DOTALL)
		match = oa.search(inputURL)
		if match:
			with open('data/itatti/ss_assets_811_130578.csv', 'r') as csvfile:
				reader = csv.DictReader(csvfile)
				for sheetX in reader:
					artworkID = sheetX['Work[36658]']
					photoOnlineURN = re.sub('drs:', '', str(sheetX['Filename']))
					if match.group(1) == photoOnlineURN:
						iri = 'http://purl.org/emmedi/mauth/itatti/artwork/'+artworkID
			return iri 
	else:
		return inputURL








