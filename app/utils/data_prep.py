import geopandas as gpd
from geopandas import GeoDataFrame
import pandas as pd
from shapely.ops import unary_union
from sklearn.cluster import KMeans
from fastapi import Request
from app.services import get_geojson

def generate_search_buffer(activity_line: GeoDataFrame, search_radius: int):
    """
    """

    activity_gdf_sg = activity_line.copy().to_crs(epsg=3414)
    search_buffer = activity_gdf_sg.buffer(search_radius, resolution = 16)
    search_gdf = gpd.GeoDataFrame(geometry=search_buffer, crs='EPSG:3414')

    return activity_gdf_sg, search_gdf



def search_nearby_items(activity_gdf_sg: GeoDataFrame, search_gdf: GeoDataFrame, item_gdf: GeoDataFrame, avoidance: bool):
    """ Search for nearby POIs, amenities and obstacles in a given search radius
    
    Args:
     - activity_line (GeoDataFrame): GDF of the Euclidean line between the Start/End points, which showcases where the buffer should extend from
     - search_radius (int): Search radius buffer distance around activity line
     - item_gdf (GeoDataframe): GDF passed in to conduct the search on

    """
    # Transform CRS to run the search in more accurate EPSG:3414
    item_gdf_sg = item_gdf.copy().to_crs(epsg=3414)

    # Add a distance attribute (shows distance of nearby items)
    intersecting_item = gpd.sjoin(item_gdf_sg, search_gdf, how='inner', predicate='intersects')
    intersecting_item['distance'] = intersecting_item.geometry.apply(lambda x: activity_gdf_sg.geometry.distance(x).min())
    intersecting_item = intersecting_item.sort_values(by='distance', ascending=True)

    if not avoidance:
        return intersecting_item.to_crs(epsg=4326)

    avoidance_buffer = intersecting_item.buffer(10, resolution=16)
    unified_geometry = unary_union(avoidance_buffer)
    return gpd.GeoDataFrame(geometry=[unified_geometry], crs='EPSG:3414').to_crs(epsg=4326)


    

def generate_avoidance_zones(activity_gdf_sg: GeoDataFrame, search_gdf: GeoDataFrame, avoidance_gdf: GeoDataFrame):
    # Generate buffers and unify geometries for avoidance zones
    near_avoidance = near_avoidance.copy().to_crs(epsg=3414)
    avoidance_buffer = near_avoidance.buffer(10, resolution=16)
    unified_geometry = unary_union(avoidance_buffer)
    avoidance_buffer_gdf = gpd.GeoDataFrame(geometry=[unified_geometry], crs='EPSG:3414')
    return avoidance_buffer_gdf.to_crs(epsg=4326)



def find_clusters(item_gdf, num_clusters):
    # Function code as provided
    pass

# def find_clusters(item_gdf, num_clusters):
#   """
#   Finds clusters of items in a GeoDataFrame if number of items in GeoDataFrame is larger than num_clusters.
#   Then, randomly select one item from each cluster.
#   Output: GeoDataFrame of items (one from each cluster) in crs WGS84 (EPSG:4326).
#   """
#   # return original GeoDataFrame if number of items too small
#   if len(item_gdf) <= num_clusters:
#     item_gdf['cluster'] = 1 # set all items into same cluster
#     return item_gdf, item_gdf

#   # Create a copy and transform crs
#   item_gdf = item_gdf.copy().to_crs(epsg=3414)

#   # Perform K means on coordinates
#   coords = item_gdf.geometry.apply(lambda geom: [geom.x, geom.y]).tolist()
#   kmeans = KMeans(n_clusters=num_clusters, n_init=10).fit(coords)
#   item_gdf['cluster'] = kmeans.labels_

#   # Randomly select one POI from each cluster
#   selected_items = item_gdf.groupby('cluster').apply(lambda x: x.sample(1)).reset_index(drop=True)

#   # Transform back to WGS84 (EPSG:4326) before returning
#   item_gdf = item_gdf.to_crs(epsg=4326)
#   selected_items = selected_items.to_crs(epsg=4326)

#   return selected_items, item_gdf

def concat_poi_gdf(file_keys: list, request: Request):
    """ Concatenates GeoDataFrames for the given file keys using the loaded geojson_files.

    Args:
    - file_keys (list): List of keys to call and pull the GeoJSON from application state

    Returns:
    - concatenated_gdf (GeoDataFrame): A combined GDF of the multiple GDFs pulled and passed in
    """
    if file_keys == []:
        return None
    
    gdfs = []
    for key in file_keys:
        try:
            gdfs.append(gpd.read_file(get_geojson(key, request)))
        except:
            print(f"Warning: {key} not found in memory.")
            pass

    for item in gdfs:
        print(type(item))

    concatenated_gdf = pd.concat(gdfs, ignore_index=True)
    concatenated_gdf.crs = 'EPSG:4326'
    return concatenated_gdf


