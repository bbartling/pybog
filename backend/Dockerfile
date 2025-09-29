FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for file processing and health checks
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    libmagic-dev \
    file \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    procps \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories with proper permissions
RUN mkdir -p /app/data/outputs /app/data/uploads && \
    chmod 755 /app/data/outputs /app/data/uploads

# Create non-root user for security
RUN useradd -m -u 1000 pybog && \
    chown -R pybog:pybog /app
USER pybog

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]