#!/usr/bin/env python3
import json
from planet import api
from planet.api import downloader, filters
import csv
import os
from pprint import pprint
from osgeo import ogr
import shutil


ITEMLIMIT=1
DOWNLOAD_BASE_DIR="."
DEBUG=False
TARGETSRID=32635
BANDS=['PSScene4Band']
CLOUDCOVERLT=0.01

try:
	from osgeo import ogr, osr, gdal
except:
	sys.exit('ERROR: cannot find GDAL/OGR modules')

# https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-buffer
def polyToJSONFile(poly):
	outDriver = ogr.GetDriverByName('GeoJSON')
	outDataSource = outDriver.CreateDataSource('test.geojson')
	outLayer = outDataSource.CreateLayer('test.geojson', geom_type=ogr.wkbPolygon )

	# Get the output Layer's Feature Definition
	featureDefn = outLayer.GetLayerDefn()

	# create a new feature
	outFeature = ogr.Feature(featureDefn)

	# Set new geometry
	outFeature.SetGeometry(poly)

	# Add new feature to output Layer
	outLayer.CreateFeature(outFeature)

	# dereference the feature
	outFeature = None

	# Save and close DataSources
	outDataSource = None		

def createBuffer(inputPoint, bufferDist):
	# inputds = ogr.Open(inputfn)
	# inputlyr = inputds.GetLayer()

	# shpdriver = ogr.GetDriverByName('ESRI Shapefile')
	# if os.path.exists(outputBufferfn):
	#     shpdriver.DeleteDataSource(outputBufferfn)
	# outputBufferds = shpdriver.CreateDataSource(outputBufferfn)
	# bufferlyr = outputBufferds.CreateLayer(outputBufferfn, geom_type=ogr.wkbPolygon)
	# featureDefn = bufferlyr.GetLayerDefn()

   
	geomBuffer = inputPoint.Buffer(bufferDist)

	env = geomBuffer.GetEnvelope()

	minX = env[0]
	minY = env[2]
	maxX = env[1]
	maxY = env[3]

	coord = [(minX, minY),
			 (minX, maxY),
			 (maxX, maxY),
			 (maxX, minY),
			 (minX, minY)
			]

	envGeom = ogr.Geometry(ogr.wkbPolygon)
	ring = ogr.Geometry(ogr.wkbLinearRing)

	for x,y in coord:
		ring.AddPoint_2D(x,y)
	envGeom.AddGeometry(ring)    
	return envGeom

# SRID 32635
source = osr.SpatialReference()
source.ImportFromEPSG(32635)

target = osr.SpatialReference()
target.ImportFromEPSG(4326)
transform = osr.CoordinateTransformation(source, target)

with open("secret.json") as secret:
	settings=json.load(secret)

print("Planet API Key: {}".format(settings['PlanetKey']))

client = api.ClientV1(api_key=settings['PlanetKey'])

def warpToFile(targetDir, identifier, filename, poly, asset, targetSRID):
	polyToJSONFile(poly)
	pprint(asset['location'])
	vsicurl_url="/vsicurl/{}".format(asset['location'])
	output_file="{}/{}_{}_SRID{}_subarea.tif".format(targetDir,identifier,filename,targetSRID)
	gdal.Warp(output_file, vsicurl_url, dstSRS = "EPSG:{}".format(targetSRID), cutlineDSName = 'test.geojson', cropToCutline = True)

with open('ALL_MapMounds.csv', newline='') as csvfile:
	moundsreader = csv.DictReader(csvfile)

	for row in moundsreader:
		#pprint(row)
		targetDir = "{0}/{1}".format(DOWNLOAD_BASE_DIR, row['identifier'])
		print("Trying {0}".format(targetDir))
		if DEBUG or not os.path.isdir(targetDir):


			point = ogr.CreateGeometryFromWkt(row["geospatialcolumn"])
			#print(point.ExportToWkt())
			poly = createBuffer(point, 150)	
			#print(poly.ExportToWkt())	
			point.Transform(transform)
			poly.Transform(transform)
			print("\t"+point.ExportToWkt())		
			#print(poly.ExportToJson())
			#print(poly.ExportToWkt())


			


			polyJSON = json.loads(poly.ExportToJson())
			aoi = polyJSON
			#pprint(aoi)
			# build a filter for the AOI
			query = filters.and_filter(
				filters.geom_filter(aoi),
				filters.range_filter('cloud_cover', lt=CLOUDCOVERLT),
			)

			# we are requesting PlanetScope 4 Band imagery
			item_types = BANDS
			request = api.filters.build_search_request(query, item_types)
			# this will cause an exception if there are any API related errors
			results = client.quick_search(request)

			# items_iter returns an iterator over API response pages
			dl = downloader.create(client)
			dl.on_complete = lambda *a: completed.append(a)

			for item in results.items_iter(limit=ITEMLIMIT):
				perms = item['_permissions']
				#pprint(perms)
				if ("assets.visual:download" in perms and "assets.visual_xml:download" in perms):
					sceneType=["visual", "visual_xml"]
				elif ("assets.analytic:download" in perms and "assets.analytic_xml:download" in perms):
					sceneType=["analytic", "analytic_xml"]				
				elif ("assets.basic_analytic:download" in perms and "assets.basic_analytic:download" in perms):
					sceneType=["basic_analytic", "basic_analytic_xml"]	
				else:
					pprint(row)
					pprint(item)
					print("ERROR DOWNLOADING - No image available {}".format(item['id']))
					continue;
				os.makedirs(targetDir, exist_ok=True)

				with open('{0}/{1}.json'.format(targetDir, row['identifier']),'w') as mound:
					json.dump(row, mound)
				print("\tDownloading {0} with type: {1}".format(item['id'], sceneType))
				#https://github.com/planetlabs/planet-client-python/issues/101#issuecomment-296319842
				assets = client.get_assets(item).get()
				activation = [client.activate(assets[sceneType[0]]), client.activate(assets[sceneType[1]])]
				
				# wait for activation
				assets = client.get_assets(item).get()
				pprint(assets)
				callback = api.write_to_file(directory=targetDir)


				#body = client.download(assets[sceneType[0]], callback=callback)
				bodyxml = client.download(assets[sceneType[1]], callback=callback)

				#body.await()
				bodyxml.await()
				#def warpToFile(targetDir, identifier, filename, poly, asset,targetSRID):
				warpToFile(targetDir, row['identifier'], "{}_{}".format(item['id'],sceneType[0]), poly, assets[sceneType[0]], TARGETSRID)


		else:
			RED='\033[0;31m'
			print("\t {1} !! {0} already exists! Skipping!".format(targetDir, RED))

		if debug:	
			break