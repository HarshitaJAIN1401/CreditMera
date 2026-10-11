"""Objective image quality and watermark correlation metrics.

Implements:
- PSNR: Peak Signal-to-Noise Ratio (dB)
- SSIM: Structural Similarity Index
- NC: Normalized Cross-Correlation for watermark bitstreams
- BER: Bit Error Rate
"""
from typing import Optional, Dict, Any
import numpy as np
from skimage.metrics import structural_similarity as compute_ssim_skimage


def calculate_mse(image_a: np.ndarray, image_b: np.ndarray) -> float:
    """Calculate Mean Squared Error between two images."""
    if image_a.shape != image_b.shape:
        raise ValueError(f"Shape mismatch: {image_a.shape} vs {image_b.shape}")
    arr_a = image_a.astype(np.float64)
    arr_b = image_b.astype(np.float64)
    return float(np.mean((arr_a - arr_b) ** 2))


def calculate_psnr(
    original: np.ndarray,
    watermarked: np.ndarray,
    max_val: float = 255.0,
) -> float:
    """Calculate Peak Signal-to-Noise Ratio (PSNR) in decibels (dB).

    Args:
        original: Reference image array (uint8 or float64).
        watermarked: Watermarked or modified image array.
        max_val: Maximum possible pixel intensity (255.0 for standard 8-bit).

    Returns:
        float: PSNR value in dB. Returns 100.0 dB if images are identical (MSE == 0).
    """
    mse = calculate_mse(original, watermarked)
    if mse == 0.0:
        return 100.0  # Perfect reconstruction indicator
    psnr = 10.0 * np.log10((max_val ** 2) / mse)
    return float(psnr)


def calculate_ssim(
    original: np.ndarray,
    watermarked: np.ndarray,
) -> float:
    """Calculate Structural Similarity Index (SSIM).

    Args:
        original: Reference image array (H, W) or (H, W, C).
        watermarked: Degraded/watermarked image array.

    Returns:
        float: SSIM index in range [-1.0, 1.0]. 1.0 indicates identical structure.
    """
    if original.shape != watermarked.shape:
        raise ValueError(f"Shape mismatch: {original.shape} vs {watermarked.shape}")

    orig = original.astype(np.float64)
    wm = watermarked.astype(np.float64)

    is_multichannel = (orig.ndim == 3 and orig.shape[2] in (3, 4))
    if is_multichannel:
        return float(compute_ssim_skimage(
            orig,
            wm,
            channel_axis=2,
            data_range=255.0,
        ))
    else:
        return float(compute_ssim_skimage(
            orig,
            wm,
            data_range=255.0,
        ))


def calculate_nc(
    watermark_a: np.ndarray,
    watermark_b: np.ndarray,
) -> float:
    """Calculate Normalized Correlation (NC / NCC) between two binary bit arrays.

    Uses bipolar mapping: bit 0 -> -1.0, bit 1 -> +1.0.
    In this representation, NC = 1.0 for perfect match, 0.0 for uncorrelated random noise,
    and -1.0 for completely inverted bits.

    Args:
        watermark_a: 1D array of bits (0 or 1).
        watermark_b: 1D array of bits (0 or 1).

    Returns:
        float: Correlation coefficient in [-1.0, 1.0].
    """
    a = np.asarray(watermark_a, dtype=np.float64).flatten()
    b = np.asarray(watermark_b, dtype=np.float64).flatten()

    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0

    a = a[:min_len]
    b = b[:min_len]

    # Map {0, 1} to {-1, +1}
    bipolar_a = 2.0 * (a > 0.5) - 1.0
    bipolar_b = 2.0 * (b > 0.5) - 1.0

    norm_a = np.linalg.norm(bipolar_a)
    norm_b = np.linalg.norm(bipolar_b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    nc = np.dot(bipolar_a, bipolar_b) / (norm_a * norm_b)
    return float(np.clip(nc, -1.0, 1.0))


def calculate_ber(
    original_bits: np.ndarray,
    extracted_bits: np.ndarray,
) -> float:
    """Calculate Bit Error Rate (BER).

    Args:
        original_bits: Ground-truth bits (0 or 1).
        extracted_bits: Extracted bits (0 or 1).

    Returns:
        float: BER in range [0.0, 1.0].
    """
    a = (np.asarray(original_bits).flatten() > 0.5).astype(np.uint8)
    b = (np.asarray(extracted_bits).flatten() > 0.5).astype(np.uint8)

    min_len = min(len(a), len(b))
    if min_len == 0:
        return 1.0

    errors = np.count_nonzero(a[:min_len] != b[:min_len])
    return float(errors / min_len)


def evaluate_watermark_quality(
    original_img: np.ndarray,
    watermarked_img: np.ndarray,
    original_bits: Optional[np.ndarray] = None,
    extracted_bits: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Compute consolidated perceptual quality and watermark recovery metrics."""
    mse_val = calculate_mse(original_img, watermarked_img)
    psnr_val = calculate_psnr(original_img, watermarked_img)
    ssim_val = calculate_ssim(original_img, watermarked_img)

    result = {
        "mse": round(mse_val, 4),
        "psnr_db": round(psnr_val, 2),
        "ssim": round(ssim_val, 4),
    }

    if original_bits is not None and extracted_bits is not None:
        result["nc"] = round(calculate_nc(original_bits, extracted_bits), 4)
        result["ber"] = round(calculate_ber(original_bits, extracted_bits), 4)

    return result
