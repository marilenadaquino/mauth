from flask import Flask, request , redirect , jsonify ,render_template , url_for
from flask_restplus import Resource, Api, Namespace , fields
from flask_swagger_ui import get_swaggerui_blueprint
from flask_accept import accept

from apispec import APISpec

from json import dumps
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import OWL, DC , RDF , RDFS
from rdflib.plugins.sparql import prepareQuery
from SPARQLWrapper import SPARQLWrapper, JSON 
from collections import defaultdict
import urllib , connoisseur , utils , config , re , requests , json 
from urllib.parse import unquote , urlparse

app = Flask(__name__, static_url_path='/static/')
api = Api(app=app)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "mAuth"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)


def queryMauth(artwork_iri):
	""" query the knowledge base including observed attributions, returns a JSON file with sorted results.
	Results are sent to the API and the Web App. """
	queryKb = """ 
	PREFIX mauth: <http://purl.org/emmedi/mauth/>
	PREFIX dcterms: <http://purl.org/dc/terms/>
	SELECT DISTINCT * WHERE  {
		{ ?obs mauth:hasObservedArtwork ?artwork ; rdfs:label ?obsLabel ;
			mauth:hasObservedArtist ?artist . 
				OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
				OPTIONAL {?obs mauth:hasAttributionDate ?date .} .
				OPTIONAL {?artwork dcterms:title|rdfs:label ?artworkTitle.} .
				OPTIONAL {?artist dcterms:title|rdfs:label ?artistTitle.} .
				OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
				OPTIONAL {?obs mauth:citesAsEvidence ?bibl .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar dcterms:title|rdfs:label ?scholarLabel .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasHIndex ?h_index .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasArtistIndex ?a_indexNode . ?a_indexNode mauth:hasIndexedArtist ?artist ; mauth:hasArtistIndex ?a_index} .
				OPTIONAL {?obs mauth:image ?image .} .
			} UNION
			{ ?other owl:sameAs+ ?artwork . 
				?obs mauth:hasObservedArtwork ?other ; rdfs:label ?obsLabel ;
				mauth:hasObservedArtist ?artist . 
				OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
				OPTIONAL {?obs mauth:hasAttributionDate ?date .} .
				OPTIONAL {?other dcterms:title|rdfs:label ?artworkTitle.} .
				OPTIONAL {?artist dcterms:title|rdfs:label ?artistTitle.} .
				OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
				OPTIONAL {?obs mauth:citesAsEvidence ?bibl .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar dcterms:title|rdfs:label ?scholarLabel .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasHIndex ?h_index .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasArtistIndex ?a_indexNode . ?a_indexNode mauth:hasIndexedArtist ?artist ; mauth:hasArtistIndex ?a_index} .
				OPTIONAL {?obs mauth:image ?image .} .
				FILTER (?artwork != ?other)
			} UNION
			{ ?artwork owl:sameAs+ ?other . 
				?obs mauth:hasObservedArtwork ?other ; rdfs:label ?obsLabel ;
				mauth:hasObservedArtist ?artist . 
				OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
				OPTIONAL{?obs mauth:hasAttributionDate ?date .} .
				OPTIONAL {?other dcterms:title|rdfs:label ?artworkTitle.} .
				OPTIONAL {?artist dcterms:title|rdfs:label ?artistTitle.} .
				OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
				OPTIONAL {?obs mauth:citesAsEvidence ?bibl .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar dcterms:title|rdfs:label ?scholarLabel .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasHIndex ?h_index .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasArtistIndex ?a_indexNode . ?a_indexNode mauth:hasIndexedArtist ?artist ; mauth:hasArtistIndex ?a_index} .
				OPTIONAL {?obs mauth:image ?image .} .
				FILTER (?artwork != ?other)
			}  
			UNION
			{ ?artwork owl:sameAs ?com. ?other owl:sameAs ?com. 
				?obs mauth:hasObservedArtwork ?other ; rdfs:label ?obsLabel ;
				mauth:hasObservedArtist ?artist . 
				OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
				OPTIONAL{?obs mauth:hasAttributionDate ?date .} .
				OPTIONAL {?other dcterms:title|rdfs:label ?artworkTitle.} .
				OPTIONAL {?artist dcterms:title|rdfs:label ?artistTitle.} .
				OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
				OPTIONAL {?obs mauth:citesAsEvidence ?bibl .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar dcterms:title|rdfs:label ?scholarLabel .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasHIndex ?h_index .} .
				OPTIONAL {?obs mauth:agreesWith ?scholar . ?scholar mauth:hasArtistIndex ?a_indexNode . ?a_indexNode mauth:hasIndexedArtist ?artist ; mauth:hasArtistIndex ?a_index} .
				OPTIONAL {?obs mauth:image ?image .} .
				FILTER (?artwork != ?other)
			}        
	} 

	VALUES ?artwork {<"""+ str(artwork_iri) +""">}"""
	try:
		artwork_iri = artwork_iri.replace('\r','')
		if 'http' in artwork_iri or 'https' in artwork_iri:
			sparql = SPARQLWrapper(config.SPARQLendpoint)
			sparql.setQuery(queryKb)
			sparql.setReturnFormat(JSON)
			results = sparql.query().convert()   
			return utils.rank(utils.rebuildResults(results)) 
	except Exception as error:
		print (error)

# mAuth API
#@name_space.route("/<path:artwork_iri>")
class FullHistory(Resource):

	# @api.doc(responses={ 200: 'OK', 400: 'Invalid Argument' }, 
	# 		 params={ 'artwork_iri': 'Specify the IRI associated with the artwork' })
	
	def get(self, artwork_iri):
		"""Accepts in input the IRI of an artwork."""
		try:
			result = queryMauth(artwork_iri)
			return result
		except KeyError as e:
			print(e)

api.add_resource(FullHistory, '/full/<path:artwork_iri>')

@app.route('/')
def hello():
    return redirect(url_for('home'))

# mAuth Web app
# homepage and search tpl
@app.route('/home', methods=['GET'])
@accept('text/html')
def index():
	"""Accepts in input either the IRI of the artwork or the webpage describing the artwork."""
	# templates/index.html
	if request.args != '':
		if request.args.get('uri_source'):
			artwork = utils.getURI(request.args.get('uri_source'))
		elif request.args.get('id'):
			artwork = utils.getURI(request.args('id') )
		elif request.args.get('imageId'):
			artwork = utils.getURI(request.args['imageId'])
		else:
			artwork = request.args
		results = queryMauth(artwork)
	else:
		artwork = ''
		results = ''
	return render_template('index.html', results=results, searchURL=artwork)

# permanent link (shortcut) to the search interface
@app.route('/search', methods=['GET'])
@accept('text/html')
def search():
	"""Accepts in input either the IRI of the artwork or the webpage describing the artwork."""
	# templates/search.html
	if request.args != '':
		if request.args.get('uri_source'):
			artwork = utils.getURI(request.args.get('uri_source'))
		elif request.args.get('id'):
			artwork = utils.getURI(request.args('id') )
		elif request.args.get('imageId'):
			artwork = utils.getURI(request.args['imageId'])
		else:
			artwork = request.args
		results = queryMauth(artwork)
	else:
		artwork = ''
		results = ''
	return render_template('search.html', results=results, searchURL=artwork)


@app.template_filter()
def maximum(_list):
	try:
		return max(_list)[0]
	except Exception as e:
		print(str(e))

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=False, port=8000)