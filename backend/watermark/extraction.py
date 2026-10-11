"""High-level unified image watermark extraction service.
"""
import time
from typing import Union, Optional, NamedTuple
from pathlib import Path
import numpy as np
from PIL import Image

from watermark.transforms import decode_image
from watermark.dct import extract_dct
from watermark.svd import extract_svd
from watermark.dct_svd import extract_dct_svd
from watermark.payload import PayloadVerificationResult, encode_payload
from watermark.metrics import calculate_nc, calculate_ber


class ExtractionResult(NamedTuple):
    valid: bool
    asset_id: Optional[int]
    timestamp_nonce: Optional[int]
    crc_passed: bool
    hmac_passed: bool
    status: str
    extracted_bits: np.ndarray
    nc: Optional[float]
    ber: Optional[float]
    algorithm: str
    elapsed_seconds: float


def extract_watermark(
    image_source: Union[bytes, str, Path, np.ndarray, Image.Image],
    secret_key: str,
    algorithm: str = "dct_svd",
    alpha: float = 0.10,
    expected_asset_id: Optional[int] = None,
) -> ExtractionResult:
    """Blindly extract and verify an embedded watermark from an image.

    Args:
        image_source: Suspect image bytes, path, numpy array, or PIL Image.
        secret_key: Secret key matching the embedder's key.
        algorithm: One of 'dct_svd' (default), 'dct', or 'svd'.
        alpha: Watermark strength factor matching embedding.
        expected_asset_id: Optional asset ID to compute ground-truth NC/BER comparison.

    Returns:
        ExtractionResult: Verification outcome, extracted asset ID, and security statuses.
    """
    start_time = time.perf_counter()

    # 1. Decode and validate suspect image
    image_rgb = decode_image(image_source)

    algo = algorithm.lower().strip()
    if algo in ("dct_svd", "dct-svd", "hybrid"):
        verification_result, raw_bits = extract_dct_svd(image_rgb, secret_key, alpha=alpha)
        canonical_algo = "dct_svd"
    elif algo in ("dct", "baseline_dct"):
        verification_result, raw_bits = extract_dct(image_rgb, secret_key)
        canonical_algo = "dct"
    elif algo in ("svd", "baseline_svd"):
        verification_result, raw_bits = extract_svd(image_rgb, secret_key, alpha=alpha)
        canonical_algo = "svd"
    else:
        raise ValueError(f"Unknown watermarking algorithm '{algorithm}'. Supported: dct_svd, dct, svd.")

    nc_val: Optional[float] = None
    ber_val: Optional[float] = None

    if expected_asset_id is not None:
        try:
            _, expected_bits = encode_payload(
                expected_asset_id, secret_key, timestamp_nonce=verification_result.timestamp_nonce or 0
            )
            nc_val = round(calculate_nc(expected_bits, raw_bits), 4)
            ber_val = round(calculate_ber(expected_bits, raw_bits), 4)
        except Exception:
            pass

    elapsed = round(time.perf_counter() - start_time, 4)

    return ExtractionResult(
        valid=verification_result.valid,
        asset_id=verification_result.asset_id,
        timestamp_nonce=verification_result.timestamp_nonce,
        crc_passed=verification_result.crc_passed,
        hmac_passed=verification_result.hmac_passed,
        status=verification_result.status,
        extracted_bits=raw_bits,
        nc=nc_val,
        ber=ber_val,
        algorithm=canonical_algo,
        elapsed_seconds=elapsed,
    )
