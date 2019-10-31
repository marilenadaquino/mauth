import connoisseur , utils , config , os , datetime
import data.itatti.run as itatti
import data.frick.run as frick
import data.zeri.run as zeri
from pymantic import sparql

dirpath = os.getcwd()+'/'

# providers' graphs and linksets
#itatti.run()
print("[DONE] itatti graphs"+str(datetime.datetime.now()))
#frick.run()
print("[DONE] frick graphs"+str(datetime.datetime.now()))
#zeri.run()
print("[DONE] zeri graphs"+str(datetime.datetime.now()))

# query artworks linkset to initialize Connoisseur() and start mAuth crawler
get_artworks = """
	PREFIX owl: <http://www.w3.org/2002/07/owl#>
	SELECT DISTINCT ?artwork
	FROM <"""+config.artworks_linkset+""">
	WHERE { {?a ?b ?artwork } UNION {?artwork ?b ?c } }"""

sparqlW = connoisseur.SPARQLWrapper(config.SPARQLendpoint)
sparqlW.setQuery(get_artworks)
sparqlW.setReturnFormat(connoisseur.JSON)
results = sparqlW.query().convert()
artworkList = list( result["artwork"]["value"] for result in (results["results"]["bindings"]))
print("[DONE] get list of artworks"+str(datetime.datetime.now()))

kb = connoisseur.Connoisseur(artworkList, config.attributions_graph)

# recursive and transitive linksets artworks, artists, historians
kb.updateLinksets(config.artworks_linkset, config.settingsFile, 'artworks')
kb.updateLinksets(config.artists_linkset, config.settingsFile, 'artists')
kb.updateLinksets(config.historians_linkset, config.settingsFile, 'historians')
print("[DONE] recursive/transitive linksets"+str(datetime.datetime.now()))

# create observation graph			
kb.updateAttributions()
print("[DONE] observation graph")

# create statistics graph
utils.rankHistorian(config.historiansIndexes_rdf)
print("[DONE] statistics graph")