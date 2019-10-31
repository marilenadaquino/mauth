# mauth
mAuth: mining authoritativeness in art history

mAuth includes:

 * a [semantic crawler](connoisseur.py) for fetching attributions
 * a [triplestore](blazegraph/) for storing harvested attributions, linksets, and few data sources
 * a backup copy of [data](data/) retrieved and hosted for third-party institutions
 * an Flask [API](mauth.py) to serve data on contradictory attributions, and a web application based on the API (for visualizing ranked attributions) 
 * results of the [corpus analysis](corpus_analysis/) (for defining measures )
 * results of the [user study](user_study_results/) (for evaluating the ranking model)

### HOW TO

 * [config.py](config.py) to change configuration
 * [run.py](run.py) to create the knowledge base including linksets (artists/, historians/, artworks/), three test graphs ([zeri/](data/zeri/), [itatti/](data/itatti/), and [frick/](data/frick/)), harvested attributions (attributions/), and scholars indexes (h_index/)
 * [blazegraph/run.sh](blazegraph/) to launch the triplestore (non-writable mode)
 * [mauth API/webapp](mauth.py) to launch the application and the API. NB. Flask requires gunicorn or similar for production environments

### How to cite this work:
 
 * M. Daquino, Mining Authoritativeness in Art Historical Photo Archives, Studies on the Semantic Web 34. ISBN: 978-1-64368-010-1 (print) | 978-1-64368-011-8 (online). doi:[10.3233/SSW190006](https://doi.org/10.3233/SSW190006)

Corpus analysis and user study results: 
 
 * M. Daquino, A computational analysis of art historical linked data for assessing authoritativeness of attributions, Journal of the Association for Information Science and Technology, 1–13. doi:[10.1002/asi.24301](https://doi.org/10.1002/asi.24301).
 * M. Daquino, mAuth - Corpus analysis, 2019, data retrieved from Figshare, doi:[10.6084/m9.figshare.7411262](https://doi.org/10.6084/m9.figshare.7411262).
 * M. Daquino, mAuth - Results of the User Study, 2019, data retrieved from Figshare, doi:[10.6084/m9.figshare.7409384](https://doi.org/10.6084/m9.figshare.7409384).

Other related publications:

 * M. Daquino and F. Tomasi, Historical Context Ontology (HiCO): a conceptual model for describing context information of cultural heritage objects, in: Research Conference on Metadata and Semantics Research, Springer, 2015, pp. 424–436. doi:[10.1007/978-3-319-24129-6_37](https://doi.org/10.1007/978-3-319-24129-6_37).
 * M. Daquino, F. Mambelli, S. Peroni, F. Tomasi and F. Vitali, Enhancing semantic expressivity in the cultural heritage domain: exposing the Zeri Photo Archive as Linked Open Data, Journal on Computing and Cultural Heritage (JOCCH) 10(4) (2017), 21. doi:[10.1145/3051487](https://doi.org/10.1145/3051487)