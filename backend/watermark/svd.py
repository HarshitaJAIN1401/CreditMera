"""Independent Baseline Spatial SVD Watermarking Implementation.

Decomposes 8x8 spatial luminance blocks via Singular Value Decomposition (SVD)
and embeds watermark bits into the principal singular value using Quantization
Index Modulation (QIM). Serves as an independent spatial-domain baseline.
"""
from typing import Tuple, Dict, Any
import numpy as np

from watermark.transforms import (
    rgb_to_ycbcr,
    ycbcr_to_rgb,
    pad_to_block_multiple,
    unpad_from_block_multiple,
    split_blocks,
    merge_blocks,
)
from watermark.payload import (
    scatter_and_repeat_bits,
    gather_and_vote_bits,
    encode_payload,
    decode_payload,
    PayloadVerificationResult,
)
from watermark.metrics import evaluate_watermark_quality


BASE_SVD_STEP = 200.0


def embed_svd(
    image: np.ndarray,
    asset_id: int,
    secret_key: str,
    alpha: float = 0.10,
    timestamp_nonce: int = 0,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Embed an authenticated asset ID watermark using pure spatial SVD QIM.

    Args:
        image: RGB input image (H, W, 3).
        asset_id: Unique integer asset identifier.
        secret_key: Secret key for payload authentication and permutation.
        alpha: Embedding strength factor (typically 0.05 - 0.25).
        timestamp_nonce: Registration timestamp or nonce.

    Returns:
        Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
            (watermarked_rgb, ground_truth_bits, quality_metrics)
    """
    raw_payload, payload_bits = encode_payload(asset_id, secret_key, timestamp_nonce)

    ycbcr = rgb_to_ycbcr(image)
    y_channel = ycbcr[:, :, 0]

    padded_y, orig_shape = pad_to_block_multiple(y_channel, block_size=8)
    h_pad, w_pad = padded_y.shape
    blocks = split_blocks(padded_y, block_size=8)
    num_blocks = blocks.shape[0]

    scattered_bits, repetition_factor = scatter_and_repeat_bits(
        payload_bits, num_blocks, secret_key
    )

    delta = max(alpha * BASE_SVD_STEP, 1.0)
    d0 = delta * 0.25
    d1 = delta * 0.75

    modified_blocks = np.empty_like(blocks)

    for i in range(num_blocks):
        block = blocks[i]
        # Full SVD decomposition: block = U @ np.diag(s) @ Vt
        u, s, vt = np.linalg.svd(block, full_matrices=True)
        bit = scattered_bits[i]
        d_val = d1 if bit == 1 else d0

        # QIM on principal singular value s[0] (strictly non-negative)
        s_mod = s.copy()
        k = max(0, int(np.round((s[0] - d_val) / delta)))
        s_mod[0] = k * delta + d_val

        # Reconstruct spatial block
        recon_block = u @ np.diag(s_mod) @ vt
        modified_blocks[i] = recon_block

    reconstructed_y = merge_blocks(modified_blocks, h_pad, w_pad, block_size=8)
    unpadded_y = unpad_from_block_multiple(reconstructed_y, orig_shape)

    watermarked_ycbcr = ycbcr.copy()
    watermarked_ycbcr[:, :, 0] = unpadded_y
    watermarked_rgb = ycbcr_to_rgb(watermarked_ycbcr)

    metrics = evaluate_watermark_quality(image, watermarked_rgb)
    metrics["repetition_factor"] = repetition_factor
    metrics["num_blocks"] = num_blocks
    metrics["algorithm"] = "Baseline-SVD"
    metrics["alpha"] = alpha

    return watermarked_rgb, payload_bits, metrics


def extract_svd(
    watermarked_image: np.ndarray,
    secret_key: str,
    alpha: float = 0.10,
) -> Tuple[PayloadVerificationResult, np.ndarray]:
    """Blindly extract watermark bits and verify payload using spatial SVD QIM.

    Args:
        watermarked_image: RGB image containing potential watermark.
        secret_key: Secret key for permutation and HMAC verification.
        alpha: Embedding strength parameter matching the embedder.

    Returns:
        Tuple[PayloadVerificationResult, np.ndarray]: (verification_result, raw_128_bits)
    """
    ycbcr = rgb_to_ycbcr(watermarked_image)
    y_channel = ycbcr[:, :, 0]

    padded_y, _ = pad_to_block_multiple(y_channel, block_size=8)
    blocks = split_blocks(padded_y, block_size=8)
    num_blocks = blocks.shape[0]

    delta = max(alpha * BASE_SVD_STEP, 1.0)
    d0 = delta * 0.25
    d1 = delta * 0.75

    extracted_block_bits = np.empty(num_blocks, dtype=np.float64)

    for i in range(num_blocks):
        _, s, _ = np.linalg.svd(blocks[i], full_matrices=False)
        val = s[0]
        # Distance to centroid d0 vs centroid d1 modulo delta
        remainder = val % delta
        dist0 = min(abs(remainder - d0), abs(remainder - (d0 + delta)), abs(remainder - (d0 - delta)))
        dist1 = min(abs(remainder - d1), abs(remainder - (d1 + delta)), abs(remainder - (d1 - delta)))

        extracted_block_bits[i] = 1.0 if dist1 < dist0 else 0.0

    voted_bits, confidence = gather_and_vote_bits(
        extracted_block_bits, num_blocks, secret_key
    )

    result = decode_payload(voted_bits, secret_key)
    return result, voted_bits
