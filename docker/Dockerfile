FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for potential future needs (OCR, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire pybog project
COPY . .

# Install original bog_builder package from upstream so generated scripts can import it
RUN pip install --no-cache-dir git+https://github.com/Cnoccir/pybog.git@f8f9da77b397d358a9168e050d243720ff1633b7

# Create directories for outputs and uploads
RUN mkdir -p /app/outputs /app/uploads /app/logs

# Expose port for the FastAPI service
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI server using our simplified API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
