# coding: utf-8
import requests , time , csv , sys , rdflib , md5 , hashlib, logging , json , urllib
from bs4 import BeautifulSoup
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS
from fuzzywuzzy import fuzz

logging.basicConfig()

url = "http://arthistorians.info/index"
page=requests.get(url)
soup=BeautifulSoup(page.text,"lxml")

BIO = Namespace("http://purl.org/vocab/bio/0.1/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

uriBase = "https://w3id.org/arthistorians"
arthistorians_graph = URIRef('http://purl.org/emmedi/mauth/historians/')
g=rdflib.ConjunctiveGraph(identifier=URIRef(arthistorians_graph))
g.bind('bio', BIO)
g.bind('foaf', FOAF)

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


def strip_tags(html, invalid_tags):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.findAll(True):
        if tag.name in invalid_tags:
            s = ""
            for c in tag.contents:
                if not isinstance(c, NavigableString):
                    c = strip_tags(unicode(c), invalid_tags)
                s += unicode(c)
            tag.replaceWith(s)
    return soup
invalid_tags = ['b', 'i', 'u']


def scrape_dictionary_arthistorians():
	""" web scraping of the online dictionary of art historians and transformation into a RDF named graph"""
	# get all the pages in the alphabetical list
	g_data = soup.findAll("span", {"class": "views-summary views-summary-unformatted"})
	for item in g_data:
		alpha_link = item.find("a")
		alpha_part_url = alpha_link.get('href')
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
			g.add(( URIRef(artist_url), DCTERMS.subject, URIRef(uriBase+artist_part_url) ))		
			g.add(( URIRef(uriBase+artist_part_url), RDF.type, FOAF.Person ))
			
			# scrape each page and create a graph
			soupArtist=BeautifulSoup(artist_page.text,"lxml")
			try:
				# name
				nameContainer = soupArtist.find("div", {"class": "field-name-field-dc-title"})
				nameDiv = nameContainer.find("div", {"class": "field-items"})
				name= nameDiv.find("div", {"class": "field-item"}).text
				g.add(( URIRef(uriBase+artist_part_url), DCTERMS.title, Literal(name) ))	
				
				# alternative names
				altNameContainer = soupArtist.find("div", {"class": "field-name-field-local-names"})
				if altNameContainer:
					altNameDiv = altNameContainer.find("div", {"class": "field-items"})
					altNames= altNameDiv.findAll("div", {"class": "field-item"})
					for altName in altNames:
						g.add(( URIRef(uriBase+artist_part_url), DCTERMS.alternative, Literal(altName.text) ))
				
				# birth
				birthContainer = soupArtist.find("div", {"class": "field-name-field-dc-date-born"})
				if birthContainer:
					birthDiv = birthContainer.find("div", {"class": "field-items"})
					birthDateCont= birthDiv.find("div", {"class": "field-item"})
					birthDate= birthDateCont.find("span").get('content')
					birthYear= birthDateCont.find("span").text
					g.add(( URIRef(uriBase+artist_part_url), BIO.birth, URIRef(uriBase+artist_part_url+'/birth') ))
					g.add(( URIRef(uriBase+artist_part_url+'/birth'), RDF.type, URIRef(BIO.Birth) ))
					g.add(( URIRef(uriBase+artist_part_url+'/birth'), DCTERMS.date, Literal(birthDate,datatype=XSD.dateTime) ))
					g.add(( URIRef(uriBase+artist_part_url+'/birth'), BIO.principal, URIRef(uriBase+artist_part_url) ))
					birthPlaceContainer = soupArtist.find("div", {"class": "field-name-field-dc-coverage-born"})
					if birthPlaceContainer:
						birthPlaceDiv = birthPlaceContainer.find("div", {"class": "field-items"})
						birthPlace= birthPlaceDiv.find("div", {"class": "field-item"})
						g.add(( URIRef(uriBase+artist_part_url+'/birth'), BIO.place, URIRef(uriBase+'/'+clean_to_uri(birthPlace)) ))
						g.add(( URIRef(uriBase+'/'+clean_to_uri(birthPlace)) , RDFS.label, Literal(birthPlace) ))
				
				# death
				deathContainer = soupArtist.find("div", {"class": "field-name-field-dc-date-died"})
				if deathContainer:
					deathDiv = deathContainer.find("div", {"class": "field-items"})
					deathDateCont= deathDiv.find("div", {"class": "field-item"})
					deathDate= deathDateCont.find("span").get('content')
					deathYear= deathDateCont.find("span").text
					g.add(( URIRef(uriBase+artist_part_url), BIO.death, URIRef(uriBase+artist_part_url+'/death') ))
					g.add(( URIRef(uriBase+artist_part_url+'/death'), RDF.type, URIRef(BIO.Death) ))
					g.add(( URIRef(uriBase+artist_part_url+'/death'), DCTERMS.date, Literal(deathDate,datatype=XSD.dateTime) ))
					g.add(( URIRef(uriBase+artist_part_url+'/death'), BIO.principal, URIRef(uriBase+artist_part_url) ))
					deathPlaceContainer = soupArtist.find("div", {"class": "field-name-field-dc-coverage-died"})
					if deathPlaceContainer:
						deathPlaceDiv = deathPlaceContainer.find("div", {"class": "field-items"})
						deathPlace= deathPlaceDiv.find("div", {"class": "field-item"})
						g.add(( URIRef(uriBase+artist_part_url+'/death'), BIO.place, URIRef(uriBase+'/'+clean_to_uri(deathPlace)) ))
						g.add(( URIRef(uriBase+'/'+clean_to_uri(deathPlace)) , RDFS.label, Literal(deathPlace) ))
				
				# overview
				overviewContainer = soupArtist.find("div", {"class": "field-type-text-with-summary"})
				if overviewContainer:
					overviewDiv = overviewContainer.find("div", {"class": "field-items"})
					g.add(( URIRef(uriBase+artist_part_url), RDFS.comment, Literal(overviewDiv,datatype=RDF.HTML ) ))	
				
				# bibliography
				biblioContainer = soupArtist.find("div", {"class": "field-name-field-dc-relation"})
				if biblioContainer:
					biblioDiv = biblioContainer.find("div", {"class": "field-items"})
					biblio = biblioDiv.find("div", {"class": "field-item"}).text
					biblioRefs = biblio.split(';')
					for biblioRef in biblioRefs:
						m = hashlib.md5.new()
						m = m.update(biblioRef)
						m = m.hexdigest()
						g.add(( URIRef(uriBase+artist_part_url), DCTERMS.creator, URIRef(uriBase+'/biblio/'+str(m)) ))
						g.add(( URIRef(uriBase+'/biblio/'+str(m)), DCTERMS.bibliographicCitation, Literal(biblioRef) ))

				# source
				sourceContainer = soupArtist.find("div", {"class": "field-name-field-dc-source"})
				if sourceContainer:
					sourceDiv = sourceContainer.find("div", {"class": "field-items"})
					source = sourceDiv.find("div", {"class": "field-item"}).text
					sourceRefs = source.split(';')
					for sourceRef in sourceRefs:
						ms = hashlib.md5.new()
						ms = ms.update(biblioRef)
						ms = ms.hexdigest()
						
						g.add(( URIRef(uriBase+'/biblio/'+str(ms)), DCTERMS.subject , URIRef(uriBase+artist_part_url) ))
						g.add(( URIRef(uriBase+'/biblio/'+str(ms)), DCTERMS.bibliographicCitation, Literal(sourceRef) ))
				g.serialize(destination='arthistorians_dictionary.nq', format='nquads')			
			except:
				pass

	