# Docker Deployment

API Extractor can be deployed using Docker for both CLI and HTTP server modes. This guide covers building, running, and configuring the Docker image.

## Quick Start

### Build the Image

```bash
docker build -t api-extractor .
```

### Run as HTTP Server

```bash
docker run -d \
  -p 8000:8000 \
  -v /path/to/code:/app/code:ro \
  -e API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code \
  --name api-extractor \
  api-extractor
```

### Test the Server

```bash
curl http://localhost:8000/api/v1/health
```

## Using Docker Compose

A `docker-compose.yml` file is included in the repository for easy deployment.

### Start the Service

```bash
# Place code to analyze in ./code-to-analyze directory
mkdir -p code-to-analyze
cp -r /path/to/your/code code-to-analyze/

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Analyze Code

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/code"}'
```

## Docker Image Details

The Docker image includes:

- **Base Image**: Python 3.11 slim
- **Health Check**: Configured to check `/api/v1/health` every 30s
- **Volume Mount**: `/app/code` for analyzed code
- **Security**: Path whitelist set to `/app/code` and `/tmp`
- **CORS**: Enabled for web UIs
- **Working Directory**: `/app`

## Environment Variables

Configure the Docker container using environment variables:

```yaml
environment:
  - API_EXTRACTOR_HOST=0.0.0.0
  - API_EXTRACTOR_PORT=8000
  - API_EXTRACTOR_LOG_LEVEL=info
  - API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code,/tmp
```

| Variable | Default | Description |
|----------|---------|-------------|
| `API_EXTRACTOR_HOST` | `0.0.0.0` | Server host binding |
| `API_EXTRACTOR_PORT` | `8000` | Server port |
| `API_EXTRACTOR_LOG_LEVEL` | `info` | Log level (`debug`, `info`, `warning`, `error`) |
| `API_EXTRACTOR_ALLOWED_PATH_PREFIXES` | (empty) | Comma-separated whitelist of allowed path prefixes |

## Volume Mounts

Mount your source code as a read-only volume:

```bash
docker run -d \
  -p 8000:8000 \
  -v /path/to/project1:/app/code/project1:ro \
  -v /path/to/project2:/app/code/project2:ro \
  api-extractor
```

**Important**: Always use `:ro` (read-only) flag for security.

## Using CLI Mode in Docker

Run API Extractor in CLI mode to extract APIs and exit:

```bash
# Extract to stdout
docker run --rm \
  -v /path/to/code:/app/code:ro \
  api-extractor \
  api-extractor extract /app/code

# Extract to file on host
docker run --rm \
  -v /path/to/code:/app/code:ro \
  -v $(pwd):/output \
  api-extractor \
  api-extractor extract /app/code --output /output/openapi.json
```

### CLI Options

```bash
# Verbose output
docker run --rm -v /path/to/code:/app/code:ro api-extractor \
  api-extractor extract /app/code --verbose

# YAML format
docker run --rm -v /path/to/code:/app/code:ro -v $(pwd):/output api-extractor \
  api-extractor extract /app/code --output /output/api.yaml --format yaml

# Custom metadata
docker run --rm -v /path/to/code:/app/code:ro -v $(pwd):/output api-extractor \
  api-extractor extract /app/code \
    --output /output/api.json \
    --title "My API" \
    --version "2.0.0"
```

## Multi-Stage Builds

For production deployments, you can create optimized multi-stage builds:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY pyproject.toml ./
COPY api_extractor/ ./api_extractor/

RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/api-extractor /usr/local/bin/api-extractor
COPY api_extractor/ ./api_extractor/

# Security: Run as non-root user
RUN useradd -m -u 1000 extractor && \
    chown -R extractor:extractor /app

USER extractor

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["api-extractor", "serve"]
```

## Docker Compose for Sidecar Pattern

Example `docker-compose.yml` for sidecar deployment:

```yaml
version: '3.8'

services:
  # Your application
  app:
    image: my-app:latest
    ports:
      - "8080:8080"
    volumes:
      - app-code:/app/code:ro
    networks:
      - app-network

  # API Extractor sidecar
  api-extractor:
    image: api-extractor:latest
    ports:
      - "8000:8000"
    volumes:
      - app-code:/app/code:ro
    environment:
      - API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code
      - API_EXTRACTOR_LOG_LEVEL=info
    networks:
      - app-network
    depends_on:
      - app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 5s

volumes:
  app-code:

networks:
  app-network:
    driver: bridge
```

## Health Checks

Docker health checks ensure the container is running properly:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1
```

Check health status:

```bash
docker ps
docker inspect --format='{{.State.Health.Status}}' api-extractor
```

## Security Best Practices

### Run as Non-Root User

```dockerfile
RUN useradd -m -u 1000 extractor
USER extractor
```

### Read-Only Volumes

```bash
docker run -v /path/to/code:/app/code:ro api-extractor
```

### Path Whitelist

```bash
docker run -e API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code api-extractor
```

### Resource Limits

```bash
docker run \
  --memory="512m" \
  --cpus="1.0" \
  api-extractor
```

Or in `docker-compose.yml`:

```yaml
services:
  api-extractor:
    image: api-extractor:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Logging

### View Logs

```bash
# Follow logs
docker logs -f api-extractor

# Last 100 lines
docker logs --tail 100 api-extractor

# Logs since timestamp
docker logs --since 2024-01-01T00:00:00 api-extractor
```

### Configure Logging Driver

```yaml
services:
  api-extractor:
    image: api-extractor:latest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## CI/CD Integration

### Build in CI Pipeline

```yaml
# GitHub Actions example
name: Build Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t api-extractor:${{ github.sha }} .

      - name: Test image
        run: |
          docker run -d --name test-extractor api-extractor:${{ github.sha }}
          sleep 5
          curl -f http://localhost:8000/api/v1/health
          docker stop test-extractor

      - name: Push to registry
        run: |
          docker tag api-extractor:${{ github.sha }} registry.example.com/api-extractor:latest
          docker push registry.example.com/api-extractor:latest
```

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs api-extractor
```

Common issues:
- Port 8000 already in use: Change port mapping `-p 9000:8000`
- Volume mount permission denied: Check file permissions
- Missing dependencies: Rebuild image

### Health Check Failing

```bash
# Check health check logs
docker inspect api-extractor | jq '.[0].State.Health'

# Test health endpoint manually
docker exec api-extractor curl http://localhost:8000/api/v1/health
```

### 403 Forbidden Errors

- Verify `API_EXTRACTOR_ALLOWED_PATH_PREFIXES` includes the requested path
- Check that volume is mounted correctly
- Ensure path doesn't contain `..` or target system directories

### Performance Issues

- Increase memory limit: `--memory="1g"`
- Increase CPU limit: `--cpus="2.0"`
- For large codebases, mount specific subdirectories

## Updating the Image

```bash
# Pull latest changes
git pull

# Rebuild image
docker build -t api-extractor:latest .

# Stop old container
docker stop api-extractor
docker rm api-extractor

# Start new container
docker run -d \
  -p 8000:8000 \
  -v /path/to/code:/app/code:ro \
  --name api-extractor \
  api-extractor:latest
```

Or with Docker Compose:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## See Also

- [HTTP Server Guide](http-server.md) - HTTP API documentation
- [Kubernetes Deployment](kubernetes.md) - Production orchestration
- [AWS Lambda Deployment](lambda.md) - Serverless deployment
