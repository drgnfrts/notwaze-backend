import geopandas as gpd
from geopandas import GeoDataFrame
from shapely.geometry import LineString, Point
from app.models.schemas import UserData
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from app.utils.onemap import get_route_OneMapAPI, regenerate_api_key


load_dotenv(".env.production")

def generate_full_route(user_data: UserData, route_points_gdf: GeoDataFrame, nearby_poi_gdf: GeoDataFrame, nearby_amenities_gdf: GeoDataFrame, avoidance_buffer_gdf: GeoDataFrame):
    # Function code as provided

    """ Final route generation function, which calls the OneMap API for all points and adds in amenities as needed.
    
    """

    # Initialise values and variables
    max_route_length = user_data["max_route_length"]
    i = 0
    CUT_OFF = 1000
    # selected_pois, nearby_pois, nearby_amenities = selected_pois.copy(), nearby_pois.copy(), nearby_amenities.copy()
    metadata = {
        "final_points_gdf_list": [route_points_gdf.iloc[[0]]],
        "final_route_geometry": [],
        "route_times": [],
        "route_distances" : [],
        "total_time" : 0,
        "total_distance": 0

    }

    last_amenity_idx, avoidance_check_attempts = -1, 0

    end_point_gdf = route_points_gdf.iloc[[-1]]
    end_point = end_point_gdf.geometry.iloc[0]
    print(f"END POINT")
    print(end_point)
    
    while i < len(route_points_gdf) - 1:

        current_point_gdf = route_points_gdf.iloc[[i]]
        next_point_gdf = route_points_gdf.iloc[[i + 1]]

        current_point = current_point_gdf.geometry.iloc[0]
        next_point = next_point_gdf.geometry.iloc[0]

        print(f"Attempting to find route between {current_point_gdf['NAME'].iloc[0]} and {next_point_gdf['NAME'].iloc[0]}")

        # Get the route geometry from OneMap API
        route_geometry, latest_time, latest_distance = get_route_OneMapAPI(current_point, next_point)

        # Attempt to finish the walking trail and backtrack if needed
        if metadata["total_distance"] + latest_distance >= max_route_length:
            route_geometry, latest_time, latest_distance = get_route_OneMapAPI(current_point, end_point)

            if latest_distance + metadata["total_distance"] < max_route_length:
                metadata = update_metadata(metadata, end_point_gdf, route_geometry, latest_time, latest_distance)
                break

            metadata = handle_backtrack(metadata, end_point_gdf, max_route_length)
            if metadata['total_distance'] == 0:
                return None, None

        # Add an amenity if the distance between points is too long
        # Does not yet check if there is a barrier free route to amenity
        if user_data['amenity'] and latest_distance >= CUT_OFF and (next_point != end_point):
            inserted_amenity, _ = find_nearest_amenity(current_point_gdf, nearby_amenities_gdf)
            route_geometry_to_amenity, time_to_amenity, distance_to_amenity = get_route_OneMapAPI(current_point, inserted_amenity.geometry)
            route_geometry_after_amenity, time_after_amenity, distance_from_amenity = get_route_OneMapAPI(inserted_amenity.geometry, next_point)

            if distance_to_amenity + distance_from_amenity + metadata['total_distance'] < max_route_length:
                print("adding amenity")
                metadata = update_metadata(metadata, inserted_amenity, route_geometry_to_amenity, time_to_amenity, distance_to_amenity)
                metadata = update_metadata(metadata, inserted_amenity, route_geometry_after_amenity, time_after_amenity, distance_from_amenity)
                avoidance_check_attempts = 0
                i += 1
                continue
        
        print("Checking for barrier free")
        # Check whether it hits avoidance buffers and replace the destination if needed
        if user_data['barrier_free'] and avoidance_check_attempts <= 5 and i + 1 != len(route_points_gdf) - 1:
            if route_geometry.intersects(avoidance_buffer_gdf.unary_union):
               route_points_gdf.iloc[[i+1]] = replace_destination(current_point_gdf, next_point_gdf, nearby_poi_gdf, nearby_amenities_gdf)[0]
               avoidance_check_attempts += 1
               continue
                      

        print(f"Route from {current_point_gdf['NAME'].iloc[0]} to {next_point_gdf['NAME'].iloc[0]}")

        # update metrics
        metadata = update_metadata(metadata, next_point_gdf, route_geometry, latest_time, latest_distance)
        avoidance_check_attempts = 0
        i += 1

        print(metadata['final_points_gdf_list'])
        final_gdf = gpd.GeoDataFrame(pd.concat(metadata['final_points_gdf_list'], ignore_index=True)).to_crs("EPSG:4326")
    
    return final_gdf, metadata

def nearest_neighbor_route(start_gdf: GeoDataFrame, points_gdf: GeoDataFrame, end_gdf: GeoDataFrame) -> GeoDataFrame:
    """
    Generates a route by visiting the nearest unvisited point from the current point, starting from the start point(s).
    Uses Euclidean distance in a projected coordinate system (EPSG:3414) for distance calculations.

    Parameters:
    - start_gdf (GeoDataFrame): GeoDataFrame containing the starting point(s).
    - points_gdf (GeoDataFrame): GeoDataFrame containing the points to visit.

    Returns:
    - route_points_gdf (GeoDataFrame): GeoDataFrame of points in the order they are visited in the route.
    """

    # Transform to projected CRS for accurate distance calculations
    projected_crs = 'EPSG:3414'
    start_gdf_proj = start_gdf.copy().to_crs(projected_crs)
    points_gdf_proj = points_gdf.copy().to_crs(projected_crs)
    end_gdf_proj = end_gdf.copy().to_crs(projected_crs)

    # Combine columns from both GeoDataFrames
    all_columns = start_gdf_proj.columns.union(points_gdf_proj.columns)

    # Reindex both GeoDataFrames to have the same columns
    route_points_gdf = start_gdf_proj.reindex(columns=all_columns, fill_value=np.nan)
    remaining_points = points_gdf_proj.reindex(columns=all_columns, fill_value=np.nan)

    while not remaining_points.empty:
        # Nearest neighbours greedy alogirthm
        # Get the last point in the current route
        last_point = route_points_gdf.iloc[-1].geometry

        # Extract coordinates and calculate distances
        remaining_points['distance'] = remaining_points.geometry.apply(lambda x: last_point.distance(x))

        # Take nearest point and append to route, then drop from remaining points
        nearest_idx = remaining_points['distance'].idxmin()
        nearest = remaining_points.loc[[nearest_idx]]
        route_points_gdf = pd.concat([route_points_gdf, nearest], ignore_index=True)
        remaining_points = remaining_points.drop(nearest_idx)

    # Transform back to WGS84 (EPSG:4326) for mapping
    route_points_gdf = pd.concat([route_points_gdf, end_gdf_proj], ignore_index=True)
    route_points_gdf = route_points_gdf.to_crs(epsg=4326)

    return route_points_gdf

def get_last_point(metadata):
    last_item = metadata['final_points_gdf_list'][-1]
    
    if isinstance(last_item, gpd.GeoDataFrame):
        # If it's a GeoDataFrame, use .iloc
        last_point = last_item.geometry.iloc[0]
    elif isinstance(last_item, pd.Series):
        # If it's a Series, access the geometry directly
        last_point = last_item.geometry
    elif isinstance(last_item, Point):
        # If it's a Point object, access coordinates directly
        last_point = last_item
    else:
        print(type(last_item))
        raise ValueError("Unexpected type in final_points_gdf_list")
    
    return last_point




def handle_backtrack(metadata: dict, end_point_gdf: GeoDataFrame, max_route_length: int):

    while metadata["total_distance"] >= max_route_length and len(metadata['final_points_gdf_list']) > 1:
        print("Backtracking by 1. Popping the last point:")
        print(metadata['final_points_gdf_list'][-1])
        metadata['final_points_gdf_list'].pop()
        metadata["final_route_geometry"].pop()
        metadata["total_time"] -= metadata["route_times"].pop()
        metadata["total_distance"] -= metadata["route_distances"].pop()

        last_point = get_last_point(metadata)
        end_point = end_point_gdf.geometry.iloc[0]
        print("------")
        print(f"last_point - {type(last_point)}")
        print(last_point)
        print(f"end_point - {type(last_point)}")
        print(end_point)

        route_geometry_to_end, time_to_end, distance_to_end = get_route_OneMapAPI(last_point, end_point)
        if metadata["total_distance"] + distance_to_end < max_route_length:
            metadata = update_metadata(metadata, end_point_gdf, route_geometry_to_end, time_to_end, distance_to_end)

    return metadata
        



def replace_destination(current_point_gdf, next_point_gdf, nearby_poi, nearby_amenity):

    print(f"Intersection Found. Route from {current_point_gdf['NAME'].iloc[0]} to {next_point_gdf['NAME'].iloc[0]} intersects with avoidance area. Reselecting route point.")

    # if the next point is an amenity
    next_point_name = next_point_gdf['NAME'].iloc[0]
    next_point_geometry = next_point_gdf.geometry.iloc[0]

    if next_point_name in ['Toilet', 'Drinking Water']:
        remaining_nearby_amenity = nearby_amenity[nearby_amenity['geometry'] != next_point_geometry]
        new_next_point_gdf = find_nearest_amenity(next_point_geometry, remaining_nearby_amenity)
    else:
        cluster_num = next_point_gdf['cluster'].iloc[0]
        remaining_nearby_poi = nearby_poi[nearby_poi['geometry'] != next_point_geometry]
        cluster_points = remaining_nearby_poi[remaining_nearby_poi['cluster'] == cluster_num]

        if len(cluster_points) >= 1:
            new_next_point_gdf = cluster_points.sample()
        else:
           new_next_point_gdf = remaining_nearby_poi.sample()

    return new_next_point_gdf

def update_metadata(metadata: dict, point_gdf: GeoDataFrame, route_geometry: LineString, latest_time, latest_distance):
    metadata['final_points_gdf_list'].append(point_gdf)
    metadata["final_route_geometry"].append(route_geometry)
    metadata["route_times"].append(latest_time)
    metadata["route_distances"].append(latest_distance)
    metadata["total_time"] += latest_time
    metadata["total_distance"] += latest_distance

    return metadata


def find_nearest_amenity(point_gdf, amenity_gdf):
  """
  Find the nearest amenity to a given point.
  """
  # Transform CRS to projected CRS to ensure accurate calculation
  point_gdf = point_gdf.to_crs('EPSG:3414')

  amenity_gdf = amenity_gdf.to_crs('EPSG:3414')

  print(point_gdf.crs, amenity_gdf.crs)

  # Find distance between point and amenity in amenity_gdf
  amenity_gdf['distance'] = amenity_gdf.geometry.apply(lambda x: point_gdf.geometry.distance(x).min())
  print(amenity_gdf)
  # Find the minimum distance and the corresponding nearest amenity
  amenity_gdf = amenity_gdf.to_crs('EPSG:4326')
  point_gdf = point_gdf.to_crs('EPSG:4326')
  nearest_amenity = amenity_gdf.loc[amenity_gdf['distance'].idxmin()]
  print(nearest_amenity)
  print(nearest_amenity.index)
  distance = nearest_amenity['distance']

  # Drop distance column
  print('reached here')
  amenity_gdf = amenity_gdf.drop('distance', axis=1)
  

  print(nearest_amenity)
  return nearest_amenity, distance