FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY api/ ./api/
COPY bog_builder/ ./bog_builder/

# Create necessary directories
RUN mkdir -p /app/data/outputs /app/data/uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
