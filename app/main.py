from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router  # Import the unified API router
from app.services import load_all_geojson_files
# 
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs before the application starts receiving requests
    print("Loading GeoJSON files from S3...")
    app.state.geojson_files = load_all_geojson_files()
    print("GeoJSON files loaded into memory.")
    yield
    # This code runs when the application is shutting down
    print("Application is shutting down")
    
    # Purge the app state
    app.state.geojson_files.clear()
    print("GeoJSON files cleared from memory.")

# Initialize the FastAPI app with the lifespan context manager
app = FastAPI(
    title="FastAPI Backend for LLM and Geospatial Processing",
    description="A backend service with real-time WebSocket streaming, S3 integration, and external LLM API integration",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)