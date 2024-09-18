import folium
from folium.plugins import PolyLineTextPath

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
      polyline = folium.PolyLine(locations=locations, color='blue', weight=2, opacity=1, tooltip=f'Route {i+1}')
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




# The line below is to import the CSS from font-awesome -- to use their icons (refer to icon_dict in function add_poi_markers)
html = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">'

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
folium.GeoJson(search_buffer_gdf.geometry,
               style_function=lambda x: {
                   'fillOpacity': 0.1       # Set fill opacity to 10%
                }
                ).add_to(m)

# Add locactions of stairs in red
folium.GeoJson(
    avoidance_buffer_gdf.geometry,
    style_function=lambda x: {'color': 'magenta'},
    tooltip='Stairs'
    ).add_to(m)


# Add user location to the map
folium.Marker(
    [user_gdf.iloc[0].geometry.y, user_gdf.iloc[0].geometry.x],
    popup='User Location',
    icon=folium.Icon(color='red')
).add_to(m)

# Add end location to the map
folium.Marker(
    [end_gdf.iloc[0].geometry.y, end_gdf.iloc[0].geometry.x],
    popup='End Location',
    icon=folium.Icon(color='red')
).add_to(m)

# Add POIs to the map
add_markers(final_route_points_gdf)

# Add routes to the map
add_route_lines(final_route)

# Display the map
m

print("Total Distance (metres):", final_distance)
print("Total Time (minutes):", round(final_time/60, 2))