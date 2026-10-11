"""Image decoding, validation, color-space conversion, and block-partitioning utilities.

Provides robust handling for RGB, RGBA, and grayscale inputs, conversion to/from
ITU-R BT.601 YCbCr color-space, dimension validation, and block reshaping.
"""
from io import BytesIO
from pathlib import Path
from typing import Tuple, Union, Optional
import numpy as np
from PIL import Image


class ImageValidationError(ValueError):
    """Raised when an image fails decoding or dimension/format validation."""
    pass


MIN_IMAGE_DIMENSION = 64
MAX_IMAGE_DIMENSION = 8192
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}

# Protect against memory exhaustion and decompression bombs
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION


def decode_image(
    source: Union[bytes, str, Path, np.ndarray, Image.Image],
    min_dim: int = MIN_IMAGE_DIMENSION,
    max_dim: int = MAX_IMAGE_DIMENSION,
) -> np.ndarray:
    """Decode an image from bytes, file path, numpy array, or PIL Image into an RGB uint8 array.

    Args:
        source: Input image bytes, path, numpy array, or PIL Image.
        min_dim: Minimum allowed width/height (default 64).
        max_dim: Maximum allowed width/height (default 8192).

    Returns:
        np.ndarray: Image array of shape (H, W, 3) with dtype uint8.

    Raises:
        ImageValidationError: If format is invalid, corrupted, or dimensions are out of bounds.
    """
    try:
        if isinstance(source, np.ndarray):
            arr = source
            if arr.ndim == 2:
                # Grayscale to RGB
                arr = np.stack([arr] * 3, axis=-1)
            elif arr.ndim == 3:
                if arr.shape[2] == 4:
                    # RGBA to RGB (composite onto white background or drop alpha)
                    arr = arr[:, :, :3]
                elif arr.shape[2] != 3:
                    raise ImageValidationError(
                        f"Unsupported number of channels: {arr.shape[2]}. Expected 1, 3, or 4."
                    )
            else:
                raise ImageValidationError(f"Invalid array dimensions: {arr.ndim}. Expected 2D or 3D.")
            image_rgb = arr.astype(np.uint8)
        else:
            if isinstance(source, (str, Path)):
                path = Path(source)
                if not path.is_file():
                    raise ImageValidationError(f"File not found: {path}")
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    raise ImageValidationError(
                        f"Unsupported file format '{path.suffix}'. Allowed: {sorted(SUPPORTED_EXTENSIONS)}"
                    )
                pil_img = Image.open(path)
            elif isinstance(source, bytes):
                if len(source) == 0:
                    raise ImageValidationError("Empty image byte payload provided.")
                pil_img = Image.open(BytesIO(source))
            elif isinstance(source, Image.Image):
                pil_img = source
            else:
                raise ImageValidationError(f"Unsupported source type: {type(source).__name__}")

            # Inspect dimensions immediately after opening to prevent decompression bombs
            w_init, h_init = pil_img.size
            if h_init < min_dim or w_init < min_dim:
                raise ImageValidationError(
                    f"Image dimensions ({w_init}x{h_init}) are too small. Minimum required is {min_dim}x{min_dim}."
                )
            if h_init > max_dim or w_init > max_dim:
                raise ImageValidationError(
                    f"Image dimensions ({w_init}x{h_init}) exceed maximum allowed limit of {max_dim}x{max_dim}."
                )

            # Verify image integrity and normalize mode
            pil_img.load()
            if pil_img.mode in ("RGBA", "LA"):
                # Composite onto white background to avoid transparent black artifacts
                bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                bg.paste(pil_img, mask=pil_img.split()[-1])
                pil_img = bg
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            image_rgb = np.array(pil_img, dtype=np.uint8)

    except ImageValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageValidationError(f"Image decompression bomb detected: {exc}") from exc
    except Exception as exc:
        raise ImageValidationError(f"Failed to decode image: {exc}") from exc

    h, w = image_rgb.shape[:2]
    if h < min_dim or w < min_dim:
        raise ImageValidationError(
            f"Image dimensions ({w}x{h}) are too small. Minimum required is {min_dim}x{min_dim}."
        )
    if h > max_dim or w > max_dim:
        raise ImageValidationError(
            f"Image dimensions ({w}x{h}) exceed maximum allowed limit of {max_dim}x{max_dim}."
        )

    return image_rgb


def encode_image(
    image_rgb: np.ndarray,
    format: str = "PNG",
    quality: int = 95,
) -> bytes:
    """Encode an RGB uint8 numpy array into image file bytes.

    Args:
        image_rgb: Array of shape (H, W, 3) and dtype uint8.
        format: Target format (e.g. 'PNG', 'JPEG', 'WEBP').
        quality: Compression quality for lossy formats (1-100).

    Returns:
        bytes: Encoded image file content.
    """
    if image_rgb.dtype != np.uint8:
        image_rgb = np.clip(image_rgb, 0, 255).astype(np.uint8)

    pil_img = Image.fromarray(image_rgb, mode="RGB")
    buf = BytesIO()
    fmt_upper = format.upper()
    if fmt_upper in ("JPEG", "JPG"):
        pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
    elif fmt_upper == "WEBP":
        pil_img.save(buf, format="WEBP", quality=quality)
    else:
        pil_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def rgb_to_ycbcr(image_rgb: np.ndarray) -> np.ndarray:
    """Convert RGB float/uint8 image to ITU-R BT.601 YCbCr (float64).

    Y range: [16, 235] scaled to full range [0, 255] for transform stability.
    Standard full-range BT.601:
      Y  =  0.299000 * R + 0.587000 * G + 0.114000 * B
      Cb = -0.168736 * R - 0.331264 * G + 0.500000 * B + 128.0
      Cr =  0.500000 * R - 0.418688 * G - 0.081312 * B + 128.0

    Args:
        image_rgb: Array of shape (H, W, 3), range [0, 255].

    Returns:
        np.ndarray: float64 array of shape (H, W, 3).
    """
    arr = image_rgb.astype(np.float64)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    y = 0.299000 * r + 0.587000 * g + 0.114000 * b
    cb = -0.168736 * r - 0.331264 * g + 0.500000 * b + 128.0
    cr = 0.500000 * r - 0.418688 * g - 0.081312 * b + 128.0

    return np.stack([y, cb, cr], axis=-1)


def ycbcr_to_rgb(image_ycbcr: np.ndarray) -> np.ndarray:
    """Convert ITU-R BT.601 YCbCr (float64) back to RGB (uint8).

    Inverse transformation:
      R = Y + 1.402000 * (Cr - 128.0)
      G = Y - 0.344136 * (Cb - 128.0) - 0.714136 * (Cr - 128.0)
      B = Y + 1.772000 * (Cb - 128.0)

    Args:
        image_ycbcr: float64 array of shape (H, W, 3).

    Returns:
        np.ndarray: uint8 array of shape (H, W, 3) clipped to [0, 255].
    """
    y = image_ycbcr[:, :, 0]
    cb = image_ycbcr[:, :, 1] - 128.0
    cr = image_ycbcr[:, :, 2] - 128.0

    r = y + 1.402000 * cr
    g = y - 0.344136 * cb - 0.714136 * cr
    b = y + 1.772000 * cb

    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(np.round(rgb), 0, 255).astype(np.uint8)


def pad_to_block_multiple(
    channel: np.ndarray,
    block_size: int = 8,
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """Pad a 2D channel so its height and width are exact multiples of block_size.

    Args:
        channel: 2D array of shape (H, W).
        block_size: Size of square blocks (default 8).

    Returns:
        Tuple[np.ndarray, Tuple[int, int]]: (padded_channel, (original_H, original_W))
    """
    h, w = channel.shape[:2]
    pad_h = (block_size - (h % block_size)) % block_size
    pad_w = (block_size - (w % block_size)) % block_size

    if pad_h == 0 and pad_w == 0:
        return channel.copy(), (h, w)

    # Edge reflection padding avoids sharp artificial frequency edges
    padded = np.pad(channel, ((0, pad_h), (0, pad_w)), mode="edge")
    return padded, (h, w)


def unpad_from_block_multiple(
    channel: np.ndarray,
    original_shape: Tuple[int, int],
) -> np.ndarray:
    """Crop a padded 2D channel back to its original dimensions."""
    orig_h, orig_w = original_shape
    return channel[:orig_h, :orig_w]


def split_blocks(channel: np.ndarray, block_size: int = 8) -> np.ndarray:
    """Partition a 2D channel of shape (H, W) into (N, block_size, block_size) blocks.

    Requires H and W to be divisible by block_size.

    Returns:
        np.ndarray: Array of shape (N, block_size, block_size) where N = (H/B) * (W/B).
    """
    h, w = channel.shape
    if h % block_size != 0 or w % block_size != 0:
        raise ValueError(
            f"Channel dimensions ({h}, {w}) must be divisible by block_size {block_size}."
        )

    num_h = h // block_size
    num_w = w // block_size

    # Reshape and transpose to extract non-overlapping blocks in row-major order
    reshaped = channel.reshape(num_h, block_size, num_w, block_size)
    transposed = reshaped.transpose(0, 2, 1, 3)
    blocks = transposed.reshape(num_h * num_w, block_size, block_size)
    return blocks


def merge_blocks(
    blocks: np.ndarray,
    height: int,
    width: int,
    block_size: int = 8,
) -> np.ndarray:
    """Reconstruct a 2D channel from (N, block_size, block_size) blocks.

    Args:
        blocks: Array of shape (N, block_size, block_size).
        height: Target height (divisible by block_size).
        width: Target width (divisible by block_size).
        block_size: Size of square blocks.

    Returns:
        np.ndarray: 2D array of shape (height, width).
    """
    num_h = height // block_size
    num_w = width // block_size
    if blocks.shape[0] != num_h * num_w:
        raise ValueError(
            f"Block count {blocks.shape[0]} does not match expected {num_h * num_w} blocks."
        )

    reshaped = blocks.reshape(num_h, num_w, block_size, block_size)
    transposed = reshaped.transpose(0, 2, 1, 3)
    channel = transposed.reshape(height, width)
    return channel
