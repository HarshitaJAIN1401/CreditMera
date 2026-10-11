"""Unit tests for image decoding, validation, color-space, and block partitioning.
"""
import pytest
import numpy as np
from io import BytesIO
from PIL import Image

from watermark.transforms import (
    decode_image,
    encode_image,
    rgb_to_ycbcr,
    ycbcr_to_rgb,
    pad_to_block_multiple,
    unpad_from_block_multiple,
    split_blocks,
    merge_blocks,
    ImageValidationError,
)


@pytest.mark.unit
def test_decode_image_from_numpy():
    arr = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    decoded = decode_image(arr)
    assert decoded.shape == (128, 128, 3)
    assert decoded.dtype == np.uint8
    np.testing.assert_array_equal(arr, decoded)


@pytest.mark.unit
def test_decode_image_from_grayscale():
    gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    decoded = decode_image(gray)
    assert decoded.shape == (100, 100, 3)
    # R, G, B channels should match the grayscale values
    np.testing.assert_array_equal(decoded[:, :, 0], gray)
    np.testing.assert_array_equal(decoded[:, :, 1], gray)


@pytest.mark.unit
def test_decode_image_from_bytes():
    pil_img = Image.new("RGB", (128, 128), color=(200, 100, 50))
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    decoded = decode_image(buf.getvalue())
    assert decoded.shape == (128, 128, 3)
    assert decoded[0, 0, 0] == 200
    assert decoded[0, 0, 1] == 100
    assert decoded[0, 0, 2] == 50


@pytest.mark.unit
def test_decode_image_too_small_raises():
    small = np.zeros((32, 32, 3), dtype=np.uint8)
    with pytest.raises(ImageValidationError, match="too small"):
        decode_image(small, min_dim=64)


@pytest.mark.unit
def test_decode_empty_bytes_raises():
    with pytest.raises(ImageValidationError, match="Empty image"):
        decode_image(b"")


@pytest.mark.unit
def test_rgb_ycbcr_roundtrip_precision():
    """Verify that RGB -> YCbCr -> RGB preserves image with minimal roundoff error."""
    rng = np.random.default_rng(42)
    original = rng.integers(0, 256, size=(128, 128, 3), dtype=np.uint8)

    ycbcr = rgb_to_ycbcr(original)
    reconstructed = ycbcr_to_rgb(ycbcr)

    diff = np.abs(original.astype(np.float64) - reconstructed.astype(np.float64))
    # Standard rounding error should never exceed 1 intensity value
    assert np.max(diff) <= 1.0
    # Mean absolute error across all pixels should be negligible (< 0.1)
    assert np.mean(diff) < 0.1


@pytest.mark.unit
def test_padding_and_unpadding_arbitrary_dimensions():
    # Non-multiple of 8 dimensions: 133 x 95
    channel = np.random.rand(133, 95)
    padded, orig_shape = pad_to_block_multiple(channel, block_size=8)

    assert padded.shape == (136, 96)  # 136 = 17*8, 96 = 12*8
    assert orig_shape == (133, 95)

    unpadded = unpad_from_block_multiple(padded, orig_shape)
    assert unpadded.shape == (133, 95)
    np.testing.assert_array_equal(channel, unpadded)


@pytest.mark.unit
def test_split_and_merge_blocks_roundtrip():
    h, w = 64, 48
    channel = np.arange(h * w, dtype=np.float64).reshape((h, w))
    blocks = split_blocks(channel, block_size=8)

    expected_num_blocks = (64 // 8) * (48 // 8)  # 8 * 6 = 48
    assert blocks.shape == (expected_num_blocks, 8, 8)

    merged = merge_blocks(blocks, h, w, block_size=8)
    np.testing.assert_array_equal(channel, merged)
