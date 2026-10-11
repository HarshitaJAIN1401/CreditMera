"""Pydantic schemas for visual similarity detection."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SimilarityMetrics(BaseModel):
    phash: Dict[str, Any]
    dhash: Dict[str, Any]
    ssim: Dict[str, Any]


class SimilarityCompareResponse(BaseModel):
    composite_similarity_score: float = Field(..., ge=0.0, le=1.0)
    similarity_percentage: float
    similarity_tier: str
    explanation: str
    metrics: Dict[str, Any]
    dimensions: Dict[str, List[int]]
    legal_disclaimer: str


class SimilaritySearchMatch(BaseModel):
    asset_id: int
    title: str
    category: Optional[str] = "Other"
    country: Optional[str] = "International"
    hamming_distance: int
    similarity_score: float
    similarity_percentage: float
    similarity_tier: str


class SimilaritySearchResponse(BaseModel):
    query_phash: str
    total_registered_evaluated: int
    matches: List[SimilaritySearchMatch]
    top_match: Optional[SimilaritySearchMatch]
    legal_disclaimer: str
