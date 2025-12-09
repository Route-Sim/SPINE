---
title: "Docker Containerization"
summary: "Production-ready Docker setup for SPINE simulation with multi-stage builds, Poetry dependency management, and Docker Compose orchestration."
source_paths:
  - "Dockerfile"
  - "docker-compose.yml"
  - ".dockerignore"
last_updated: "2025-01-27"
owner: "Mateusz Polis"
tags: ["module", "infra", "deployment"]
links:
  parent: "../SUMMARY.md"
  siblings: []
---

# Docker Containerization

> **Purpose:** Provides a complete containerized deployment solution for the SPINE simulation system, enabling consistent deployment across environments with optimized multi-stage builds and proper dependency management.

## Context & Motivation

The SPINE simulation requires a complex runtime environment with specific Python dependencies managed by Poetry. Containerization provides:

- **Consistency**: Identical runtime environment across development, testing, and production
- **Isolation**: Clean separation from host system dependencies
- **Scalability**: Easy horizontal scaling and orchestration
- **Deployment**: Simplified deployment to cloud platforms and container orchestration systems
- **Dependency Management**: Reliable Poetry-based dependency resolution in containerized environment

## Responsibilities & Boundaries

**In-scope:**
- Multi-stage Docker build optimization
- Poetry dependency management in containers
- Docker Compose orchestration
- Health checks and monitoring
- Environment variable configuration
- Production-ready image optimization

**Out-of-scope:**
- Kubernetes deployment manifests
- CI/CD pipeline integration
- Monitoring and logging infrastructure
- Load balancing configuration

## Architecture & Design

### Multi-Stage Build Architecture

```
Builder Stage (python:3.10-slim)
├── Install Poetry
├── Install production dependencies
├── Copy application code
└── Build virtual environment

Runtime Stage (python:3.10-slim)
├── Copy virtual environment from builder
├── Copy application code
├── Set runtime environment
└── Expose WebSocket server
```

### Docker Compose Services

```
spine-backend
├── Build: Multi-stage Dockerfile
├── Port: 8000 (configurable)
├── Environment: HOST, PORT, LOG_LEVEL
├── Health Check: WebSocket endpoint
├── Restart Policy: unless-stopped
└── Network: spine-network
```

## Usage Instructions

### Building the Application

```bash
# Build using Docker Compose
docker-compose build

# Build with custom tag
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

### Running the Application

```bash
# Start in foreground
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f spine-backend
```

### Configuration

Environment variables can be set via:

1. **Docker Compose environment file:**
```bash
# Create .env file
echo "SPINE_PORT=8080" >> .env
echo "SPINE_LOG_LEVEL=DEBUG" >> .env
```

2. **Direct environment variables:**
```bash
SPINE_PORT=8080 SPINE_LOG_LEVEL=DEBUG docker-compose up
```

3. **Docker Compose override:**
```yaml
# docker-compose.override.yml
services:
  spine-backend:
    environment:
      - LOG_LEVEL=DEBUG
```

### Accessing the Application

- **WebSocket Server**: `ws://localhost:8000/ws`
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs` (if FastAPI docs enabled)

## Implementation Notes

### Multi-Stage Build Benefits

- **Size Optimization**: Final image excludes build dependencies (~200MB vs ~800MB)
- **Security**: Minimal attack surface with only runtime dependencies
- **Performance**: Faster container startup and deployment

### Poetry Integration

- **Virtual Environment**: Poetry creates isolated environment in builder stage
- **Dependency Caching**: Leverages Poetry's dependency resolution
- **Production Dependencies**: Only installs runtime dependencies (`--no-dev`)

### Health Checks

- **WebSocket Endpoint**: Verifies application is serving requests
- **Graceful Degradation**: Container restart on health check failures
- **Startup Time**: 40-second grace period for application initialization

## Performance

### Image Size Optimization

- **Base Image**: `python:3.10-slim` (~45MB)
- **Application Dependencies**: ~150MB (FastAPI, NumPy, SciPy, Pydantic)
- **Total Runtime Image**: ~200MB

### Resource Requirements

- **Memory**: Minimum 512MB, recommended 1GB
- **CPU**: Single core sufficient for development
- **Storage**: ~200MB for image, ~100MB for logs

## Security & Reliability

### Security Considerations

- **Non-root User**: Application runs as non-privileged user
- **Minimal Dependencies**: Only production dependencies included
- **No Shell Access**: Container designed for single-purpose execution

### Error Handling

- **Graceful Shutdown**: SIGTERM handling for clean container termination
- **Health Monitoring**: Automatic restart on health check failures
- **Logging**: Structured logging to stdout for container log aggregation

## Future Enhancements

### World Data Persistence

```yaml
# Future volume configuration
volumes:
  - ./data:/app/data:ro  # Read-only world data
  - ./config:/app/config:ro  # Configuration files
  - ./logs:/app/logs  # Log persistence
```

### Production Deployment

- **Kubernetes Manifests**: Deployment and service configurations
- **Monitoring**: Standard logging and health checks
- **Logging**: Centralized logging with ELK stack
- **Load Balancing**: Multiple instance deployment

## References

- [Docker Multi-stage Builds](https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/#use-multi-stage-builds)
- [Poetry Docker Integration](https://python-poetry.org/docs/configuration/#virtualenvsin-project)
- [FastAPI Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose Configuration](https://docs.docker.com/compose/compose-file/)
