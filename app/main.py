from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router  # Import the unified API router
from app.services import load_all_geojson_files
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs before the application starts receiving requests
    print("Loading GeoJSON files from S3...")
    app.state.geojson_files = load_all_geojson_files()
    print("GeoJSON files loaded into memory.")
    app.state.user_data = {} 
    yield
    # This code runs when the application is shutting down
    print("Application is shutting down")
    
    # Purge the app state
    app.state.geojson_files.clear()
    app.state.user_data.clear()
    print("GeoJSON files cleared from memory.")

# Initialize the FastAPI app with the lifespan context manager
app = FastAPI(
    title="FastAPI Backend for Walk-Eaze",
    description="A backend service with enabling routing to points of interest in Singapore",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to specific IPs or domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)