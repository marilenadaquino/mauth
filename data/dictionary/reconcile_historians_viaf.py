# coding: utf-8
import requests , time , csv , sys , rdflib , hashlib, logging , json , urllib
from bs4 import BeautifulSoup
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS
from fuzzywuzzy import fuzz
from time import sleep
# use python3 beacuse of the encoding issues

url = "http://arthistorians.info/index"
page=requests.get(url)
soup=BeautifulSoup(page.text,"lxml")

def reconcile():
	""" web scraping of the dictionary of art historians and reconciliation to viaf """
	baseURL = 'http://viaf.org/viaf/search/viaf?query=local.personalNames+%3D+%22'
	f=csv.writer(open('historians_reconciled_viaf.csv', 'w', encoding='utf-8'))
	f.writerow(['search']+['result']+['viaf']+['lc']+['isni']+['ratio']+['partialRatio']+['tokenSort']+['tokenSet']+['avg'])
	g_data = soup.findAll("span", {"class": "views-summary views-summary-unformatted"})
	for item in g_data:
		alpha_link = item.find("a")
		alpha_part_url = alpha_link.get('href')
		#if alpha_part_url == '/index/s':
		alpha_url = "http://arthistorians.info"+alpha_part_url
		alpha_page= requests.get(alpha_url)
		soupArtists=BeautifulSoup(alpha_page.text,"lxml")
		artist_tds = soupArtists.findAll("td", {"class": "views-field views-field-title active"})
		# get all the artists in each page
		for artist_td in artist_tds:
			artist_link = artist_td.find("a")
			artist_part_url = artist_link.get('href')
			artist_url = "http://arthistorians.info"+artist_part_url
			artist_page= requests.get(artist_url)
			# scrape each page and create a graph
			soupArtist=BeautifulSoup(artist_page.text,"lxml")
			nameContainer = soupArtist.find("div", {"class": "field-name-field-dc-title"})
			nameDiv = nameContainer.find("div", {"class": "field-items"})
			if nameDiv:
				name= nameDiv.find("div", {"class": "field-item"}).text

				rowEdited = urllib.parse.quote(name.strip())
				url = baseURL+rowEdited+'%22+and+local.sources+%3D+%22lc%22&sortKeys=holdingscount&maximumRecords=1&httpAccept=application/rdf+json'
				response = requests.get(url).content.decode('utf-8')
				print(response)
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
				f.writerow([name.strip()]+[label]+[viafid]+[lc]+[isni]+[ratio]+[partialRatio]+[tokenSort]+[tokenSet]+[avg])
				#print(name.encode('ascii', 'ignore'), ' #### ', label.encode('ascii', 'ignore'), ' --- ', viafid)

# reconcile()

# after cleaning the resulting csv, create a named graph 
# including the whole dataset (obtained by using get_critics_dictionary.py)
def sameAs_critics():
	""" given a csv with double-checked entity reconciliation 
	(between historians of the online dictionary and VIAF), 
	creates sameAs links in a new linkset"""
	# open the graph already created
	arthistorians_graph = URIRef('http://purl.org/emmedi/mauth/historians/')
	g=rdflib.ConjunctiveGraph(identifier=URIRef(arthistorians_graph))
	g.parse("arthistorians_dictionary.nq", format="nquads")
	g.bind('owl', OWL)
	with open('FINAL_dict_historians_reconciled_viaf.csv', 'r', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			firstName = row['search'].strip()
			altName = row['result'].strip()
			viaf = row['viaf'].strip()
			lc = row['lc'].strip()
			isni = row['isni'].strip()
			if viaf != '':
				for s,p,o in g.triples( (None, DCTERMS.title, None )):
					if (s, DCTERMS.alternative, None) in g:
						for s,p1,o1 in g.triples( (s, DCTERMS.alternative, None )):
							if altName.strip() == o1.strip():
								g.add(( s , OWL.sameAs , URIRef(viaf) ))
								g.add(( s , DCTERMS.alternative , Literal(firstName) ))
								if lc != '':
									g.add(( s , OWL.sameAs , URIRef(lc) ))
								if isni != '':
									g.add(( s , OWL.sameAs , URIRef(isni) ))
					elif altName.strip() != o.strip() and firstName.strip() == o.strip():
						g.add(( s , OWL.sameAs , URIRef(viaf) ))
						g.add(( s , DCTERMS.alternative , Literal(firstName) ))
						if lc != '':
							g.add(( s , OWL.sameAs , URIRef(lc) ))
						if isni != '':
							g.add(( s , OWL.sameAs , URIRef(isni) ))
	g.serialize(destination='linkset_arthistorians_dictionary.nq', format='nquads')

# sameAs_critics()