# Standalone Production Dockerfile for Sahayak AI FastAPI Microservice
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY app ./app

# Expose microservice port
EXPOSE 8000

ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

# Run standalone FastAPI application via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

