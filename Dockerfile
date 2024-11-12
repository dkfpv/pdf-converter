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

# Create storage directories
RUN mkdir -p storage/uploads storage/outputs storage/temp
RUN chmod -R 777 storage

# Environment variables
ENV PORT=8000
ENV RAILWAY=true

# Expose the port
EXPOSE $PORT

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
