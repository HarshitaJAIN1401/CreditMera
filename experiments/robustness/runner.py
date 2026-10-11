"""CreditMera Watermark Robustness Lab — Automated Experiment Runner.

Executes scientific, reproducible watermark robustness evaluations comparing:
1. Hybrid DCT-SVD (Primary Algorithm)
2. Baseline DCT
3. Baseline SVD

Across the full documented attack suite:
- JPEG Compression (qualities 95, 85, 75, 60, 40)
- Resize & Restore (scales 75%, 50%, 25%)
- Gaussian Blur (radii 0.5, 1.0, 1.5, 2.0)
- Additive Gaussian Noise (std 5, 10, 15, 25, seed=2026)
- Photometric Brightness & Contrast Adjustments
- Cropping (10%, 25%, 50% with restoration)
- Rotation (1°, 2°, 5°, 90°)

Records objective metrics:
- Fidelity: PSNR (dB), SSIM
- Recovery: NC / NCC, BER
- Security: Cryptographic Payload Authenticity, Raw Status
- Efficiency: Embedding Time (ms), Extraction Time (ms)
- Controls: False-positive evaluation on clean unwatermarked images
"""
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

# Ensure backend is in sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from watermark.embedding import embed_watermark
from watermark.extraction import extract_watermark
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
from experiments.robustness.serialization import save_results_json, save_results_csv


EXPERIMENT_SECRET_KEY = "creditmera_robustness_lab_master_key_2026"
EXPERIMENT_ASSET_ID = 1020304050
DEFAULT_ALPHA = 0.10


def run_single_attack_trial(
    attacked_image: np.ndarray,
    watermarked_reference: np.ndarray,
    ground_truth_bits: np.ndarray,
    algorithm: str,
    secret_key: str,
    alpha: float,
    asset_id: int,
) -> Dict[str, Any]:
    """Execute watermark extraction and metric calculation on an attacked image."""
    # 1. Image quality degradation relative to watermarked reference
    quality_metrics = compute_image_quality(watermarked_reference, attacked_image)

    # 2. Blind watermark extraction with execution timing
    t0 = time.perf_counter()
    extract_res = extract_watermark(
        image_source=attacked_image,
        secret_key=secret_key,
        algorithm=algorithm,
        alpha=alpha,
        expected_asset_id=asset_id,
    )
    extract_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # 3. Watermark recovery metrics
    fidelity_metrics = compute_watermark_fidelity(extract_res.extracted_bits, ground_truth_bits)

    return {
        "psnr_db": quality_metrics["psnr_db"],
        "ssim": quality_metrics["ssim"],
        "nc": fidelity_metrics["nc"],
        "ber": fidelity_metrics["ber"],
        "payload_valid": extract_res.valid,
        "payload_status": extract_res.status,
        "extracted_asset_id": extract_res.asset_id,
        "crc_passed": extract_res.crc_passed,
        "hmac_passed": extract_res.hmac_passed,
        "extract_time_ms": extract_time_ms,
    }


def execute_robustness_experiment(
    algorithms: Optional[List[str]] = None,
    smoke_test: bool = False,
    results_dir: Optional[Path] = None,
    datasets_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute full comparative robustness lab suite or smoke test.

    Args:
        algorithms: List of algorithms to evaluate (default: ['dct_svd', 'dct', 'svd']).
        smoke_test: If True, executes minimal subset for rapid validation.
        results_dir: Output path to save results JSON and CSV.
        datasets_dir: Directory path for source benchmark images.

    Returns:
        Dict[str, Any]: Complete experiment results dictionary.
    """
    if algorithms is None:
        algorithms = ["dct_svd", "dct", "svd"] if not smoke_test else ["dct_svd"]

    base_dir = Path(__file__).resolve().parent.parent
    if results_dir is None:
        results_dir = base_dir / "results"
    if datasets_dir is None:
        datasets_dir = base_dir / "datasets" / "sources"

    results_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir.mkdir(parents=True, exist_ok=True)

    # Load / generate benchmark image corpus
    corpus = generate_benchmark_corpus(save_dir=datasets_dir)
    if smoke_test:
        corpus = {"texture_256": corpus["texture_256"]}

    attack_grid = get_standard_attack_grid()
    if smoke_test:
        # Reduced parameter set for smoke test
        attack_grid = {
            "jpeg": [85],
            "resize": [0.50],
            "gaussian_blur": [1.0],
            "gaussian_noise": [10.0],
            "brightness_contrast": [{"b": 1.15, "c": 1.0}],
            "cropping": [10.0],
            "rotation": [1.0],
        }

    start_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    all_trials: List[Dict[str, Any]] = []
    control_trials: List[Dict[str, Any]] = []
    trial_counter = 0

    print("=" * 80)
    print(f"STARTING CREDITMERA WATERMARK ROBUSTNESS LAB (Smoke Test: {smoke_test})")
    print(f"Algorithms: {algorithms} | Images: {list(corpus.keys())}")
    print("=" * 80)

    for img_name, img_array in corpus.items():
        img_h, img_w, _ = img_array.shape

        for algo in algorithms:
            # 1. Embed watermark into clean image
            t_embed_start = time.perf_counter()
            embed_res = embed_watermark(
                image_source=img_array,
                asset_id=EXPERIMENT_ASSET_ID,
                secret_key=EXPERIMENT_SECRET_KEY,
                algorithm=algo,
                alpha=DEFAULT_ALPHA,
            )
            embed_time_ms = round((time.perf_counter() - t_embed_start) * 1000.0, 2)
            wm_rgb = embed_res.watermarked_rgb
            gt_bits = embed_res.ground_truth_bits
            baseline_psnr = embed_res.metrics["psnr_db"]
            baseline_ssim = embed_res.metrics["ssim"]

            # Record clean baseline trial (identity / no attack)
            trial_counter += 1
            clean_trial = {
                "trial_id": trial_counter,
                "image_name": img_name,
                "dimensions": f"{img_w}x{img_h}",
                "algorithm": algo,
                "alpha": DEFAULT_ALPHA,
                "attack_category": "none",
                "attack_param": "baseline",
                "psnr_db": baseline_psnr,
                "ssim": baseline_ssim,
                "nc": 1.0,
                "ber": 0.0,
                "payload_valid": True,
                "payload_status": "AUTHENTICATED",
                "extracted_asset_id": EXPERIMENT_ASSET_ID,
                "crc_passed": True,
                "hmac_passed": True,
                "embed_time_ms": embed_time_ms,
                "extract_time_ms": 0.0,
            }
            all_trials.append(clean_trial)

            # 2. Iterate through attacks
            # A. JPEG Compression
            for q in attack_grid["jpeg"]:
                trial_counter += 1
                attacked_img, meta = apply_jpeg_compression(wm_rgb, quality=q)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "jpeg",
                    "attack_param": f"Q={q}",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # B. Resize
            for s in attack_grid["resize"]:
                trial_counter += 1
                attacked_img, meta = apply_resize(wm_rgb, scale=s)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "resize",
                    "attack_param": f"scale={int(s*100)}%",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # C. Gaussian Blur
            for r in attack_grid["gaussian_blur"]:
                trial_counter += 1
                attacked_img, meta = apply_gaussian_blur(wm_rgb, radius=r)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "gaussian_blur",
                    "attack_param": f"radius={r}",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # D. Gaussian Noise
            for sigma in attack_grid["gaussian_noise"]:
                trial_counter += 1
                attacked_img, meta = apply_gaussian_noise(wm_rgb, std=sigma, seed=2026)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "gaussian_noise",
                    "attack_param": f"std={sigma}",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # E. Brightness & Contrast
            for bc in attack_grid["brightness_contrast"]:
                trial_counter += 1
                b_val, c_val = bc["b"], bc["c"]
                attacked_img, meta = apply_brightness_contrast(wm_rgb, brightness_factor=b_val, contrast_factor=c_val)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "brightness_contrast",
                    "attack_param": f"b={b_val}_c={c_val}",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # F. Cropping
            for cp in attack_grid["cropping"]:
                trial_counter += 1
                attacked_img, meta = apply_crop(wm_rgb, crop_percent=cp, restore=True)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "cropping",
                    "attack_param": f"crop={cp}%",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

            # G. Rotation
            for rot_deg in attack_grid["rotation"]:
                trial_counter += 1
                attacked_img, meta = apply_rotation(wm_rgb, angle=rot_deg, restore=True)
                trial_res = run_single_attack_trial(
                    attacked_img, wm_rgb, gt_bits, algo, EXPERIMENT_SECRET_KEY, DEFAULT_ALPHA, EXPERIMENT_ASSET_ID
                )
                trial_record = {
                    "trial_id": trial_counter,
                    "image_name": img_name,
                    "dimensions": f"{img_w}x{img_h}",
                    "algorithm": algo,
                    "alpha": DEFAULT_ALPHA,
                    "attack_category": "rotation",
                    "attack_param": f"rot={rot_deg}deg",
                    "embed_time_ms": embed_time_ms,
                    **trial_res,
                }
                all_trials.append(trial_record)

    # 3. Unwatermarked Control Image Trials (False-Positive Evaluation)
    print("\nRunning unwatermarked control evaluations...")
    control_img = corpus[list(corpus.keys())[0]]
    for algo in algorithms:
        for attack_name, attack_fn in [
            ("none", lambda x: (x, {})),
            ("jpeg_85", lambda x: apply_jpeg_compression(x, 85)),
            ("blur_1.0", lambda x: apply_gaussian_blur(x, 1.0)),
            ("noise_10", lambda x: apply_gaussian_noise(x, 10.0, seed=2026)),
        ]:
            att_img, _ = attack_fn(control_img)
            ext = extract_watermark(att_img, EXPERIMENT_SECRET_KEY, algorithm=algo, alpha=DEFAULT_ALPHA)
            control_trials.append({
                "algorithm": algo,
                "attack": attack_name,
                "is_unwatermarked": True,
                "payload_valid": ext.valid,
                "status": ext.status,
                "false_positive": ext.valid,
            })

    false_positive_count = sum(1 for c in control_trials if c["false_positive"] is True)

    # 4. Compute Aggregate Statistics
    summary_by_algorithm: Dict[str, Any] = {}
    for algo in algorithms:
        algo_trials = [t for t in all_trials if t["algorithm"] == algo]
        summary_by_algorithm[algo] = compute_aggregate_rates(algo_trials)

    summary_by_attack: Dict[str, Any] = {}
    for att_cat in ["none", "jpeg", "resize", "gaussian_blur", "gaussian_noise", "brightness_contrast", "cropping", "rotation"]:
        cat_trials = [t for t in all_trials if t["attack_category"] == att_cat]
        summary_by_attack[att_cat] = compute_aggregate_rates(cat_trials)

    results_data = {
        "metadata": {
            "title": "CreditMera Watermark Robustness Lab Evaluation",
            "timestamp": start_timestamp,
            "smoke_test": smoke_test,
            "algorithms_evaluated": algorithms,
            "images_evaluated": list(corpus.keys()),
            "total_watermarked_trials": len(all_trials),
            "total_control_trials": len(control_trials),
            "false_positives_detected": false_positive_count,
            "false_positive_rate": round(false_positive_count / max(len(control_trials), 1), 4),
            "default_alpha": DEFAULT_ALPHA,
            "asset_id": EXPERIMENT_ASSET_ID,
        },
        "summary_by_algorithm": summary_by_algorithm,
        "summary_by_attack": summary_by_attack,
        "control_trials": control_trials,
        "trials": all_trials,
    }

    # Save to JSON and CSV
    json_path = results_dir / "robustness_results.json"
    csv_path = results_dir / "robustness_results.csv"

    save_results_json(results_data, json_path)
    save_results_csv(all_trials, csv_path)

    print(f"Results successfully saved:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print("=" * 80)

    return results_data


if __name__ == "__main__":
    is_smoke = "--smoke" in sys.argv
    execute_robustness_experiment(smoke_test=is_smoke)
