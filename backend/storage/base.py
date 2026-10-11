"""Abstract base class for CreditMera file storage providers.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageProvider(ABC):
    """Abstract file storage provider interface."""

    @abstractmethod
    def save(self, data: bytes, relative_path: str) -> str:
        """Save file bytes to storage and return the canonical relative storage path."""
        pass

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        """Read and return raw file bytes from storage."""
        pass

    @abstractmethod
    def delete(self, relative_path: str) -> bool:
        """Delete file from storage. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    def get_absolute_path(self, relative_path: str) -> Path:
        """Return absolute local filesystem path (for local streaming / access)."""
        pass

    def get_presigned_url(self, relative_path: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned GET URL if supported by the storage backend (e.g. S3).
        Returns None for local filesystem storage.
        """
        return None

