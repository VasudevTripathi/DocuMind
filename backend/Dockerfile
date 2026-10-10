FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for C-extensions if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create data directories for persistence
RUN mkdir -p data/uploads data/db data/vector_store

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Expose backend port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start Uvicorn server (respects dynamic cloud $PORT e.g. on Render)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
