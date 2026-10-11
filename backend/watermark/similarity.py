"""CreditMera Visual Similarity Detection Engine.

Provides perceptual image similarity analysis completely independent of the
cryptographic DCT-SVD watermark engine:
- Perceptual Hash (pHash) based on 32x32 DCT low-frequency energy.
- Difference Hash (dHash) based on horizontal intensity gradients.
- Structural Similarity Index (SSIM) on aspect-normalized representations.
- Calibrated composite visual similarity scoring with documented decision tiers.

IMPORTANT: Visual similarity indicates statistical resemblance under geometric/perceptual
transformations (resize, compression, slight color shifts) and does NOT constitute
legal proof of copyright infringement or ownership.
"""
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image
from scipy.fftpack import dct
from skimage.metrics import structural_similarity as compute_ssim_skimage


def to_pil_grayscale(image: np.ndarray) -> Image.Image:
    """Ensure array is properly converted to a PIL 8-bit Grayscale Image."""
    if isinstance(image, Image.Image):
        return image.convert("L")
    if not isinstance(image, np.ndarray):
        raise TypeError(f"Expected numpy array or PIL Image, got {type(image)}")
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if len(image.shape) == 2:
        return Image.fromarray(image, mode="L")
    return Image.fromarray(image).convert("L")


def compute_phash(image: np.ndarray, hash_size: int = 8, highfreq_factor: int = 4) -> str:
    """Compute 64-bit Perceptual Hash (pHash) using 2D Discrete Cosine Transform.

    Args:
        image: RGB or grayscale image array.
        hash_size: Dimensions of the low-frequency square to sample (default 8 -> 64-bit hash).
        highfreq_factor: Scaling factor for DCT computation resolution (default 4 -> 32x32).

    Returns:
        str: 16-character hexadecimal representation of the 64-bit pHash.
    """
    pil_gray = to_pil_grayscale(image)
    img_size = hash_size * highfreq_factor  # 32x32
    # High-quality anti-aliasing downsampling prevents high-frequency folding
    resized = pil_gray.resize((img_size, img_size), Image.Resampling.LANCZOS)
    arr = np.asarray(resized, dtype=np.float64)

    # 2D DCT (orthogonal normalization)
    d = dct(dct(arr, axis=0, norm="ortho"), axis=1, norm="ortho")

    # Extract top-left 8x8 low-frequency coefficients
    low_freq = d[:hash_size, :hash_size]

    # Compute median excluding the DC term at [0, 0] to maintain contrast invariance
    dc_free_vals = low_freq.flatten()[1:]
    median_val = float(np.median(dc_free_vals))

    # Construct bitmask where 1 indicates coefficient > median
    diff = low_freq > median_val
    diff[0, 0] = False  # Explicitly zero out DC component

    # Convert 64 boolean bits to 16 hex characters
    int_val = 0
    for bit in diff.flatten():
        int_val = (int_val << 1) | int(bit)
    return f"{int_val:016x}"


def compute_dhash(image: np.ndarray, hash_size: int = 8) -> str:
    """Compute 64-bit Difference Hash (dHash) tracking horizontal intensity gradients.

    Args:
        image: RGB or grayscale image array.
        hash_size: Grid height and output bit dimension (default 8 -> 64 bits from (8, 9) grid).

    Returns:
        str: 16-character hexadecimal representation of the 64-bit dHash.
    """
    pil_gray = to_pil_grayscale(image)
    # Resize to (hash_size + 1, hash_size) -> (9, 8) to compare adjacent columns
    resized = pil_gray.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    arr = np.asarray(resized, dtype=np.float64)

    # Compute horizontal difference: col[x + 1] > col[x]
    diff = arr[:, 1:] > arr[:, :-1]

    int_val = 0
    for bit in diff.flatten():
        int_val = (int_val << 1) | int(bit)
    return f"{int_val:016x}"


def hamming_distance(hex_hash_a: str, hex_hash_b: str) -> int:
    """Calculate the Hamming distance (number of bit differences) between two 64-bit hex hashes."""
    val_a = int(hex_hash_a, 16)
    val_b = int(hex_hash_b, 16)
    xor_val = val_a ^ val_b
    return bin(xor_val).count("1")


def hash_similarity(hex_hash_a: str, hex_hash_b: str, max_bits: int = 64) -> float:
    """Convert Hamming distance into normalized similarity score in range [0.0, 1.0]."""
    dist = hamming_distance(hex_hash_a, hex_hash_b)
    return float(max(0.0, min(1.0, 1.0 - (dist / float(max_bits)))))


def normalize_image_for_ssim(
    image: np.ndarray,
    target_size: Tuple[int, int] = (256, 256)
) -> np.ndarray:
    """Aspect-ratio-preserving padding and normalization to target size for SSIM."""
    if isinstance(image, Image.Image):
        pil_img = image.convert("RGB")
    else:
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        if len(image.shape) == 2:
            pil_img = Image.fromarray(image, mode="L").convert("RGB")
        else:
            pil_img = Image.fromarray(image, mode="RGB")

    target_w, target_h = target_size
    w, h = pil_img.size

    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Create letterboxed canvas with neutral gray background (128)
    canvas = Image.new("RGB", (target_w, target_h), (128, 128, 128))
    pad_left = (target_w - new_w) // 2
    pad_top = (target_h - new_h) // 2
    canvas.paste(resized, (pad_left, pad_top))

    return np.asarray(canvas.convert("L"), dtype=np.uint8)


def compute_normalized_ssim(image_a: np.ndarray, image_b: np.ndarray) -> float:
    """Compute Structural Similarity Index (SSIM) between two arbitrary-sized images."""
    gray_a = normalize_image_for_ssim(image_a)
    gray_b = normalize_image_for_ssim(image_b)

    ssim_val, _ = compute_ssim_skimage(gray_a, gray_b, full=True)
    return float(max(0.0, min(1.0, ssim_val)))


def evaluate_similarity_tier(composite_score: float, phash_dist: int) -> Tuple[str, str]:
    """Calibrate decision tier and descriptive explanation based on composite similarity."""
    if composite_score >= 0.90 and phash_dist <= 6:
        return (
            "EXACT_OR_NEAR_EXACT",
            "Images exhibit near-identical visual structure and perceptual hash alignment. "
            "Likely identical source with minor compression, re-saving, or format conversion."
        )
    elif composite_score >= 0.75 and phash_dist <= 14:
        return (
            "HIGH_SIMILARITY",
            "High structural and perceptual resemblance detected. "
            "May represent a cropped, resized, re-encoded, or mildly modified version of the reference work."
        )
    elif composite_score >= 0.55 and phash_dist <= 24:
        return (
            "MODERATE_SIMILARITY",
            "Moderate perceptual correlation found. Images share noticeable composition, tone, or structural elements, "
            "but differ significantly in details, cropping, or post-processing."
        )
    else:
        return (
            "LOW_SIMILARITY",
            "Low visual correlation. Images possess distinct perceptual signatures and structural features."
        )


def compare_images(
    image_a: np.ndarray,
    image_b: np.ndarray,
    weights: Tuple[float, float, float] = (0.40, 0.30, 0.30)
) -> Dict[str, Any]:
    """Execute complete visual similarity analysis between two images."""
    w_phash, w_dhash, w_ssim = weights

    # 1. Perceptual Hash
    phash_a = compute_phash(image_a)
    phash_b = compute_phash(image_b)
    dist_phash = hamming_distance(phash_a, phash_b)
    sim_phash = hash_similarity(phash_a, phash_b)

    # 2. Difference Hash
    dhash_a = compute_dhash(image_a)
    dhash_b = compute_dhash(image_b)
    dist_dhash = hamming_distance(dhash_a, dhash_b)
    sim_dhash = hash_similarity(dhash_a, dhash_b)

    # 3. Structural Similarity Index
    sim_ssim = compute_normalized_ssim(image_a, image_b)

    # 4. Composite Calibrated Score
    composite = (w_phash * sim_phash) + (w_dhash * sim_dhash) + (w_ssim * sim_ssim)
    composite = float(round(max(0.0, min(1.0, composite)), 4))

    tier, explanation = evaluate_similarity_tier(composite, dist_phash)

    h_a, w_a = image_a.shape[:2] if hasattr(image_a, "shape") else (image_a.height, image_a.width)
    h_b, w_b = image_b.shape[:2] if hasattr(image_b, "shape") else (image_b.height, image_b.width)

    return {
        "composite_similarity_score": composite,
        "similarity_percentage": round(composite * 100.0, 1),
        "similarity_tier": tier,
        "explanation": explanation,
        "metrics": {
            "phash": {
                "hash_a": phash_a,
                "hash_b": phash_b,
                "hamming_distance": dist_phash,
                "similarity_score": round(sim_phash, 4),
            },
            "dhash": {
                "hash_a": dhash_a,
                "hash_b": dhash_b,
                "hamming_distance": dist_dhash,
                "similarity_score": round(sim_dhash, 4),
            },
            "ssim": {
                "score": round(sim_ssim, 4),
            },
        },
        "dimensions": {
            "image_a": [int(w_a), int(h_a)],
            "image_b": [int(w_b), int(h_b)],
        },
        "legal_disclaimer": (
            "Technical visual similarity is an algorithmic estimate of perceptual correlation. "
            "It does not constitute conclusive proof of copyright infringement, original authorship, "
            "or unauthorized reproduction. Visual similarity findings should be corroborated with "
            "cryptographic watermark authentication and verified registration receipts."
        ),
    }
