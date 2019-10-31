#!/usr/bin/python
# -*- coding: UTF-8
import requests , time , csv , sys , rdflib , hashlib, logging , json , urllib , re , string ,io
from rdflib import URIRef , XSD, Namespace , Literal 
from rdflib.namespace import OWL, DCTERMS , RDF , RDFS
from fuzzywuzzy import fuzz
import xml.etree.ElementTree as ET
from pymantic import sparql
from io import BytesIO     # for handling byte strings
from io import StringIO    # for handling unicode strings

CIDOC = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
HICO = Namespace("http://purl.org/emmedi/hico/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
CITO = Namespace("http://purl.org/spar/cito/")

base = 'http://purl.org/emmedi/mauth/itatti/'
criterion = 'http://purl.org/emmedi/mauth/criteria/'
itatti_graph = URIRef(base)
arthistorians_graph = URIRef('http://purl.org/emmedi/mauth/historians/')
artists_graph = URIRef('http://purl.org/emmedi/mauth/artists/')

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

def strip_punct(text):
	text = re.sub(r"[^\w\s\']","", text).strip()
	return text

# utils
def get_criteria(attribution):
	""" given a string representing an attribution, return a list of suitable criteria 
	and cited entities (that agree with the attribution) for reconciliation"""
	criteria = []
	attribution = str(attribution)
	re.sub("^b\'","", attribution)
	# documentation
	if 'expertise' in attribution:
		criteria.append(('documentation', ''))

	# archival classification
	if 'filed' in attribution or 'Filed' in attribution or 'flied' in attribution:
		criteria.append(('archival-classification', 'Bernard Berenson'))
	
	# caption
	if 'label attached to the work' in attribution:
		criteria.append(('caption-on-photo', ''))
	
	# archival-creator-bibliography
	if 'listed' in attribution or 'Listed' in attribution:
		criteria.append(('archival-creator-bibliography','Bernard Berenson'))
	
	# artist signature
	if 'Artist\'s signature' in attribution or 'Signed work' in attribution or 'Work inscribed with artist\'s name' in attribution or 'Signed and dated work' in attribution:
		criteria.append(('artist-signature',''))
	
	# sigla
	if 'monogram' in attribution:
		criteria.append(('sigla',''))
	
	# auction
	if 'auction' in attribution:
	 	auction1 = re.compile("b?(.*) auction", re.IGNORECASE|re.DOTALL).search(attribution)
	 	if auction1:
	 		criteria.append(('auction-attribution', strip_punct(auction1.group(1)).strip() ))
	
	# scholar attribution
	if 'comunication by' in attribution or 'communication by' in attribution or 'attribution by' in attribution or 'authenticated by' in attribution:
		person1Pattern = re.compile("(by\s)(.*)(\sto B)", re.IGNORECASE|re.DOTALL)
		person2Pattern = re.compile("(by\s)(.*)(\s\()", re.IGNORECASE|re.DOTALL)
		person3Pattern = re.compile("(by\s)(.*)(\son)", re.IGNORECASE|re.DOTALL)
		person4Pattern = re.compile("(by\s)(.*)(\sattributing)", re.IGNORECASE|re.DOTALL)
		person5Pattern = re.compile("(by\s)(.*)(\:)", re.IGNORECASE|re.DOTALL)
		person6Pattern = re.compile("(by\s)(.*)(\,)", re.IGNORECASE|re.DOTALL)
		match1 = person1Pattern.search(attribution)
		match2 = person2Pattern.search(attribution)
		match3 = person3Pattern.search(attribution)
		match4 = person4Pattern.search(attribution)
		match5 = person5Pattern.search(attribution)
		if 'Bernard Berenson' in attribution:
			criterion = 'archival-creator-attribution'
		else:
			criterion = 'scholar-attribution'
		
		if match1:
			personName = match1.group(2)
			criteria.append((criterion, personName))
		
		elif match2:
			personName = match2.group(2)
			criteria.append((criterion, personName))
		
		elif match3:
			personName = match3.group(2)
			criteria.append((criterion, personName))
		
		elif match4:
			personName = match4.group(2)
			criteria.append((criterion, personName))
		
		elif match5:
			personName = match5.group(2)
			criteria.append((criterion, personName))
		else:
		 	criteria.append((criterion, ''))
	
	if 'described by Mary Berenson' in attribution:
		criteria.append(('scholar-attribution', 'Mary Berenson'))

	# archive creator note on photo
	if ('notes by Bernard Berenson' in attribution) or ('andwritten note by Bernard Berenson' in attribution) or ('andwritten note (partially erased) by Bernard Berenson' in attribution):
		criteria.append(('archival-creator-note-on-photo','Bernard Berenson'))
	if 'notes by Mary and Bernard Berenson' in attribution:
		criteria.append(('archival-creator-note-on-photo', 'Bernard Berenson'))
		criteria.append(('archival-creator-note-on-photo', 'Mary Berenson'))
	

	# scholar note on photo
	if (('note by' in attribution) or ('note signed by' in attribution)) and ('Bernard Berenson' not in attribution):
		person1Pattern = re.compile(r".*by\s(.*)(\sreads\:?)")
		person11Pattern = re.compile(r".*by\s(.*)(\sread\:?)")
		person2Pattern = re.compile(r".*by\s(.*)(\s\()(.*\sread?s?\:?)")
		person3Pattern = re.compile(r".*by\s(.*)(\son)")
		person4Pattern = re.compile(r".*by\s(.*)(\sattribut)")
		person5Pattern = re.compile(r".*by\s(.*)(\:)")
		person6Pattern = re.compile(r".*by\s(.*)(\,)")
		person7Pattern = re.compile(r".*by\s(.*)(\(see)")
		if person1Pattern.search(attribution):
			personName = person1Pattern.search(attribution).group(1)
			personName = re.sub('\(now erased\)','', personName)
			personName = re.sub('\, 26 July 1924\,','', personName)
			personName = re.sub('\(now partially erased\)','', personName)
			personName = re.sub('\(erased\)','', personName)
			personName = re.sub('\, now erased\,?','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person11Pattern.search(attribution):
			personName = person11Pattern.search(attribution).group(1)
			personName = re.sub('\(now erased\)','', personName)
			personName = re.sub('\, 26 July 1924\,','', personName)
			personName = re.sub('\(now partially erased\)','', personName)
			personName = re.sub('\(erased\)','', personName)
			personName = re.sub('\, now erased\,?','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person2Pattern.search(attribution) and 'read' not in attribution:
			personName = person2Pattern.search(attribution).group(1)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person3Pattern.search(attribution) and 'read' not in attribution and 'attributing' not in attribution:
			personName = person3Pattern.search(attribution).group(1)
			personName = re.sub(' of a head in a tondo','', personName)
			personName = re.sub(' \(partially illegible\) reporting an attribution of the work to Piero di Cosimo\,','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person4Pattern.search(attribution):
			personName = person4Pattern.search(attribution).group(1)
			personName = re.sub('\(now erased\)','', personName)
			personName = re.sub('\(partially illegible\) reporting an','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person5Pattern.search(attribution) and 'read' not in attribution:
			personName = person5Pattern.search(attribution).group(1)
			personName = re.sub('\(erased\)','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person6Pattern.search(attribution) and 'attribut' not in attribution and 'read' not in attribution:
			personName = person6Pattern.search(attribution).group(1)
			personName = re.sub('\(now partially erased\)','', personName)
			personName = re.sub('\(erased\)','', personName)
			personName = re.sub('\, now erased\,?','', personName)
			personName = re.sub('\, 26 July 1924\,','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person7Pattern.search(attribution) and 'attribut' not in attribution and 'read' not in attribution:
			personName = person7Pattern.search(attribution).group(1)
			personName = re.sub('\(now erased\)','', personName)
			personName = re.sub('( dated .*)','', personName)
			personName = re.sub('\(now partially erased\)','', personName)
			personName = re.sub('\(erased\)','', personName)
			personName = re.sub('\, now erased\,?','', personName)
			personName = re.sub('(\:.*)','', personName)
			criteria.append(('scholar-note-on-photo', personName.strip()))
		if person1Pattern.search(attribution) is None and person11Pattern.search(attribution) is None and person2Pattern.search(attribution) is None and person3Pattern.search(attribution) is None and person4Pattern.search(attribution) is None and person5Pattern.search(attribution) is None and person6Pattern.search(attribution) is None and person7Pattern.search(attribution) is None:
			criteria.append(('scholar-note-on-photo', ''))
	
	# anonymous note on photo
	if 'andwritten note (see' in attribution or 'andwritten notes attributing' in attribution \
		or 'andwritten note attributing' in attribution or 'andwritten note report' in attribution \
		or 'andwritten note stating' in attribution or 'handwritten note reads' in attribution \
		or 'handwritten note (' in attribution \
		or 'typewritten note attributing' in attribution:
		criteria.append(('anonymous-note-on-photo',''))
	
	# museum attribution
	if 'online' in attribution or 'website' in attribution or 'atabase' in attribution or 'email' in attribution:
		emailPattern = re.compile(r"^email from (.*)\,", flags=re.IGNORECASE) 
		if emailPattern.search(attribution): # website Fondazione della Cassa di Risparmio di Perugia (
			museum = emailPattern.search(attribution).group(1)
			criteria.append(('museum-attribution', museum))
		museumPattern = re.compile(r"^museum's website", flags=re.IGNORECASE) 
		museum2Pattern = re.compile(r"^website (.*)\s(\()", flags=re.IGNORECASE) 
		museum3Pattern = re.compile(r"^(.*)\swebsite", flags=re.IGNORECASE)
		museum4Pattern = re.compile(r"^(.*)\sdatabase", flags=re.IGNORECASE)
		museum5Pattern = re.compile(r"^museum's online", flags=re.IGNORECASE) 
		museum51Pattern = re.compile(r"^museum on line", flags=re.IGNORECASE)
		museum6Pattern = re.compile(r"^(.*)\sonline", flags=re.IGNORECASE) 
		if museumPattern.search(attribution): # museum's website
			criteria.append(('museum-attribution',''))
		if museum2Pattern.search(attribution): # website Fondazione della Cassa di Risparmio di Perugia (
			museum = museum2Pattern.search(attribution).group(1)
			criteria.append(('museum-attribution', museum))
		if museum3Pattern.search(attribution): # Metropolitan Museum of Art website
			museum = museum3Pattern.search(attribution).group(1)
			criteria.append(('museum-attribution', museum))
		if museum4Pattern.search(attribution): # Metropolitan Museum of Art website
			museum = museum4Pattern.search(attribution).group(1)
			criteria.append(('museum-attribution', museum))
		if museum5Pattern.search(attribution) or museum51Pattern.search(attribution): # museum's online
			criteria.append(('museum-attribution',''))
		if museum6Pattern.search(attribution) and "Fondazione Federico Zeri" not in attribution: # Fondazione Federico Zeri online catalog will be wrong!
			museum = museum6Pattern.search(attribution).group(1)
			criteria.append(('museum-attribution', museum))
	if "Fondazione Federico Zeri" in attribution:
		criteria.append(('scholar-attribution', 'Fondazione Federico Zeri'))
	
	# bibliography	
	if "Inventory" in attribution:
		criteria.append(('bibliography', ''))
	if 'Gabriella Capecchi' in attribution:
		criteria.append(('bibliography', 'Gabriella Capecchi'))
	if 'Edvige Lugaro' in attribution:
		criteria.append(('bibliography', 'Edvige Lugaro'))
	if 'Ulrich Middeldorf' in attribution:
		criteria.append(('bibliography', 'Ulrich Middeldorf'))
	if 'Luisa Vertova' in attribution:
		criteria.append(('bibliography', 'Luisa Vertova'))
	if 'Franco Russoli' in attribution:
		criteria.append(('bibliography', 'Franco Russoli'))
	if 'Anneke De Vries' in attribution:
		criteria.append(('bibliography', 'Anneke De Vries'))
	if 'Sherwood A. Fehm' in attribution:
		criteria.append(('bibliography', 'Sherwood A. Fehm'))
	if 'Bruno Zanardi' in attribution:
		criteria.append(('bibliography', 'Bruno Zanardi'))
	if 'Stefan Weppelmann' in attribution:
		criteria.append(('bibliography', 'Stefan Weppelmann'))
	if 'Filippo Todini' in attribution:
		criteria.append(('bibliography', 'Filippo Todini'))
	if 'Richard Offner' in attribution:
		criteria.append(('bibliography', 'Richard Offner'))
	if 'Susan L. Caroselli' in attribution:
		criteria.append(('bibliography', 'Susan L. Caroselli'))
	if 'Fabio Massaccesi' in attribution:
		criteria.append(('bibliography', 'Fabio Massaccesi'))
	if 'Fabio Bisogni' in attribution:
		criteria.append(('bibliography', 'Fabio Bisogni'))	
	if 'Richard Offner with Klara Steinweg' in attribution:
		criteria.append(('bibliography', 'Richard Offner'))
		criteria.append(('bibliography', 'Klara Steinweg'))
	if 'Donal Cooper and Janet Robson' in attribution:
		criteria.append(('bibliography', 'Donal Cooper'))
		criteria.append(('bibliography', 'Janet Robson'))
	if 'Enrica Neri Lusanna' in attribution:
		criteria.append(('bibliography', 'Enrica Neri Lusanna'))
	if 'Fausta Gualdi Sabatini' in attribution:
		criteria.append(('bibliography', 'Fausta Gualdi Sabatini'))
	if 'Christian Von Holst' in attribution:
		criteria.append(('bibliography', 'Christian Von Holst'))
	if 'Raphael, Cellini & a Renaissance banker' in attribution:
		criteria.append(('bibliography', ''))
	if "L'umana bellezza tra Piero della Francesca e Raffaello" in attribution:
		criteria.append(('bibliography', ''))
	if "Pittura fiorentina alla vigilia del Rinascimento" in attribution:
		criteria.append(('bibliography', 'Boskovits M.'))
	if "G. Sarti" in attribution:
		criteria.append(('bibliography', 'G. Sarti'))
	if "Linda Pisani" in attribution:
		criteria.append(('bibliography', 'Linda Pisani'))
	if "Schulze Altcappenberg" in attribution:
		criteria.append(('bibliography', 'Schulze Altcappenberg'))
	if "Louis A. Waldman" in attribution:
		criteria.append(('bibliography', 'Louis A. Waldman'))
	if "Benozzo Gozzoli. Allievo a Roma, maestro in Umbra" in attribution:
		criteria.append(('bibliography', ''))
	if "Piero Torriti" in attribution:
		criteria.append(('bibliography', 'Piero Torriti'))
	if "Stefano G. Casu" in attribution:
		criteria.append(('bibliography', 'Stefano G. Casu'))
	if "Alessandra Tamborino" in attribution:
		criteria.append(('bibliography', 'Alessandra Tamborino'))
	if "Paola Caccialupi" in attribution:
		criteria.append(('bibliography', 'Paola Caccialupi'))
	if "David Alan Brown" in attribution:
		criteria.append(('bibliography', 'David Alan Brown'))
	if "Moretti, Da" in attribution:
		criteria.append(('bibliography', 'Moretti'))
	if "Laurence Kanter and John Marciari" in attribution:
		criteria.append(('bibliography', 'Laurence Kanter'))
		criteria.append(('bibliography', 'John Marciari'))
	if "Laurence B. Kanter" in attribution:
		criteria.append(('bibliography', 'Laurence Kanter'))
	if "Emmanuele Mattaliano" in attribution:
		criteria.append(('bibliography', 'Emmanuele Mattaliano'))
	if "Megan Holmes" in attribution:
		criteria.append(('bibliography', 'Megan Holmes'))
	if "Robert G. La France" in attribution:
		criteria.append(('bibliography', 'Robert G. La France'))
	if "Laura Pagnotta" in attribution:
		criteria.append(('bibliography', 'Laura Pagnotta'))
	if "Enzo Carli" in attribution:
		criteria.append(('bibliography', 'Enzo Carli'))
	if "Paola Rossi" in attribution:
		criteria.append(('bibliography', 'Paola Rossi'))
	if "Miguel Falomir" in attribution:
		criteria.append(('bibliography', 'Miguel Falomir'))
	if "Carl B. Strehlke" in attribution:
		criteria.append(('bibliography', 'Carl B. Strehlke'))
	if "Peter Humfrey" in attribution:
		criteria.append(('bibliography', 'Peter Humfrey'))
	if "G. Fossaluzza" in attribution:
		criteria.append(('bibliography', 'G. Fossaluzza'))
	if "Philip Rylands" in attribution:
		criteria.append(('bibliography', 'Philip Rylands'))
	if "Vincenzo Mancini" in attribution:
		criteria.append(('bibliography', 'Vincenzo Mancini'))
	if "Rodolfo Pallucchini" in attribution:
		criteria.append(('bibliography', 'Rodolfo Pallucchini'))
	if "Claire-Lise Schwok" in attribution:
		criteria.append(('bibliography', 'Claire-Lise Schwok'))
	if "Luisa Mortari" in attribution:
		criteria.append(('bibliography', 'Luisa Mortari'))
	if "Fern Rusk Shapley" in attribution:
		criteria.append(('bibliography', 'Fern Rusk Shapley'))
	if "Harold E. Wethey" in attribution:
		criteria.append(('bibliography', 'Harold E. Wethey'))
	if "Anna Cavallaro" in attribution:
		criteria.append(('bibliography', 'Anna Cavallaro'))
	if "Silvia Topi" in attribution:
		criteria.append(('bibliography', 'Silvia Topi'))
	if "Filippo Rossi" in attribution:
		criteria.append(('bibliography', 'Filippo Rossi'))
	if "Karla Langedijk" in attribution:
		criteria.append(('bibliography', 'Karla Langedijk'))
	if "Elena Merciai" in attribution:
		criteria.append(('bibliography', 'Elena Merciai'))
	if "Giovanni Sarti" in attribution:
		criteria.append(('bibliography', 'Giovanni Sarti'))
	if "Serena Skerl Del Conte" in attribution:
		criteria.append(('bibliography', 'Serena Skerl Del Conte'))
	if "Anna Maria Fioravanti Baraldi" in attribution:
		criteria.append(('bibliography', 'Anna Maria Fioravanti Baraldi'))
	if "Eliot W. Rowland" in attribution:
		criteria.append(('bibliography', 'Eliot W. Rowland'))
	if "Luciano Bellosi" in attribution:
		criteria.append(('bibliography', 'Luciano Bellosi'))
	if 'Lo stato degli studi, i problemi, le risposte della filologia' in attribution:
		criteria.append(('bibliography', ''))
	if 'Sumptuosa tabula picta' in attribution:
		criteria.append(('bibliography', ''))
	if 'Giles Robertson' in attribution:
		criteria.append(('bibliography', 'Giles Robertson'))


	# collection attribution
	if "Alana Collection" in attribution:
		criteria.append(('collection-attribution', 'The Alana Collection'))
	if "Rowlands" in attribution:
		criteria.append(('collection-attribution', 'Rowlands Collection'))
	
	# archive creator bibliography
	if 'Bernard and Mary Berenson Collection of ' in attribution:
		criteria.append(('archival-creator-bibliography', 'Bernard Berenson'))
		criteria.append(('archival-creator-bibliography', 'Mary Berenson'))
	if 'Bernard Berenson Collection of ' in attribution or 'Un artista fuori del suo tempo' in attribution \
	or 'Italian Pictures of the Renaissance' in attribution or "Disegni dei Pittori Fiorentini" in attribution \
	or "Bernard Berenson, Lorenzo Lotto" in attribution:
		criteria.append(('archival-creator-bibliography', 'Bernard Berenson'))

	# if ('filed' not in attribution) and ('Filed' not in attribution) and ('listed' not in attribution) \
	# and ('label attached to the work' not in attribution) and ('monogram' not in attribution) \
	# and ('Artist\'s signature' not in attribution) and ('Signed work' not in attribution) \
	# and ('Work inscribed with artist\'s name' not in attribution) and ('Signed and dated work' not in attribution) \
	# and ('Listed' not in attribution) and ('handwritten' not in attribution) and ('Handwritten' not in attribution) \
	# and ('auction' not in attribution) and ('Inventory' not in attribution) and ('comunication' not in attribution) \
	# and ('verbal' not in attribution) and ('website' not in attribution) and ('online' not in attribution) \
	# and ('email' not in attribution) and ('atabase' not in attribution) \
	# and ('comunication by' not in attribution) and ('communication by' not in attribution) \
	# and ('attribution by' not in attribution) and ('authenticated by' not in attribution) \
	# and ('Fondazione Federico Zeri' not in attribution):
	# 	criteria.append(('bibliography', '')) 

	# TODO work on the bibliography criterion and on authors of the biblio
	return criteria	


def get_other_criteria_and_artist(attribution):
	""" given a string representing an attribution, return a list of suitable criteria 
	and cited entities (that agree with the attribution) for reconciliation"""
	criteria = [] # includes tuples in the form: (criterion, artist, cited entity)
	attribution = str(attribution.strip())
	re.sub("^b\'","", attribution)
	
	# documentation
	documentation1 = re.compile('xpertized by (.*) as (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation2 = re.compile('xpertise by (.*)attributing (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation3 = re.compile('xpertise (?:signed\s)?by (.*), dated (.*), attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation4 = re.compile('xpertises by (.*) and (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation5 = re.compile('xpertized for (.*) by (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation6 = re.compile('andwritten expertise attributing the work to (.*) signed by (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation7 = re.compile('andwritten expertise (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation8 = re.compile('ypewritten expertise (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation78 = re.compile('expertise (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation9 = re.compile('andwritten expertise by (.*[^and]) dated (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation10 = re.compile('andwritten expertise signed by (.*) and dated (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation11 = re.compile('eference to expertises by (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation12 = re.compile('xpertise by (.*) attributing the work to (.*).', re.IGNORECASE|re.DOTALL).search(attribution)
	documentation13 = re.compile('andwritten expertise signed by (.*)attributing the work to (.*), dated (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if documentation1: # Expertized by Hans Gronau as Pier Francesco Fiorentino (see surrogate 103894_2)'
		criteria.append(('documentation', strip_punct(documentation1.group(2)), strip_punct(documentation1.group(1)) ))	
	if documentation2:
		if documentation3: # Expertise by A. Venturi, dated 1 June 1914, attributing the work to Correggio (see surrogate 124967_2).
			criteria.append(('documentation', strip_punct(documentation3.group(3)), strip_punct(documentation3.group(1)) ))
		else: # Expertise by P. & D. Colnaghi & Co. attributing the work to the Master of the San Martino a Mensola Annunciation
			criteria.append(('documentation', strip_punct(documentation2.group(2)), strip_punct(documentation2.group(1)) ))
	if documentation4: # Expertises by Raimond Van Marle and Walter Friedl\xc3\xa4nder attributing the work to Piero di Cosimo (see surrogate 103451_1)
		criteria.append(('documentation', strip_punct(documentation4.group(3)), strip_punct(documentation4.group(1)) ))
		criteria.append(('documentation', strip_punct(documentation4.group(3)), strip_punct(documentation4.group(2)) ))	
	if documentation5: # Expertized for Sotheby's by Lionello Venturi as Benvenuto di Giovanni.
		criteria.append(('documentation', strip_punct(documentation5.group(3)), strip_punct(documentation5.group(2)) ))
		criteria.append(('auction-attribution', strip_punct(documentation5.group(3)), strip_punct(documentation5.group(1)) ))
	if documentation7 or documentation8:
		if documentation6: # Handwritten expertise attributing the work to Jacopo Tintoretto signed by August L. Mayer (see surrogate 110646_2).
			criteria.append(('documentation', strip_punct(documentation6.group(1)), strip_punct(documentation6.group(2)) ))
		if documentation9: # Handwritten expertise by Hermann Voss dated 1955 attributing the work to Titian (see
			criteria.append(('documentation', strip_punct(documentation9.group(3)), strip_punct(documentation9.group(1)) ))			
		elif documentation10: # Handwritten expertise signed by Giuseppe Fiocco and dated 2 August 1944, attributing the work to Lorentino d'Arezzo (see surrogate 120218_2).
			criteria.append(('documentation', strip_punct(documentation10.group(3)), strip_punct(documentation10.group(1)) ))
		else: # Handwritten expertise by Mikl\xc3\xb3s Boskovits attributing the work to Niccol\xc3\xb2 di Pietro Gerini 
			# criteria.append(('documentation', strip_punct(documentation78.group(2)), strip_punct(documentation78.group(1)) ))	
			pass
	if documentation11: # Reference to expertises by Detlev von Hadeln, O. Fischel, Hermann Voss, Antonio Morassi, and Valentiner attributing the work to Titian (see surrogate 109008_2)'
		for scholar in documentation11.group(1).split(','):
			criteria.append(('documentation', strip_punct(documentation11.group(2)), strip_punct(scholar) ))	
	if documentation12: # Expertized for Sotheby's by Lionello Venturi as Benvenuto di Giovanni.
		criteria.append(('documentation', strip_punct(documentation12.group(2)), strip_punct(documentation12.group(1)) ))
	if documentation13: # Expertized for Sotheby's by Lionello Venturi as Benvenuto di Giovanni.
		criteria.append(('documentation', strip_punct(documentation13.group(2)), strip_punct(documentation13.group(1)) ))
	

	# archival classification
	archivalclassification1 = re.compile('filed with (.*) at Biblioteca', re.IGNORECASE|re.DOTALL).search(attribution)
	archivalclassification2 = re.compile('filed with (.*) as', re.IGNORECASE|re.DOTALL).search(attribution)
	if archivalclassification1: # filed with Vittore Carpaccio at Biblioteca Berenson, Fototeca.
	 	criteria.append(('archival-classification', strip_punct(archivalclassification1.group(1)) , ''))
	if archivalclassification2: # filed with Vittore Carpaccio at Biblioteca Berenson, Fototeca.
	 	criteria.append(('archival-classification', strip_punct(archivalclassification2.group(1)) , ''))

	# archival-creator-attribution
	archivalcreatorattribution1 = re.compile('insured as (.*) by the Berensons', re.IGNORECASE|re.DOTALL).search(attribution)
	if archivalcreatorattribution1: # filed with Vittore Carpaccio at Biblioteca Berenson, Fototeca.
	 	criteria.append(('archival-creator-attribution', strip_punct(archivalcreatorattribution1.group(1)) , 'Bernard Berenson'))
	 	criteria.append(('archival-creator-attribution', strip_punct(archivalcreatorattribution1.group(1)) , 'Mary Berenson'))

	# archival-creator-bibliography
	archivalcreatorbibliography0 = re.compile('isted by (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	archivalcreatorbibliography1 = re.compile('isted by (.*) as (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivalcreatorbibliography2 = re.compile('ublished by (.*) as (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivalcreatorbibliography3 = re.compile('ublished as (.*) in (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	archivalcreatorbibliography4 = re.compile('isted as (.*) by (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	if archivalcreatorbibliography0:
		if archivalcreatorbibliography1: # Listed by Bernard Berenson as an early work by Bachiacca (I
			criteria.append(('archival-creator-bibliography', strip_punct(archivalcreatorbibliography1.group(2)), strip_punct(archivalcreatorbibliography1.group(1)) ))
		else:
			criteria.append(('archival-creator-bibliography', strip_punct(archivalcreatorbibliography0.group(2)), strip_punct(archivalcreatorbibliography0.group(1)) ))

	if 'Italian Pictures of the Renaissance' in attribution:
		criteria.append(('archival-creator-bibliography', '', 'Bernard Berenson'))
	if archivalcreatorbibliography2: # published by Bernard Berenson as Follower of Giovanni del Biondo (Homeless Paintings of the Renaissance, ed. H. Kiel, 1969).
		criteria.append(('archival-creator-bibliography', strip_punct(archivalcreatorbibliography2.group(2)), strip_punct(archivalcreatorbibliography2.group(1)) ))
	if archivalcreatorbibliography3: # published as Giovanni del Bindino ? in Bernard Berenson, "Quadri senza casa. Il Trecento senese. II," Dedalo XI, 6 (1930): 328-362
		criteria.append(('archival-creator-bibliography', strip_punct(archivalcreatorbibliography3.group(1)), strip_punct(archivalcreatorbibliography3.group(2)) ))
	if archivalcreatorbibliography4: # Listed by Bernard Berenson as an early work by Bachiacca (I
		criteria.append(('archival-creator-bibliography', strip_punct(archivalcreatorbibliography4.group(1)), strip_punct(archivalcreatorbibliography4.group(2)) ))
	
	# auction attribution
	auctionattribution1 = re.compile('^\s?as (.*) at (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution2 = re.compile('^\s?as (.*) at (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution3 = re.compile('(.*) \(at Wildenstein\)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution4 = re.compile('as attributed to (.*) at (.*)\'s \(', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution5 = re.compile('(.*) by Finarte', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution6 = re.compile('^\s?in (.*) at (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution7 = re.compile("^\s?San Marco Casa d\'aste(.*) as (.*)", re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution8 = re.compile('(.*) auction catalog(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution9 = re.compile('(.*) \((.*) auction catalog', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution91 = re.compile('(.*) in (.*) auction catalog', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution10 = re.compile('^sold as (.*) at (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	#auctionattribution11 = re.compile('^Sold at (.*) as (.*) and', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution12 = re.compile('^\s?sold at (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution13 = re.compile('^\s?sold at (.*) as (.*) and', re.IGNORECASE|re.DOTALL).search(attribution) #sameas 11
	auctionattribution14 = re.compile('^\s?sold at (.*) as attributed to (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution15 = re.compile('^\s?at (.*) sold as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution16 = re.compile('at (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution17 = re.compile('ascribed to (.*) at (.*) auction', re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution18 = re.compile("typewritten note by Wildenstein reporting Bernard Berenson's attribution to (.*) and (.*)", re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution19 = re.compile("(.*) according to Wildenstein (.*)", re.IGNORECASE|re.DOTALL).search(attribution)
	auctionattribution20 = re.compile("Harewood catalog as (.*)", re.IGNORECASE|re.DOTALL).search(attribution)
	
	if auctionattribution1: # as School of Perugino at Wildenstein (see surrogate 127475_2)
		if auctionattribution2:
			criteria.append(('auction-attribution', strip_punct(auctionattribution2.group(1)), strip_punct(auctionattribution2.group(2)) ))
		else:
			criteria.append(('auction-attribution', strip_punct(auctionattribution1.group(1)), strip_punct(auctionattribution1.group(2)) ))
	## exception
	if auctionattribution3: # Agnolo Gaddi (at Wildenstein) 
		criteria.append(('auction-attribution', strip_punct(auctionattribution3.group(1)), 'Wildenstein'))
	if auctionattribution4:	# as attributed to Perugino at Wildenstein's (see related Surrogates 120832_2 and 120833_2).
		criteria.append(('auction-attribution', strip_punct(auctionattribution4.group(1)), strip_punct(auctionattribution4.group(2)) ))
	if auctionattribution5:	# circle of Michelangelo by Finarte
		criteria.append(('auction-attribution', strip_punct(auctionattribution5.group(1)), 'Finarte'))
	if auctionattribution6: # in 1989 at Christie's as the Master of Marradi.
		criteria.append(('auction-attribution', strip_punct(auctionattribution6.group(2)), strip_punct(auctionattribution6.group(3))))
	if auctionattribution7: # San Marco Casa d'aste, 6 July 2008, as Simone dei Crocifissi.
		criteria.append(('auction-attribution', strip_punct(auctionattribution7.group(2)), "San Marco Casa d'aste" ))
	if auctionattribution8: # Christie\'s auction catalog, 13 December 1946, as Giovanni Bellini
		criteria.append(('auction-attribution', strip_punct(auctionattribution8.group(3)), strip_punct(auctionattribution8.group(1)) ))
	if auctionattribution9: # Perino del Vaga? (Christie's auction catalog, 20-21 November 1958).
		criteria.append(('auction-attribution', strip_punct(auctionattribution9.group(1)), strip_punct(auctionattribution9.group(2)) ))
	if auctionattribution91: # Perino del Vaga? (Christie's auction catalog, 20-21 November 1958).
		criteria.append(('auction-attribution', strip_punct(auctionattribution91.group(1)), strip_punct(auctionattribution91.group(2)) ))
	if auctionattribution10: # sold as Giovanni Antonio Sogliani at Christie's, New York, 30 January 2013, lot 125.
		criteria.append(('auction-attribution', strip_punct(auctionattribution10.group(1)), strip_punct(auctionattribution10.group(2))))	
	if auctionattribution12: 
		if auctionattribution13: # sold at Christie's as Perugino and as Giovan Battista Caporali.
			criteria.append(('auction-attribution', strip_punct(auctionattribution13.group(2)), strip_punct(auctionattribution13.group(1))))
		elif auctionattribution14: # sold at Galerie Fischer as attributed to Benozzo Gozzoli. 
			criteria.append(('auction-attribution', strip_punct(auctionattribution14.group(2)), strip_punct(auctionattribution14.group(1))))
		else: # sold at Christie's as Morazzone.
			criteria.append(('auction-attribution', strip_punct(auctionattribution12.group(2)), strip_punct(auctionattribution12.group(1))))
	if auctionattribution15: # at Kleinberger sold as Carlo Crivelli
		criteria.append(('auction-attribution', strip_punct(auctionattribution15.group(2)), strip_punct(auctionattribution15.group(1)) ))
	if auctionattribution16: # in 2000 at Christie's as the Master of the Fiesole Epiphany.
		criteria.append(('auction-attribution', strip_punct(auctionattribution16.group(2)), strip_punct(auctionattribution16.group(1))))
	if auctionattribution17: # in 2000 at Christie's as the Master of the Fiesole Epiphany.
		criteria.append(('auction-attribution', strip_punct(auctionattribution17.group(1)), strip_punct(auctionattribution17.group(2))))
	if auctionattribution18: # in 2000 at Christie's as the Master of the Fiesole Epiphany.
		criteria.append(('auction-attribution', strip_punct(auctionattribution18.group(1)), 'Wildenstein' ))
		criteria.append(('archival-creator-attribution', strip_punct(auctionattribution18.group(1)), 'Bernard Berenson' ))
	if auctionattribution19: # in 2000 at Christie's as the Master of the Fiesole Epiphany.
		criteria.append(('auction-attribution', strip_punct(auctionattribution19.group(1)), 'Wildenstein' ))	
	if auctionattribution20: # in 2000 at Christie's as the Master of the Fiesole Epiphany.
		criteria.append(('auction-attribution', strip_punct(auctionattribution20.group(1)), 'Harewood' ))	
	
	if "at Wildenstein's Lorenzo di" in attribution:
		criteria.append(('auction-attribution', 'Lorenzo di Niccolò', 'Wildenstein' ))
	
	# museum attribution
	museumattribution1 = re.compile('exhibited as (.*) at (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution11 = re.compile('exhibited as (.*) at (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution2 = re.compile('attributed to (.*) at (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution3 = re.compile('attributed at museum to(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution4 = re.compile('previously as (.*) at (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution5 = re.compile('catalogo della mostra(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution6 = re.compile('Metropolitan Museum of Art(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution7 = re.compile('Art Gallery, Manchester(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution8 = re.compile('exhibited in (.*) as (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	museumattribution9 = re.compile('attributed to (.*) on the Mt Holyoke College Museum of Art', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if museumattribution1: # exhibited as Alonso Berruguete at Palazzo Grassi, Venice, 1962.'
		criteria.append(('museum-attribution', strip_punct(museumattribution1.group(1)), strip_punct(museumattribution1.group(2))))
	if museumattribution11: # exhibited as Alonso Berruguete at Palazzo Grassi, Venice, 1962.'
		criteria.append(('museum-attribution', strip_punct(museumattribution11.group(1)), strip_punct(museumattribution11.group(2))))
	if museumattribution2: # attributed to Taddeo di Bartolo at W.R. Nelson Gallery of Art
		criteria.append(('museum-attribution', strip_punct(museumattribution2.group(1)), strip_punct(museumattribution2.group(2))))
	if museumattribution3:
		criteria.append(('museum-attribution', strip_punct(museumattribution3.group(1)), ''))
	if museumattribution4:
		criteria.append(('museum-attribution', strip_punct(museumattribution4.group(1)), strip_punct(museumattribution4.group(2)) ))
	if museumattribution5:
		criteria.append(('museum-attribution', strip_punct(museumattribution5.group(2)), strip_punct(museumattribution5.group(1)) ))
	if museumattribution6:
		criteria.append(('museum-attribution', strip_punct(museumattribution6.group(2)), 'Metropolitan Museum of Art' ))
	if museumattribution7:
		criteria.append(('museum-attribution', strip_punct(museumattribution7.group(2)), 'Art Gallery, Manchester' ))
	if museumattribution8:
		criteria.append(('museum-attribution', strip_punct(museumattribution8.group(2)), '' ))
	if museumattribution9:
		criteria.append(('museum-attribution', strip_punct(museumattribution9.group(1)), 'Mt Holyoke College Museum of Art' ))

	# collection attribution
	collectionattribution1 = re.compile('published as work of (.*) in (.*)\,', re.IGNORECASE|re.DOTALL).search(attribution)
	collectionattribution2 = re.compile('as (.*) in (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	collectionattribution3 = re.compile('as (.*) in (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	collectionattribution4 = re.compile('(.*) catalog (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	collectionattribution5 = re.compile('attributed to (.*) in (.*) collection', re.IGNORECASE|re.DOTALL).search(attribution)
	if collectionattribution1: # published as work of an unknown Florentine painter in The J. Paul Getty Collection, exh. cat.,. 
		criteria.append(('collection-attribution', strip_punct(collectionattribution1.group(1)), strip_punct(collectionattribution1.group(2)) ))
	if collectionattribution2 and 'ollection' in attribution and 'Berenson' not in attribution: 
		if re.match('as (.*) in (.*)\(', attribution) is not None: # as Palma il Vecchio in the Moroni Collection, Bergamo (see related Surrogate 122866_1)
			criteria.append(('collection-attribution', strip_punct(collectionattribution2.group(1)), strip_punct(collectionattribution2.group(2)) ))
		else:
			criteria.append(('collection-attribution', strip_punct(collectionattribution2.group(1)), strip_punct(collectionattribution2.group(2)) ))
	if collectionattribution4 and 'ollection' in attribution: # Wantage collection catalog (1886, n. 173) as Jacopo Palma il vecchio.
		criteria.append(('collection-attribution', strip_punct(collectionattribution4.group(3)), strip_punct(collectionattribution4.group(1))))
	if collectionattribution5 and 'ollection' in attribution: # Wantage collection catalog (1886, n. 173) as Jacopo Palma il vecchio.
		criteria.append(('collection-attribution', strip_punct(collectionattribution5.group(1)), strip_punct(collectionattribution5.group(2))))
	
	# inscription
	inscription1 = re.compile('nscription (.*) reads (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription2 = re.compile("inscribed with (.*)\'s name", re.IGNORECASE|re.DOTALL).search(attribution)
	inscription3 = re.compile('inscribed: (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription4 = re.compile('Work inscribed (.*).', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription5 = re.compile('as (.*) on label formerly attached to painting', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription6 = re.compile('inscription on the back of the panel attributing the work to (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription7 = re.compile('typewritten inscription reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	inscription8 = re.compile('old inscription on back: (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if inscription1: # inscription on the work reads "P[aolo] Veronese.
		criteria.append(('inscription', strip_punct(inscription1.group(2)), ''))
	if inscription2: # Work inscribed with Pollaiuolo\'s name.
		criteria.append(('inscription', strip_punct(inscription2.group(1)), ''))
	if inscription3: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription3.group(1)), ''))
	if inscription4: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription4.group(1)), ''))
	if inscription5: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription5.group(1)), ''))
	if inscription6: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription6.group(1)), ''))
	if inscription7: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription7.group(1)), ''))
	if inscription8: # Work inscribed: "Titian".  Work inscribed: Andrea del Sarto.
		criteria.append(('inscription', strip_punct(inscription8.group(1)), ''))
	# caption on photo
	if 'caption' in attribution: 
		caption1 = re.compile('caption as (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		caption2 = re.compile('caption attributing the work to (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
		caption3 = re.compile('(.*) \( see printed', re.IGNORECASE|re.DOTALL).search(attribution)
		if caption1: # on printed caption as Perugian School (see related Surrogate 120266_1).'
			criteria.append(('caption-on-photo', strip_punct(caption1.group(1)), ''))
		if caption2: # printed caption attributing the work to Pollaiolo (see Surrogate 124104_1).
			criteria.append(('caption-on-photo', strip_punct(caption2.group(1)), ''))
		if caption3: # Milanese school according to label (see related Surrogates 123217_2 and 123216_2).
			criteria.append(('caption-on-photo', strip_punct(caption3.group(1)), ''))
	caption4 = re.compile('(.*) according to label', re.IGNORECASE|re.DOTALL).search(attribution)
	caption5 = re.compile('attributed to (.*) on printed caption', re.IGNORECASE|re.DOTALL).search(attribution)
	caption6 = re.compile('typewritten label reads (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	caption7 = re.compile('printed caption attributing the work to (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	caption8 = re.compile('typewritten label attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	if caption4: # Milanese school according to label (see related Surrogates 123217_2 and 123216_2).
		criteria.append(('caption-on-photo', strip_punct(caption4.group(1)), ''))
	if caption5: # attributed to Duccio on printed caption
		criteria.append(('caption-on-photo', strip_punct(caption5.group(1)), ''))
	if caption6: # attributed to Duccio on printed caption
		criteria.append(('caption-on-photo', strip_punct(caption6.group(1)), ''))
	if caption7: # attributed to Duccio on printed caption
		criteria.append(('caption-on-photo', strip_punct(caption7.group(1)), ''))
	if caption8: # attributed to Duccio on printed caption
		criteria.append(('caption-on-photo', strip_punct(caption8.group(1)), ''))

	# bibliography
	## exceptions
	bibliography1 = re.compile('Boskovits identifies (.*) \(see (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography2 = re.compile('The Berenson Collection(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography3 = re.compile('The Berenson Collection(.*) as (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography4 = re.compile('Harold E. Wethey(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography5 = re.compile('Fabrizio Lollini, "Tura(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography6 = re.compile('Lionello Puppi,(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography7 = re.compile('Attributed to (.*) in (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography8 = re.compile('New York:(.*)University Press(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography9 = re.compile('Romanino: Un pittore in rivolta(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography10 = re.compile('(.*) in Filippo Todini, La pittura umbra (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography11 = re.compile('Emilio Negro and Nicosetta Roio, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography12 = re.compile('Marco Carminati, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography13 = re.compile('Fabio Bisogni, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography14 = re.compile('Alessandro Conti, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography15 = re.compile('Maria Teresa Fiorio, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography16 = re.compile('David Alan Brown, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography17 = re.compile('Fritz Heinemann, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography18 = re.compile('Caterina Furlan, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography19 = re.compile('Athens: Hellenic (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography20 = re.compile('(.*), Paul Schubring(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography21 = re.compile('as (.*) in Bernard Berenson, Homeless(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography22 = re.compile('Giovanni Antonio Boltraffio (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography23 = re.compile('(.*) in Giles Robertson(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography24 = re.compile('as (.*) in Alessandro Ballarin(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography25 = re.compile('as (.*) in Joanna Winiewicz(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography26 = re.compile('Luigi Servolini(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography27 = re.compile('Giorgione e i giorgioneschi(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography28 = re.compile('Marzia Faietti and Daniela Scaglietti Kelescian(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography29 = re.compile('Filippo Todini,(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography30 = re.compile('A. Ugolini, (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography31 = re.compile('Domenico Sedini,(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography32 = re.compile('published \s?as (.*) by (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography33 = re.compile('Domenico Sedini(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography34 = re.compile('Pier Virgilio Begni Redona(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography35 = re.compile('Rodolfo Pallucchini and Paola Rossi(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography36 = re.compile('Francesco Verla pittore(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography37 = re.compile('George Martin Richter(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography38 = re.compile('Monica Molteni(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography39 = re.compile('published as (.*) in (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography40 = re.compile('as (.*) in: Joanna Winiewicz-Wolska', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography41 = re.compile('attributed to (.*) in: Maestri e botteghe', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography42 = re.compile('Giles Robertson(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography43 = re.compile('Richard Cocke(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography44 = re.compile('Alessandro Ballarin(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography45 = re.compile('L\'opera completa di Sebastiano(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography46 = re.compile('Federico Zeri(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography47 = re.compile('Paola Caccialupi(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography48 = re.compile('Luisa Mortari(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	bibliography49 = re.compile('Daniele Benati(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	

	if "as Francesco d'Antonio in Bernard Berenson, Homeless Paintings of the Renaissance" in attribution: # as Francesco d'Antonio in Bernard Berenson, Homeless Paintings of the Renaissance, ed. H. Kiel
		auth = re.match('(.*) \( see printed', attribution)
		criteria.append(('bibliography', "Francesco d'Antonio", 'Bernard Berenson'))
	if bibliography1: # Mikl\xc3\xb3s Boskovits identifies the Saint Cecilia Master with Gaddo Gaddi (see Mikl\xc3\xb3s Boskovits, "Un nome per il maestro del Trittico Horne," Saggi e memorie di storia dell\'arte 27 (2003): 57-70).
		criteria.append(('bibliography', strip_punct(bibliography1.group(1)), strip_punct(bibliography1.group(2)) ))
	if bibliography2:
		if bibliography3: # Franco Russoli, The Berenson Collection, preface by Nicky Mariano (Milan: Arti Grafiche Ricordi, 1964), VIII, as Nardo di Cione;
			criteria.append(('bibliography', strip_punct(bibliography3.group(2)), 'Franco Russoli' ))
		else:
			criteria.append(('bibliography', strip_punct(bibliography2.group(2)), 'Franco Russoli' ))
	
	if "Sir John Wyndham Pope" in attribution:
		criteria.append(('bibliography', 'Bernardo Ciuffagni', 'Sir John Wyndham Pope-Hennessy' ))
	if 'Villa I Tatti Inventory' in attribution:
		criteria.append(('bibliography', '', 'Bernard Berenson' ))
	if bibliography4: # Harold E. Wethey, The Paintings of Titian, vol. 2, The Portraits ([London]: Phaidon, 1969-1975), as Giovanni Cariani. ' [] 
		criteria.append(('bibliography', strip_punct(bibliography4.group(2)), 'Harold E. Wethey' ))
	if bibliography5: # Harold E. Wethey, The Paintings of Titian, vol. 2, The Portraits ([London]: Phaidon, 1969-1975), as Giovanni Cariani. ' [] 
		criteria.append(('bibliography', strip_punct(bibliography5.group(2)), 'Fabrizio Lollini' ))
	if bibliography6: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography6.group(2)), 'Lionello Puppi' ))
	if bibliography7: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography7.group(1)), strip_punct(bibliography7.group(2)) ))
	if bibliography8: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography8.group(3)), '' ))
	if bibliography9: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography9.group(2)), '' ))
	if bibliography10: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography10.group(1)), 'Filippo Todini' ))
	if bibliography11: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography11.group(2)), 'Emilio Negro' ))
		criteria.append(('bibliography', strip_punct(bibliography11.group(2)), 'Nicosetta Roio' ))
	if bibliography12: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography12.group(2)), 'Marco Carminati' ))
	if bibliography13: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography13.group(2)), 'Fabio Bisogni' ))
	if bibliography14: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography14.group(2)), 'Alessandro Conti' ))
	if bibliography15: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography15.group(2)), 'Maria Teresa Fiorio' ))
	if bibliography16: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography16.group(2)), 'David Alan Brown' ))
	if bibliography17: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography17.group(2)), 'Fritz Heinemann' ))
	if bibliography18: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography18.group(2)), 'Caterina Furlan' ))
	if bibliography19: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography19.group(2)), '' ))
	if bibliography20: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography20.group(1)), 'Paul Schubring' ))
	if bibliography21: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography21.group(1)), 'Bernard Berenson' ))
	if bibliography22: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography22.group(1)), 'Giovanni Antonio Boltraffio' ))
	if bibliography23: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography23.group(1)), 'Giles Robertson' ))
	if bibliography24: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography24.group(1)), 'Alessandro Ballarin' ))
	if bibliography25: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography25.group(1)), 'Joanna Winiewicz-Wolska' ))
	if bibliography26: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography26.group(2)), 'Luigi Servolini' ))
	if bibliography27: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography27.group(2)), '' ))
	if bibliography28: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography28.group(2)), 'Marzia Faietti' ))
		criteria.append(('bibliography', strip_punct(bibliography28.group(2)), 'Daniela Scaglietti Kelescian' ))
	if bibliography29: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography29.group(2)), 'Filippo Todini' ))
	if bibliography30: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography30.group(2)), 'A. Ugolini' ))
	if bibliography31: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography31.group(2)), 'Domenico Sedini' ))
	if bibliography32: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography32.group(1)), strip_punct(bibliography32.group(2)) ))
	if bibliography33: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography33.group(1)), 'Domenico Sedini' ))
	if bibliography34: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography34.group(2)), 'Pier Virgilio Begni Redona' ))
	if bibliography35: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography35.group(2)), 'Rodolfo Pallucchini' ))
		criteria.append(('bibliography', strip_punct(bibliography35.group(2)), 'Paola Rossi' ))
	if bibliography36: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography36.group(2)), '' ))
	if bibliography37: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography37.group(2)), 'George Martin Richter' ))
	if bibliography38: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography38.group(2)), 'Monica Molteni' ))
	if bibliography39: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography39.group(2)), '' ))
	if bibliography40: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography40.group(1)), 'Joanna Winiewicz-Wolska' ))
	if bibliography41: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography41.group(1)), '' ))
	if bibliography42: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography42.group(2)), 'Giles Robertson' ))
	if bibliography43: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography43.group(2)), 'Richard Cocke' ))	
	if bibliography44: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography44.group(2)), 'Alessandro Ballarin' ))	
	if bibliography45: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography45.group(2)), '' ))	
	if bibliography46: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography46.group(2)), 'Federico Zeri' ))	
	if bibliography47: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography47.group(2)), 'Paola Caccialupi' ))	
	if bibliography48: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography48.group(2)), 'Luisa Mortari' ))	
	if bibliography49: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('bibliography', strip_punct(bibliography49.group(2)), 'Daniele Benati' ))	
	
	# market attribution
	market1 = re.compile('mostra-mercato (.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	if market1: # Lionello Puppi, "Giovanni Buonconsiglio detto Marescalco," Rivista dell\'Istituto Naziona
		criteria.append(('market-attribution', strip_punct(market1.group(2)), '' ))
	

	# scholar attribution or archival-creator-attribution
	scholarattribution1 = re.compile('^\s?as (.*) by (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution2 = re.compile('communication by (.*) to (.*): (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution3 = re.compile('(.*)\(com?munication by (.*) to', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution4 = re.compile('(.*) or (.*)\(communication by (.*) to', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution5 = re.compile('described by (.*) as (.*) and', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution51 = re.compile('described by (.*) in (.*) as (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution6 = re.compile('attributed by (.*) to (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution7 = re.compile('attributed to (.*) by (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution8 = re.compile('attributed to (.*) by (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution9 = re.compile('attributed to (.*) by (.*).', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution10 = re.compile('attributed to (.*) by (.*) \(see', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution11 = re.compile('attributed by (.*) in (.*) to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution12 = re.compile('authenticated by (.*) as (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution13 = re.compile('Fondazione Federico Zeri(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution14 = re.compile('typewritten letter sent by (.*) to (.*)attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution15 = re.compile('NIKI, Dutch University Institute(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution16 = re.compile('handwritten note reporting (.*)\'s attribution to(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution17 = re.compile('handwritten note reporting (.*)\'s and (.*)\'s attribution to(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution18 = re.compile('reference to an attestation by (.*),(.*)attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution19 = re.compile('handwritten note reporting (.*)\'s attribution of the work to (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution20 = re.compile('Associated with (.*) by (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution21 = re.compile('letter from (.*) to (.*)attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution22 = re.compile('^\s?Voss:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution23 = re.compile('^\s?Morassi and Zampetti:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution24 = re.compile('^\s?Longhi:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarattribution25 = re.compile('^\s?Everett Fahy:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if 'Bernard Berenson' in attribution:
		criterion = "archival-creator-attribution"
	else:
		criterion = "scholar-attribution"

	if scholarattribution1:	# as Lombard artist imitating a Flemish prototype by Roberto Longhi (see related Surrogate 124061_2)
		criteria.append((criterion, strip_punct(scholarattribution1.group(1)), strip_punct(scholarattribution1.group(2))))
	if scholarattribution2:	# communication by D\xc3\xb2ra Sallay to Biblioteca Berenson, Fototeca, 2011: "fake".'
		criteria.append((criterion, strip_punct(scholarattribution2.group(3)), strip_punct(scholarattribution2.group(1))))
	if scholarattribution3:	# Marco Marziale (communication by Francesco Smeraldi to Biblioteca Berenson, Fototeca).
		# if 'late work by' in attribution: # late work by Guidoccio Cozzarelli (communication by D\xc3\xb2ra Sallay to Biblioteca Berenson, Fototeca, 2016).
		# 	attribution = re.sub("late work by","", attribution).strip()
		# else:
		# 	attribution = attribution
		criteria.append((criterion, strip_punct(scholarattribution3.group(1)), strip_punct(scholarattribution3.group(2))))
	if scholarattribution4: # Francesco Beccaruzzi or Domenico Campagnola (communication by Francesco Smeraldi to Biblioteca Berenson, Fototeca).
		criteria.append((criterion, strip_punct(scholarattribution4.group(1)), strip_punct(scholarattribution4.group(3))))
	if scholarattribution5: # described by Mary Berenson in 1915 insurance list as School of Sano and not insured. 
		criteria.append((criterion, strip_punct(scholarattribution5.group(2)), strip_punct(scholarattribution5.group(1))))
	
	if scholarattribution51: # described by Mary Berenson in 1915 insurance list as "School Vercelli Alchemist (not insured)".
		criteria.append((criterion, strip_punct(scholarattribution51.group(3)), strip_punct(scholarattribution51.group(1))))
	if scholarattribution6: # attributed by Federico Zeri to an Umbrian collaborator of Antoniazzo Romano, possibly Mariano di Ser Austerio (see related Surrogate 120326_2).
		criteria.append((criterion, strip_punct(scholarattribution6.group(2)), strip_punct(scholarattribution6.group(1))))
	if scholarattribution7:
		if scholarattribution8: # attributed to Sassetta by P. Bottenwieser, commented by Bernard Berenson as: "late and careless"
			criteria.append((criterion, strip_punct(scholarattribution8.group(1)), strip_punct(scholarattribution8.group(2))))
		elif scholarattribution9: # attributed to Girolamo da Cremona by Federico Zeri. Expertized for Sotheby's by Lionello Venturi as Benvenuto di Giovanni.
			criteria.append((criterion, strip_punct(scholarattribution9.group(1)), strip_punct(scholarattribution9.group(2))))
		elif scholarattribution10: # attributed to the Master of the Richardson Triptych by Gaudenz Freuler (see related  Surrogates 127112_2 et al.)
			criteria.append((criterion, strip_punct(scholarattribution10.group(1)), strip_punct(scholarattribution10.group(2))))
		else: # attributed to the Master of the Vitae Imperatorum by John Pope-Hennessy
			auth = re.match('attributed to (.*) by (.*)', attribution)
			criteria.append((criterion, strip_punct(auth.group(1)), strip_punct(auth.group(2))))
	if scholarattribution11: # attributed by Gronau in 1923 to Antoniazzo Romano (see surrogate 120299_2).
		criteria.append((criterion, strip_punct(scholarattribution11.group(3)), strip_punct(scholarattribution11.group(1))))
	if scholarattribution12: # authenticated by Bernard Berenson as Titian, 9 March 1940.
		criteria.append((criterion, strip_punct(scholarattribution12.group(2)), strip_punct(scholarattribution12.group(1))))
	if scholarattribution13:
		criteria.append((criterion, strip_punct(scholarattribution13.group(2)), 'Fondazione Federico Zeri'))
	if scholarattribution14:
		criteria.append((criterion, strip_punct(scholarattribution14.group(3)), strip_punct(scholarattribution14.group(1))))
	if scholarattribution15:
		criteria.append((criterion, strip_punct(scholarattribution15.group(2)), 'NIKI, Dutch University Institute for Art History Florence' ))
	if scholarattribution16:
		if scholarattribution17:
			criteria.append((criterion, strip_punct(scholarattribution17.group(3)), strip_punct(scholarattribution17.group(1)) ))
			criteria.append((criterion, strip_punct(scholarattribution17.group(3)), strip_punct(scholarattribution17.group(2)) ))
		else:
			criteria.append((criterion, strip_punct(scholarattribution16.group(2)), strip_punct(scholarattribution16.group(1)) ))
	if scholarattribution18:
		criteria.append((criterion, strip_punct(scholarattribution18.group(2)), strip_punct(scholarattribution18.group(1)) ))
	if scholarattribution19:
		criteria.append((criterion, strip_punct(scholarattribution19.group(2)), strip_punct(scholarattribution19.group(1)) ))
	if scholarattribution20:
		criteria.append((criterion, strip_punct(scholarattribution20.group(1)), strip_punct(scholarattribution20.group(2)) ))
	if scholarattribution21:
		criteria.append((criterion, strip_punct(scholarattribution21.group(2)), strip_punct(scholarattribution21.group(1)) ))
	if scholarattribution22:
		criteria.append((criterion, strip_punct(scholarattribution22.group(1)), 'Hermann Voss' ))
	if scholarattribution23:
		criteria.append((criterion, strip_punct(scholarattribution23.group(1)), 'Morassi' ))
		criteria.append((criterion, strip_punct(scholarattribution23.group(1)), 'Zampetti' ))
	if scholarattribution24:
		criteria.append((criterion, strip_punct(scholarattribution24.group(1)), 'Roberto Longhi' ))
	if scholarattribution25:
		criteria.append((criterion, strip_punct(scholarattribution25.group(1)), 'Everett Fahy' ))

	if 'The Burlington Magazine  (1962): 252-230 as School of Giovanni Bellini.' in attribution:
		criteria.append((criterion, 'School of Giovanni Bellini', '' ))
	
	# scholar-note-on-photo
	scholarnoteonphoto = re.compile('note(.*)by(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	if 'Bernard Berenson' in attribution:
		criterionPhoto = "archival-creator-note-on-photo"
	else:
		criterionPhoto = "scholar-note-on-photo"
	if scholarnoteonphoto: 
		scholarnoteonphoto1 = re.compile('note(.*)by (.*) attributing the work to (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto2 = re.compile('^\s?handwritten note(.*)by (.*[^and]) reads.(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto3 = re.compile('^\s?handwritten note(.*)by (.*) reads?:?(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto4 = re.compile('^\s?handwritten note(.*)by (.*) and (.*) reads:(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto5 = re.compile('^\s?handwritten note(.*)by (.*) and (.*) read:(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto6 = re.compile('^\s?handwritten note(.*)by (.*[^and]) read:(.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		scholarnoteonphoto7 = re.compile('^\s?handwritten note(.*)by (.*) with reference to an expertise \(', re.IGNORECASE|re.DOTALL).search(attribution)
		
		if scholarnoteonphoto1: # Handwritten note by Bernard Berenson attributing the work to the Master of the Fogg Piet\xc3\xa0 (see
			criteria.append((criterionPhoto, scholarnoteonphoto1.group(3), scholarnoteonphoto1.group(2)))		
		if scholarnoteonphoto2: # handwritten note by Mary Berenson, later crossed out, reads. Luca di Tom\xc3\xa8 ?"
			criteria.append((criterionPhoto, scholarnoteonphoto2.group(3), scholarnoteonphoto2.group(2)))
		if scholarnoteonphoto3: # handwritten note by Bernard Berenson reads: " \'Pietro Luzi\' inscription on back
			if scholarnoteonphoto4: # handwritten note by Bernard Berenson and Nicky Mariano (now erased) reads:
				criteria.append((criterionPhoto, scholarnoteonphoto4.group(4), scholarnoteonphoto4.group(2)))
				criteria.append(('scholar-note-on-photo', scholarnoteonphoto4.group(4), scholarnoteonphoto4.group(3)))	
			else:
				criteria.append((criterionPhoto, scholarnoteonphoto3.group(3), scholarnoteonphoto3.group(2)))
		if scholarnoteonphoto5: # handwritten notes by Bernard Berenson read: "Titian" and "Titian?"
			criteria.append((criterionPhoto, scholarnoteonphoto5.group(4), scholarnoteonphoto5.group(2)))
			criteria.append(('scholar-note-on-photo', scholarnoteonphoto5.group(4), scholarnoteonphoto5.group(3)))		
		if scholarnoteonphoto6: # handwritten notes, partly by Bernard Berenson and Nicky Mariano, read: "With Domenico Morone" (s
			criteria.append((criterionPhoto, scholarnoteonphoto6.group(3), scholarnoteonphoto6.group(2)))		
		if scholarnoteonphoto7: # Handwritten note by Hermann Voss with reference to an expertise (see surrogate 109040_2).
			criteria.append((criterionPhoto, '', scholarnoteonphoto7.group(2)))
		# else: # Handwritten note signed by Erling Skaug: "Bartolo di Fredi / A. di Bartolo"
		# 	auth = re.match('andwritten note(.*)by (.*):(.*) \(', attribution)
		# 	criteria.append(('scholar-note-on-photo', strip_punct(auth.group(3)), strip_punct(auth.group(2))))
	scholarnoteonphoto8 = re.compile('note(.*)by (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto9 = re.compile('andwritten note stating that (.*) attributed the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)					
	scholarnoteonphoto91 = re.compile('andwritten notes? stating that (.*) attributes the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)					
	scholarnoteonphoto92 = re.compile('andwritten notes? indicating that (.*) attributes the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)					
	scholarnoteonphoto10 = re.compile('^\s?handwritten note in the (.*) hand attributing the work to (.*) on the back (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto11 = re.compile('^\s?Handwritten note by (.*) \(?erased\)?:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto12 = re.compile('^\s?Handwritten note by (.*) \(?now erased\)? reads (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto13 = re.compile('^\s?Handwritten note by Bernard Berenson: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto14 = re.compile('^\s?handwritten note by (.*) reporting the attribution of the work to (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto15 = re.compile('^\s?Handwritten note signed by (.*): (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto16 = re.compile('^\s?Handwritten note by Nicky Mariano:(.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto17 = re.compile('Handwritten notes? by Mary Berenson: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto171 = re.compile('Handwritten notes? by Mary Berenson reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto18 = re.compile('Handwritten note by Hermann Voss: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto19 = re.compile('handwritten note by Nicky Mariano(?:, now erased,)? reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto20 = re.compile('handwritten note by Hanna Kiel reads: (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto21 = re.compile('handwritten note by Mik(.*): (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto22 = re.compile('handwritten note by Paolo Paolini(.*): (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	scholarnoteonphoto23 = re.compile('handwritten note by (.*) reporting (.*)\'s attribution of the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	
	archivecreatornoteonphoto0 = re.compile('^\s?Handwritten notes by Bernard Berenson(?:\sread)?: (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto1 = re.compile('^\s?Handwritten notes by Bernard Berenson (erased): (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto2 = re.compile('^\s?handwritten notes by Bernard Berenson (now erased) read: (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto3 = re.compile('^\s?handwritten notes by Bernard Berenson with attribution (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto4 = re.compile('^\s?Other Attributions: handwritten note by Bernard Berenson reads: (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto5 = re.compile('handwritten note by Bernard Berenson with attribution (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto6 = re.compile('Handwritten notes by Bernard Berenson (erased):(.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto7 = re.compile('handwritten notes by Bernard Berenson (now erased) read: (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto8 = re.compile('Handwritten note by Bernard Berenson on a(.*): (.*)\(', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto9 = re.compile('Other attributions: handwritten notes by Bernard Berenson read: (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto10 = re.compile('Handwritten note by Bernard Berenson (covered by typewritten expertise): (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	archivecreatornoteonphoto11 = re.compile('Handwritten note by Bernard Berenson (crossed out): (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if scholarnoteonphoto8: # handwritten note stating that Federico Zeri attributes the work to Giovanni di Pietro (Lo Spagna) (see related
		criteria.append((criterionPhoto, scholarnoteonphoto8.group(2), scholarnoteonphoto8.group(1)))
	if scholarnoteonphoto9: # handwritten note stating that Bernard Berenson attributed the work to an artist close to Lippo Vanni (see related Surrogate 125667_2).
		criteria.append((criterionPhoto, scholarnoteonphoto9.group(2), scholarnoteonphoto9.group(1)))
	if scholarnoteonphoto91: # handwritten note stating that Bernard Berenson attributed the work to an artist close to Lippo Vanni (see related Surrogate 125667_2).
		criteria.append((criterionPhoto, scholarnoteonphoto91.group(2), scholarnoteonphoto91.group(1)))	
	if scholarnoteonphoto92: # handwritten note stating that Bernard Berenson attributed the work to an artist close to Lippo Vanni (see related Surrogate 125667_2).
		criteria.append((criterionPhoto, scholarnoteonphoto92.group(2), scholarnoteonphoto92.group(1)))	
	if scholarnoteonphoto10: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto10.group(2), scholarnoteonphoto10.group(1)))
	if scholarnoteonphoto11: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto11.group(2), scholarnoteonphoto11.group(1)))
	if scholarnoteonphoto12: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto12.group(2), scholarnoteonphoto12.group(1)))
	if scholarnoteonphoto13: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto13.group(1), 'Bernard Berenson' ))
	if scholarnoteonphoto14: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto14.group(2), scholarnoteonphoto14.group(1) ))
	if scholarnoteonphoto15: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto15.group(2), scholarnoteonphoto15.group(1) ))
	if scholarnoteonphoto16: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, scholarnoteonphoto16.group(1), 'Nicky Mariano' ))
	if scholarnoteonphoto17:
		criteria.append((criterion, strip_punct(scholarnoteonphoto17.group(1)), 'Mary Berenson' ))
	if scholarnoteonphoto171:
		criteria.append((criterion, strip_punct(scholarnoteonphoto171.group(1)), 'Mary Berenson' ))
	if scholarnoteonphoto18:
		criteria.append((criterion, strip_punct(scholarnoteonphoto18.group(1)), 'Hermann Voss' ))
	if scholarnoteonphoto19:
		criteria.append((criterion, strip_punct(scholarnoteonphoto19.group(1)), 'Nicky Mariano' ))
	if scholarnoteonphoto20:
		criteria.append((criterion, strip_punct(scholarnoteonphoto20.group(1)), 'Hanna Kiel' ))
	if scholarnoteonphoto21:
		criteria.append((criterion, strip_punct(scholarnoteonphoto21.group(1)), 'Boskovits M.' ))
	if scholarnoteonphoto22:
		criteria.append((criterion, strip_punct(scholarnoteonphoto22.group(1)), 'Paolo Paolini' ))
	if scholarnoteonphoto22:
		criteria.append((criterion, strip_punct(scholarnoteonphoto23.group(3)), strip_punct(scholarnoteonphoto23.group(1)) ))
		criteria.append(('scholar-attribution', strip_punct(scholarnoteonphoto23.group(3)), strip_punct(scholarnoteonphoto23.group(2)) ))

	if archivecreatornoteonphoto0: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, archivecreatornoteonphoto0.group(1), 'Bernard Berenson' ))
	if archivecreatornoteonphoto1: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, archivecreatornoteonphoto1.group(1), 'Bernard Berenson' ))
	if archivecreatornoteonphoto2: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, archivecreatornoteonphoto2.group(1), 'Bernard Berenson' ))
	if archivecreatornoteonphoto3: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, archivecreatornoteonphoto3.group(1), 'Bernard Berenson' ))
	if archivecreatornoteonphoto4: # handwritten note in the photographer Jacquier's hand attributing the work to Raffaellino del Garbo on the back of a photograph held at Biblioteca Berenson, Fototeca (see 504713_2)" [] 
		criteria.append((criterionPhoto, archivecreatornoteonphoto4.group(1), 'Bernard Berenson' ))
	if archivecreatornoteonphoto5:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto5.group(1)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto6:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto6.group(1)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto7:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto7.group(1)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto8:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto8.group(2)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto9:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto9.group(1)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto10:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto10.group(1)), 'Bernard Berenson' ))
	if archivecreatornoteonphoto11:
		criteria.append((criterion, strip_punct(archivecreatornoteonphoto11.group(1)), 'Bernard Berenson' ))

	if 'Raphael (see handwritten letter by Spearman ' in attribution:
		criteria.append((criterionPhoto, 'Raphael', 'Spearman' ))


	# anonymous-note-on-photo
	anonymousnoteonphoto = re.compile('^\s?handwritten note:(.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	if anonymousnoteonphoto: 
		anonymousnoteonphoto1 = re.compile('^handwritten note: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
		if anonymousnoteonphoto1: # Handwritten note: "Pordenone?" (see surrogate 109523_2).
			criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto1.group(1)), '' ))
		else: # handwritten note: "Titian"
			criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto.group(1)), '' ))
	anonymousnoteonphoto2 = re.compile('^\s?(?:same)?handwritten note (?:\(crossed out\))? reads:? (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto21 = re.compile('^\s?(?:same)?handwritten note reads:? (.*) on the back', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto3 = re.compile('^\s?note reads (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto4 = re.compile('^\s?note(.*)reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto5 = re.compile('^\s?noted as attributed to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto6 = re.compile('^\s?handwritten notes? attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto7 = re.compile('^\s?handwritten note attributing the work to (.*).', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto71 = re.compile('^\s?handwritten note, then crossed out, attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto8 = re.compile('^\s?handwritten note (erased) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto9 = re.compile('^\s?handwritten note transcribing (.*) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto10 = re.compile('^\s?handwritten notes attributing the work to (.*).', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto11 = re.compile('^\s?handwritten note on the back of a photograph attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto12 = re.compile('^\s?unidentified handwritten note reads (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto13 = re.compile('^\s?typewritten attestation attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto14 = re.compile('^\s?typewritten notes? reads?: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto15 = re.compile('^\s?unidentified handwritten note attributing the work to (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto16 = re.compile('^\s?typewritten indication on the back (.*)reads: (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto17 = re.compile('^\s?typewritten notes? attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto18 = re.compile('^\s?handwritten notes? reads?:? (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto19 = re.compile('^\s?unidentified handwritten note reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto20 = re.compile('^\s?same handwritten note reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto21 = re.compile('note (then crossed out) reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto22 = re.compile('^\s?another handwritten note attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto23 = re.compile('^\s?handwritten note reads:? "(.*)" \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto24 = re.compile('^\s?handwritten note \(now erased\) reads: "(.*)" \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto25 = re.compile('^\s?typewritten text reads "(.*)" \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto26 = re.compile('^\s?unidentified handwritten note attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto27 = re.compile('^\s?handwritten notes? (then crossed out) attributing the work to (.*), on the back', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto28 = re.compile('note (then crossed out) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto29 = re.compile('^\s?handwritten note reporting the old attribution of the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto30 = re.compile('^\s?\s?printed note reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto31 = re.compile('^\s?\s?handwritten note (now erased) attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto32 = re.compile('^\s?handwritten note attributing the panel "Madonna and Child" to (.*) or', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto33 = re.compile('^\s?handwritten note, then crossed out, reads: (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto34 = re.compile('^\s?handwritten notes reporting older attributions of the work to (.*),', re.IGNORECASE|re.DOTALL).search(attribution)
	anonymousnoteonphoto35 = re.compile('^\s?label from unidentified catalog attributing the work to (.*) \(', re.IGNORECASE|re.DOTALL).search(attribution)
	
	if anonymousnoteonphoto2: #handwritten note reads "with Titian"
		if anonymousnoteonphoto21:
			criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto21.group(1)), '' ))
		else:
			criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto2.group(1)), '' ))
	if anonymousnoteonphoto3:	# note reads "A. Schiavone?" (see related Surrogate 110592_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto3.group(1)), '' ))
	if anonymousnoteonphoto4:	# note reads "A. Schiavone?" (see related Surrogate 110592_2). # handwritten note (then crossed out) reads: "Boltraffio??" 
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto4.group(2)), '' ))
	if anonymousnoteonphoto5: # noted as attributed to Titian (see related Surrogate 110396_2).'
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto5.group(1)), '' ))
	if anonymousnoteonphoto6: # handwritten notes attributing the work to Paolo Veronese
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto6.group(1)), '' ))
	if anonymousnoteonphoto7: # handwritten notes attributing the work to Paolo Veronese
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto7.group(1)), '' ))
	if anonymousnoteonphoto71: # handwritten notes attributing the work to Paolo Veronese
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto71.group(1)), '' ))
	if anonymousnoteonphoto8: # Handwritten note (erased) attributing the work to Titian (see
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto8.group(1)), '' ))
	if anonymousnoteonphoto9: # handwritten note transcribing an inscription on the back of the painting attributing the work to Parmigianino (see surrogate 106137_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto9.group(2)), '' ))
	if anonymousnoteonphoto10: # handwritten note transcribing an inscription on the back of the painting attributing the work to Parmigianino (see surrogate 106137_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto10.group(1)), '' ))
	if anonymousnoteonphoto11: # handwritten note transcribing an inscription on the back of the painting attributing the work to Parmigianino (see surrogate 106137_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto11.group(1)), '' ))
	if anonymousnoteonphoto12: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto12.group(1)), '' ))
	if anonymousnoteonphoto13: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto13.group(1)), '' ))
	if anonymousnoteonphoto14: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto14.group(1)), '' ))
	if anonymousnoteonphoto15: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto15.group(1)), '' ))
	if anonymousnoteonphoto16: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto16.group(2)), '' ))
	if anonymousnoteonphoto17: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto17.group(1)), '' ))
	if anonymousnoteonphoto18: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto18.group(1)), '' ))
	if anonymousnoteonphoto19: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto19.group(1)), '' ))
	if anonymousnoteonphoto20: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto20.group(1)), '' ))
	if anonymousnoteonphoto21: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto21.group(1)), '' ))
	if anonymousnoteonphoto22: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto22.group(1)), '' ))
	if anonymousnoteonphoto23: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto23.group(1)), '' ))
	if anonymousnoteonphoto24: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto24.group(1)), '' ))
	if anonymousnoteonphoto25: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto25.group(1)), '' ))
	if anonymousnoteonphoto26: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto26.group(1)), '' ))
	if anonymousnoteonphoto27: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto27.group(1)), '' ))
	if anonymousnoteonphoto28: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto28.group(1)), '' ))
	if anonymousnoteonphoto29: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto29.group(1)), '' ))
	if anonymousnoteonphoto30: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto30.group(1)), '' ))
	if anonymousnoteonphoto31: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto31.group(1)), '' ))
	if anonymousnoteonphoto32: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto32.group(1)), '' ))
	if anonymousnoteonphoto33: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto33.group(1)), '' ))
	if anonymousnoteonphoto34: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto34.group(1)), '' ))
	if anonymousnoteonphoto35: # unidentified handwritten note reads "Padovanino?" (see related Surrogate 109274_2).
		criteria.append(('anonymous-note-on-photo', strip_punct(anonymousnoteonphoto35.group(1)), '' ))

	if 'With Fra Angelico, propapbly fake' in attribution:
		criteria.append(('anonymous-note-on-photo', 'Fra Angelico', '' ))
	if 'Pietro Lorenzetti (see' in attribution:
		criteria.append(('anonymous-note-on-photo', 'Pietro Lorenzetti', '' ))
	if 'Francesco Traini (see' in attribution:
		criteria.append(('anonymous-note-on-photo', 'Francesco Traini', '' ))
	
	# other
	other1 = re.compile('formerly attributed to (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	other2 = re.compile('www.vads.ac.uk(.*) to (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	other3 = re.compile('Frascione Arte online(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	other4 = re.compile('first attribution: (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	other5 = re.compile('Your Paintings database(.*) as (.*)', re.IGNORECASE|re.DOTALL).search(attribution)
	if other1: # formerly attributed to Marco Basaiti.
		criteria.append(('other', strip_punct(other1.group(1)), '' ))
	if other2:
		criteria.append(('other', strip_punct(other2.group(2)), 'VADS' ))
	if other3:
		criteria.append(('other', strip_punct(other3.group(2)), 'Frascione Arte online' ))
	if other4:
		criteria.append(('other', strip_punct(other4.group(1)), '' ))
	if other5:
		criteria.append(('other', strip_punct(other5.group(2)), 'BBC and Public Catalogue Foundation' ))

	if 'La Diana, 1 (1929), as Girolamo di Benvenuto' in attribution:
		criteria.append(('other', 'Girolamo di Benvenuto' , '' ))
	if 'Jacopo Palma il vecchio in two clippings' in attribution:
		criteria.append(('other', 'Jacopo Palma il vecchio' , '' ))
	# none
	if 'school of Francesco Laurana' in attribution:
		criteria.append(('none', 'school of Francesco Laurana' , '' ))
	if ' Jacopo della Quercia.' in attribution:
		criteria.append(('none', 'Jacopo della Quercia' , '' ))

	# inventory

	return criteria	


def get_year(text):
	""" match four digits in the string if lower that 2018 and attributes default value to others"""
	criteria = set()
	rg = re.compile('.*([\[\(]?((?:18[0-9]|19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
	match = rg.search(text)
	if match:
		criteria.add(match.group(1))
	return criteria


# 1. create rdf data 
def itatti_to_rdf(initial_csv,itatti_rdf):
	""" extract data from xls file and transform artworks, creation, attributions and artists"""	
	g=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))
	g.bind('owl', OWL)
	g.bind('crm', CIDOC)
	g.bind('hico', HICO)
	with open(initial_csv, 'r', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for sheetX in reader:
			artworkID = sheetX['Work[36658]']
			artworkLabel = sheetX['Title[36661]']
			photoOnlineURN = re.sub('drs:', '', str(sheetX['Filename']))
			photoID = sheetX['Image Accession Number[36690]']
			creationDateLabel = sheetX['Date Description[36664]']
			artistLabel = sheetX['Creator[36659]']
			attributionLabel = sheetX['Description[36680]']

			# artwork E28_Conceptual_Object
			if str(artworkID) != '':
				artworkID = str(artworkID)
				g.add(( URIRef(base+'artwork/'+artworkID) , RDF.type , URIRef(CIDOC.E28_Conceptual_Object) ))
				g.add(( URIRef(base+'artwork/'+artworkID) , DCTERMS.title , Literal(artworkLabel) ))
				if str(sheetX['Filename']) != '':
					g.add(( URIRef(base+'artwork/'+artworkID) , FOAF.depiction , URIRef('https://nrs.harvard.edu/'+photoOnlineURN) ))
					g.add(( URIRef('https://nrs.harvard.edu/'+photoOnlineURN) , DCTERMS.title , Literal(photoID) ))
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
				# attribution 
				g.add(( URIRef(base+'artwork/'+artworkID+'/creation') , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution') ))
				g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CIDOC.P3_has_note , Literal(attributionLabel) ))
				g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
				g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationType , URIRef(base+'itatti-preferred-attribution') ))

	return g.serialize(destination=itatti_rdf, format='nquads')


# 2. reconcile artists to VIAF and co. and manually double check DONE
def reconcile_artists_to_viaf(itatti_rdf,artists_csv):
	""" parse the .nq file, get the artists, fuzzy string matching to VIAF, create a csv 'artists_itatti_viaf.csv' to be manually double checked"""
	baseURL = 'http://viaf.org/viaf/search/viaf?query=local.personalNames+%3D+%22'
	f=csv.writer(open(artists_csv, 'w', encoding='utf-8'))
	f.writerow(['id']+['search']+['result']+['viaf']+['lc']+['isni']+['ratio']+['partialRatio']+['tokenSort']+['tokenSet']+['avg'])

	g=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))
	g.parse(itatti_rdf, format="nquads")
	g.bind('owl', OWL)
	names = set()
	for s,p,o in g.triples((None, CIDOC.P14_carried_out_by, None)):
		for o1, p1, name in g.triples((o, DCTERMS.title, None )):
			name = re.sub("([\(\[]).*?([\)\]])", "", name)
			name = re.sub("artist", "", name)
			names.add((name.strip(), o ))

	for name, idName in names:
		rowEdited = urllib.parse.quote(name.strip())
		url = baseURL+rowEdited+'%22+and+local.sources+%3D+%22lc%22&sortKeys=holdingscount&maximumRecords=1&httpAccept=application/rdf+json'		
		response = requests.get(url).content.decode('utf-8')
		try:
			response = response[response.index('<recordData xsi:type="ns1:stringOrXmlFragment">')+47:response.index('</recordData>')].replace('&quot;','"')
			response = json.loads(response)
			print (response)
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
def artists_linkset(artists_csv_revised, linkset_artists_itatti):
	""" read the csv manually double checked, renamed 'FINAL_artists_itatti_viaf.csv', and create a linkset for artists."""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(artists_graph))
	g.bind('owl', OWL)
	with open(artists_csv_revised, 'r', encoding='utf-8') as csvfile:
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
				g.add(( URIRef(viaf) , OWL.sameAs , URIRef(uri) ))
			if lc != '':
				g.add(( URIRef(uri) , OWL.sameAs , URIRef(lc) ))
				g.add(( URIRef(lc) , OWL.sameAs , URIRef(uri) ))
			if isni != '':
				g.add(( URIRef(uri) , OWL.sameAs , URIRef(isni) ))
				g.add(( URIRef(isni) , OWL.sameAs , URIRef(uri) ))
	g.serialize(destination=linkset_artists_itatti, format='nquads')


# 4. create the linkset of artworks - reconciliation to zeri's via pastec DONE (partially)
def reconcile_itatti_artworks_to_zeri(pastec_data, zeri_data, itatti_rdf,linkset_itatti_zeri_artworks):
	""" get the match obtained from pastec, get the URI of artworks in zeri and itatti and create sameAs links """
	# get artwork URI and photo filenames from zeri dataset
	tree = ET.parse(zeri_data)
	root = tree.getroot()
	zeriURIandImages = []
	for scheda in root.findall('./SCHEDA'):	
		artworkID = scheda.attrib['sercdoa']
		for photo in scheda.findall('ALLEGATI/FOTO'):
				photoID = photo.text
				photoID = re.search('([^/]*.$)', photoID).group(1)
				zeriURIandImages.append(( 'http://purl.org/emmedi/mauth/zeri/artwork/'+artworkID , photoID ))

	# get artwork URI and photo filenames from itatti dataset
	g=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))	
	g.parse(itatti_rdf, format="nquads")
	itattiURIandImages = []
	for s,p,o in g.triples((None, FOAF.depiction, None)):
		for o1, p1, name in g.triples((o, DCTERMS.title, None )):
			itattiURIandImages.append((str(s), str(name)))
	# create the new graph
	linkset=rdflib.ConjunctiveGraph(identifier=URIRef('http://purl.org/emmedi/mauth/artworks/'))
	linkset.bind('owl', OWL)
	with open(pastec_data,'r') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			zeriImg = row['zeri'].strip()
			itattiImgTBC = row['itatti'].strip()
			score = row['score']
			lastDigit = itattiImgTBC[-1]
			allButlastDigit = itattiImgTBC[:-1]
			itattiImg = allButlastDigit+'_'+lastDigit
			for x,y in zeriURIandImages:
				if y == zeriImg:
					for z,w in itattiURIandImages:
						if w == itattiImg:
							linkset.add(( URIRef(x), OWL.sameAs, URIRef(z) ))
							linkset.add(( URIRef(z), OWL.sameAs, URIRef(x) ))
	return linkset.serialize(destination=linkset_itatti_zeri_artworks, format='nquads')


# 5. get the criteria underpinning the attribution
def methodology_itatti(itatti_rdf, initial_csv):
	""" extract from each attribution the criterion and define a controlled vocabulary (reuse the zeri one). 
	Secondly, update the itatti.nq file adding the interpretation criterion to each attribution."""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))
	g.parse(itatti_rdf, format="nquads")
	g.bind('hico', HICO)
	g.bind('cito', CITO)
	g.bind('prov', PROV)

	# pattern = re.compile(r"\.(?![^(]*\))") # dot outside parentesis indicate several criteria are provided BUT not always...
	# date = re.compile(r"((18|19|20)\d{2})")
	
	with open(initial_csv, encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		disc = 0
		for row in reader: 
			artworkID = row['Work[36658]']
			
			# preferred attribution
			if 'Note - attribution:' in row['Description[36680]']:
				line = str(row['Description[36680]'])
				attribs = line.split("Note - attribution:",1)[1] 
				attribs = re.sub('sources?:', '', attribs, flags=re.IGNORECASE)
				# remove other attributions
				if 'Other attr' in attribs:
					attrib = re.compile('Other attr', re.IGNORECASE|re.DOTALL).split(attribs)[0]
					# remove other annotations
					if "Note" in attrib:
						attrib = attribs.split('Note')[0]					
				else:
					attrib = attribs
					# remove other annotations
					if "Note" in attrib:
						attrib = attribs.split('Note')[0]
				attrib = attrib.strip().strip('\n\r').strip('\n').strip('\t')		
				# multiple criteria
				if (';' in attrib):
					attributions = attrib.split(';') 
					for attribution in attributions:
						rg = re.compile('.*([\[\(]?((?:18[0-9]|19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
						match = rg.search(attribution)
						if match:
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , PROV.startedAtTime , Literal(match.group(1)+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
						for crit, person in get_criteria(attribution):
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationCriterion , URIRef(criterion+crit) ))
							if len(person) != 0:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CITO.agreesWith , URIRef(base+clean_to_uri(person)) ))
								g.add(( URIRef(base+clean_to_uri(person)), RDFS.label, Literal(person) ))
						# if len(get_criteria(attribution)) == 0:
						# 	print(get_criteria(attribution.encode('utf-8')), attribution.encode('utf-8'))
				else:
					rg = re.compile('.*([\[\(]?((?:19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
					match = rg.search(attrib)
					if match:
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , PROV.startedAtTime , Literal(match.group(1)+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
					for crit, person in get_criteria(attrib):
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , HICO.hasInterpretationCriterion , URIRef(criterion+crit) ))
						if len(person) != 0:
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution') , CITO.agreesWith , URIRef(base+clean_to_uri(person)) ))
							g.add(( URIRef(base+clean_to_uri(person)), RDFS.label, Literal(person) ))
					# if len(get_criteria(attrib)) == 0:
					# 	print(get_criteria(attrib.encode('utf-8')), attrib.encode('utf-8'))
			
			# discarded attributions
			if 'Other attr' in row['Description[36680]'] or 'Other Attr' in row['Description[36680]']:
				
				otherAttribution1 = re.compile('other attr([^:]*):(.*)$', re.IGNORECASE|re.DOTALL).search(str(row['Description[36680]']))
				
				if otherAttribution1:
					disc += 1
					otherAttribution = otherAttribution1.group(2).strip()
					otherAttribution2 = re.compile('(.*)Note').search(otherAttribution)	
					if otherAttribution2:
						otherAttribution = otherAttribution2.group(0).strip()
					else:
						otherAttribution = otherAttribution
					
					# multiple attributions
					if (';' in otherAttribution):
						attributions = otherAttribution.split(';') 
						n = 0
						for attribu in attributions:
							# if 'Note' in attribu:
							# 	pass
							# else:
								n += 1
								g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation'+str(n) ) ))	
								g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) ))						
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CIDOC.P3_has_note , Literal(attribu) ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationType , URIRef(base+'itatti-discarded-attribution') ))

								rg = re.compile('.*([\[\(]?((?:18[0-9]|19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
								match = rg.search(attribu)
								if match:
									g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , PROV.startedAtTime , Literal(match.group(1)+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
								
								for crit, artist, person in get_other_criteria_and_artist(attribu):
									if crit is not None:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , HICO.hasInterpretationCriterion , URIRef(criterion+crit) ))
									# else:
									# 	print(attribution.encode('utf-8'), get_other_criteria_and_artist(attribution.encode('utf-8')),'\n')
									if artist is not None:
										g.add(( URIRef(base+'artwork/'+artworkID+'/creation'+str(n)) , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(artist)) ))		
									if person is not None:
										g.add(( URIRef(base+'artwork/'+artworkID+'/attribution'+str(n)) , CITO.agreesWith , URIRef(base+clean_to_uri(person)) ))
										g.add(( URIRef(base+clean_to_uri(person)), RDFS.label, Literal(person) ))
								# if len(get_other_criteria_and_artist(attribution)) == 0:
								# 	print(attribution.encode('utf-8'), get_other_criteria_and_artist(attribution.encode('utf-8')),'\n')

					# single attribution		
					else:
						g.add(( URIRef(base+'artwork/'+artworkID) , CIDOC.P94i_was_created_by , URIRef(base+'artwork/'+artworkID+'/creation1') ))	
						g.add(( URIRef(base+'artwork/'+artworkID+'/creation1') , PROV.wasGeneratedBy , URIRef(base+'artwork/'+artworkID+'/attribution1') ))						
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , CIDOC.P3_has_note , Literal(otherAttribution) ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , HICO.hasInterpretationType , URIRef(HICO+'authorship-attribution') ))
						g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , HICO.hasInterpretationType , URIRef(base+'itatti-discarded-attribution') ))

						rg = re.compile('.*([\[\(]?((?:19[0-9]|20[01])[0-9])[\]\)]?)', re.IGNORECASE|re.DOTALL)
						match = rg.search(otherAttribution)
						if match:
							g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , PROV.startedAtTime , Literal(match.group(1)+'-01-01T00:00:01Z', datatype=XSD.dateTime) ))
						
						for crit, artist, person in get_other_criteria_and_artist(otherAttribution):
							if crit is not None:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , HICO.hasInterpretationCriterion , URIRef(criterion+crit) ))
							# else:
							# 	print(otherAttribution.encode('utf-8'), get_other_criteria_and_artist(otherAttribution.encode('utf-8')),'\n')
							if artist is not None:
								g.add(( URIRef(base+'artwork/'+artworkID+'/creation1') , CIDOC.P14_carried_out_by , URIRef(base+'artist/'+clean_to_uri(artist)) ))		
							if person is not None:
								g.add(( URIRef(base+'artwork/'+artworkID+'/attribution1') , CITO.agreesWith , URIRef(base+clean_to_uri(person)) ))
								g.add(( URIRef(base+clean_to_uri(person)), RDFS.label, Literal(person) ))
						# if len(get_other_criteria_and_artist(attribOther)) == 0:
						# 	print(attribOther.encode('utf-8'), get_other_criteria_and_artist(attribOther.encode('utf-8')),'\n')

				else:
					print(row['Description[36680]'])
			else:
				pass
		
		return g.serialize(destination=itatti_rdf, format='nquads')
		

# 6. reconcile historians to VIAF and co. and manually double check
def reconcile_historians_to_viaf(itatti_rdf, historians_itatti_viaf):
	""" extract from each attribution the historian cited, fuzzy string matching to VIAF, create a csv 'historians_itatti_viaf.csv' to be manually double checked
	Secondly, update the itatti.nq file adding the historian cited to each attribution."""
	baseURL = 'http://viaf.org/viaf/search/viaf?query=local.names+%3D+%22'
	f=csv.writer(open(historians_itatti_viaf, 'w', encoding='utf-8'))
	f.writerow(['id']+['search']+['result']+['viaf']+['lc']+['isni']+['ratio']+['partialRatio']+['tokenSort']+['tokenSet']+['avg'])

	g=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))
	g.parse(itatti_rdf, format="nquads")
	g.bind('cito', CITO)
	names = set()
	for s,p,o in g.triples((None, CITO.agreesWith, None)):
		for s1,p1,o1 in g.triples((o, RDFS.label, None)):
			names.add((o1, o))
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


# 7. create the linkset of historians
def historians_linkset(itatti_rdf,historians_revised,linkset_arthistorians_itatti):
	""" read the csv manually double-checked, renamed 'FINAL_historians_itatti_viaf.csv', and create a linkset for historians."""
	g=rdflib.ConjunctiveGraph(identifier=URIRef(arthistorians_graph))
	g.bind('owl', OWL)
	ok=rdflib.ConjunctiveGraph(identifier=URIRef(itatti_graph))
	ok.parse(itatti_rdf, format="nquads")
	with open(historians_revised, 'r', encoding='utf-8') as csvfile:
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
			# cleaning labels in the original graph and create the new FINAL one
			for s1,p1,o1 in ok.triples(( None, RDFS.label, None )):
				if s1 == uri:
					ok.remove(( s1, RDFS.label, None ))
					ok.add(( URIRef(s1), RDFS.label, Literal(firstName) ))
	g.serialize(destination=linkset_arthistorians_itatti, format='nquads')
	ok.serialize(destination=itatti_rdf, format='nquads')