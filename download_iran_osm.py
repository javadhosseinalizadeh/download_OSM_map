import requests
import json
import os
import time

def download_osm_data(bbox):
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass query to download all nodes, ways, and relations within a bounding box (Iran)
    query = f"""
    [out:json];
    (
      node({bbox});
      way({bbox});
      relation({bbox});
    );
    out body geom;
    """
    
    max_retries = 3
    retry_delay = 30  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(overpass_url, data={"data": query}, timeout=300)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries}: Failed to download OSM data. Error: {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"All retries failed. Last error: {str(e)}")
            time.sleep(retry_delay)
    
    return None

def osm_to_geojson(data):
    # Convert Overpass API JSON to GeoJSON format with nodes, ways, and relations
    features = []
    
    # Parse nodes
    for element in data['elements']:
        if element['type'] == 'node':
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [element['lon'], element['lat']]
                },
                'properties': element.get('tags', {})
            }
            features.append(feature)
        
        # Parse ways
        elif element['type'] == 'way' and 'geometry' in element:
            coordinates = [[node['lon'], node['lat']] for node in element['geometry']]
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinates
                },
                'properties': element.get('tags', {})
            }
            features.append(feature)

        # Parse relations (if they have geometry)
        elif element['type'] == 'relation' and 'members' in element:
            members = element['members']
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'GeometryCollection',
                    'geometries': []
                },
                'properties': element.get('tags', {})
            }
            for member in members:
                if member['type'] == 'way' and 'geometry' in member:
                    coordinates = [[node['lon'], node['lat']] for node in member['geometry']]
                    geometry = {
                        'type': 'LineString',
                        'coordinates': coordinates
                    }
                    feature['geometry']['geometries'].append(geometry)
            features.append(feature)

    geojson_data = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return json.dumps(geojson_data)

def simplify_geojson(geojson_data, tolerance=0.001):
    """
    Simplifies GeoJSON geometries. This function applies basic Douglas-Peucker simplification.
    """
    from shapely.geometry import shape, mapping
    from shapely.ops import transform
    import pyproj

    simplified_features = []

    for feature in geojson_data['features']:
        geometry = feature['geometry']
        if geometry['type'] == 'LineString':
            line = shape(geometry)
            simplified = line.simplify(tolerance)
            feature['geometry'] = mapping(simplified)
        elif geometry['type'] == 'Point':
            # Points don't need simplification
            pass
        simplified_features.append(feature)

    geojson_data['features'] = simplified_features
    return geojson_data

def main():
    # Bounding box for Iran (South-West and North-East corners)
    bbox = "24.396308,44.031311,39.771722,63.333557"
    
    try:
        iran_data = download_osm_data(bbox)
        
        if iran_data and 'elements' in iran_data:
            iran_geojson = json.loads(osm_to_geojson(iran_data))
            
            # Save the full GeoJSON data
            with open('iran_map.geojson', 'w') as f:
                json.dump(iran_geojson, f)
            
            print("GeoJSON file saved.")

            # Simplify the GeoJSON
            simplified_geojson = simplify_geojson(iran_geojson, tolerance=0.001)
            
            # Save the simplified GeoJSON
            with open('iran_simplified.geojson', 'w') as f:
                json.dump(simplified_geojson, f)
            
            print(f"Simplified GeoJSON file saved at: {os.path.abspath('iran_simplified.geojson')}")
        else:
            print("Invalid OSM data received.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
