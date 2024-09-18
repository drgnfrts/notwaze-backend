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
    activity_line = activity_line.copy().to_crs(epsg=3414)
    search_buffer = activity_line.buffer(search_radius, resolution = 16)
    search_gdf = gpd.GeoDataFrame(geometry=search_buffer, crs='EPSG:3414')

    return search_gdf



def search_nearby_items(search_gdf: GeoDataFrame, item_gdf: GeoDataFrame, avoidance: bool):
    """ Search for nearby POIs, amenities and obstacles in a given search radius
    
    Args:
     - activity_line (GeoDataFrame): GDF of the Euclidean line between the Start/End points, which showcases where the buffer should extend from
     - search_radius (int): Search radius buffer distance around activity line
     - item_gdf (GeoDataframe): GDF passed in to conduct the search on

    """
    intersecting_item_gdf = gpd.sjoin(item_gdf, search_gdf, how='inner', predicate='intersects')
    intersecting_item_gdf.drop(columns=['index_right'], inplace=True)

    # Add a distance attribute (shows distance of nearby items)

    if not avoidance:
        return intersecting_item_gdf

    avoidance_buffer = intersecting_item_gdf.buffer(10, resolution=16)
    unified_geometry = unary_union(avoidance_buffer)
    return gpd.GeoDataFrame(geometry=[unified_geometry], crs='EPSG:3414')


def find_clusters(item_gdf: GeoDataFrame, num_clusters: int):
    """ Generates clusters of points if number of items in GeoDataFrame is larger than num_clusters.

    Args: 
    - item_gdf (GeoDataFrame): GDF to perform clustering on
    - num_clusters (int): Number of clusters to be generated
    
    """
    if len(item_gdf) <= num_clusters:
        item_gdf['cluster'] = 1 # set all items into same cluster
        return item_gdf, item_gdf

    # Create a copy and transform crs
    #item_gdf = item_gdf.copy().to_crs(epsg=3414)

    # Perform K means on coordinates
    print(item_gdf)
    coords = item_gdf.geometry.apply(lambda geom: [geom.x, geom.y]).tolist()
    print(coords)
    kmeans = KMeans(n_clusters=num_clusters, n_init=10).fit(coords)
    item_gdf['cluster'] = kmeans.labels_

    # Randomly select one POI from each cluster
    selected_items = item_gdf.groupby('cluster').apply(lambda x: x.sample(1)).reset_index(drop=True)
    print(selected_items)
    selected_items = selected_items.to_crs(epsg=4326)
    return selected_items


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
            gdf = gpd.read_file(get_geojson(key, request))
            gdf = gdf.to_crs('EPSG:3414')  # Reproject to EPSG:3414
            gdfs.append(gdf)
        except:
            print(f"Warning: {key} not found in memory.")
            pass

    for item in gdfs:
        print(type(item))

    concatenated_gdf = pd.concat(gdfs, ignore_index=True)
    concatenated_gdf.crs = 'EPSG:3414'
    return concatenated_gdf


