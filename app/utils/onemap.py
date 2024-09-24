import requests
import os
import polyline
from dotenv import load_dotenv, set_key
from shapely.geometry import LineString


def regenerate_api_key():
    """Regenerates the OneMap API Key if expired.

    Args: None

    Returns: None
    
    """
    
    load_dotenv(dotenv_path=".env.production")

    # Define the URL for the API token request
    url = "https://www.onemap.gov.sg/api/auth/post/getToken"

    # Load email and password from environment variables
    payload = {
        "email": os.getenv('ONEMAP_EMAIL'),
        "password": os.getenv('ONEMAP_PASSWORD')
    }

    # Send the request to get the token
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        api_key = response.json().get('access_token')

        if api_key:
            # Write the API key to the .env.production file
            set_key(".env.production", 'ONEMAP_API_KEY', api_key)
            print("API key successfully stored in .env.production")
        else:
            print("API key not found in the response")
    else:
        print(f"Failed to fetch API key. Status code: {response.status_code}")



def get_route_OneMapAPI(start, end):
    """ Calls the OneMap API to get the route between two points.

    Args:
     - start (): Starting point of the route
     - end (): Ending point of the route
    
    Returns:
     - flipped_route_line (LineString): Route generated with coordinates in long/lat format
     - time (str): Time estimated by OneMap API to complete the route
     - distance (str): Distance of route generated

    """
    load_dotenv()
    print("point coordinates as follows")
    print(start.y, start.x, end.y, end.x)

    attempted = False
    while not attempted:
        url = f"https://www.onemap.gov.sg/api/public/routingsvc/route?start={start.y}%2C{start.x}&end={end.y}%2C{end.x}&routeType=walk"
        headers = {"Authorization": os.getenv("ONEMAP_API_KEY")}
        print("pinged onemap api")
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 401:
            regenerate_api_key()
            print("pinging for new key")
            continue

        if response.status_code != 200:
            print(f"Error: HTTP status code {response.status_code}")
            print("Unexpected Error, check again")
            return None, None, None
        
        attempted = True
    
    data = response.json()
    route_geometry = data['route_geometry']
    time = data['route_summary']['total_time']
    distance = data['route_summary']['total_distance']

    # Converting route_geometry into a LineString feature
    coordinates = polyline.decode(route_geometry)
    route_line = LineString(coordinates)

    # Change back from lat/long format to the long, lat 
    flipped_coordinates = [(y, x) for x, y in route_line.coords]
    flipped_route_line = LineString(flipped_coordinates)
    print("Called OneMap API")
    print(time, distance)
    return flipped_route_line, time, distance



    