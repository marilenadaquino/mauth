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
from urllib import unquote

app = Flask(__name__, static_url_path='')
api = Api(app)
# python 2!

def queryMauth(artwork_iri):
    try:
        # TODO expand the SPARQL query including all the information
        print "hello mauth"
        print ("artwork_iri", artwork_iri)
        artwork_iri = artwork_iri.replace('\r','')
        get_history = """ 
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

        VALUES ?artwork {<"""+ artwork_iri +""">}"""
        # TODO add bias index
        sparql = SPARQLWrapper('http://0.0.0.0:9999/blazegraph/sparql')
        sparql.setQuery(get_history)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        print 'hello results \n', connoisseur.rank(utils.rebuildResults(results))
        #group by provider
        return connoisseur.rank(utils.rebuildResults(results)) 
            
    except Exception as error:
        print (error)


class FullHistory(Resource):
    def get(self, artwork_iri):
        print ('hello SPARQL endpoint')
        # if find the URI in the triple store
        return queryMauth(artwork_iri)
        # else: do everything from scratch (and consider that the URI might be wrong - i.e. not an artwork)
    
api.add_resource(FullHistory, '/full/<path:artwork_iri>')

@app.route('/', methods=['GET'])
@accept('text/html')
def index():
    # static/index.html
    if request.args != '' :
        print request.args
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


@app.route('/search', methods=['GET'])
@accept('text/html')
def search():
    # templates/search.html
    if request.args != '' :
        print request.args
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
    print artwork , results
    return render_template('search.html', results=results, searchURL=artwork)


# @app.route('/results', methods=['GET'])
# @accept('text/html')
# def results():
#     # templates/results.html
#     if request.args.get('uri_source'):
#         artwork = utils.getURI(request.args.get('uri_source'))
#     elif request.args.get('id'):
#         artwork = utils.getURI(request.args('id') )
#     elif request.args.get('imageId'):
#         artwork = utils.getURI(request.args['imageId'])
#     else:
#         artwork = request.args
#     results = queryMauth(artwork)
#     return render_template('results.html', searchURL=artwork, results=results ) 

@app.template_filter()
def maximum(_list):
    try:
        return max(_list)[0]
    except Exception as e:
        print(str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=8000)