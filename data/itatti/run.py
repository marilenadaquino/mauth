import data.itatti.itatti_to_rdf as itatti
from pymantic import sparql
import os , datetime

dirpath = os.getcwd()+'/data/itatti/'

initial_csv = dirpath+'csv/ss_assets_811_130578.csv'

artists_csv = dirpath+'csv/artists_itatti_viaf.csv'
artists_csv_revised = dirpath+'csv/FINAL_artists_itatti_viaf.csv'

zeri_data = dirpath+'other/fzeri_OA_2015_11_26_175351.xml'
pastec_data = dirpath+'other/images_zeri_itatti_matched.csv'

historians_viaf = dirpath+'csv/historians_itatti_viaf.csv'
historians_revised = dirpath+'csv/FINAL_historians_itatti_viaf.csv'

itatti_rdf = dirpath+'rdf/itatti_attributions.nq'
linkset_artists_itatti = dirpath+'rdf/linkset_artists_itatti.nq'
linkset_itatti_zeri_artworks = dirpath+'rdf/linkset_itatti_zeri_artworks.nq'
linkset_arthistorians_itatti = dirpath+'rdf/linkset_arthistorians_itatti.nq'

def run():
	""" create itatti graph and fill 3 linksets artworks, artists, historians """
	print(str(datetime.datetime.now()))
	# 1. create rdf/itatti_attributions.nq
	if os.path.isfile(itatti_rdf) == False:
		itatti.itatti_to_rdf(initial_csv,itatti_rdf)
		print("itatti - created rdf/itatti_attributions.nq"+str(datetime.datetime.now()))
	
	# 3. create rdf/linkset_artists_itatti.nq
	if os.path.isfile(artists_csv_revised):
		itatti.artists_linkset(artists_csv_revised, linkset_artists_itatti)
		print("itatti - created rdf/linkset_artists_itatti.nq"+str(datetime.datetime.now()))
	else:
		# 2. create a csv with artists reconciliation to viaf to be manually revised and renamed artists_csv_revised
		itatti.reconcile_artists_to_viaf(artists_csv, itatti_rdf) 
		print("itatti - created a csv with artists reconciliation to viaf to be manually revised and renamed artists_csv_revised"+str(datetime.datetime.now()))
	
	if os.path.isfile(linkset_itatti_zeri_artworks) == False:
		# 4. create rdf/linkset_itatti_zeri_artworks.nq
		itatti.reconcile_itatti_artworks_to_zeri(pastec_data,zeri_data,itatti_rdf,linkset_itatti_zeri_artworks)
		print("itatti - created rdf/linkset_itatti_zeri_artworks.nq"+str(datetime.datetime.now()))
	
	# 5. add criteria to rdf/itatti_attributions.nq
	itatti.methodology_itatti(itatti_rdf, initial_csv)
	print("itatti - added criteria to rdf/itatti_attributions.nq"+str(datetime.datetime.now()))

	# 7. create rdf/linkset_arthistorians_itatti.nq
	if os.path.isfile(historians_revised):
		itatti.historians_linkset(itatti_rdf,historians_revised,linkset_arthistorians_itatti)
		print("itatti - created rdf/linkset_arthistorians_itatti.nq"+str(datetime.datetime.now()))

	else:
		# 6. create csv/historians_itatti_viaf.csv to be manually revised and renamed historians_revised
		itatti.reconcile_historians_to_viaf(itatti_rdf, historians_viaf)
		print("itatti - created csv/historians_itatti_viaf.csv to be manually revised and renamed historians_revised"+str(datetime.datetime.now()))
	
	# 8. upload all files
	server = sparql.SPARQLServer('http://127.0.0.1:9999/blazegraph/sparql')
	server.update('load <file://'+itatti_rdf+'>') 
	server.update('load <file://'+linkset_itatti_zeri_artworks+'>') 
	server.update('load <file://'+linkset_arthistorians_itatti+'>') 
	server.update('load <file://'+linkset_artists_itatti+'>') 
	print("itatti - uploaded all files"+str(datetime.datetime.now()))