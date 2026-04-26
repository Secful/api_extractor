# Multi-stage build for API Extractor HTTP server
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY api_extractor/ ./api_extractor/
COPY pyproject.toml README.md ./

# Create directory for code to analyze
RUN mkdir -p /app/code

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV API_EXTRACTOR_HOST=0.0.0.0
ENV API_EXTRACTOR_PORT=8000
ENV API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code,/tmp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run server
CMD ["api-extractor", "serve", "--host", "0.0.0.0", "--port", "8000"]
