# ==============================================================================
# CreditMera Backend - Cloud Container Dockerfile (Render / Cloud PaaS)
# ==============================================================================

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install minimal OS runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -g 10001 creditmera && \
    useradd -u 10001 -g creditmera -m -s /bin/bash creditmera

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --default-timeout=100 --retries 10 -r requirements.txt && \
    rm -rf /root/.cache/pip

# Copy backend application source code and migrations
COPY backend/app/ ./app/
COPY backend/watermark/ ./watermark/
COPY backend/verification/ ./verification/
COPY backend/storage/ ./storage/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./alembic.ini

# Create local storage directory and grant ownership
RUN mkdir -p /app/storage_data && \
    chown -R creditmera:creditmera /app

USER creditmera

EXPOSE 8000

ENV PORT=8000

# Run database migrations and start server binding to Render's dynamic $PORT
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
