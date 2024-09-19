# Walk-Eaze FastAPI Backend for LLM and Geospatial Processing

This project is a backend service built for Walk-Eaze with **FastAPI** that aims to enable geospatial data processing and interactions with Amazon Titan LLM, for dynamic route generation and chat.


## Features

- **S3 Integration**: Load and manage GeoJSON files directly from Amazon S3.
- **Routing Service**: Input your start and end points, how far you want to talk, how many things you want to see, and let our routing service do its magic!
    - Selection of points closer to your start and end points, ordered using the nearest neighbours heuristic
    - Routing with OneMap API
    - Possible to generate barrier-free routes, with some success


## Setup and Installation

### 1. Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/drgnfrts/notwaze-backend.git
cd notwaze-backend
```

### 2. Install Poetry and Dependencies

Install Poetry package manager by referencing [their documentation](https://python-poetry.org/docs/#installation). Then, install the dependencies. This command will create a virtual environment and install all the packages listed in the pyproject.toml file.

```bash
poetry install
```
### 3. Configure Environment Variables

Create a .env file in the root directory and add your AWS credentials and other necessary environment variables:

```plaintext
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=your_aws_default_region
BUCKET_NAME=your_s3_bucket_name
```

### 4. Activate the shell and start development server
Activate the virtual environment managed by Poetry, then start the server with uvicorn:


```bash
poetry shell
uvicorn app.main:app --reload
```

Alternatively, build the container and run (locally) with Docker Compose:

```bash
docker-compose build
docker-compose up
```

The app will be accessible at http://127.0.0.1:8000

## API Endpoints
- GET /geojsons/: List all loaded GeoJSON file keys.
- GET /geojson/{file_key}: Retrieve a specific GeoJSON file by its key.

## Acknowledgments
Special thanks to my hackathon team and the open-source community for making this project possible.