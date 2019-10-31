import data.zeri.zeri_to_rdf as zeri
from pymantic import sparql
import os , sys , datetime

dirpath = os.getcwd()+'/data/zeri/'

initial_xml = dirpath+'xml/fzeri_OA_2015_11_26_175351.xml'
authority = dirpath+'xml/Authority-Artist-updated.xml'

historians_revised = dirpath+'csv/FINAL_critics_all_reconciled.csv'

sandrart = dirpath+'rdf/FINAL_artists_sandrart_reconciled.rdf'
zeri_rdf = dirpath+'rdf/zeri_attributions.nq'
linkset_artists_zeri = dirpath+'rdf/linkset_artists_zeri.nq'
linkset_arthistorians_zeri = dirpath+'rdf/linkset_arthistorians_zeri.nq'

def run():
	""" create zeri graph and fill 3 linksets artworks, artists, historians """
	print(str(datetime.datetime.now()))
	# 1. create rdf/zeri_attributions.nq
	if os.path.isfile(zeri_rdf) == False:
		zeri.zeri_to_rdf(initial_xml,zeri_rdf)
		print("zeri - created rdf/zeri_attributions.nq"+str(datetime.datetime.now()))
	
	# 2. create rdf/linkset_artists_zeri.nq
	if os.path.isfile(linkset_artists_zeri) == False:
		zeri.artists_linkset(authority,sandrart,linkset_artists_zeri)
		print("zeri - created rdf/linkset_artists_zeri.nq"+str(datetime.datetime.now()))

	# 3. create artwork linksets
	zeri.reconcile_zeri_artworks_to_all()
	print("zeri - created artwork linksets"+str(datetime.datetime.now()))

	if os.path.isfile(linkset_arthistorians_zeri) == False:
		# 4. create rdf/linkset_arthistorians_zeri.nq
		zeri.historians_linkset(historians_revised,linkset_arthistorians_zeri)
		print("zeri - creates rdf/linkset_arthistorians_zeri.nq"+str(datetime.datetime.now()))	

	# upload every file in rdf/ (including vocabulary criteria)
	server = sparql.SPARQLServer('http://127.0.0.1:9999/blazegraph/sparql')
	for filename in os.listdir(dirpath+'rdf/'):
		if filename.endswith(".nq"):
			server.update('load <file://'+dirpath+'rdf/'+filename+'>')
	print("zeri - uploaded every file in rdf/ (including vocabulary criteria)"+str(datetime.datetime.now()))