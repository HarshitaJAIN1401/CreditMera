"""Comprehensive unit tests for the CreditMera Watermark Engine.

Validates baseline DCT, baseline SVD, and hybrid DCT-SVD algorithms,
cryptographic key isolation, and perceptual quality trade-offs across
representative test images.
"""
import pytest
import numpy as np

from watermark.embedding import embed_watermark
from watermark.extraction import extract_watermark
from watermark.transforms import ImageValidationError


@pytest.fixture
def synthetic_test_images():
    """Generates reproducible representative synthetic test patterns."""
    rng = np.random.default_rng(101)

    # 1. Smooth gradient pattern (256x256)
    x = np.linspace(0, 255, 256, dtype=np.uint8)
    gradient_2d = np.tile(x, (256, 1))
    gradient_rgb = np.stack([gradient_2d, gradient_2d.T, np.flipud(gradient_2d)], axis=-1)

    # 2. Textural checkerboard/sinusoidal image (256x256)
    u, v = np.meshgrid(np.linspace(0, 8 * np.pi, 256), np.linspace(0, 8 * np.pi, 256))
    texture_2d = ((np.sin(u) * np.cos(v) + 1.0) * 127.5).astype(np.uint8)
    texture_rgb = np.stack([texture_2d, texture_2d, texture_2d], axis=-1)

    # 3. Non-square image (160x224)
    non_square_rgb = rng.integers(30, 220, size=(160, 224, 3), dtype=np.uint8)

    return {
        "gradient": gradient_rgb,
        "texture": texture_rgb,
        "non_square": non_square_rgb,
    }


@pytest.mark.unit
def test_hybrid_dct_svd_embedding_and_extraction(synthetic_test_images):
    """Verify end-to-end embedding and blind extraction using Hybrid DCT-SVD."""
    image = synthetic_test_images["texture"]
    asset_id = 100200300
    secret_key = "secure_production_quality_key"

    embed_res = embed_watermark(
        image,
        asset_id=asset_id,
        secret_key=secret_key,
        algorithm="dct_svd",
        alpha=0.10,
    )

    # Perceptual quality verification
    assert embed_res.metrics["psnr_db"] >= 38.0, f"PSNR too low: {embed_res.metrics['psnr_db']} dB"
    assert embed_res.metrics["ssim"] >= 0.95, f"SSIM too low: {embed_res.metrics['ssim']}"

    # Extraction with correct key
    extract_res = extract_watermark(
        embed_res.watermarked_rgb,
        secret_key=secret_key,
        algorithm="dct_svd",
        alpha=0.10,
        expected_asset_id=asset_id,
    )

    assert extract_res.valid is True
    assert extract_res.asset_id == asset_id
    assert extract_res.crc_passed is True
    assert extract_res.hmac_passed is True
    assert extract_res.status == "AUTHENTICATED"
    assert extract_res.nc == 1.0
    assert extract_res.ber == 0.0


@pytest.mark.unit
def test_baseline_dct_embedding_and_extraction(synthetic_test_images):
    """Verify end-to-end embedding and extraction using Baseline DCT."""
    image = synthetic_test_images["gradient"]
    asset_id = 456789
    secret_key = "dct_eval_key"

    embed_res = embed_watermark(
        image,
        asset_id=asset_id,
        secret_key=secret_key,
        algorithm="dct",
        alpha=0.12,
    )

    assert embed_res.metrics["psnr_db"] >= 38.0
    assert embed_res.metrics["ssim"] >= 0.95

    extract_res = extract_watermark(
        embed_res.watermarked_rgb,
        secret_key=secret_key,
        algorithm="dct",
        alpha=0.12,
        expected_asset_id=asset_id,
    )

    assert extract_res.valid is True
    assert extract_res.asset_id == asset_id
    assert extract_res.crc_passed is True
    assert extract_res.hmac_passed is True
    assert extract_res.nc == 1.0


@pytest.mark.unit
def test_baseline_svd_embedding_and_extraction(synthetic_test_images):
    """Verify end-to-end embedding and extraction using Baseline Spatial SVD."""
    image = synthetic_test_images["texture"]
    asset_id = 789012
    secret_key = "svd_eval_key"

    embed_res = embed_watermark(
        image,
        asset_id=asset_id,
        secret_key=secret_key,
        algorithm="svd",
        alpha=0.10,
    )

    assert embed_res.metrics["psnr_db"] >= 36.0
    assert embed_res.metrics["ssim"] >= 0.93

    extract_res = extract_watermark(
        embed_res.watermarked_rgb,
        secret_key=secret_key,
        algorithm="svd",
        alpha=0.10,
        expected_asset_id=asset_id,
    )

    assert extract_res.valid is True
    assert extract_res.asset_id == asset_id
    assert extract_res.crc_passed is True
    assert extract_res.hmac_passed is True
    assert extract_res.nc == 1.0


@pytest.mark.unit
def test_incorrect_key_fails_authentication(synthetic_test_images):
    """CRITICAL SECURITY TEST: Extraction using an incorrect key must NOT recover asset."""
    image = synthetic_test_images["texture"]
    asset_id = 999111
    correct_key = "genuine_creator_key"
    attacker_key = "hostile_adversary_wrong_key"

    embed_res = embed_watermark(
        image,
        asset_id=asset_id,
        secret_key=correct_key,
        algorithm="dct_svd",
        alpha=0.10,
    )

    extract_res = extract_watermark(
        embed_res.watermarked_rgb,
        secret_key=attacker_key,
        algorithm="dct_svd",
        alpha=0.10,
    )

    # The unauthorized key cannot decrypt/unpermute the blocks or pass HMAC
    assert extract_res.valid is False
    assert extract_res.hmac_passed is False
    assert extract_res.asset_id != asset_id


@pytest.mark.unit
def test_non_square_dimensions_supported(synthetic_test_images):
    """Ensure arbitrary non-square image dimensions are seamlessly padded and processed."""
    image = synthetic_test_images["non_square"]  # 160 x 224
    asset_id = 888222
    secret_key = "non_square_key"

    embed_res = embed_watermark(
        image,
        asset_id=asset_id,
        secret_key=secret_key,
        algorithm="dct_svd",
    )

    assert embed_res.watermarked_rgb.shape == image.shape

    extract_res = extract_watermark(
        embed_res.watermarked_rgb,
        secret_key=secret_key,
        algorithm="dct_svd",
    )

    assert extract_res.valid is True
    assert extract_res.asset_id == asset_id


@pytest.mark.unit
def test_alpha_tradeoff_behavior(synthetic_test_images):
    """Verify that increasing alpha changes PSNR trade-off predictably."""
    image = synthetic_test_images["gradient"]
    asset_id = 1234
    secret_key = "alpha_test_key"

    res_low = embed_watermark(image, asset_id, secret_key, algorithm="dct_svd", alpha=0.05)
    res_high = embed_watermark(image, asset_id, secret_key, algorithm="dct_svd", alpha=0.20)

    # Lower alpha should yield higher PSNR (less distortion)
    assert res_low.metrics["psnr_db"] > res_high.metrics["psnr_db"]
    # Both should maintain good visual fidelity
    assert res_low.metrics["psnr_db"] > 40.0
    assert res_high.metrics["psnr_db"] > 35.0


@pytest.mark.unit
def test_invalid_algorithm_rejected():
    dummy = np.zeros((128, 128, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Unknown watermarking algorithm"):
        embed_watermark(dummy, 1, "k", algorithm="unsupported_quantum_wavelet")
