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
async def get_geojson_route(file_key: str, request: Request):
    """
    Endpoint to get a specific GeoJSON file by its key.
    """
    return get_geojson(file_key, request)

# Route for generating a route using geospatial data
# @router.post("/generate-route")
# async def generate_route(request: dict):
#     """
#     Endpoint to process geospatial data and prepare it for the frontend.
#     """
#     try:
#         # Load GeoJSON data
#         file_path = request.get("file_path")
#         gdf = GeoDataLoader.load_geojson(file_path)

#         # Perform necessary geospatial operations
#         search_radius = request.get("search_radius", 1500)
#         user_location = request.get("user_location", [103.8496, 1.2974])  # Default location
#         user_point = Point(user_location[0], user_location[1])
#         user_gdf = gpd.GeoDataFrame([{'geometry': user_point}], crs="EPSG:4326")
        
#         # Search for nearby items
#         _, nearby_items = GeoAnalyzer.search_nearby_items(user_gdf, search_radius, gdf)

#         # Find clusters among the points of interest
#         num_clusters = request.get("num_clusters", 5)
#         clustered_items = GeoAnalyzer.find_clusters(nearby_items, num_clusters)

#         # Convert the data to GeoJSON format
#         geojson_data = GeoDataLoader.prepare_geojson_for_frontend(clustered_items)
        
#         return JSONResponse(content={"geojson": geojson_data})
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error generating route: {str(e)}")

# # WebSocket Endpoint for streaming LLM responses
# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     """WebSocket endpoint for streaming LLM responses."""
#     await websocket_manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             request = json.loads(data)
#             if request.get("action") == "generate_text":
#                 prompt = request.get("prompt", "Hello, World!")
#                 # Stream the LLM response
#                 async for response_chunk in LLMService.stream_llm_response(prompt):
#                     await websocket_manager.send_message(response_chunk, websocket)
#     except WebSocketDisconnect:
#         websocket_manager.disconnect(websocket)
#     except Exception as e:
#         await websocket.close(code=1002)
#         raise HTTPException(status_code=500, detail=f"Error streaming data: {str(e)}")
