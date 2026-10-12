# ==============================================================================
# CreditMera Backend - Production Dockerfile
# Multi-stage / minimal footprint container running as non-root user
# ==============================================================================

FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install minimal OS runtime dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd -g 10001 creditmera && \
    useradd -u 10001 -g creditmera -m -s /bin/bash creditmera

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --default-timeout=100 --retries 10 -r requirements.txt && \
    rm -rf /root/.cache/pip

# Copy application source code and Alembic migrations
COPY app/ ./app/
COPY watermark/ ./watermark/
COPY verification/ ./verification/
COPY storage/ ./storage/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create local storage directory and grant ownership to non-root user
RUN mkdir -p /app/storage_data && \
    chown -R creditmera:creditmera /app

# Switch to non-root user
USER creditmera

# Expose internal FastAPI port
EXPOSE 8000

# Container healthcheck using the readiness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

ENV PORT=8000

# Production server execution with dynamic port binding and automatic migration
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
