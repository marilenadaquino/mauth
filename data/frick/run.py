import data.frick.frick_to_rdf as frick
from pymantic import sparql
import os , datetime

dirpath = os.getcwd()+'/data/frick/'

initial_csv = dirpath+'csv/Frick_Photoarchive_Italian_16_century.csv'

tb_revised_csv = dirpath+'csv/frick_attributions.csv'
attributions_revised = dirpath+'csv/FINAL_frick_attributions.csv'

artists_csv = dirpath+'csv/artists_frick_viaf.csv'
artists_csv_revised = dirpath+'csv/FINAL_artists_frick_viaf.csv'

frick_rdf = dirpath+'rdf/frick_attributions.nq'
linkset_artists_frick = dirpath+'rdf/linkset_artists_frick.nq'
others = dirpath+'rdf/others.nq'


def run():
	""" create frick graph and fill linksets of artists """
	print(str(datetime.datetime.now()))
	# 1. create rdf/frick_attributions.nq
	if os.path.isfile(frick_rdf) == False:
		frick.to_rdf(initial_csv, frick_rdf) 
		print("frick - created rdf/frick_attributions.nq"+str(datetime.datetime.now()))

	# 3. create rdf/linkset_artists_frick.nq
	if os.path.isfile(artists_csv_revised):
		frick.artists_linkset(artists_csv_revised, linkset_artists_frick)
		print("frick - created rdf/linkset_artists_frick.nq"+str(datetime.datetime.now()))
	else:
		# 2. create a csv with artists reconciliation to viaf to be manually revised and renamed artists_csv_revised
		frick.reconcile_artists_to_viaf(artists_csv, frick_rdf) 
		print("frick - created a csv with artists reconciliation to viaf to be manually revised and renamed artists_csv_revised"+str(datetime.datetime.now()))
	
	if os.path.isfile(attributions_revised):
		# 4. add criteria to rdf/frick_attributions.nq
		frick.methodology_frick(frick_rdf, attributions_revised)
		print("frick - added criteria to rdf/frick_attributions.nq"+str(datetime.datetime.now()))
	else:
		# 1.1 create csv/frick_attributions_viaf.csv to be revised and renamed attributions_revised
		frick.export_attr(initial_csv, tb_revised_csv)
		print("frick - created csv/frick_attributions_viaf.csv to be revised and renamed attributions_revised"+str(datetime.datetime.now()))

	# 5. upload all files
	server = sparql.SPARQLServer('http://127.0.0.1:9999/blazegraph/sparql')
	server.update('load <file://'+frick_rdf+'>') 
	server.update('load <file://'+linkset_artists_frick+'>') 
	if os.path.isfile(others):
		server.update('load <file://'+others+'>') 
	print("frick - uploaded all files"+str(datetime.datetime.now()))