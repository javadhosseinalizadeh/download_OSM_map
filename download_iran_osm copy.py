import requests
import json
from osmium import SimpleHandler, Way, Relation
from subprocess import Popen, PIPE
import os

class HighwayHandler(SimpleHandler):
    def __init__(self):
        SimpleHandler.__init__(self)
        self.ways = []
        self.relations = []

    def way(self, w):
        if 'highway' in w.tags:
            self.ways.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[n.lon, n.lat] for n in w.nodes]
                },
                'properties': dict(w.tags)
            })

    def relation(self, r):
        if 'highway' in r.tags:
            self.relations.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[n.lon, n.lat] for n in r.members]
                },
                'properties': dict(r.tags)
            })

def download_osm_data(country_name):
    overpass_url = "http://overpass-api.eu/api/interpreter"
    
    query = f"""
    [out:json];
    area["name"="{country_name}"]["admin_level"="2"]->.searchArea;
    (
      way(area.searchArea)["highway"];
      relation(area.searchArea)["highway"];
    );
    out body;
    """
    
    response = requests.post(overpass_url, data={"data": query})
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to download OSM data. Status code: {response.status_code}")

def osm_to_geojson(data):
    handler = HighwayHandler()
    handler.apply_file(data)
    
    features = handler.ways + handler.relations
    
    geojson_data = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return json.dumps(geojson_data)

def simplify_geojson(input_path, output_path, tolerance=0.001):
    command = f"geojson-vt --simplify-tolerance {tolerance} {input_path} > {output_path}"
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    _, error = process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"Simplification failed: {error.decode()}")

def geojson_to_topojson(input_path, output_path):
    command = f"topojson --id-property id -p {input_path} > {output_path}"
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    _, error = process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"TopoJSON conversion failed: {error.decode()}")

def main():
    country_name = "Iran"
    
    # Download OSM data
    iran_data = download_osm_data(country_name)
    
    # Convert OSM data to GeoJSON
    iran_geojson = osm_to_geojson(iran_data)
    
    # Save GeoJSON to file
    with open('iran_highways.geojson', 'w') as f:
        f.write(iran_geojson)
    
    print("GeoJSON file saved.")
    
    # Simplify GeoJSON
    simplify_geojson('iran_highways.geojson', 'iran_simplified.geojson')
    print("GeoJSON simplified.")
    
    # Convert to TopoJSON
    geojson_to_topojson('iran_simplified.geojson', 'iran_highways.topojson')
    print("TopoJSON file created.")

if __name__ == "__main__":
    main()
