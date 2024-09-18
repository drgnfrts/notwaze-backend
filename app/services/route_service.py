from fastapi import Request
import geopandas as gpd
from shapely.geometry import Point, LineString
# from app.utils.data_prep import (
#     search_nearby_items,
#     find_clusters,
#     generate_avoidance_zones,
#     concat_poi_gdf
# )
# from app.utils.route_generation import (
#     nearest_neighbor_route,
#     generate_full_route,
#     check_intersections
# )
from app.models.schemas import UserData
from app.utils.data_prep import concat_poi_gdf, generate_search_buffer, search_nearby_items

def generate_route(request: Request, user_data: UserData):  # -> RouteRequest:
    """
    Args:
    - route_request (Request): FastAPI request
    - user_data (UserData): User preferences and data
    
    Returns:

    """

    # Convert user and end locations to GeoDataFrames
    user_location = Point(tuple(user_data['user_location']))  # Reverse to (lon, lat)
    end_location = Point(tuple(user_data['end_location']))
    user_gdf = gpd.GeoDataFrame(
        [{'geometry': user_location, 'NAME': 'User', 'TYPE': 'User'}],
        crs="EPSG:4326"
    )
    end_gdf = gpd.GeoDataFrame(
        [{'geometry': end_location, 'NAME': 'End', 'TYPE': 'End'}],
        crs="EPSG:4326"
    )

    # Create an activity line between start and end
    if user_location != end_location:
        line = LineString([user_location, end_location])
        activity_line = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")
    else:
        activity_line = user_gdf

    activity_gdf_sg, search_gdf_sg = generate_search_buffer(activity_line, user_data['search_radius'])

    print("we reach line 47")

    # Prepare the keys to pull from memory and concat together
    input_data_keys = {
        'poi_gdf': [f"{poi_type}.geojson" for poi_type in user_data['poi_types']] if user_data['poi_types'] else [],
        'amenity_gdf': [f"{amenity_type}.geojson" for amenity_type in user_data['amenity_types']] if user_data['amenity_types'] else None,
        'avoidance_gdf': ['stairs.geojson'] if user_data['barrier_free'] else None
    }


    poi_gdf, amenity_gdf, avoidance_gdf = (
        concat_poi_gdf(keys, request) for keys in input_data_keys.values())
    
    nearby_pois = search_nearby_items(activity_gdf_sg, search_gdf_sg, poi_gdf, False) if poi_gdf is not None else None
    nearby_amenity = search_nearby_items(activity_gdf_sg, search_gdf_sg, amenity_gdf, False) if amenity_gdf is not None else None
    nearby_avoidance_buffer = search_nearby_items(activity_gdf_sg, search_gdf_sg, avoidance_gdf, True) if avoidance_gdf is not None else None

    print(nearby_pois, nearby_amenity, nearby_avoidance_buffer)

    # # Find clusters and select POIs
    # selected_pois, near_pois_filter = find_clusters(near_pois, user_data.num_POIs)

    # # Generate route points
    # route_points_gdf = nearest_neighbor_route(user_gdf, selected_pois)
    # route_points_gdf = route_points_gdf.append(end_gdf, ignore_index=True)

    # # Generate the route
    # final_route_points_gdf, final_route_geometries, total_time, total_distance, final_selected_amenities = generate_full_route(
    #     route_points_gdf, user_data.max_route_length, near_amenities, avoidance_buffer_gdf
    # )

    # # Prepare the response
    # if final_route_points_gdf is None:
    #     raise Exception("No valid route found within the given constraints.")

    # route_points = [
    #     RoutePoint(
    #         name=row['NAME'],
    #         type=row['TYPE'],
    #         latitude=row.geometry.y,
    #         longitude=row.geometry.x
    #     ) for idx, row in final_route_points_gdf.iterrows()
    # ]

    # route_segments = []
    # for i, geom in enumerate(final_route_geometries):
    #     route_segments.append(
    #         RouteSegment(
    #             from_point=route_points[i],
    #             to_point=route_points[i+1],
    #             geometry=[(lat, lon) for lon, lat in geom.coords]
    #         )
    #     )

    # return RouteResponse(
    #     total_distance=total_distance,
    #     total_time=total_time,
    #     route_points=route_points,
    #     route_segments=route_segments
    # )
