"""CreditMera Watermark Robustness Lab — Evaluation Corpus Generator.

Provides reproducible standard test images with varied frequency characteristics:
1. Smooth Gradient: Dominant low-frequency DCT energy.
2. High-Frequency Sinusoidal Texture: Dense mid-to-high frequency components.
3. Naturalistic Composite Scene: Multi-frequency photographic composition with sharp edges and textured regions.
4. Non-Square Dimension Pattern: Non-square dimensions (192x256) verifying block padding boundaries.
"""
from pathlib import Path
from typing import Dict
import numpy as np
from PIL import Image


def generate_benchmark_corpus(save_dir: Path = None) -> Dict[str, np.ndarray]:
    """Generate and optionally persist the standard 4-image evaluation corpus.

    Args:
        save_dir: Optional directory path to persist source PNG images.

    Returns:
        Dict[str, np.ndarray]: Dictionary mapping image labels to RGB numpy arrays.
    """
    rng = np.random.default_rng(2026)

    # 1. Smooth gradient (256x256)
    x = np.linspace(0, 255, 256, dtype=np.uint8)
    grad_2d = np.tile(x, (256, 1))
    grad_rgb = np.stack([grad_2d, grad_2d.T, np.flipud(grad_2d)], axis=-1)

    # 2. High-frequency sinusoidal texture (256x256)
    u, v = np.meshgrid(np.linspace(0, 10 * np.pi, 256), np.linspace(0, 10 * np.pi, 256))
    tex = ((np.sin(u) * np.cos(v) + 1.0) * 127.5).astype(np.uint8)
    tex_rgb = np.stack([tex, tex, tex], axis=-1)

    # 3. Multi-frequency Naturalistic composite scene (256x256)
    scene = np.zeros((256, 256, 3), dtype=np.float64)
    scene[:, :, 0] = np.linspace(40, 210, 256)[:, None]
    scene[:, :, 1] = np.linspace(70, 230, 256)[None, :]
    scene[:, :, 2] = 128.0
    y_idx, x_idx = np.ogrid[:256, :256]
    circle_mask = ((x_idx - 128)**2 + (y_idx - 128)**2) < 64**2
    scene[circle_mask] += [50, -40, 60]
    rect_mask = (y_idx >= 30) & (y_idx <= 80) & (x_idx >= 30) & (x_idx <= 120)
    scene[rect_mask] = [200, 180, 50]
    noise = rng.normal(0, 8, (256, 256, 3))
    nat_rgb = np.clip(scene + noise, 0, 255).astype(np.uint8)

    # 4. Non-square dimensions image (192x256)
    u_ns, v_ns = np.meshgrid(np.linspace(0, 6 * np.pi, 256), np.linspace(0, 6 * np.pi, 192))
    ns_pattern = ((np.sin(u_ns) + np.cos(v_ns) + 2.0) * 63.75).astype(np.uint8)
    ns_rgb = np.stack([ns_pattern, np.flipud(ns_pattern), np.fliplr(ns_pattern)], axis=-1)

    corpus = {
        "gradient_256": grad_rgb,
        "texture_256": tex_rgb,
        "naturalistic_256": nat_rgb,
        "non_square_192x256": ns_rgb,
    }

    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        for name, arr in corpus.items():
            img_path = save_dir / f"{name}.png"
            if not img_path.exists():
                Image.fromarray(arr).save(img_path, format="PNG")

    return corpus
