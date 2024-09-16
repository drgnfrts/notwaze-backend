# app/api/routes.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from app.services import get_geojson
# from app.services import GeoDataLoader, GeoAnalyzer, RouteGenerator
# from app.services.llm_service import LLMService
# from app.websocket.websocket_manager import websocket_manager
import json
from shapely.geometry import Point
import geopandas as gpd

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
        # Convert Point to a JSON-serializable format (e.g., tuple)
        # user_location = (103.84959994451148, 1.2973812128576168)
        # end_loc = (1.29469651737808, 103.813299661497)

        # Store user data in app state with JSON-serializable format
        request.app.state.user_data = {
            "user_location": user_data["user_location"],
            "end_location": user_data["end_location"],
            "search_radius": user_data["search_radius"],
            "num_POIs": 5,
            "max_route_length": user_data["max_route_length"]
        }

        # Return the stored user data
        return {"message": "User data collected successfully", "data": request.app.state.user_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing user data: {str(e)}")