"""API v1 router assembly."""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.assets import router as assets_router
from app.api.v1.verification import router as verification_router
from app.api.v1.robustness import router as robustness_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.similarity import router as similarity_router
from app.api.v1.cases import router as cases_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(assets_router)
api_v1_router.include_router(verification_router)
api_v1_router.include_router(verification_router, prefix="/assets")
api_v1_router.include_router(robustness_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(similarity_router)
api_v1_router.include_router(cases_router)

__all__ = ["api_v1_router"]


