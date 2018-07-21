from flask import Flask, request , redirect , jsonify
from flask_restful import Resource, Api
from flask_accept import accept
from flask import render_template

# import linkset
from json import dumps
from rdflib import URIRef , XSD, Namespace , Literal
from rdflib.namespace import OWL, DC , RDF , RDFS
from rdflib.plugins.sparql import prepareQuery
from SPARQLWrapper import SPARQLWrapper, JSON 
from collections import defaultdict
import urllib , connoisseur , utils , re , requests , json

app = Flask(__name__, static_url_path='')
api = Api(app)
# python 2!

def queryMauth(artwork_iri):
    try:
        # TODO expand the SPARQL query including all the information
        get_history = """ 
        PREFIX mauth: <http://purl.org/emmedi/mauth/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        SELECT DISTINCT * WHERE  {
                { ?obs mauth:hasObservedArtwork ?artwork ; rdfs:label ?obsLabel ;
                    mauth:hasObservedArtist ?artist . ?artwork a <http://www.cidoc-crm.org/cidoc-crm/E28_Conceptual_Object> ; 
                    OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
                    OPTIONAL {?obs mauth:hasAttributionDate ?date .} .
                    OPTIONAL {?artwork dcterms:title ?artworkTitle.} .
                    OPTIONAL {?artist dcterms:title ?artistTitle.} .
                    OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
                    OPTIONAL {?obs mauth:agreesWith ?scholar .} .
                    OPTIONAL {?obs mauth:image ?image .} .
                } UNION
                { ?other owl:sameAs ?artwork . 
                    ?obs mauth:hasObservedArtwork ?other ; rdfs:label ?obsLabel ;
                    mauth:hasObservedArtist ?artist . ?artwork a <http://www.cidoc-crm.org/cidoc-crm/E28_Conceptual_Object> .
                    OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
                    OPTIONAL {?obs mauth:hasAttributionDate ?date .} .
                    OPTIONAL {?other dcterms:title ?artworkTitle.} .
                    OPTIONAL {?artist dcterms:title ?artistTitle.} .
                    OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
                    OPTIONAL {?obs mauth:agreesWith ?scholar .} .
                    OPTIONAL {?obs mauth:image ?image .} .
                } UNION
                { ?artwork owl:sameAs ?other . 
                    ?obs mauth:hasObservedArtwork ?other ; rdfs:label ?obsLabel ;
                    mauth:hasObservedArtist ?artist . ?artwork a <http://www.cidoc-crm.org/cidoc-crm/E28_Conceptual_Object> .
                    OPTIONAL {?obs mauth:hasObservedCriterion ?criterion . ?criterion rdfs:label ?criterionLabel } .
                    OPTIONAL{?obs mauth:hasAttributionDate ?date .} .
                    OPTIONAL {?other dcterms:title ?artworkTitle.} .
                    OPTIONAL {?artist dcterms:title ?artistTitle.} .
                    OPTIONAL {?obs mauth:hasSourceOfAttribution ?source .} .
                    OPTIONAL {?obs mauth:agreesWith ?scholar .} .
                    OPTIONAL {?obs mauth:image ?image .} .
                }        
        } 
        VALUES ?artwork {<"""+ artwork_iri +""">}"""
        # TODO change endpoint, or maybe not...
        sparql = SPARQLWrapper('http://127.0.0.1:9999/blazegraph/sparql')
        sparql.setQuery(get_history)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        print 'hello results \n', results
        #group by provider
        return connoisseur.rank(utils.rebuildResults(results)) 
            
    except Exception as error:
        print error


class FullHistory(Resource):
    def get(self, artwork_iri):
        print 'hello SPARQL endpoint'
        # if find the URI in the triple store
        return queryMauth(artwork_iri)
        # else: do everything from scratch (and consider that the URI might be wrong - i.e. not an artwork)
    
api.add_resource(FullHistory, '/full/<path:artwork_iri>')

@app.route('/')
@accept('text/html')
def index():
    # static/index.html
    return app.send_static_file('index.html')


@app.route('/search', methods=['GET'])
@accept('text/html')
def search():
    # templates/index.html
    return render_template('search.html')


@app.route('/results', methods=['GET'])
@accept('text/html')
def results():
    # templates/results.html
    inputURI = request.args['uri_source']
    artwork = utils.getURI(inputURI)
    
    if request.method == 'GET':
        results = queryMauth(artwork)
        #sortedResults = sorted( results, key = lambda attr:attr['score'], reverse = False )
        #response = json.loads(req.content)
        return render_template('results.html', searchURL=artwork, results=results ) 


if __name__ == '__main__':
    app.run(host='localhost', debug=True, port=8000)