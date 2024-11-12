# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/requirements.txt .
COPY backend/main.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create storage directories with explicit permissions
RUN mkdir -p /app/storage/uploads \
    /app/storage/outputs \
    /app/storage/temp \
    && chmod -R 777 /app/storage

# Environment variables
ENV PORT=8000

# Create start script
RUN echo '#!/bin/bash\n\
mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/temp\n\
chmod -R 777 /app/storage\n\
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"' > start.sh && \
    chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]
