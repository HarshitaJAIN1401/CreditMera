"""Unit tests for objective quality and watermark recovery metrics.
"""
import pytest
import numpy as np

from watermark.metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_nc,
    calculate_ber,
    calculate_mse,
    evaluate_watermark_quality,
)


@pytest.mark.unit
def test_psnr_identical_images():
    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    psnr = calculate_psnr(img, img)
    assert psnr == 100.0


@pytest.mark.unit
def test_psnr_known_noise():
    img1 = np.zeros((100, 100), dtype=np.uint8)
    # If every pixel difference is 1, MSE = 1.0.
    # PSNR = 10 * log10(255^2 / 1) = 10 * log10(65025) ~= 48.13 dB
    img2 = np.ones((100, 100), dtype=np.uint8)
    psnr = calculate_psnr(img1, img2)
    assert abs(psnr - 48.13) < 0.1


@pytest.mark.unit
def test_ssim_identical_images():
    img = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
    ssim = calculate_ssim(img, img)
    assert abs(ssim - 1.0) < 1e-5


@pytest.mark.unit
def test_ssim_decreases_with_noise():
    img = np.full((128, 128, 3), 128, dtype=np.uint8)
    noisy = np.clip(img.astype(np.int16) + np.random.randint(-40, 40, img.shape), 0, 255).astype(np.uint8)
    ssim = calculate_ssim(img, noisy)
    assert ssim < 0.90


@pytest.mark.unit
def test_nc_identical_bits():
    bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
    nc = calculate_nc(bits, bits)
    assert abs(nc - 1.0) < 1e-5


@pytest.mark.unit
def test_nc_inverted_bits():
    bits_a = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
    bits_b = 1 - bits_a
    nc = calculate_nc(bits_a, bits_b)
    assert abs(nc - (-1.0)) < 1e-5


@pytest.mark.unit
def test_ber_calculation():
    bits_a = np.array([1, 0, 1, 1], dtype=np.uint8)
    bits_b = np.array([1, 1, 1, 0], dtype=np.uint8)  # 2 errors out of 4
    ber = calculate_ber(bits_a, bits_b)
    assert ber == 0.5
