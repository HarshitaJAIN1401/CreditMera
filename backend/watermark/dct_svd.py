"""Hybrid DCT-SVD Watermarking Engine.

Combines 2D Discrete Cosine Transform (DCT) and Singular Value Decomposition (SVD)
applied specifically to the 4x4 mid-frequency DCT sub-band (excluding DC and extreme
high-frequency noise). This achieves high visual fidelity (PSNR > 45 dB, SSIM > 0.99)
and distinct frequency-domain robustness characteristics compared to pure spatial SVD.
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
from watermark.dct import dct2, idct2
from watermark.metrics import evaluate_watermark_quality


BASE_DCT_SVD_STEP = 80.0
# Mid-frequency sub-band slice: 4x4 submatrix [1:5, 1:5] of the 8x8 DCT block
SUB_START = 1
SUB_END = 5


def embed_dct_svd(
    image: np.ndarray,
    asset_id: int,
    secret_key: str,
    alpha: float = 0.10,
    timestamp_nonce: int = 0,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Embed an authenticated watermark using hybrid DCT-SVD with QIM on mid-frequencies.

    Algorithm steps:
    1. Encode asset ID, timestamp, CRC-16, and truncated HMAC-SHA256 into 128-bit payload.
    2. Convert RGB image to BT.601 YCbCr and extract luminance channel Y.
    3. Partition Y into 8x8 non-overlapping blocks.
    4. Scatter and repeat payload bits across blocks using key-derived pseudo-random permutation.
    5. For each block:
       a. Compute 2D-DCT: D = DCT2(B)
       b. Extract 4x4 mid-frequency sub-band: D_mid = D[1:5, 1:5] (DC and high frequencies untouched)
       c. Compute SVD of mid-frequency sub-band: D_mid = U_mid @ diag(S_mid) @ Vt_mid
       d. Modulate principal singular value S_mid[0] according to bit via QIM:
          S_mid'[0] = round((S_mid[0] - d_w) / delta) * delta + d_w
       e. Reconstruct mid-frequency sub-band: D_mid' = U_mid @ diag(S_mid') @ Vt_mid
       f. Insert D_mid' back into D[1:5, 1:5]
       g. Compute 2D-IDCT: B' = IDCT2(D')
    6. Merge modified blocks, unpad, and convert back to RGB.

    Args:
        image: RGB input image array of shape (H, W, 3).
        asset_id: Unique integer asset identifier.
        secret_key: Secret key string for key derivation and HMAC.
        alpha: Watermark strength factor (0.02 - 0.30). Default 0.10.
        timestamp_nonce: 32-bit timestamp or nonce.

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

    delta = max(alpha * BASE_DCT_SVD_STEP, 1.0)
    d0 = delta * 0.25
    d1 = delta * 0.75

    modified_blocks = np.empty_like(blocks)

    for i in range(num_blocks):
        block = blocks[i]
        d_block = dct2(block)

        # SVD on 4x4 mid-frequency sub-band
        sub = d_block[SUB_START:SUB_END, SUB_START:SUB_END]
        u_sub, s_sub, vt_sub = np.linalg.svd(sub, full_matrices=True)
        bit = scattered_bits[i]
        d_val = d1 if bit == 1 else d0

        # QIM on principal singular value of mid-frequency sub-band (strictly non-negative)
        s_mod = s_sub.copy()
        k = max(0, int(np.round((s_sub[0] - d_val) / delta)))
        s_mod[0] = k * delta + d_val

        # Inverse SVD back to mid-frequency sub-band
        sub_recon = u_sub @ np.diag(s_mod) @ vt_sub
        d_block[SUB_START:SUB_END, SUB_START:SUB_END] = sub_recon

        # Inverse DCT back to spatial domain
        modified_blocks[i] = idct2(d_block)

    reconstructed_y = merge_blocks(modified_blocks, h_pad, w_pad, block_size=8)
    unpadded_y = unpad_from_block_multiple(reconstructed_y, orig_shape)

    watermarked_ycbcr = ycbcr.copy()
    watermarked_ycbcr[:, :, 0] = unpadded_y
    watermarked_rgb = ycbcr_to_rgb(watermarked_ycbcr)

    metrics = evaluate_watermark_quality(image, watermarked_rgb)
    metrics["repetition_factor"] = repetition_factor
    metrics["num_blocks"] = num_blocks
    metrics["algorithm"] = "Hybrid-DCT-SVD"
    metrics["alpha"] = alpha

    return watermarked_rgb, payload_bits, metrics


def extract_dct_svd(
    watermarked_image: np.ndarray,
    secret_key: str,
    alpha: float = 0.10,
) -> Tuple[PayloadVerificationResult, np.ndarray]:
    """Blindly extract watermark bits and verify payload using hybrid DCT-SVD on mid-frequencies.

    Args:
        watermarked_image: RGB image suspected of carrying watermark.
        secret_key: Secret key matching the embedder's key.
        alpha: Strength factor matching the embedder's setting.

    Returns:
        Tuple[PayloadVerificationResult, np.ndarray]: (verification_result, raw_128_bits)
    """
    ycbcr = rgb_to_ycbcr(watermarked_image)
    y_channel = ycbcr[:, :, 0]

    padded_y, _ = pad_to_block_multiple(y_channel, block_size=8)
    blocks = split_blocks(padded_y, block_size=8)
    num_blocks = blocks.shape[0]

    delta = max(alpha * BASE_DCT_SVD_STEP, 1.0)
    d0 = delta * 0.25
    d1 = delta * 0.75

    extracted_block_bits = np.empty(num_blocks, dtype=np.float64)

    for i in range(num_blocks):
        d_block = dct2(blocks[i])
        sub = d_block[SUB_START:SUB_END, SUB_START:SUB_END]
        _, s_sub, _ = np.linalg.svd(sub, full_matrices=False)
        val = s_sub[0]

        # Circular distance to d0 and d1 modulo delta
        remainder = val % delta
        dist0 = min(abs(remainder - d0), abs(remainder - (d0 + delta)), abs(remainder - (d0 - delta)))
        dist1 = min(abs(remainder - d1), abs(remainder - (d1 + delta)), abs(remainder - (d1 - delta)))

        extracted_block_bits[i] = 1.0 if dist1 < dist0 else 0.0

    voted_bits, confidence = gather_and_vote_bits(
        extracted_block_bits, num_blocks, secret_key
    )

    result = decode_payload(voted_bits, secret_key)
    return result, voted_bits
