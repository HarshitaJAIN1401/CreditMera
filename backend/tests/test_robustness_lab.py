"""Unit and integration tests for CreditMera Phase 5 Watermark Robustness Lab.

Validates:
1. All 7 attack transformations modify images as expected and preserve dimensions.
2. Parameter validation fails safely on out-of-bound arguments.
3. Stochastic attacks (Gaussian noise) are deterministic with a fixed random seed.
4. Image quality (PSNR, SSIM) and watermark fidelity (NC, BER) calculations.
5. Result serialization roundtrips accurately for both JSON and CSV.
6. Benchmark corpus generation preserves image formats and varied frequencies.
7. Full experiment runner pipeline completes reliably from end to end (smoke test).
"""
import sys
import tempfile
from pathlib import Path
import pytest
import numpy as np
from PIL import Image

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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


@pytest.fixture
def sample_rgb_image() -> np.ndarray:
    """Generate a reproducible 256x256 test image with mid-frequency texture."""
    u, v = np.meshgrid(np.linspace(0, 8 * np.pi, 256), np.linspace(0, 8 * np.pi, 256))
    tex = ((np.sin(u) * np.cos(v) + 1.0) * 127.5).astype(np.uint8)
    return np.stack([tex, tex, tex], axis=-1)


class TestAttackTransformations:

    def test_jpeg_compression(self, sample_rgb_image):
        """JPEG compression alters image while maintaining shape and uint8 dtype."""
        att_img, meta = apply_jpeg_compression(sample_rgb_image, quality=75)
        assert att_img.shape == sample_rgb_image.shape
        assert att_img.dtype == np.uint8
        assert not np.array_equal(att_img, sample_rgb_image)
        assert meta["attack"] == "jpeg_compression"
        assert meta["quality"] == 75

    def test_resize_and_restore(self, sample_rgb_image):
        """Resize downsamples and restores dimensions accurately."""
        att_img, meta = apply_resize(sample_rgb_image, scale=0.50, interpolation="bicubic")
        assert att_img.shape == sample_rgb_image.shape
        assert att_img.dtype == np.uint8
        assert not np.array_equal(att_img, sample_rgb_image)
        assert meta["intermediate_dimensions"] == (128, 128)

    def test_gaussian_blur(self, sample_rgb_image):
        """Gaussian blur low-pass filters the image."""
        att_img, meta = apply_gaussian_blur(sample_rgb_image, radius=1.5)
        assert att_img.shape == sample_rgb_image.shape
        assert att_img.dtype == np.uint8
        assert not np.array_equal(att_img, sample_rgb_image)
        assert meta["radius"] == 1.5

    def test_gaussian_noise(self, sample_rgb_image):
        """Gaussian noise adds noise and is reproducible with fixed seed."""
        img1, meta1 = apply_gaussian_noise(sample_rgb_image, std=15.0, seed=1234)
        img2, meta2 = apply_gaussian_noise(sample_rgb_image, std=15.0, seed=1234)
        img3, meta3 = apply_gaussian_noise(sample_rgb_image, std=15.0, seed=5678)

        # Same seed must yield bit-exact identical arrays
        np.testing.assert_array_equal(img1, img2)
        # Different seeds must yield different noise
        assert not np.array_equal(img1, img3)
        assert img1.shape == sample_rgb_image.shape

    def test_brightness_contrast(self, sample_rgb_image):
        """Brightness and contrast modify pixel intensities."""
        att_img, meta = apply_brightness_contrast(sample_rgb_image, brightness_factor=1.20, contrast_factor=0.80)
        assert att_img.shape == sample_rgb_image.shape
        assert not np.array_equal(att_img, sample_rgb_image)

    def test_cropping_with_restoration(self, sample_rgb_image):
        """Cropping with restoration maintains original dimensions with zero padding."""
        att_img, meta = apply_crop(sample_rgb_image, crop_percent=25.0, restore=True)
        assert att_img.shape == sample_rgb_image.shape
        assert meta["restored"] is True
        # Corner pixels should be zero-padded
        assert att_img[0, 0, 0] == 0

    def test_rotation(self, sample_rgb_image):
        """Rotation by small angle alters pixel coordinates and restores canvas."""
        att_img, meta = apply_rotation(sample_rgb_image, angle=5.0, restore=True)
        assert att_img.shape == sample_rgb_image.shape
        assert not np.array_equal(att_img, sample_rgb_image)

    def test_invalid_parameters_fail_safely(self, sample_rgb_image):
        """Invalid parameter bounds raise ValueError safely."""
        with pytest.raises(ValueError, match="quality must be between"):
            apply_jpeg_compression(sample_rgb_image, quality=120)

        with pytest.raises(ValueError, match="scale must be in range"):
            apply_resize(sample_rgb_image, scale=0.01)

        with pytest.raises(ValueError, match="radius must be non-negative"):
            apply_gaussian_blur(sample_rgb_image, radius=-1.0)

        with pytest.raises(ValueError, match="standard deviation must be non-negative"):
            apply_gaussian_noise(sample_rgb_image, std=-5.0)

        with pytest.raises(ValueError, match="must be positive"):
            apply_brightness_contrast(sample_rgb_image, brightness_factor=-0.5)

        with pytest.raises(ValueError, match="between 1.0 and 90.0"):
            apply_crop(sample_rgb_image, crop_percent=99.0)


class TestRobustnessMetrics:

    def test_image_quality_metrics(self, sample_rgb_image):
        """Image quality metric calculation produces correct values."""
        # Identical images: PSNR = 100 dB, SSIM = 1.0
        q_identical = compute_image_quality(sample_rgb_image, sample_rgb_image)
        assert q_identical["psnr_db"] == 100.0
        assert q_identical["ssim"] == 1.0

        # Noisy image has lower PSNR and SSIM
        noisy, _ = apply_gaussian_noise(sample_rgb_image, std=20.0, seed=42)
        q_noisy = compute_image_quality(sample_rgb_image, noisy)
        assert q_noisy["psnr_db"] < 40.0
        assert q_noisy["ssim"] < 0.95

    def test_watermark_fidelity_metrics(self):
        """NC and BER calculation matches theoretical bounds."""
        bits_a = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
        bits_b = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
        bits_inverted = 1 - bits_a

        # Perfect match
        fid_perfect = compute_watermark_fidelity(bits_b, bits_a)
        assert fid_perfect["nc"] == 1.0
        assert fid_perfect["ber"] == 0.0

        # Completely inverted
        fid_inv = compute_watermark_fidelity(bits_inverted, bits_a)
        assert fid_inv["nc"] == -1.0
        assert fid_inv["ber"] == 1.0

    def test_aggregate_rates_calculation(self):
        """Aggregation denominator and rates calculate correctly."""
        trials = [
            {"payload_valid": True, "nc": 1.0, "ber": 0.0, "psnr_db": 42.0, "ssim": 0.98},
            {"payload_valid": True, "nc": 0.95, "ber": 0.02, "psnr_db": 38.0, "ssim": 0.95},
            {"payload_valid": False, "nc": 0.40, "ber": 0.30, "psnr_db": 28.0, "ssim": 0.80},
        ]
        rates = compute_aggregate_rates(trials)
        assert rates["total_samples"] == 3
        assert rates["authenticated_count"] == 2
        assert rates["authentication_rate"] == round(2 / 3, 4)
        assert rates["mean_nc"] == round((1.0 + 0.95 + 0.40) / 3, 4)


class TestSerializationAndRunner:

    def test_json_and_csv_serialization(self):
        """JSON and CSV serialization roundtrip without loss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            json_file = tmp_path / "test_results.json"
            csv_file = tmp_path / "test_results.csv"

            dummy_data = {
                "metadata": {"title": "Test Lab", "count": 2},
                "trials": [
                    {"trial_id": 1, "algorithm": "dct_svd", "nc": 1.0, "valid": True},
                    {"trial_id": 2, "algorithm": "dct", "nc": 0.90, "valid": False},
                ],
            }

            save_results_json(dummy_data, json_file)
            assert json_file.exists()
            loaded_json = load_results_json(json_file)
            assert loaded_json["metadata"]["title"] == "Test Lab"

            save_results_csv(dummy_data["trials"], csv_file)
            assert csv_file.exists()
            loaded_csv = load_results_csv(csv_file)
            assert len(loaded_csv) == 2
            assert loaded_csv[0]["algorithm"] == "dct_svd"

    def test_corpus_generation(self):
        """Corpus generator creates all 4 benchmark images."""
        corpus = generate_benchmark_corpus()
        assert "gradient_256" in corpus
        assert "texture_256" in corpus
        assert "naturalistic_256" in corpus
        assert "non_square_192x256" in corpus
        assert corpus["non_square_192x256"].shape == (192, 256, 3)

    def test_runner_smoke_test(self):
        """End-to-end smoke test of the robustness experiment runner."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            res_dir = tmp_path / "results"
            data_dir = tmp_path / "datasets"

            results = execute_robustness_experiment(
                algorithms=["dct_svd"],
                smoke_test=True,
                results_dir=res_dir,
                datasets_dir=data_dir,
            )

            assert (res_dir / "robustness_results.json").exists()
            assert (res_dir / "robustness_results.csv").exists()
            assert results["metadata"]["smoke_test"] is True
            assert len(results["trials"]) > 0
            # Control trials must have 0 false positives
            assert results["metadata"]["false_positives_detected"] == 0
