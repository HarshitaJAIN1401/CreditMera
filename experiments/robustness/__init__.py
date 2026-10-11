"""CreditMera Watermark Robustness Lab Package.
"""
from experiments.robustness.attacks import (
    apply_jpeg_compression,
    apply_resize,
    apply_gaussian_blur,
    apply_gaussian_noise,
    apply_brightness_contrast,
    apply_crop,
    apply_rotation,
    get_standard_attack_grid,
)
from experiments.robustness.metrics import (
    compute_image_quality,
    compute_watermark_fidelity,
    compute_aggregate_rates,
)
from experiments.robustness.corpus import generate_benchmark_corpus
from experiments.robustness.serialization import (
    save_results_json,
    save_results_csv,
    load_results_json,
    load_results_csv,
)
from experiments.robustness.runner import execute_robustness_experiment

__all__ = [
    "apply_jpeg_compression",
    "apply_resize",
    "apply_gaussian_blur",
    "apply_gaussian_noise",
    "apply_brightness_contrast",
    "apply_crop",
    "apply_rotation",
    "get_standard_attack_grid",
    "compute_image_quality",
    "compute_watermark_fidelity",
    "compute_aggregate_rates",
    "generate_benchmark_corpus",
    "save_results_json",
    "save_results_csv",
    "load_results_json",
    "load_results_csv",
    "execute_robustness_experiment",
]
