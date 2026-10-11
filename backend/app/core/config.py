"""Core configuration settings for CreditMera backend using Pydantic Settings.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_DEFAULT_SECRET_KEY = "creditmera_insecure_dev_secret_change_in_production_32bytes_min"
DEV_DEFAULT_WATERMARK_KEY = "creditmera_master_watermark_key_change_in_prod"
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    # Application metadata
    APP_NAME: str = "CreditMera"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Cryptographic keys and security
    SECRET_KEY: str = Field(
        default=DEV_DEFAULT_SECRET_KEY,
        description="Used for JWT/Receipt HMAC signing"
    )
    WATERMARK_SECRET_KEY: str = Field(
        default=DEV_DEFAULT_WATERMARK_KEY,
        description="Master key for watermark coefficient permutation/sub-band keying"
    )
    ALGORITHM_VERSION: str = "v1.0-dct-svd"

    # Database
    DATABASE_URL: str = "sqlite:///./creditmera.db"

    # Storage settings
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_DIR: str = "./storage_data"
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: str = "png,jpg,jpeg,webp,tiff"

    # S3 / Cloud Storage settings (Phase 8)
    S3_BUCKET_NAME: str = "creditmera-assets"
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: Optional[str] = None  # Custom endpoint for MinIO / LocalStack
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_PRESIGNED_EXPIRY_SECONDS: int = 3600
    S3_PREFIX: str = "assets"

    # Watermarking parameters
    DEFAULT_WATERMARK_ALPHA: float = 0.10
    WATERMARK_BLOCK_SIZE: int = 8
    PAYLOAD_NUM_BITS: int = 64

    # Auth & Tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    RECEIPT_ISSUER: str = "CreditMera Ownership Authority v1.0"
    MAX_IMAGE_DIMENSION: int = 8192
    MIN_IMAGE_DIMENSION: int = 64

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Strictly enforce secure, non-default cryptographic keys in production."""
        is_prod = self.ENVIRONMENT.strip().lower() in ("production", "prod")
        if is_prod:
            if self.SECRET_KEY == DEV_DEFAULT_SECRET_KEY:
                raise ValueError(
                    "Production environment requires a unique, secure SECRET_KEY; "
                    "the development default secret is strictly prohibited in production."
                )
            if self.WATERMARK_SECRET_KEY == DEV_DEFAULT_WATERMARK_KEY:
                raise ValueError(
                    "Production environment requires a unique, secure WATERMARK_SECRET_KEY; "
                    "the development default secret is strictly prohibited in production."
                )
            if len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
                raise ValueError(
                    f"Production environment requires SECRET_KEY to be at least {MIN_SECRET_KEY_LENGTH} characters long."
                )
            if len(self.WATERMARK_SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
                raise ValueError(
                    f"Production environment requires WATERMARK_SECRET_KEY to be at least {MIN_SECRET_KEY_LENGTH} characters long."
                )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions_set(self) -> set:
        return {ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()}


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of configuration settings."""
    return Settings()
