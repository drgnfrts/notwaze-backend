# app/api/routes.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from app.services import get_geojson, generate_route
import json
from shapely.geometry import Point
import geopandas as gpd
from app.models.schemas import RouteRequest, RouteResponse

# Create the main API router
router = APIRouter()

# GeoJSON Routes
@router.get("/geojsons/")
async def list_geojson_files(request: Request):
    """
    Endpoint to list all loaded GeoJSON file keys.
    """
    return {"files": list(request.app.state.geojson_files.keys())}

@router.get("/geojson/{file_key}")
async def get_geojson_file(file_key: str, request: Request):
    """
    Endpoint to get a specific GeoJSON file by its key.
    """
    return get_geojson(file_key, request)
    
@router.post("/generate_route")
async def generate_route_endpoint(request: Request, user_data: dict):
    try:
        # Access the GeoJSON files and user data from app state
        
        request.app.state.user_data = {
            "user_location": user_data["user_location"],
            "end_location": user_data["end_location"],
            "search_radius": user_data["search_radius"],
            "num_POIs": 5,
            "max_route_length": user_data["max_route_length"],
            # below are placeholder values
            "poi_types": ['monument', 'historicSite', 'park', 'museum'],
            "amenity": user_data['amenity'], #True
            "barrier_free": user_data['barrier_free'] #True
        }

        # Pass necessary data to the service function
        route_response = generate_route(request, request.app.state.user_data)
        return route_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))