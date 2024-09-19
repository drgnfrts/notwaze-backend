from pydantic import BaseModel
from typing import List, Tuple, Optional

class UserData(BaseModel):
    user_location: List[float]
    end_location: List[float]
    search_radius: int
    num_POIs: int
    max_route_length: int
    poi_types: List[str]
    amenity: bool
    barrier_free: bool

class RouteRequest(BaseModel):
    user_data: UserData

class RoutePoint(BaseModel):
    name: str
    type: str
    latitude: float
    longitude: float

class RouteSegment(BaseModel):
    from_point: RoutePoint
    to_point: RoutePoint
    geometry: List[Tuple[float, float]]

class RouteResponse(BaseModel):
    total_distance: float
    total_time: float
    route_points: List[RoutePoint]
    route_segments: List[RouteSegment]
