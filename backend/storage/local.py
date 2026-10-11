"""Local filesystem storage provider for CreditMera.
"""
from pathlib import Path
from typing import Union
from app.core.config import get_settings
from storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Storage provider backed by local filesystem directory."""

    def __init__(self, base_dir: Union[str, Path, None] = None):
        if base_dir is None:
            settings = get_settings()
            base_dir = settings.LOCAL_STORAGE_DIR
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve and prevent path traversal attacks outside base_dir using canonical containment."""
        p = Path(relative_path)
        if p.is_absolute() or bool(p.anchor) or relative_path.startswith(("/", "\\")):
            raise ValueError(f"Path traversal detected: absolute or rooted path not permitted: {relative_path}")

        clean_rel = p.as_posix()
        target = (self.base_dir / clean_rel).resolve()

        if not target.is_relative_to(self.base_dir):
            raise ValueError(f"Path traversal detected: {relative_path}")

        if target == self.base_dir:
            raise ValueError(f"Path traversal detected: target cannot be base directory: {relative_path}")

        return target

    def save(self, data: bytes, relative_path: str) -> str:
        """Save file bytes to target relative path inside base_dir."""
        target_path = self._resolve_safe_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return Path(relative_path).as_posix().lstrip("/\\")

    def read(self, relative_path: str) -> bytes:
        """Read bytes from storage."""
        target_path = self._resolve_safe_path(relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Stored file not found: {relative_path}")
        return target_path.read_bytes()

    def delete(self, relative_path: str) -> bool:
        """Delete file if it exists."""
        try:
            target_path = self._resolve_safe_path(relative_path)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                return True
            return False
        except Exception:
            return False

    def exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        try:
            target_path = self._resolve_safe_path(relative_path)
            return target_path.exists() and target_path.is_file()
        except Exception:
            return False

    def get_absolute_path(self, relative_path: str) -> Path:
        """Return absolute Path object."""
        return self._resolve_safe_path(relative_path)
