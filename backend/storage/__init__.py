"""Storage abstraction package for CreditMera."""
from functools import lru_cache
from storage.base import StorageProvider
from storage.local import LocalStorageProvider
from storage.s3 import S3StorageProvider
from app.core.config import get_settings


@lru_cache()
def get_storage() -> StorageProvider:
    """Return configured storage provider instance (local or s3)."""
    settings = get_settings()
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "s3":
        return S3StorageProvider()
    return LocalStorageProvider(settings.LOCAL_STORAGE_DIR)


__all__ = ["StorageProvider", "LocalStorageProvider", "S3StorageProvider", "get_storage"]

