"""S3 and S3-compatible cloud object storage provider for CreditMera.

Compatible with AWS S3, MinIO, Cloudflare R2, and LocalStack.
"""
import io
import logging
from pathlib import Path
from typing import Optional, Union

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.core.config import get_settings
from storage.base import StorageProvider

logger = logging.getLogger(__name__)


class S3StorageProvider(StorageProvider):
    """Storage provider backed by AWS S3 or S3-compatible object storage (MinIO, R2)."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        prefix: Optional[str] = None,
        presigned_expiry_seconds: Optional[int] = None,
        s3_client=None,
    ):
        settings = get_settings()
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region_name = region_name or settings.S3_REGION
        self.endpoint_url = endpoint_url if endpoint_url is not None else settings.S3_ENDPOINT_URL
        self.prefix = (prefix if prefix is not None else settings.S3_PREFIX).strip("/\\")
        self.presigned_expiry_seconds = presigned_expiry_seconds or settings.S3_PRESIGNED_EXPIRY_SECONDS

        if s3_client is not None:
            self._client = s3_client
        else:
            client_kwargs = {
                "service_name": "s3",
                "region_name": self.region_name,
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            if aws_access_key_id or settings.S3_ACCESS_KEY_ID:
                client_kwargs["aws_access_key_id"] = aws_access_key_id or settings.S3_ACCESS_KEY_ID
            if aws_secret_access_key or settings.S3_SECRET_ACCESS_KEY:
                client_kwargs["aws_secret_access_key"] = aws_secret_access_key or settings.S3_SECRET_ACCESS_KEY

            # Configure S3 client with standard retry logic and signature version v4
            boto_config = Config(
                retries={"max_attempts": 3, "mode": "standard"},
                signature_version="s3v4",
            )
            client_kwargs["config"] = boto_config
            self._client = boto3.client(**client_kwargs)

    def _resolve_safe_key(self, relative_path: str) -> str:
        """Resolve and validate storage key to prevent traversal and malformed S3 paths."""
        p = Path(relative_path)
        if p.is_absolute() or bool(p.anchor) or relative_path.startswith(("/", "\\")):
            raise ValueError(f"Path traversal detected: absolute or rooted key not permitted: {relative_path}")

        clean_path = p.as_posix().lstrip("/\\")
        parts = clean_path.split("/")
        if any(part in ("..", "") for part in parts):
            raise ValueError(f"Path traversal detected: invalid relative path: {relative_path}")

        if self.prefix:
            return f"{self.prefix}/{clean_path}"
        return clean_path

    def save(self, data: bytes, relative_path: str) -> str:
        """Upload raw file bytes to S3 object key."""
        key = self._resolve_safe_key(relative_path)

        # Infer content type based on extension
        ext = Path(relative_path).suffix.lower()
        content_type = "image/png"
        if ext in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif ext == ".webp":
            content_type = "image/webp"
        elif ext == ".tiff":
            content_type = "image/tiff"

        try:
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return Path(relative_path).as_posix().lstrip("/\\")
        except ClientError as e:
            logger.error(f"S3 put_object failed for key '{key}': {e}")
            raise IOError(f"Failed to persist file to S3: {e}") from e

    def read(self, relative_path: str) -> bytes:
        """Download raw file bytes from S3 object key."""
        key = self._resolve_safe_key(relative_path)
        try:
            response = self._client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                raise FileNotFoundError(f"Stored S3 object not found: {relative_path}") from e
            logger.error(f"S3 get_object failed for key '{key}': {e}")
            raise IOError(f"Failed to read file from S3: {e}") from e

    def delete(self, relative_path: str) -> bool:
        """Delete object from S3."""
        try:
            key = self._resolve_safe_key(relative_path)
            self._client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True
        except Exception as e:
            logger.warning(f"S3 delete_object failed for path '{relative_path}': {e}")
            return False

    def exists(self, relative_path: str) -> bool:
        """Check if S3 object exists using head_object."""
        try:
            key = self._resolve_safe_key(relative_path)
            self._client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                return False
            logger.warning(f"S3 head_object returned unexpected error for key '{relative_path}': {e}")
            return False
        except Exception:
            return False

    def get_presigned_url(self, relative_path: str, expires_in: Optional[int] = None) -> str:
        """Generate a secure, time-limited presigned GET URL for direct client download."""
        key = self._resolve_safe_key(relative_path)
        expiry = expires_in or self.presigned_expiry_seconds
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expiry,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for key '{key}': {e}")
            raise IOError(f"Failed to generate presigned S3 URL: {e}") from e

    def get_absolute_path(self, relative_path: str) -> Path:
        """Return URI format for cloud storage references."""
        key = self._resolve_safe_key(relative_path)
        return Path(f"s3://{self.bucket_name}/{key}")
