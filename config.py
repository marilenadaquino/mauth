from rdflib import Namespace
from pymantic import sparql


# auxiliary files
settingsFile = "settings/settings.json"
mappingDocument = "settings/artist.json"
observations = "observations/"
objProperty = 'artist' # string for observation URI design 
historiansIndexes_rdf = 'data/historiansIndexes_rdf.nq'

# graphs
attributions_graph = 'http://purl.org/emmedi/mauth/attributions/'
artworks_linkset = 'http://purl.org/emmedi/mauth/artworks/'
artists_linkset = 'http://purl.org/emmedi/mauth/artists/'
historians_linkset = 'http://purl.org/emmedi/mauth/historians/'
 
# blazegraph instance
SPARQLendpoint = 'http://0.0.0.0:9999/blazegraph/sparql'
server = sparql.SPARQLServer(SPARQLendpoint)

