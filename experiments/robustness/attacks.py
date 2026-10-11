"""CreditMera Watermark Robustness Lab — Attack Transformations.

Implements standard benchmark image distortions to evaluate watermark survival:
1. Lossy JPEG compression (qualities 95, 85, 75, 60, 40).
2. Geometric resizing / scaling (75%, 50%, 25%) with bilinear/bicubic restoration.
3. Gaussian blurring (documented filter radii/sigmas).
4. Additive Gaussian noise (documented standard deviations with deterministic PRNG seed).
5. Photometric brightness and contrast variations.
6. Cropping (10%, 25%, 50%) with coordinate canvas restoration.
7. Rotation (sub-degree/small angles: 1°, 2°, 5°, and right angle: 90°).

Every transformation:
- Modifies the input image without altering original sources.
- Preserves output dimensions and 3-channel RGB uint8 format.
- Records explicit parameters and execution metadata.
- Validates parameter boundaries and fails safely on invalid inputs.
"""
import io
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance


def _ensure_rgb_image(image_input: Any) -> Image.Image:
    """Validate and convert input to PIL Image in RGB format."""
    if isinstance(image_input, np.ndarray):
        if image_input.ndim != 3 or image_input.shape[2] != 3:
            raise ValueError(f"Expected 3D RGB array of shape (H, W, 3), got {image_input.shape}")
        if image_input.dtype != np.uint8:
            image_input = np.clip(image_input, 0, 255).astype(np.uint8)
        return Image.fromarray(image_input, mode="RGB")
    elif isinstance(image_input, Image.Image):
        return image_input.convert("RGB")
    else:
        raise TypeError(f"Unsupported image type: {type(image_input)}")


def apply_jpeg_compression(
    image: np.ndarray,
    quality: int = 85,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Simulate lossy JPEG compression through an in-memory byte stream.

    Args:
        image: RGB numpy array (H, W, 3) uint8.
        quality: JPEG compression quality integer in [1, 100].

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (compressed_rgb, metadata)
    """
    if not (1 <= quality <= 100):
        raise ValueError(f"JPEG quality must be between 1 and 100, got {quality}")

    pil_img = _ensure_rgb_image(image)
    orig_shape = image.shape

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    compressed_bytes = buf.getvalue()

    decompressed = Image.open(io.BytesIO(compressed_bytes)).convert("RGB")
    result_array = np.array(decompressed, dtype=np.uint8)

    metadata = {
        "attack": "jpeg_compression",
        "quality": quality,
        "compressed_size_bytes": len(compressed_bytes),
        "original_shape": orig_shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_resize(
    image: np.ndarray,
    scale: float = 0.50,
    interpolation: str = "bicubic",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Downsample image by scale factor, then restore to original dimensions.

    Args:
        image: RGB numpy array (H, W, 3).
        scale: Scaling factor in range (0.05, 1.0) (e.g. 0.75, 0.50, 0.25).
        interpolation: 'bilinear' or 'bicubic'.

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (resized_restored_rgb, metadata)
    """
    if not (0.05 <= scale <= 1.0):
        raise ValueError(f"Resize scale must be in range [0.05, 1.0], got {scale}")

    interp_map = {
        "bicubic": Image.Resampling.BICUBIC,
        "bilinear": Image.Resampling.BILINEAR,
        "nearest": Image.Resampling.NEAREST,
    }
    resample = interp_map.get(interpolation.lower())
    if resample is None:
        raise ValueError(f"Unsupported interpolation '{interpolation}'. Choose 'bicubic' or 'bilinear'.")

    pil_img = _ensure_rgb_image(image)
    orig_w, orig_h = pil_img.size

    down_w = max(int(orig_w * scale), 8)
    down_h = max(int(orig_h * scale), 8)

    downscaled = pil_img.resize((down_w, down_h), resample=resample)
    restored = downscaled.resize((orig_w, orig_h), resample=resample)
    result_array = np.array(restored, dtype=np.uint8)

    metadata = {
        "attack": "resize",
        "scale": scale,
        "intermediate_dimensions": (down_w, down_h),
        "interpolation": interpolation,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_gaussian_blur(
    image: np.ndarray,
    radius: float = 1.0,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Apply Gaussian low-pass spatial filtering.

    Args:
        image: RGB numpy array (H, W, 3).
        radius: Blur standard deviation / kernel radius (radius >= 0.0).

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (blurred_rgb, metadata)
    """
    if radius < 0.0:
        raise ValueError(f"Gaussian blur radius must be non-negative, got {radius}")

    pil_img = _ensure_rgb_image(image)
    if radius > 0.0:
        blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=radius))
    else:
        blurred = pil_img.copy()

    result_array = np.array(blurred, dtype=np.uint8)
    metadata = {
        "attack": "gaussian_blur",
        "radius": radius,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_gaussian_noise(
    image: np.ndarray,
    std: float = 10.0,
    seed: Optional[int] = 2026,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Add zero-mean Gaussian noise with fixed seed for reproducibility.

    Args:
        image: RGB numpy array (H, W, 3) uint8.
        std: Noise standard deviation in intensity units (std >= 0.0).
        seed: Random seed for deterministic reproducibility.

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (noisy_rgb, metadata)
    """
    if std < 0.0:
        raise ValueError(f"Noise standard deviation must be non-negative, got {std}")

    rng = np.random.default_rng(seed)
    noise = rng.normal(loc=0.0, scale=std, size=image.shape)
    noisy_float = image.astype(np.float64) + noise
    result_array = np.clip(noisy_float, 0.0, 255.0).astype(np.uint8)

    metadata = {
        "attack": "gaussian_noise",
        "std": std,
        "seed": seed,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_brightness_contrast(
    image: np.ndarray,
    brightness_factor: float = 1.0,
    contrast_factor: float = 1.0,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Adjust image luminance brightness and contrast factors.

    Args:
        image: RGB numpy array (H, W, 3).
        brightness_factor: Multiplier for brightness (> 0.0, 1.0 = unchanged).
        contrast_factor: Multiplier for contrast (> 0.0, 1.0 = unchanged).

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (adjusted_rgb, metadata)
    """
    if brightness_factor <= 0.0 or contrast_factor <= 0.0:
        raise ValueError(
            f"Brightness and contrast factors must be positive, got b={brightness_factor}, c={contrast_factor}"
        )

    pil_img = _ensure_rgb_image(image)
    if brightness_factor != 1.0:
        enh_b = ImageEnhance.Brightness(pil_img)
        pil_img = enh_b.enhance(brightness_factor)

    if contrast_factor != 1.0:
        enh_c = ImageEnhance.Contrast(pil_img)
        pil_img = enh_c.enhance(contrast_factor)

    result_array = np.array(pil_img, dtype=np.uint8)
    metadata = {
        "attack": "brightness_contrast",
        "brightness_factor": brightness_factor,
        "contrast_factor": contrast_factor,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_crop(
    image: np.ndarray,
    crop_percent: float = 25.0,
    mode: str = "center",
    restore: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Crop a percentage of image area, with coordinate zero-padding restoration.

    Args:
        image: RGB numpy array (H, W, 3).
        crop_percent: Percentage of area to crop in range [1.0, 90.0].
        mode: 'center' or 'border'.
        restore: If True, pads cropped image back to original dimensions with zeros.

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (cropped_rgb, metadata)
    """
    if not (1.0 <= crop_percent <= 90.0):
        raise ValueError(f"Crop percent must be between 1.0 and 90.0, got {crop_percent}")

    h, w, c = image.shape
    scale = np.sqrt(1.0 - (crop_percent / 100.0))
    crop_w = max(int(w * scale), 8)
    crop_h = max(int(h * scale), 8)

    x1 = (w - crop_w) // 2
    y1 = (h - crop_h) // 2
    x2 = x1 + crop_w
    y2 = y1 + crop_h

    cropped_patch = image[y1:y2, x1:x2, :]

    if restore:
        result_array = np.zeros_like(image)
        result_array[y1:y2, x1:x2, :] = cropped_patch
    else:
        result_array = cropped_patch

    metadata = {
        "attack": "cropping",
        "crop_percent": crop_percent,
        "cropped_patch_shape": cropped_patch.shape,
        "crop_box": (x1, y1, x2, y2),
        "restored": restore,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def apply_rotation(
    image: np.ndarray,
    angle: float = 5.0,
    restore: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Rotate image by specified angle in degrees.

    Args:
        image: RGB numpy array (H, W, 3).
        angle: Angle in degrees (-360.0 to 360.0).
        restore: If True, maintains canvas size and rotates back by -angle.

    Returns:
        Tuple[np.ndarray, Dict[str, Any]]: (rotated_rgb, metadata)
    """
    if not (-360.0 <= angle <= 360.0):
        raise ValueError(f"Rotation angle must be in [-360, 360], got {angle}")

    pil_img = _ensure_rgb_image(image)
    orig_size = pil_img.size

    if angle == 0.0:
        return image.copy(), {"attack": "rotation", "angle": 0.0, "restored": restore}

    if abs(angle) == 90.0 or abs(angle) == 180.0 or abs(angle) == 270.0:
        rot = pil_img.rotate(angle, resample=Image.Resampling.NEAREST, expand=False)
        result_array = np.array(rot, dtype=np.uint8)
    else:
        # Small angle rotation with bilinear interpolation
        rotated = pil_img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)
        if restore:
            # Rotate back to evaluate geometric loss and interpolation artifacts
            counter_rotated = rotated.rotate(-angle, resample=Image.Resampling.BILINEAR, expand=False)
            result_array = np.array(counter_rotated, dtype=np.uint8)
        else:
            result_array = np.array(rotated, dtype=np.uint8)

    metadata = {
        "attack": "rotation",
        "angle": angle,
        "restored": restore,
        "original_shape": image.shape,
        "output_shape": result_array.shape,
    }
    return result_array, metadata


def get_standard_attack_grid() -> Dict[str, list]:
    """Return the authoritative documented Phase 5 attack parameter grid."""
    return {
        "jpeg": [95, 85, 75, 60, 40],
        "resize": [0.75, 0.50, 0.25],
        "gaussian_blur": [0.5, 1.0, 1.5, 2.0],
        "gaussian_noise": [5.0, 10.0, 15.0, 25.0],
        "brightness_contrast": [
            {"b": 1.15, "c": 1.0},
            {"b": 0.85, "c": 1.0},
            {"b": 1.0, "c": 1.20},
            {"b": 1.0, "c": 0.80},
        ],
        "cropping": [10.0, 25.0, 50.0],
        "rotation": [1.0, 2.0, 5.0, 90.0],
    }
