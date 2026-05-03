# Build stage — install heavy dependencies once
FROM python:3.11-slim

WORKDIR /app

# System dependencies needed by librosa
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project (models/ and api/ both needed at runtime)
COPY models/ ./models/
COPY api/ ./api/

# FastAPI runs on port 8000
EXPOSE 8000

# Start the server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
