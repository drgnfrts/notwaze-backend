import geopandas as gpd
import pandas as pd
import json
from shapely.geometry import LineString, Point, Polygon, MultiLineString, mapping
from shapely.ops import unary_union
from dotenv import load_dotenv
import folium
import polyline
import requests
import random
import time
from sklearn.cluster import KMeans
from fastapi import HTTPException, Request

# Load environment variables from .env file
load_dotenv()

# def generate_route(request: Request):
#    geojsons = request.app.state.geojson
#    user_data = request.app.state.user_data
#    user_gdf = gpd.GeoDataFrame([{'geometry': Point(user_data['user_location'])}], crs="EPSG:4326")
#    pass

# def concat_poi_gdf(file_keys: list):
#    for key in file_keys:
#       # logic to seperate into poi types
#       pass
#     # logic to concat the poi files
      

# """# User Input"""

# # Location of SCIS1 (User Start Point)
# user_longitude = 103.84959994451148
# user_latitude = 1.2973812128576168

# # # # Location of Clarke Quay (User End Point)
# # end_longitude = 103.84509297803696
# # end_latitude = 1.2888419050771158

# # User Preferences
# search_radius = 500 # metre
# num_POIs = 5
# max_route_length = 3000 # metres

# """
# The pois_input cannot be empty, must have at least 1 set of data
# Both amenity_input and avoidance_input are optional.
# If they are empty, they will be replaced by an empty GeoDataFrame.

# Types of POIs: museum_gdf,monument_gdf,historicSite_gdf,park_gdf
# Types of Amenities: toilet_gdf, drinkingWater_gdf
# Types of Avoidance: stairs_gdf

# e.g.
# You can have:
# pois_input = [park_gdf]
# amenity_input = []
# avoidance_input = []
# """

# # User Preferences
# pois_input = [museum_gdf,monument_gdf,historicSite_gdf,park_gdf]
# amenity_input = []
# avoidance_input = []

# # Convert input into shapely objects
# user_location = Point((user_longitude, user_latitude))
# end_location = Point((end_longitude, end_latitude))

# def create_gdf(point, name, type_):
#     return gpd.GeoDataFrame([{'geometry': point, 'NAME': name, 'TYPE': type_}], crs="EPSG:4326")

# # Create GeoDataFrames
# user_gdf = create_gdf(user_location, 'User', 'User')

# if user_location != end_location:
#     end_gdf = create_gdf(end_location, 'End', 'End')
#     activity_line_gdf = gpd.GeoDataFrame(geometry=[LineString([user_location, end_location])], crs="EPSG:4326")
# else:
#     end_gdf = user_gdf
#     activity_line_gdf = user_gdf

# # Create an empty GeoDataFrame
# empty_gdf = gpd.GeoDataFrame(columns=['NAME', 'TYPE', 'geometry'], geometry='geometry', crs='EPSG:4326')

# # Check if inputs are empty and set to empty_gdf if they are
# pois_gdf = pd.concat(pois_input, ignore_index=True) if pois_input else empty_gdf
# amenity_gdf = pd.concat(amenity_input, ignore_index=True) if amenity_input else empty_gdf
# avoidance_gdf = pd.concat(avoidance_input, ignore_index=True) if avoidance_input else empty_gdf

# pois_gdf.set_crs('EPSG:4326', inplace=True)
# amenity_gdf.set_crs('EPSG:4326', inplace=True)
# avoidance_gdf.set_crs('EPSG:4326', inplace=True)





"""# Data Preparation

## Functions For Data Preparation
"""

def search_nearby_items(activity_line, search_buffer_gdf, item_gdf):
  # Returns a GeoDataFrame of items within search_buffer

  # Find intersection
  intersecting_item_gdf = gpd.sjoin(item_gdf, search_buffer_gdf, how='inner', predicate='intersects')
  intersecting_item_gdf.drop(columns=['index_right'], inplace=True)

  return intersecting_item_gdf

def find_clusters(item_gdf, num_clusters):

  # return original GeoDataFrame if number of items <= number of clusters set by user
  if len(item_gdf) <= num_clusters:
    item_gdf['cluster'] = 1 # set all items into same cluster
    return item_gdf

  # Perform K means clustering using coordinates
  coords = item_gdf.geometry.apply(lambda geom: [geom.x, geom.y]).tolist()
  kmeans = KMeans(n_clusters=num_clusters, n_init=10).fit(coords)
  item_gdf['cluster'] = kmeans.labels_

  # Randomly select one POI from each cluster
  selected_items = item_gdf.groupby('cluster').apply(lambda x: x.sample(1)).reset_index(drop=True)

  return selected_items

"""## Execution"""

# activity_line_gdf.to_crs(epsg=3414, inplace = True)
# pois_gdf.to_crs(epsg=3414, inplace = True)
# amenity_gdf.to_crs(epsg=3414, inplace = True)
# avoidance_gdf.to_crs(epsg=3414, inplace = True)

# Create a search area around activity line
search_buffer = activity_line_gdf.buffer(search_radius, resolution=16)
search_buffer_gdf = gpd.GeoDataFrame(geometry=search_buffer, crs='EPSG:3414')

near_pois = search_nearby_items(activity_line_gdf,search_buffer_gdf,pois_gdf)
near_amenities = search_nearby_items(activity_line_gdf,search_buffer_gdf,amenity_gdf)
near_avoidance = search_nearby_items(activity_line_gdf,search_buffer_gdf,avoidance_gdf)

# Create avoidance zone around all avoidance item (i.e. buffer around every stairs, radius = 10m)
avoidance_buffer = unary_union(near_avoidance.buffer(10, resolution=16))
avoidance_buffer_gdf = gpd.GeoDataFrame(geometry=[avoidance_buffer], crs='EPSG:3414')

# Used For Mapping
search_buffer_gdf.to_crs(epsg=4326, inplace = True)

# Used For Route Generation
user_gdf.to_crs(epsg=4326, inplace = True)
end_gdf.to_crs(epsg=4326, inplace = True)
near_pois.to_crs(epsg=4326, inplace = True)
near_amenities.to_crs(epsg=4326, inplace = True)
avoidance_buffer_gdf.to_crs(epsg=4326, inplace = True)



##############################################
##############################################
"""# Route Generation

# ## Functions to Generate Routes
# """


def nearest_neighbor_route(start_gdf, points_gdf):
  """
  Generate a route by iteratively finding the nearest neighbor.
  """
  # Create an GeoDataFrame to store the route points (starting from start point)
  route_points_gdf = start_gdf.copy()

  while not points_gdf.empty:

    current_point = route_points_gdf.iloc[-1].geometry

    # Calculate nearest point from current point
    points_gdf['distance'] = points_gdf.geometry.apply(lambda x: current_point.distance(x))
    nearest_idx = points_gdf['distance'].idxmin()
    nearest = points_gdf.loc[[nearest_idx]]

    # Concatenate the nearest point to the route
    route_points_gdf = pd.concat([route_points_gdf, nearest], ignore_index=True)
    points_gdf = points_gdf.drop(nearest_idx)

  return route_points_gdf



def get_route_OneMapAPI(start, end):
  """
  Retrieve a walking route from OneMap API between start and end points.
  """

  url = f"https://www.onemap.gov.sg/api/public/routingsvc/route?start={start.y}%2C{start.x}&end={end.y}%2C{end.x}&routeType=walk"
  headers = {"Authorization": API_KEY}

  response = requests.get(url, headers=headers)

  if response.status_code != 200:
      print(f"Error: HTTP status code {response.status_code}")
      print("Unexpected Error, Check Validity of API KEY")
      return None, None, None

  # Extract data
  data = response.json()
  route_geometry = data['route_geometry']
  time = data['route_summary']['total_time']
  distance = data['route_summary']['total_distance']

  # Converting route_geometry into a LineString feature
  coordinates = polyline.decode(route_geometry)
  route_line = LineString(coordinates)

  flipped_coordinates = [(y, x) for x, y in route_line.coords]
  flipped_route_line = LineString(flipped_coordinates)

  return flipped_route_line, time, distance



def find_nearest_amenity(point, amenity_gdf):
  """
  Find the nearest amenity to a given point.
  """
  # Transform CRS to projected CRS to ensure accurate calculation
  point_gdf = gpd.GeoDataFrame({'geometry': [point]}, crs='EPSG:4326')
  point_gdf = point_gdf.to_crs(epsg=3414)

  amenity_gdf.to_crs(epsg=3414, inplace=True)

  # Find distance between point and amenity in amenity_gdf
  amenity_gdf['distance'] = amenity_gdf.geometry.apply(lambda x: point_gdf.geometry.distance(x).min())

  # Transform back to WGS 84
  amenity_gdf.to_crs(epsg=4326, inplace=True)

  # Find the minimum distance and the corresponding nearest amenity
  nearest_amenity = amenity_gdf.loc[amenity_gdf['distance'].idxmin()]
  distance = nearest_amenity['distance']

  # Drop distance column
  amenity_gdf = amenity_gdf.drop('distance')

  return nearest_amenity, distance



def generate_full_route(route_points_gdf, max_route_length, near_amenities, selected_amenities, near_pois, selected_pois, avoidance_buffer_gdf):
    """
    Generate a full route considering amenities and avoidance zones.
    """
    route_geometries = []
    total_time = 0
    total_distance = 0

    CUT_OFF = 1000
    BACKTRACK_LIMIT = 10

    end_point_gdf = route_points_gdf.iloc[[-1]]
    end_point = end_point_gdf.geometry.iloc[0]
    last_amenity_idx = -1
    backtrack_attempts = 0
    avoidance_check_attempts = 0

    route_times = []
    route_distances = []

    i = 0

    while i < len(route_points_gdf) - 1:
        current_point_gdf = route_points_gdf.iloc[[i]]
        next_point_gdf = route_points_gdf.iloc[[i + 1]]

        current_point = current_point_gdf.geometry.iloc[0]
        next_point = next_point_gdf.geometry.iloc[0]

        # Retrieve geometry for route segment from OneMap API
        route_geometry, time, distance = get_route_OneMapAPI(current_point, next_point)

        # Check if route segment intersects avoidance zones
        if avoidance_check_attempts <= 5:
            avoidance_check_attempts += 1
            temp_next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, should_continue = check_avoidance(
                route_geometry, current_point_gdf, next_point_gdf, near_pois, selected_pois, selected_amenities, avoidance_buffer_gdf
            )

            # If next_point has changed, update route points
            if next_point_gdf.geometry.iloc[0] != temp_next_point_gdf.geometry.iloc[0]:
                next_point_gdf = temp_next_point_gdf
                route_points_gdf.loc[i + 1] = next_point_gdf.iloc[0]

                # Retry a new loop (which will get new geometry and check avoidance)
                continue

        # If total distance is too long, start backtracking
        if total_distance + distance >= max_route_length:
            route_points_gdf, route_geometries, total_time, total_distance = handle_backtrack(
                route_points_gdf, route_geometries, route_times, route_distances, time, distance, total_time, total_distance, max_route_length, end_point, i, backtrack_attempts
            )
            return route_points_gdf, route_geometries, total_time, total_distance, selected_amenities

        # If next point is too long, add amenity
        if (distance >= CUT_OFF) and (next_point != end_point) and ((i - last_amenity_idx) > 1) and (len(near_amenities) != 0):
            route_points_gdf, amenity, selected_amenities, last_amenity_idx = add_nearest_amenity(
                route_points_gdf, current_point, near_amenities, selected_amenities, i, last_amenity_idx
            )

            # Redo geometry
            route_geometry, time, distance = get_route_OneMapAPI(current_point, amenity.geometry)
            current_point_gdf = route_points_gdf.iloc[[i]]
            next_point_gdf = route_points_gdf.iloc[[i + 1]]

            current_point = current_point_gdf.geometry.iloc[0]
            next_point = next_point_gdf.geometry.iloc[0]

        # Add next route segment into route_geometries
        current_location_name = current_point_gdf['NAME'].iloc[0]
        next_location_name = next_point_gdf['NAME'].iloc[0]
        print(f"Route from {current_location_name} to {next_location_name}")

        route_geometries.append(route_geometry)
        route_times.append(time)
        route_distances.append(distance)
        total_time += time
        total_distance += distance

        # Reset avoidance check for current point
        avoidance_check_attempts = 0

        # Move onto next point
        i += 1

    return route_points_gdf, route_geometries, total_time, total_distance, selected_amenities



# # Helper Function
# def handle_backtrack(route_points_gdf, result, route_times, route_distances, time, distance, total_time, total_distance, max_route_length, end_point, i, backtrack_attempts):
#   BACKTRACK_LIMIT = 10
#   while total_distance + distance >= max_route_length and i > 0 and backtrack_attempts < BACKTRACK_LIMIT:
#     i -= 1
#     current_point_gdf = route_points_gdf.iloc[[i]]
#     current_point = current_point_gdf.geometry.iloc[0]

#     result.pop()
#     total_time -= route_times.pop()
#     total_distance -= route_distances.pop()
#     route_points_gdf = route_points_gdf.drop(route_points_gdf.index[-1])

#     backtrack_attempts += 1

#     route_geometry, time, distance = get_route_OneMapAPI(current_point, end_point)

#   if total_distance + distance >= max_route_length:
#     print("Unable to find a valid route within the distance limit.")
#     return None, None, None, None

#   route_points_gdf = pd.concat([route_points_gdf.iloc[:i + 1], pd.DataFrame([end_point])], ignore_index=True)
#   result.append(route_geometry)
#   total_time += time
#   total_distance += distance
#   return route_points_gdf, result, total_time, total_distance



# Helper Function
def add_nearest_amenity(route_points_gdf, current_point, near_amenities, selected_amenities, i, last_amenity_idx):
  CUT_OFF = 500
  amenity, amenity_distance = find_nearest_amenity(current_point, near_amenities)

  if amenity_distance <= CUT_OFF:
    temp_gdf = gpd.GeoDataFrame([amenity], columns=selected_amenities.columns, crs='EPSG:4326')
    selected_amenities = pd.concat([selected_amenities, temp_gdf], ignore_index=True)

    route_points_gdf = pd.concat([route_points_gdf.iloc[:i+1], gpd.GeoDataFrame([amenity], crs='EPSG:4326'), route_points_gdf.iloc[i+1:]], ignore_index=True)
    last_amenity_idx = i + 1

  return route_points_gdf, amenity, selected_amenities, last_amenity_idx



# Helper Function
def check_avoidance(route_geometry, current_point_gdf, next_point_gdf, near_pois, selected_pois, selected_amenities, avoidance_buffer_gdf):
  if avoidance_buffer_gdf.is_empty[0]:
    return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, False

  # if route cuts into the avoidance zones
  if route_geometry.intersects(avoidance_buffer_gdf.unary_union):

    # Print out which section is intersecting the avoidance zones
    current_location_name = current_point_gdf['NAME'].iloc[0]
    next_location_name = next_point_gdf['NAME'].iloc[0]
    print(f"Intersection Found. Route from {current_location_name} to {next_location_name} intersects with avoidance area. Reselecting route point.")

    if next_point_gdf['NAME'].iloc[0] == 'User':
      return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, False

    # Check if next point is a POI
    if next_point_gdf['TYPE'].iloc[0] not in ['Toilet', 'Drinking Water']:

      # Reselect a route point from the same cluster
      cluster_num = next_point_gdf['cluster'].iloc[0]

      # Exclude next point from near_pois and selected_pois.
      near_pois = near_pois[near_pois['geometry'] != next_point_gdf.geometry.iloc[0]]
      # removed the next line due to some errors
      selected_pois = selected_pois[selected_pois['geometry'] != next_point_gdf.geometry.iloc[0]]

      # Find matching rows in near_pois
      cluster_points = near_pois[near_pois['cluster'] == cluster_num]

      # If another point exists
      if len(cluster_points) >= 1:

        # update next_point_gdf and selected_pois
        next_point_gdf = cluster_points.sample()

        selected_pois = pd.concat([selected_pois, next_point_gdf], ignore_index=True)
        return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, True
      else:

        # update next_point_gdf and selected pois by a random sample within near_pois
        next_point_gdf = near_pois.sample()

        selected_pois = pd.concat([selected_pois, next_point_gdf], ignore_index=True)
        return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, True

  else:
    return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, False



# def generate_route_points(user_gdf, near_pois, num_POIs, end_gdf):
#     """
#     Generate a sorted list of route points.
#     """
#     poi_clusters = find_clusters(near_pois, num_POIs)
#     selected_pois = poi_clusters.groupby('cluster').sample(n=1).reset_index(drop=True)
#     route_points_gdf = nearest_neighbor_route(user_gdf, selected_pois)
#     route_points_gdf = pd.concat([route_points_gdf, end_gdf], ignore_index=True)
#     return route_points_gdf, poi_clusters, selected_pois



# def check_intersections(route_geometries, avoidance_buffer_gdf):
#     """
#     Check if any route geometries intersect with the avoidance buffer zones.

#     Parameters:
#     - route_geometries (list): List of Linestrings objects (route geometries).
#     - avoidance_buffer_gdf (GeoDataFrame): Areas to avoid.

#     Returns:
#     - bool: True if there is an intersection, False otherwise.
#     """
#     for route in route_geometries:
#         if avoidance_buffer_gdf.intersects(route).any():
#             return True
#     return False


# def regenerate_route(user_gdf, near_pois, num_POIs, end_gdf, near_amenities, avoidance_buffer_gdf, max_route_length):
#     """
#     Regenerate the route until a valid one is found or maximum attempts/time is reached.
#     """
#     global attempts
#     while attempts < MAX_ATTEMPTS:
#         if time.time() - start_time > MAX_TIME:
#             print("Maximum time exceeded. Stopping the route generation process.")
#             break

#         print(f"Attempt {attempts + 1}: Route intersects with avoidance zones. Regenerating route...")

#         # Generate sorted list of route points
#         route_points_gdf, poi_clusters, selected_pois = generate_route_points(user_gdf, near_pois, num_POIs, end_gdf)

#         # Initialize variables
#         selected_amenities = empty_gdf

#         route_points_gdf, route_geometries, time, distance, selected_amenities = generate_full_route(
#             route_points_gdf, max_route_length, near_amenities, selected_amenities, poi_clusters, selected_pois, avoidance_buffer_gdf
#         )

#         if route_points_gdf is not None and not check_intersections(route_geometries, avoidance_buffer_gdf):
#             return route_points_gdf, route_geometries, time, distance, selected_amenities, selected_pois

#         attempts += 1

#     print("Maximum attempts reached. Unable to find a valid route that satisfies the requirements.")
#     return None, None, None, None, None, None

"""## Execution"""

import time

# Define the maximum number of attempts and time to avoid infinite loops
MAX_ATTEMPTS = 2
MAX_TIME = 60  # Maximum time in seconds

# Record the start time
start_time = time.time()
attempts = 0

# Generate initial route
route_points_gdf, poi_clusters, selected_pois = generate_route_points(user_gdf, near_pois, num_POIs, end_gdf)

# Initialize variables
selected_amenities = empty_gdf

# Generate Route
final_route_points_gdf, final_route_geometries, final_time, final_distance, final_selected_amenities = generate_full_route(
    route_points_gdf, max_route_length, near_amenities, selected_amenities, poi_clusters, selected_pois, avoidance_buffer_gdf
)

if final_route_points_gdf is not None:
    final_selected_pois = selected_pois[selected_pois['NAME'].isin(final_route_points_gdf['NAME'])]

    if check_intersections(final_route_geometries, avoidance_buffer_gdf):
        final_route_points_gdf, final_route_geometries, final_time, final_distance, final_selected_amenities, final_selected_pois = regenerate_route(
            user_gdf, near_pois, num_POIs, end_gdf, near_amenities, avoidance_buffer_gdf, max_route_length
        )

    if final_route_points_gdf is not None:
        print("Valid route found that satisfies all requirements.")
    else:
        print("No valid route found.")
else:
    print("No valid route found.")



##############################################
##############################################
"""# Export"""

# Remove the last row from final_route_points_gdf
final_route_points_gdf = final_route_points_gdf.iloc[:-1]

# Concatenate final_route_points_gdf with end_gdf
final_route_points_gdf = pd.concat([final_route_points_gdf, end_gdf], ignore_index=True)

# Select specific columns from final_route_points_gdf
final_route_points_gdf = final_route_points_gdf[['NAME', 'TYPE', 'PHOTOURL', 'DESCRIPTION', 'geometry']]

# Create a GeoDataFrame for final_route_geometries
final_route_gdf = gpd.GeoDataFrame(geometry=final_route_geometries, crs="EPSG:4326")

# Save GeoDataFrames to GeoJSON files
geojson_files = {
    "search_buffer.geojson": search_buffer_gdf,
    "final_route_points.geojson": final_route_points_gdf,
    "avoidance_buffer.geojson": avoidance_buffer_gdf,
    "final_route.geojson": final_route_gdf
}

for filename, gdf in geojson_files.items():
    gdf.to_file(filename, driver="GeoJSON")



##############################################
##############################################
"""# Import"""

# Function to read and set CRS for a GeoJSON file
def read_and_set_crs(filepath, crs="EPSG:4326"):
    gdf = gpd.read_file(filepath)
    return gdf.to_crs(crs)

# Filepaths
filepaths = {
    "search_buffer": "search_buffer.geojson",
    "final_route_points": "final_route_points.geojson",
    "avoidance_buffer": "avoidance_buffer.geojson",
    "final_route": "final_route.geojson"
}

# Read GeoJSON files into GeoDataFrames and ensure CRS is set to WGS84
search_buffer_gdf = read_and_set_crs(filepaths["search_buffer"])
final_route_points_gdf = read_and_set_crs(filepaths["final_route_points"])
avoidance_buffer_gdf = read_and_set_crs(filepaths["avoidance_buffer"])
final_route_gdf = read_and_set_crs(filepaths["final_route"])

# Extract user and end GeoDataFrames from final_route_points_gdf
user_gdf = final_route_points_gdf.iloc[[0]]
end_gdf = final_route_points_gdf.iloc[[-1]]

# Extract POI and Amenity Points
final_route_points_gdf = final_route_points_gdf.iloc[1:-1]

# Convert final_route_gdf to a list of LineStrings
final_route = final_route_gdf.geometry.tolist()
