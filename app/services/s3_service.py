# app/services/s3_service.py

import os
from dotenv import load_dotenv
import boto3
from fastapi import HTTPException, Request
import geojson

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_default_region = os.getenv('AWS_DEFAULT_REGION')
bucket_name = os.getenv('S3_BUCKET_NAME')

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_default_region
)

def load_all_geojson_files() -> dict:
    """
    Load all GeoJSON files from the S3 bucket into memory.
    """
    geojson_files = {}
    try:
        # List all objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                if file_key.endswith('.geojson'):
                    # Fetch each GeoJSON file and store it in memory
                    geojson_files[file_key] = fetch_geojson_from_s3(file_key)
        else:
            print("No GeoJSON files found in the bucket.")
    except Exception as e:
        print(f"Error loading files from S3: {str(e)}")
    return geojson_files

def fetch_geojson_from_s3(file_key: str) -> dict:
    """
    Fetch a GeoJSON file from S3 and return it as a dictionary.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        geojson_content = response['Body'].read().decode('utf-8')
        return geojson.loads(geojson_content)  # Converts GeoJSON string to a dictionary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching file from S3: {str(e)}")

def get_geojson(file_key: str, request: Request):
    """
    Get a preloaded GeoJSON file from memory.
    """
    geojson_files = request.app.state.geojson_files
    if file_key in geojson_files:
        return geojson_files[file_key]
    else:
        raise HTTPException(status_code=404, detail=f"File '{file_key}' not found.")
