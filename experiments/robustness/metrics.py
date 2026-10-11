"""CreditMera Watermark Robustness Lab — Evaluation Metrics.

Computes:
1. Image Quality Degradation:
   - PSNR: Peak Signal-to-Noise Ratio (dB) against original watermarked reference.
   - SSIM: Structural Similarity Index.
2. Watermark Recovery Fidelity:
   - NC / NCC: Normalized Cross-Correlation in [-1.0, 1.0] (bipolar mapping).
   - BER: Bit Error Rate in [0.0, 1.0].
   - Payload Validity: Cryptographic authentication status (header, CRC, truncated HMAC).
   - Authentication Failures vs Extraction Failures.
3. Aggregations and Statistical Rates:
   - Watermark detection rate (NC >= threshold and valid).
   - False-positive detection rate on unwatermarked control images.
"""
from typing import Dict, Any, Optional, List
import numpy as np

from watermark.metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_nc,
    calculate_ber,
)


def compute_image_quality(
    watermarked_reference: np.ndarray,
    attacked_image: np.ndarray,
) -> Dict[str, float]:
    """Compute perceptual image fidelity metrics between reference and attacked images."""
    if watermarked_reference.shape != attacked_image.shape:
        raise ValueError(
            f"Image shape mismatch for metric calculation: "
            f"{watermarked_reference.shape} vs {attacked_image.shape}"
        )

    psnr = calculate_psnr(watermarked_reference, attacked_image)
    ssim = calculate_ssim(watermarked_reference, attacked_image)
    return {
        "psnr_db": round(float(psnr), 2),
        "ssim": round(float(ssim), 4),
    }


def compute_watermark_fidelity(
    extracted_bits: np.ndarray,
    ground_truth_bits: np.ndarray,
) -> Dict[str, float]:
    """Compute Normalized Correlation and Bit Error Rate between extracted and true bits."""
    nc_val = calculate_nc(ground_truth_bits, extracted_bits)
    ber_val = calculate_ber(ground_truth_bits, extracted_bits)
    return {
        "nc": round(float(nc_val), 4),
        "ber": round(float(ber_val), 4),
    }


def compute_aggregate_rates(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate detection, authentication, and error rates across experiment trials.

    Explicitly computes:
    - total_samples: Denominator of eligible evaluated trials.
    - authenticated_count: Number of trials passing magic, CRC, and HMAC authentication.
    - authentication_rate: Fraction of trials authenticated.
    - mean_nc: Mean Normalized Correlation.
    - mean_ber: Mean Bit Error Rate.
    - mean_psnr_db: Mean PSNR across trials.
    - mean_ssim: Mean SSIM across trials.
    """
    total = len(trials)
    if total == 0:
        return {
            "total_samples": 0,
            "authenticated_count": 0,
            "authentication_rate": 0.0,
            "mean_nc": 0.0,
            "mean_ber": 0.0,
            "mean_psnr_db": 0.0,
            "mean_ssim": 0.0,
        }

    auth_count = sum(1 for t in trials if t.get("payload_valid") is True)
    ncs = [t["nc"] for t in trials if t.get("nc") is not None]
    bers = [t["ber"] for t in trials if t.get("ber") is not None]
    psnrs = [t["psnr_db"] for t in trials if t.get("psnr_db") is not None]
    ssims = [t["ssim"] for t in trials if t.get("ssim") is not None]

    return {
        "total_samples": total,
        "authenticated_count": auth_count,
        "authentication_rate": round(auth_count / total, 4),
        "mean_nc": round(float(np.mean(ncs)), 4) if ncs else 0.0,
        "mean_ber": round(float(np.mean(bers)), 4) if bers else 0.0,
        "mean_psnr_db": round(float(np.mean(psnrs)), 2) if psnrs else 0.0,
        "mean_ssim": round(float(np.mean(ssims)), 4) if ssims else 0.0,
    }
