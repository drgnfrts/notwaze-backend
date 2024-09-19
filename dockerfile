# Use a lightweight Python base image
FROM python:3.11-slim AS build

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set the working directory
WORKDIR /app

# Copy only the dependency files
COPY pyproject.toml poetry.lock /app/

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the installed dependencies from the build stage
COPY --from=build /usr/local /usr/local
COPY --from=build /root/.local /root/.local
COPY --from=build /app /app

# Add the Poetry and Python installation paths to the PATH environment variable
ENV PATH="/root/.local/bin:$PATH"

# Expose the port
EXPOSE 8000

# Run Uvicorn with the correct module path
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
