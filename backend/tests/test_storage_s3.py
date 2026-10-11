"""Unit tests for S3 / Cloud Object Storage Provider in CreditMera Phase 8.
"""
import io
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from storage.s3 import S3StorageProvider
from storage import get_storage
from app.core.config import get_settings


@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    return client


@pytest.fixture
def s3_provider(mock_s3_client):
    return S3StorageProvider(
        bucket_name="test-creditmera-bucket",
        region_name="us-east-1",
        endpoint_url="http://localhost:9000",
        prefix="assets",
        presigned_expiry_seconds=1800,
        s3_client=mock_s3_client,
    )


def test_s3_safe_key_resolution(s3_provider):
    """Verify safe key resolution prepends prefix and normalizes paths."""
    key = s3_provider._resolve_safe_key("watermarked/image_123.png")
    assert key == "assets/watermarked/image_123.png"

    # Test without prefix
    s3_no_prefix = S3StorageProvider(
        bucket_name="test-bucket",
        prefix="",
        s3_client=s3_provider._client,
    )
    assert s3_no_prefix._resolve_safe_key("test.png") == "test.png"


def test_s3_path_traversal_prevention(s3_provider):
    """Verify relative path traversal attacks are rejected."""
    traversal_attacks = [
        "../secret.png",
        "../../etc/passwd",
        "/absolute/path.png",
        "C:\\Windows\\system32.png",
        "nested/../../outside.png",
    ]
    for attack in traversal_attacks:
        with pytest.raises(ValueError, match="Path traversal detected"):
            s3_provider._resolve_safe_key(attack)


def test_s3_save_success(s3_provider, mock_s3_client):
    """Verify save uploads bytes to S3 with correct Content-Type."""
    mock_s3_client.put_object.return_value = {"ETag": '"etag123"'}
    data = b"fake-png-data"
    result_path = s3_provider.save(data, "watermarked/img_456.png")

    assert result_path == "watermarked/img_456.png"
    mock_s3_client.put_object.assert_called_once_with(
        Bucket="test-creditmera-bucket",
        Key="assets/watermarked/img_456.png",
        Body=data,
        ContentType="image/png",
    )


def test_s3_save_client_error(s3_provider, mock_s3_client):
    """Verify save raises IOError on client error."""
    mock_s3_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "PutObject"
    )
    with pytest.raises(IOError, match="Failed to persist file to S3"):
        s3_provider.save(b"data", "test.png")


def test_s3_read_success(s3_provider, mock_s3_client):
    """Verify read retrieves bytes from S3 object."""
    mock_body = MagicMock()
    mock_body.read.return_value = b"stored-file-bytes"
    mock_s3_client.get_object.return_value = {"Body": mock_body}

    data = s3_provider.read("test.png")
    assert data == b"stored-file-bytes"
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-creditmera-bucket",
        Key="assets/test.png",
    )


def test_s3_read_not_found(s3_provider, mock_s3_client):
    """Verify read raises FileNotFoundError on NoSuchKey."""
    mock_s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
        "GetObject"
    )
    with pytest.raises(FileNotFoundError, match="Stored S3 object not found"):
        s3_provider.read("missing.png")


def test_s3_delete_success_and_failure(s3_provider, mock_s3_client):
    """Verify delete returns True on success and False on error."""
    mock_s3_client.delete_object.return_value = {}
    assert s3_provider.delete("file.png") is True

    mock_s3_client.delete_object.side_effect = Exception("Network timeout")
    assert s3_provider.delete("file.png") is False


def test_s3_exists_check(s3_provider, mock_s3_client):
    """Verify exists returns True when object exists and False on 404."""
    mock_s3_client.head_object.return_value = {"ContentLength": 1024}
    assert s3_provider.exists("present.png") is True

    mock_s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject"
    )
    assert s3_provider.exists("missing.png") is False


def test_s3_presigned_url_generation(s3_provider, mock_s3_client):
    """Verify generate_presigned_url generates valid GET URL with expiry."""
    mock_s3_client.generate_presigned_url.return_value = (
        "https://test-creditmera-bucket.s3.amazonaws.com/assets/file.png?token=xyz"
    )
    url = s3_provider.get_presigned_url("file.png", expires_in=600)
    assert "https://" in url
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "test-creditmera-bucket", "Key": "assets/file.png"},
        ExpiresIn=600,
    )


def test_s3_absolute_path_uri(s3_provider):
    """Verify get_absolute_path returns representation containing bucket and key."""
    p = s3_provider.get_absolute_path("img.png")
    assert "test-creditmera-bucket/assets/img.png" in str(p).replace("\\", "/")


def test_storage_factory_switch(monkeypatch):
    """Verify get_storage returns S3StorageProvider when configured."""
    settings = get_settings()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "factory-bucket")

    # Clear lru_cache on get_storage
    get_storage.cache_clear()
    with patch("boto3.client") as mock_boto:
        mock_boto.return_value = MagicMock()
        storage_instance = get_storage()
        assert isinstance(storage_instance, S3StorageProvider)
        assert storage_instance.bucket_name == "factory-bucket"

    # Reset cache
    get_storage.cache_clear()
