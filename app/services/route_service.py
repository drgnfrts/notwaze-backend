import geopandas as gpd
import time
from fastapi import Request
from shapely.geometry import Point, LineString
from app.utils import (
    generate_search_buffer,
    search_nearby_items,
    find_clusters,
    concat_poi_gdf,
    nearest_neighbor_route,
    generate_full_route
)
from app.models.schemas import UserData, RoutePoint, RouteSegment, RouteResponse
from app.utils.onemap import reverse_geocode


def generate_route(request: Request, user_data: UserData):  # -> RouteRequest:
    """
    Args:
    - route_request (Request): FastAPI request
    - user_data (UserData): User preferences and data
    
    Returns:

    """
    
    # Convert user and end locations to GeoDataFrames
    start_time = time.time()
    user_location, end_location = Point(tuple(user_data['user_location'])),  Point(tuple(user_data['end_location']))
    print(reverse_geocode(user_location), reverse_geocode(end_location))
    user_gdf = gpd.GeoDataFrame(
        [{'geometry': user_location, 'NAME': reverse_geocode(user_location), 'TYPE': 'Start'}],
        crs="EPSG:4326"
    )
    end_gdf = gpd.GeoDataFrame(
        [{'geometry': end_location, 'NAME': reverse_geocode(end_location), 'TYPE': 'End'}],
        crs="EPSG:4326"
    )

    # Create an activity line between start and end
    if user_location != end_location:
        line = LineString([user_location, end_location])
        activity_line = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")
    else:
        activity_line = user_gdf

    search_gdf_sg = generate_search_buffer(activity_line, user_data['search_radius'])

    # Prepare the keys to pull from memory and concat together
    input_data_keys = {
        'poi_gdf': [f"{poi_type}.geojson" for poi_type in user_data['poi_types']] if user_data['poi_types'] else [],
        'amenity_gdf': ['toilet.geojson'] if user_data['amenity'] else None,
        'avoidance_gdf': ['stairs.geojson'] if user_data['barrier_free'] else None
    }


    poi_gdf, amenity_gdf, avoidance_gdf = (
        concat_poi_gdf(keys, request) for keys in input_data_keys.values())
    

    nearby_pois = search_nearby_items(search_gdf_sg, poi_gdf, False) if poi_gdf is not None else None
    nearby_amenity = search_nearby_items(search_gdf_sg, amenity_gdf, False) if amenity_gdf is not None else None
    nearby_avoidance_buffer = search_nearby_items(search_gdf_sg, avoidance_gdf, True) if avoidance_gdf is not None else None

    print(nearby_pois)

    final_gdf = None
    while True:
        print("Started route generation attempt")
        if time.time() - start_time > 60:
            print("Maximum attempts reached. Unable to find a valid route that satisfies the requirements.")
            return None, None, None, None, None, None


        # Find clusters and select POIs
        selected_pois = find_clusters(nearby_pois, user_data['num_POIs'])
        # Generate route points
        print("starting knn")
        print("--------- user gdf")
        print(user_gdf)
        print("--------- selected poi")
        print(selected_pois)
        print("--------- end gdf")
        print(end_gdf)
        print("---------")
        route_points_gdf = nearest_neighbor_route(user_gdf, selected_pois, end_gdf)

        print('reorganised knn')
        print(route_points_gdf)

        final_gdf, metadata = generate_full_route(user_data, route_points_gdf, nearby_pois, nearby_amenity, nearby_avoidance_buffer)
        if final_gdf is not None:
            break
    
    print("returned to main backend endpoint")
    print(final_gdf)
    print(metadata)

    # Prepare the response
    if final_gdf is None:
        return None, None, None, None, None, None

    route_points = []

    for idx, row in final_gdf.iterrows():
        if row.geometry is not None:
            route_points.append(
                RoutePoint(
                    name=row['NAME'],
                    type=row['TYPE'],
                    latitude=row.geometry.y,
                    longitude=row.geometry.x
                )
            )
        else:
            print(f"Skipping row {idx} due to None geometry: {row}")

    # Debugging statement to check the created route points
    print(f"Route points: {route_points}")

    
    final_route_geometries = metadata['final_route_geometry']
    route_segments = []
    for i, geom in enumerate(final_route_geometries):
        # Ensure you only create segments if there are enough route points
        if i < len(route_points) - 1:
            route_segments.append(
                RouteSegment(
                    from_point=route_points[i],
                    to_point=route_points[i + 1],
                    geometry=[(lat, lon) for lon, lat in geom.coords]  # Extracting coordinates as (lat, lon)
                )
            )
    request.app.state.route_points = route_points
    print(request.app.state.route_points)
    return RouteResponse(
        total_distance=metadata['total_distance'],
        total_time=metadata['total_time'],
        route_points=route_points,
        route_segments=route_segments
    )
