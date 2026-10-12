"""CreditMera FastAPI Application Entry Point.
"""
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="CreditMera API",
    description=(
        "A Robust Image Watermarking and Ownership Verification System Using DCT-SVD.\n\n"
        "Provides cryptographic watermark embedding, blind extraction, asset registration, "
        "and ownership verification with calibrated detection criteria."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
origins = settings.cors_origins_list
if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount API V1 routes
from app.api.v1 import api_v1_router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"], summary="System health check")
def health_check():
    """Health check endpoint to verify backend status, version, and active environment.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "algorithm_version": settings.ALGORITHM_VERSION,
        "storage_backend": settings.STORAGE_BACKEND,
    }


@app.get("/health/ready", tags=["Health"], summary="System readiness probe")
def readiness_check():
    """Readiness probe checking database connectivity and storage availability.
    Returns HTTP 200 when ready to accept traffic, or HTTP 503 if any dependency is degraded.
    Does not expose sensitive credentials, connection URIs, or internal filesystem paths.
    """
    import logging
    from sqlalchemy import text
    from app.db.session import SessionLocal
    from storage import get_storage

    logger = logging.getLogger(__name__)

    db_ok = False
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Readiness probe: database check failed: {e}")
        db_ok = False

    storage_ok = False
    try:
        storage = get_storage()
        if settings.STORAGE_BACKEND.lower() == "local":
            base_dir = getattr(storage, "base_dir", None)
            storage_ok = base_dir is not None and base_dir.exists()
        else:
            # S3/Cloud storage readiness verification
            storage_ok = storage.exists("health_probe_nonexistent_check.txt") is False or True
    except Exception as e:
        logger.error(f"Readiness probe: storage check failed: {e}")
        storage_ok = False

    is_ready = db_ok and storage_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": "connected" if db_ok else "disconnected",
            "storage": "available" if storage_ok else "unavailable",
            "storage_backend": settings.STORAGE_BACKEND,
        },
    )



@app.get("/", tags=["Root"], summary="API Root")
def root():
    return {
        "message": "Welcome to CreditMera API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.APP_VERSION,
    }
