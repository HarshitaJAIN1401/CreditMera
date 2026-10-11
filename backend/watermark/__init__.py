"""CreditMera Watermark Engine Package.

Provides hybrid DCT-SVD, baseline DCT, and baseline SVD image watermarking,
color-space transformations, authenticated 128-bit payload coding, and
objective image quality evaluation metrics.
"""
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
from watermark.payload import (
    encode_payload,
    decode_payload,
    compute_crc16,
    compute_hmac32,
    derive_key_seed,
    scatter_and_repeat_bits,
    gather_and_vote_bits,
    PayloadVerificationResult,
    PAYLOAD_BIT_LENGTH,
    PAYLOAD_BYTE_LENGTH,
)
from watermark.metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_nc,
    calculate_ber,
    calculate_mse,
    evaluate_watermark_quality,
)
from watermark.dct import embed_dct, extract_dct
from watermark.svd import embed_svd, extract_svd
from watermark.dct_svd import embed_dct_svd, extract_dct_svd
from watermark.embedding import embed_watermark, EmbeddingResult
from watermark.extraction import extract_watermark, ExtractionResult

__all__ = [
    # Transforms
    "decode_image",
    "encode_image",
    "rgb_to_ycbcr",
    "ycbcr_to_rgb",
    "pad_to_block_multiple",
    "unpad_from_block_multiple",
    "split_blocks",
    "merge_blocks",
    "ImageValidationError",
    # Payload
    "encode_payload",
    "decode_payload",
    "compute_crc16",
    "compute_hmac32",
    "derive_key_seed",
    "scatter_and_repeat_bits",
    "gather_and_vote_bits",
    "PayloadVerificationResult",
    "PAYLOAD_BIT_LENGTH",
    "PAYLOAD_BYTE_LENGTH",
    # Metrics
    "calculate_psnr",
    "calculate_ssim",
    "calculate_nc",
    "calculate_ber",
    "calculate_mse",
    "evaluate_watermark_quality",
    # Algorithms
    "embed_dct",
    "extract_dct",
    "embed_svd",
    "extract_svd",
    "embed_dct_svd",
    "extract_dct_svd",
    # Unified Services
    "embed_watermark",
    "EmbeddingResult",
    "extract_watermark",
    "ExtractionResult",
]
