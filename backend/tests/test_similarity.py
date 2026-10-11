"""Unit and integration tests for CreditMera Visual Similarity Detection Engine."""
import io
import numpy as np
from PIL import Image, ImageDraw
import pytest

from watermark.similarity import (
    compute_phash,
    compute_dhash,
    hamming_distance,
    hash_similarity,
    compute_normalized_ssim,
    compare_images,
)


def create_test_artwork(width=256, height=256) -> np.ndarray:
    """Generate a rich test scene with defined geometric forms, gradients, and colors."""
    img = Image.new("RGB", (width, height), color=(210, 225, 245))
    draw = ImageDraw.Draw(img)
    # Background gradient or elements
    draw.rectangle([40, 40, 160, 160], fill=(25, 45, 95))
    draw.ellipse([90, 90, 210, 210], fill=(215, 65, 35))
    draw.line([(0, height), (width, 0)], fill=(240, 190, 40), width=4)
    return np.array(img)


def test_hash_format_and_length():
    img = create_test_artwork(128, 128)
    phash = compute_phash(img)
    dhash = compute_dhash(img)

    assert isinstance(phash, str)
    assert len(phash) == 16
    int(phash, 16)  # Verify valid hex

    assert isinstance(dhash, str)
    assert len(dhash) == 16
    int(dhash, 16)


def test_identical_image_similarity():
    img = create_test_artwork(256, 256)
    result = compare_images(img, img)

    assert result["composite_similarity_score"] >= 0.98
    assert result["similarity_tier"] == "EXACT_OR_NEAR_EXACT"
    assert result["metrics"]["phash"]["hamming_distance"] == 0
    assert result["metrics"]["dhash"]["hamming_distance"] == 0
    assert result["metrics"]["ssim"]["score"] >= 0.99
    assert "legal_disclaimer" in result


def test_resized_image_resilience():
    img_orig = create_test_artwork(256, 256)
    # Downscale by 50%
    img_pil = Image.fromarray(img_orig).resize((128, 128), Image.Resampling.BILINEAR)
    img_downscaled = np.array(img_pil)

    result = compare_images(img_orig, img_downscaled)

    # pHash is invariant to downscaling
    assert result["metrics"]["phash"]["hamming_distance"] <= 4
    assert result["composite_similarity_score"] >= 0.85
    assert result["similarity_tier"] in ("EXACT_OR_NEAR_EXACT", "HIGH_SIMILARITY")


def test_compressed_image_resilience():
    img_orig = create_test_artwork(256, 256)
    # Simulate JPEG compression quality 50
    buf = io.BytesIO()
    Image.fromarray(img_orig).save(buf, format="JPEG", quality=50)
    buf.seek(0)
    img_jpeg = np.array(Image.open(buf))

    result = compare_images(img_orig, img_jpeg)

    assert result["metrics"]["phash"]["hamming_distance"] <= 6
    assert result["composite_similarity_score"] >= 0.80
    assert result["similarity_tier"] in ("EXACT_OR_NEAR_EXACT", "HIGH_SIMILARITY")


def test_unrelated_distinct_images():
    img_a = create_test_artwork(128, 128)
    # Uniform noise / completely different pattern
    rng = np.random.default_rng(1234)
    img_b = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8)

    result = compare_images(img_a, img_b)

    assert result["metrics"]["phash"]["hamming_distance"] >= 15
    assert result["composite_similarity_score"] < 0.60
    assert result["similarity_tier"] == "LOW_SIMILARITY"


def test_aspect_ratio_difference_handling():
    # 200x100 vs 100x200
    img_wide = create_test_artwork(200, 100)
    img_tall = create_test_artwork(100, 200)

    result = compare_images(img_wide, img_tall)
    assert 0.0 <= result["composite_similarity_score"] <= 1.0
    assert "similarity_tier" in result
