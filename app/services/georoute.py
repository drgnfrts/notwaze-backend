"""# Install Packages using PIP Resource Manager"""

"""# Import data and packages"""

import geopandas as gpd
import pandas as pd
from bs4 import BeautifulSoup
from shapely.geometry import LineString, Point, Polygon, MultiLineString
from shapely.ops import unary_union
import folium
import polyline
import requests
import random
from sklearn.cluster import KMeans

from google.colab import drive
drive.mount('/content/drive')

pd.set_option('display.max_colwidth', None)

museum_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_Museum.geojson')
monument_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_Monument.geojson')
historicSite_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_HistoricSite.geojson')
park_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_Park.geojson')
toilet_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_Toilet.geojson')
drinkingWater_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_DrinkingWater.geojson')
stairs_gdf = gpd.read_file('/content/drive/My Drive/Colab Notebooks/data/data_cleaned/cleaned_Stairs.geojson')
stairs_gdf = stairs_gdf[stairs_gdf.geometry.type != 'Point']

"""# User Input"""

# # Location of IRAS, Novena
# longitude = 103.84225837306487
# latitude = 1.3195883289088046

# Location of SCIS1
longitude = 103.84959994451148
latitude = 1.2973812128576168

# User POI Search Radius (User Input)
search_radius = 1000 # in metres

# User Number of POIs Searched (User Input)
num_POIs = 5

# Max total distance
max_route_length = 2000 # in metres

# Convert input into shapely object
user_location = Point((longitude, latitude))

# Convert user location to a GeoDataFrame
user_gdf = gpd.GeoDataFrame([{'geometry': user_location}], crs="EPSG:4326")
user_gdf['NAME'] = 'User'
user_gdf['TYPE'] = 'User'

"""# Data Preparation

## Backend Functions For Data Preparation
"""

def search_nearby_items(user_gdf,search_radius:int,item_gdf):
  """
  Input: GeoDataFrame of user location, search_radius, and GeoDataFrame of items to search (input can be in any crs).
  Search for nearby items in a GeoDataFrame around the user.
  Output: GeoDataFrame of nearby items in crs WGS84 (EPSG:4326).
  """
  # Create a copy and transform crs
  user_gdf = user_gdf.copy().to_crs(epsg=3414)
  item_gdf = item_gdf.copy().to_crs(epsg=3414)

  search_buffer = user_gdf.buffer(search_radius, resolution=16)
  search_gdf = gpd.GeoDataFrame(geometry=search_buffer, crs='EPSG:3414')

  # Add a distance attribute (shows distance of nearby items)
  intersecting_item = gpd.sjoin(item_gdf, search_gdf, how='inner', predicate='intersects')
  intersecting_item['distance'] = intersecting_item.geometry.apply(lambda x: user_gdf.geometry.distance(x).min())
  intersecting_item = intersecting_item.sort_values(by='distance', ascending=True)

  # Transform back to WGS84 (EPSG:4326) before returning
  intersecting_item = intersecting_item.to_crs(epsg=4326)

  return search_buffer, intersecting_item



def find_clusters(item_gdf, num_clusters):
  """
  Finds clusters of items in a GeoDataFrame if number of items in GeoDataFrame is larger than num_clusters.
  Then, randomly select one item from each cluster.
  Output: GeoDataFrame of items (one from each cluster) in crs WGS84 (EPSG:4326).
  """
  # return original GeoDataFrame if number of items too small
  if len(item_gdf) <= num_clusters:
    return item_gdf

  # Create a copy and transform crs
  item_gdf = item_gdf.copy().to_crs(epsg=3414)

  # Perform K means on coordinates
  coords = item_gdf.geometry.apply(lambda geom: [geom.x, geom.y]).tolist()
  kmeans = KMeans(n_clusters=num_clusters, n_init=10).fit(coords)
  item_gdf['cluster'] = kmeans.labels_

  # Randomly select one POI from each cluster
  selected_items = item_gdf.groupby('cluster').apply(lambda x: x.sample(1)).reset_index(drop=True)

  # Transform back to WGS84 (EPSG:4326) before returning
  item_gdf = item_gdf.to_crs(epsg=4326)
  selected_items = selected_items.to_crs(epsg=4326)

  return selected_items, item_gdf

"""## Execution"""

# Concat all POIs into one single GeoDataFrame
pois_gdf = pd.concat([museum_gdf,monument_gdf,historicSite_gdf,park_gdf], ignore_index=True)
amenity_gdf = pd.concat([toilet_gdf,drinkingWater_gdf], ignore_index=True)
avoidance_gdf = pd.concat([stairs_gdf], ignore_index=True)

# Ensure crs is set properly
amenity_gdf.crs = 'EPSG:4326'
pois_gdf.crs = 'EPSG:4326'
avoidance_gdf.crs = 'EPSG:4326'

search_buffer, near_pois = search_nearby_items(user_gdf,search_radius,pois_gdf)
search_buffer, near_amenities = search_nearby_items(user_gdf,search_radius,amenity_gdf)
search_buffer, near_avoidance = search_nearby_items(user_gdf,search_radius,avoidance_gdf)

# Generate Buffers and Union
near_avoidance = near_avoidance.copy().to_crs(epsg=3414)
avoidance_buffer = near_avoidance.buffer(10, resolution=16)
unified_geometry = unary_union(avoidance_buffer)
avoidance_buffer_gdf = gpd.GeoDataFrame(geometry=[unified_geometry], crs='EPSG:3414')
avoidance_buffer_gdf = avoidance_buffer_gdf.to_crs(epsg=4326)

"""# Route Generation

## Backend Functions to Generate Routes

### New Code
"""

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI1ZTA0YmFkZDFmOTRhOWJmZTA4ZDkzNDQwOWUzZWU4MCIsImlzcyI6Imh0dHA6Ly9pbnRlcm5hbC1hbGItb20tcHJkZXppdC1pdC0xMjIzNjk4OTkyLmFwLXNvdXRoZWFzdC0xLmVsYi5hbWF6b25hd3MuY29tL2FwaS92Mi91c2VyL3Nlc3Npb24iLCJpYXQiOjE3MjYxNDk5NTUsImV4cCI6MTcyNjQwOTE1NSwibmJmIjoxNzI2MTQ5OTU1LCJqdGkiOiI4NjBTOWhQY1p4WEVNTHpsIiwidXNlcl9pZCI6MzgyMywiZm9yZXZlciI6ZmFsc2V9.zsbHV6uExSbpWWT3RxlL1B7rWQlD_iVOVKwGsEyAK3A"



def nearest_neighbor_route(start_gdf, points_gdf):
    """
    Input: Start point and points GeoDataFrame.
    Plots a route from start to nearest point, then from that point to its nearest point, and so on.
    Algorithm uses euclidean distance (not actual walking distance).
    Output: GeoDataFrame of points on the route using nearest neighbours.
    """
    # Transform CRS to projected CRS to ensure accurate calculation
    start_gdf_copy = start_gdf.copy().to_crs(epsg=3414)
    points_gdf_copy = points_gdf.copy().to_crs(epsg=3414)

    all_columns = start_gdf_copy.columns.union(points_gdf_copy.columns)

    # Reindex both GeoDataFrames to have the same columns
    start_gdf_copy = start_gdf_copy.reindex(columns=all_columns)
    points_gdf_copy = points_gdf_copy.reindex(columns=all_columns)

    # To return: list of points on the route
    route_points_gdf = start_gdf_copy

    while len(points_gdf_copy) != 0:
        # Calculate distances from the last point in the route to all other points
        last_point = route_points_gdf.iloc[-1].geometry
        points_gdf_copy['distance'] = points_gdf_copy.geometry.apply(lambda x: last_point.distance(x))

        # Find the nearest point
        nearest_idx = points_gdf_copy['distance'].idxmin()
        nearest = points_gdf_copy.loc[[nearest_idx]]

        # Concatenate the nearest point to the route
        route_points_gdf = pd.concat([route_points_gdf, nearest], ignore_index=True)

        # Drop the nearest point from the points_gdf_copy
        points_gdf_copy = points_gdf_copy.drop(nearest_idx)

    # Transform CRS back to WGS84 (EPSG:4326) for mapping
    route_points_gdf = route_points_gdf.to_crs(epsg=4326)

    return route_points_gdf



def get_route_OneMapAPI(start, end):
  """
  Input: Start and end points (shapely objects), assumes inputs are in crs WGS84 (EPSG:4326).
  Get route geometry from OneMap API using start and end points (shapely objects).
  Output: LineString of route geometry in WGS84 (EPSG:4326), time (seconds), and distance (meters) from start point to end point.
  """

  # Note: geometry.y retrieves the latitude, geometry.x retrieves the longitude
  # Assumes start and end are in latitude and longitude format.
  url = f"https://www.onemap.gov.sg/api/public/routingsvc/route?start={start.y}%2C{start.x}&end={end.y}%2C{end.x}&routeType=walk"

  headers = {"Authorization": API_KEY}
  response = requests.request("GET", url, headers=headers)

  # Error handling
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
  Input: Point (shapely object), amenity_gdf (GeoDataFrame), assumes inputs are in crs WGS84 (EPSG:4326).
  Finds the nearest amenity from a given point.
  Output: nearest amenity in WGS84 (EPSG:4326) and distance from point in meters
  """
  # Transform CRS to projected CRS to ensure accurate calculation
  point_gdf = gpd.GeoDataFrame({'geometry': [point]}, crs='EPSG:4326')
  point_gdf = point_gdf.to_crs(epsg=3414)

  amenity_gdf_copy = amenity_gdf.copy().to_crs(epsg=3414)

  # Find distance between point and amenity in amenity_gdf
  amenity_gdf_copy['distance'] = amenity_gdf_copy.geometry.apply(lambda x: point_gdf.geometry.distance(x).min())

  # Transform back to WGS 84
  amenity_gdf_copy = amenity_gdf_copy.to_crs(epsg=4326)

  # Find the minimum distance and the corresponding nearest amenity
  nearest_amenity = amenity_gdf_copy.loc[amenity_gdf_copy['distance'].idxmin()]
  distance = nearest_amenity['distance']

  return nearest_amenity, distance



def generate_full_route(route_points_gdf, max_route_length, near_amenities, selected_amenities, near_pois, selected_pois, avoidance_buffer_gdf):
  """
  Generate a list of Linestrings routes through points in route_points_gdf.

  Parameters:
  - route_points_gdf (GeoDataFrame): Points to route through.
  - max_route_length (int): Maximum allowed route length.
  - near_amenities (GeoDataFrame): Nearby amenities.
  - selected_pois (GeoDataFrame): Points of interest.
  - avoidance_buffer_gdf (GeoDataFrame): Areas to avoid.

  Returns:
  - route_points_gdf (GeoDataFrame): Updated route points.
  - result (list): List of Linestrings objects (route geometries).
  - total_time (int): Total time in seconds.
  - total_distance (int): Total distance in meters.
  - selected_amenities (GeoDataFrame): Selected amenities.
  """
  result = []
  total_time = 0
  total_distance = 0

  CUT_OFF = 500
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
      temp_next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, should_continue = check_avoidance(route_geometry, current_point_gdf, next_point_gdf, near_pois, selected_pois, selected_amenities, avoidance_buffer_gdf)

      # If next_point has changed
      if next_point_gdf.geometry.iloc[0] != temp_next_point_gdf.geometry.iloc[0]:
        next_point_gdf = temp_next_point_gdf
        route_points_gdf.loc[i+1] = next_point_gdf.iloc[0]

        # retry a new loop (which will get new geometry and check avoidance)
        continue

    # If total distance is too long
    if total_distance + distance >= max_route_length:
      route_points_gdf, result, total_time, total_distance = handle_backtrack(route_points_gdf, result, route_times, route_distances, time, distance, total_time, total_distance, max_route_length, end_point, i, backtrack_attempts)
      return route_points_gdf, result, total_time, total_distance, selected_amenities

    # If next point is too long, add amenity
    if (distance >= CUT_OFF) and (next_point != end_point) and ((i - last_amenity_idx) > 1) and (len(near_amenities) != 0):
      route_points_gdf, amenity, selected_amenities, last_amenity_idx = add_nearest_amenity(route_points_gdf, current_point, near_amenities, selected_amenities, i, last_amenity_idx)

      # redo geometry
      route_geometry, time, distance = get_route_OneMapAPI(current_point, amenity.geometry)
      current_point_gdf = route_points_gdf.iloc[[i]]
      next_point_gdf = route_points_gdf.iloc[[i + 1]]

      current_point = current_point_gdf.geometry.iloc[0]
      next_point = next_point_gdf.geometry.iloc[0]


    # Add next route segment into result
    current_location_name = current_point_gdf['NAME'].iloc[0]
    next_location_name = next_point_gdf['NAME'].iloc[0]
    print(f"Route from {current_location_name} to {next_location_name}")

    result.append(route_geometry)
    route_times.append(time)
    route_distances.append(distance)
    total_time += time
    total_distance += distance

    # reset avoidance check for current point
    avoidance_check_attempts = 0

    # Move onto next point
    i += 1

  return route_points_gdf, result, total_time, total_distance, selected_amenities



# Helper Function
def handle_backtrack(route_points_gdf, result, route_times, route_distances, time, distance, total_time, total_distance, max_route_length, end_point, i, backtrack_attempts):
  BACKTRACK_LIMIT = 10
  while total_distance + distance >= max_route_length and i > 0 and backtrack_attempts < BACKTRACK_LIMIT:
    i -= 1
    current_point_gdf = route_points_gdf.iloc[[i]]
    current_point = current_point_gdf.geometry.iloc[0]

    result.pop()
    total_time -= route_times.pop()
    total_distance -= route_distances.pop()
    route_points_gdf = route_points_gdf.drop(route_points_gdf.index[-1])

    backtrack_attempts += 1

    route_geometry, time, distance = get_route_OneMapAPI(current_point, end_point)

  if total_distance + distance >= max_route_length:
    print("Unable to find a valid route within the distance limit.")
    return None, None, None, None

  route_points_gdf = pd.concat([route_points_gdf.iloc[:i + 1], pd.DataFrame([end_point])], ignore_index=True)
  result.append(route_geometry)
  total_time += time
  total_distance += distance
  return route_points_gdf, result, total_time, total_distance



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

  # if route cuts into the avoidance zones
  if route_geometry.intersects(avoidance_buffer_gdf.unary_union):

    # Print out which section is intersecting the avoidance zones
    current_location_name = current_point_gdf['NAME'].iloc[0]
    next_location_name = next_point_gdf['NAME'].iloc[0]
    print(f"Route from {current_location_name} to {next_location_name} intersects with avoidance area. Reselecting route point.")

    if next_point_gdf['NAME'].iloc[0] == 'User':
      return next_point_gdf, near_pois, selected_pois, near_amenities, selected_amenities, False

    # Check if next point is a POI
    if next_point_gdf['TYPE'].iloc[0] not in ['Toilet', 'Drinking Water']:

      # Reselect a route point from the same cluster
      cluster_num = next_point_gdf['cluster'].iloc[0]

      # Exclude next point from near_pois and selected_pois.
      near_pois = near_pois[near_pois['geometry'] != next_point_gdf.geometry.iloc[0]]
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



def check_intersections(route_geometries, avoidance_buffer_gdf):
    """
    Check if any route geometries intersect with the avoidance buffer zones.

    Parameters:
    - route_geometries (list): List of Linestrings objects (route geometries).
    - avoidance_buffer_gdf (GeoDataFrame): Areas to avoid.

    Returns:
    - bool: True if there is an intersection, False otherwise.
    """
    for route in route_geometries:
        if avoidance_buffer_gdf.intersects(route).any():
            return True
    return False

"""## Execution"""

# Define the maximum number of attempts to avoid infinite loops
MAX_ATTEMPTS = 2
attempts = 0

# Initial route generation
selected_pois, near_pois_filter = find_clusters(near_pois, num_POIs)
selected_amenities = gpd.GeoDataFrame(columns=['NAME', 'TYPE', 'geometry', 'index_right', 'distance'], geometry='geometry', crs='EPSG:4326')
route_points_gdf = nearest_neighbor_route(user_gdf, selected_pois)
route_points_gdf = pd.concat([route_points_gdf, user_gdf], ignore_index=True)  # Return to the starting location

# Generate the initial route
final_route_points_gdf, final_route_geometries, final_time, final_distance, final_selected_amenities = generate_full_route(
    route_points_gdf, max_route_length, near_amenities, selected_amenities, near_pois_filter, selected_pois, avoidance_buffer_gdf)

# Check for intersections and rerun if necessary
while check_intersections(final_route_geometries, avoidance_buffer_gdf) and attempts < MAX_ATTEMPTS:
    print(f"Attempt {attempts + 1}: Route intersects with avoidance zones. Regenerating route...")
    selected_pois = find_clusters(near_pois, num_POIs)
    selected_pois, near_pois_filter = find_clusters(near_pois, num_POIs)
    route_points_gdf = pd.concat([route_points_gdf, user_gdf], ignore_index=True)  # Return to the starting location

    final_route_points_gdf, final_route_geometries, final_time, final_distance, final_selected_amenities = generate_full_route(
        route_points_gdf, max_route_length, near_amenities, selected_amenities, near_pois_filter, selected_pois, avoidance_buffer_gdf)

    attempts += 1

if attempts == MAX_ATTEMPTS:
    print("Maximum attempts reached. Unable to find a valid route that avoids all avoidance zones.")
else:
    print("Valid route found that avoids all avoidance zones.")

final_selected_pois = selected_pois[selected_pois['NAME'].isin(final_route_points_gdf['NAME'])]

"""# Show Full Map

### Define Functions and Variables for Mapping
"""

def add_markers(gdf):
  # Add POIs to the map

  # Dictionary for Icons, by type of structures
  icon_dict = {
      'Museum': 'university',
      'Historic Site': 'landmark',
      'Monument': 'monument',
      'Park': 'tree',
      'Toilet': 'toilet',
      'Drinking Water': 'tint'
  }

  # Dictionary for Colours, by type of structures
  color_dict = {
      'Museum': 'red',
      'Historic Site': 'orange',
      'Monument': 'purple',
      'Park': 'green',
      'Toilet': 'cadetblue',
      'Drinking Water': 'blue'
  }

  # For each poi, generate a marker and add to map
  for idx, row in gdf.iterrows():
      popup_content = f"<div style='text-align: center;'><strong>{row['NAME']}</strong><br>"

      if 'PHOTOURL' in gdf.columns and pd.notna(row['PHOTOURL']):
          popup_content += f"<img src='{row['PHOTOURL']}' style='width: 100px; height: 100px; display: block; margin: 0 auto;'><br>"

      if 'DESCRIPTION' in gdf.columns and pd.notna(row['DESCRIPTION']):
          popup_content += f"{row['DESCRIPTION']}<br>"

      popup_content += "</div>"

      folium.Marker(
          [row.geometry.y, row.geometry.x],
          popup=folium.Popup(popup_content, max_width=250),
          icon=folium.Icon(icon=icon_dict[row['TYPE']], prefix='fa', color=color_dict[row['TYPE']])
      ).add_to(m)

def add_route_lines(route_geometries):
  # add route lines to the map

  # colours for routes
  colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']

  # for each route, generate a line + arrows and add to map
  for i, route_geometry in enumerate(route_geometries):
      # Convert LineString to list of coordinate pairs
      locations = [(lat, lon) for lon, lat in route_geometry.coords]

      # Use a different color for each route
      color = colors[i % len(colors)]
      polyline = folium.PolyLine(locations=locations, color=color, weight=2, opacity=0, tooltip=f'Route {i+1}')
      polyline.add_to(m)

      # Add arrows to the polyline
      arrows = PolyLineTextPath(
          polyline,
          '➤',  # Arrow symbol
          repeat=True,
          offset=12,
          attributes={'fill': color, 'font-weight': 'bold', 'font-size': '12'}
      )
      m.add_child(arrows)

"""### Mapping using Folium"""

from IPython.display import HTML
from folium.plugins import PolyLineTextPath

# The line below is to import the CSS from font-awesome -- to use their icons (refer to icon_dict in function add_poi_markers)
HTML('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">')

# Define a map boundary so user cannot drag map out too far (Hard-coded)
min_lon, max_lon = 102.6920, 105.0920
min_lat, max_lat = 1.0305, 1.5505

# Create a folium map centered around the user's location
m = folium.Map(
    location=(user_gdf.iloc[0].geometry.y, user_gdf.iloc[0].geometry.x),
    zoom_start=15,
    control_scale=True,
    tiles='Cartodb Positron',
    max_bounds=True,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon,
    )

# Add buffer to the map
folium.GeoJson(search_buffer.to_crs(epsg=4326).geometry).add_to(m)

# Add locactions of stairs in red
folium.GeoJson(
    near_avoidance.to_crs(epsg=4326).geometry,
    style_function=lambda x: {'color': 'magenta'},
    tooltip='Stairs'
    ).add_to(m)


# Add user location to the map
folium.Marker(
    [user_gdf.iloc[0].geometry.y, user_gdf.iloc[0].geometry.x],
    popup='User Location',
    icon=folium.Icon(color='red')
).add_to(m)

# Add POIs to the map
add_markers(final_selected_pois)

# Add POIs to the map
if len(final_selected_amenities) != 0:
  add_markers(final_selected_amenities)

# Add routes to the map
add_route_lines(final_route_geometries)

# Display the map
m

print("Total Distance (metres):", final_distance)
print("Total Time (minutes):", round(final_time/60, 2))

from IPython.display import HTML
from folium.plugins import PolyLineTextPath

HTML('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">')

# Define boundaries of Singapore (Hard-coded)
min_lon, max_lon = 102.6920, 105.0920
min_lat, max_lat = 1.0305, 1.5505

# Create a folium map centered around the user's location
m = folium.Map(
    location=(user_gdf.iloc[0].geometry.y, user_gdf.iloc[0].geometry.x),
    zoom_start=15,
    control_scale=True,
    tiles='Cartodb Positron',
    max_bounds=True,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon,
    )

# Add buffer to the map
# folium.GeoJson(search_buffer.to_crs(epsg=4326).geometry).add_to(m)
folium.GeoJson(
    avoidance_gdf.to_crs(epsg=4326).geometry,
    style_function=lambda x: {'color': 'magenta'},
    tooltip='Stairs'
    ).add_to(m)

# Add user location to the map
folium.Marker(
    [user_gdf.iloc[0].geometry.y, user_gdf.iloc[0].geometry.x],
    popup='User Location',
    icon=folium.Icon(color='red')
).add_to(m)

# # Add POIs to the map
# add_markers(final_selected_pois)

# Add POIs to the map
# add_markers(pois_gdf)
# add_markers(amenity_gdf)

# Add POIs to the map
# if len(final_selected_amenities) != 0:
#   add_markers(final_selected_amenities)


# Add routes to the map
# add_route_lines(final_route_geometries)

# Display the map
m