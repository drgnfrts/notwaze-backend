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
    
@router.post("/collect-user-data")
async def collect_user_data(request: Request, user_data: dict):
    """
    Endpoint to collect and store user-specific data in the application state.
    """
    try:

        # Store user data in app state with JSON-serializable format

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

        # Return the stored user data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing user data: {str(e)}")
    return {"message": "User data collected successfully", "data": request.app.state.user_data}
    
@router.post("/generate_route")
async def generate_route_endpoint(request: Request):
    try:
        # Access the GeoJSON files and user data from app state
        
        user_data_state = request.app.state.user_data

        # Pass necessary data to the service function
        route_response = generate_route(request, user_data_state)
        return route_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))