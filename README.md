# PlanetAPI

Todo:

1. Iterate over a list of lat-long from text file. 
2. Authentiate to planetAPI using ???.
3. Download maps via lat-long centerpoint of radius 150m.


[PlanetQuickstart](https://www.planet.com/docs/api-quickstart-examples/)


Objective:

1. verification of symbols in old maps
2.  verification of mound existence and detectability in sat images
3. monitoring of standing mounds' condition in timeseries of sat images

Here is a csv with some ~8000 points representing perhaps ~5000 burial mounds in SE Bulgaria.

These points have been digitized via the FAIMS Digitisation module from topomaps where some 6 symbols are used to indicate potential mounds. These symbols are in column P. Hairy brown symbols have the highest likelihood of being mounds. Other symbols combine a variety of potentially mounded or elevated features.

The task here is to extract a 200x200m tile out of satellite image centered on the lat/long (columns J, K) for each record in the table and label it by record identifier (column B) and then with the help of PACE student workflorce test tasks 1-3 where feasible (==the error of the map is smaller than the 200x200 tilesize and we actually hit the mound).

# Setup

* sudo apt update && sudo apt install gdal-bin libgdal-dev python3-gdal
* get API key https://planet.com/account
