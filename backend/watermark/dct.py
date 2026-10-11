"""Independent Baseline DCT Watermarking Implementation.

Embeds watermark bits into mid-frequency 2D-DCT coefficients of 8x8 blocks using
differential coefficient modulation. This serves as an independent baseline algorithm
for comparative evaluation against SVD and hybrid DCT-SVD.
"""
from typing import Tuple, Dict, Any, Optional
import numpy as np
from scipy.fft import dct, idct

from watermark.transforms import (
    decode_image,
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


def dct2(block: np.ndarray) -> np.ndarray:
    """Compute 2D Discrete Cosine Transform with orthonormal scaling."""
    return dct(dct(block.T, norm="ortho").T, norm="ortho")


def idct2(block: np.ndarray) -> np.ndarray:
    """Compute 2D Inverse Discrete Cosine Transform with orthonormal scaling."""
    return idct(idct(block.T, norm="ortho").T, norm="ortho")


# Standard mid-frequency coefficient coordinates
COORD_1 = (4, 3)
COORD_2 = (3, 4)
BASE_DELTA_SCALE = 30.0


def embed_dct(
    image: np.ndarray,
    asset_id: int,
    secret_key: str,
    alpha: float = 0.10,
    timestamp_nonce: int = 0,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Embed an authenticated asset ID watermark using baseline DCT.

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

    # Convert to YCbCr and extract luminance Y
    ycbcr = rgb_to_ycbcr(image)
    y_channel = ycbcr[:, :, 0]

    # Pad Y channel to multiple of 8
    padded_y, orig_shape = pad_to_block_multiple(y_channel, block_size=8)
    h_pad, w_pad = padded_y.shape
    blocks = split_blocks(padded_y, block_size=8)
    num_blocks = blocks.shape[0]

    # Key-controlled scattering of repeated payload bits
    scattered_bits, repetition_factor = scatter_and_repeat_bits(
        payload_bits, num_blocks, secret_key
    )

    delta = max(alpha * BASE_DELTA_SCALE, 1.0)
    modified_blocks = np.empty_like(blocks)

    for i in range(num_blocks):
        block = blocks[i]
        d_block = dct2(block)
        bit = scattered_bits[i]

        c1 = d_block[COORD_1]
        c2 = d_block[COORD_2]

        # Differential modulation:
        # bit 0: c1 - c2 >= delta
        # bit 1: c2 - c1 >= delta
        avg = (c1 + c2) / 2.0
        if bit == 0:
            if (c1 - c2) < delta:
                c1 = avg + delta / 2.0
                c2 = avg - delta / 2.0
        else:
            if (c2 - c1) < delta:
                c2 = avg + delta / 2.0
                c1 = avg - delta / 2.0

        d_block[COORD_1] = c1
        d_block[COORD_2] = c2

        modified_blocks[i] = idct2(d_block)

    # Reconstruct luminance channel
    reconstructed_y = merge_blocks(modified_blocks, h_pad, w_pad, block_size=8)
    unpadded_y = unpad_from_block_multiple(reconstructed_y, orig_shape)

    watermarked_ycbcr = ycbcr.copy()
    watermarked_ycbcr[:, :, 0] = unpadded_y
    watermarked_rgb = ycbcr_to_rgb(watermarked_ycbcr)

    metrics = evaluate_watermark_quality(image, watermarked_rgb)
    metrics["repetition_factor"] = repetition_factor
    metrics["num_blocks"] = num_blocks
    metrics["algorithm"] = "Baseline-DCT"
    metrics["alpha"] = alpha

    return watermarked_rgb, payload_bits, metrics


def extract_dct(
    watermarked_image: np.ndarray,
    secret_key: str,
) -> Tuple[PayloadVerificationResult, np.ndarray]:
    """Blindly extract watermark bits and verify payload using baseline DCT.

    Args:
        watermarked_image: RGB image containing potential watermark.
        secret_key: Secret key for permutation and HMAC verification.

    Returns:
        Tuple[PayloadVerificationResult, np.ndarray]: (verification_result, raw_128_bits)
    """
    ycbcr = rgb_to_ycbcr(watermarked_image)
    y_channel = ycbcr[:, :, 0]

    padded_y, _ = pad_to_block_multiple(y_channel, block_size=8)
    blocks = split_blocks(padded_y, block_size=8)
    num_blocks = blocks.shape[0]

    extracted_block_bits = np.empty(num_blocks, dtype=np.float64)

    for i in range(num_blocks):
        d_block = dct2(blocks[i])
        c1 = d_block[COORD_1]
        c2 = d_block[COORD_2]
        # Soft confidence: difference mapped through sigmoid or hard step
        extracted_block_bits[i] = 1.0 if c2 > c1 else 0.0

    # Un-permute and majority vote
    voted_bits, confidence = gather_and_vote_bits(
        extracted_block_bits, num_blocks, secret_key
    )

    result = decode_payload(voted_bits, secret_key)
    return result, voted_bits
