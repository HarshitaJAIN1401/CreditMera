"""High-level unified image watermarking embedding service.
"""
import time
from typing import Union, Optional, Dict, Any, NamedTuple
from pathlib import Path
import numpy as np
from PIL import Image

from watermark.transforms import decode_image, encode_image
from watermark.dct import embed_dct
from watermark.svd import embed_svd
from watermark.dct_svd import embed_dct_svd
from watermark.metrics import calculate_nc, calculate_ber


class EmbeddingResult(NamedTuple):
    watermarked_bytes: bytes
    watermarked_rgb: np.ndarray
    original_rgb: np.ndarray
    asset_id: int
    ground_truth_bits: np.ndarray
    metrics: Dict[str, Any]
    algorithm: str
    alpha: float
    elapsed_seconds: float


def embed_watermark(
    image_source: Union[bytes, str, Path, np.ndarray, Image.Image],
    asset_id: int,
    secret_key: str,
    algorithm: str = "dct_svd",
    alpha: float = 0.10,
    timestamp_nonce: int = 0,
    output_format: str = "PNG",
) -> EmbeddingResult:
    """Embed an authenticated watermark into an image using the specified algorithm.

    Args:
        image_source: Input image bytes, path, numpy array, or PIL Image.
        asset_id: Numerical unique asset ID to embed.
        secret_key: Secret cryptographic key.
        algorithm: One of 'dct_svd' (default), 'dct', or 'svd'.
        alpha: Embedding strength factor.
        timestamp_nonce: Nonce or timestamp for payload freshness.
        output_format: Output image format (PNG, JPEG, etc.).

    Returns:
        EmbeddingResult: Complete result with watermarked bytes, arrays, and metrics.
    """
    start_time = time.perf_counter()

    # 1. Decode and validate input image
    original_rgb = decode_image(image_source)

    algo = algorithm.lower().strip()
    if algo in ("dct_svd", "dct-svd", "hybrid"):
        watermarked_rgb, ground_truth_bits, metrics = embed_dct_svd(
            original_rgb, asset_id, secret_key, alpha=alpha, timestamp_nonce=timestamp_nonce
        )
        canonical_algo = "dct_svd"
    elif algo in ("dct", "baseline_dct"):
        watermarked_rgb, ground_truth_bits, metrics = embed_dct(
            original_rgb, asset_id, secret_key, alpha=alpha, timestamp_nonce=timestamp_nonce
        )
        canonical_algo = "dct"
    elif algo in ("svd", "baseline_svd"):
        watermarked_rgb, ground_truth_bits, metrics = embed_svd(
            original_rgb, asset_id, secret_key, alpha=alpha, timestamp_nonce=timestamp_nonce
        )
        canonical_algo = "svd"
    else:
        raise ValueError(f"Unknown watermarking algorithm '{algorithm}'. Supported: dct_svd, dct, svd.")

    # Encode watermarked image to output format bytes
    watermarked_bytes = encode_image(watermarked_rgb, format=output_format)
    elapsed = round(time.perf_counter() - start_time, 4)
    metrics["elapsed_seconds"] = elapsed

    return EmbeddingResult(
        watermarked_bytes=watermarked_bytes,
        watermarked_rgb=watermarked_rgb,
        original_rgb=original_rgb,
        asset_id=asset_id,
        ground_truth_bits=ground_truth_bits,
        metrics=metrics,
        algorithm=canonical_algo,
        alpha=alpha,
        elapsed_seconds=elapsed,
    )
