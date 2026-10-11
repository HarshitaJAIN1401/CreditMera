"""CreditMera Phase 2 Technical Audit & Scientific Verification Script.

Executes reproducible live evaluations of:
1. Algorithm distinction (DCT vs SVD vs DCT-SVD)
2. JPEG compression encoding/decoding resilience across quality levels
3. Correct vs incorrect key extraction behavior
4. Bit-error rate (BER) and Normalized Cross-Correlation (NC) accuracy
5. Payload capacity and boundary verification
"""
import sys
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from watermark.embedding import embed_watermark
from watermark.extraction import extract_watermark
from watermark.payload import encode_payload, decode_payload, PAYLOAD_BIT_LENGTH
from watermark.transforms import decode_image, encode_image
from watermark.metrics import calculate_psnr, calculate_ssim, calculate_nc, calculate_ber


def generate_test_images():
    """Generate reproducible synthetic and naturalistic test images."""
    rng = np.random.default_rng(2026)

    # 1. Smooth gradient (256x256)
    x = np.linspace(0, 255, 256, dtype=np.uint8)
    grad_2d = np.tile(x, (256, 1))
    img_grad = np.stack([grad_2d, grad_2d.T, np.flipud(grad_2d)], axis=-1)

    # 2. High-frequency sinusoidal texture (256x256)
    u, v = np.meshgrid(np.linspace(0, 10 * np.pi, 256), np.linspace(0, 10 * np.pi, 256))
    tex = ((np.sin(u) * np.cos(v) + 1.0) * 127.5).astype(np.uint8)
    img_tex = np.stack([tex, tex, tex], axis=-1)

    # 3. Multi-frequency Naturalistic photographic pattern (256x256)
    # Simulated natural scene with low, mid, and high frequency structures
    scene = np.zeros((256, 256, 3), dtype=np.float64)
    # Background gradient
    scene[:, :, 0] = np.linspace(50, 200, 256)[:, None]
    scene[:, :, 1] = np.linspace(80, 220, 256)[None, :]
    scene[:, :, 2] = 128.0
    # Add geometric shapes and textures
    y_idx, x_idx = np.ogrid[:256, :256]
    circle_mask = ((x_idx - 128)**2 + (y_idx - 128)**2) < 60**2
    scene[circle_mask] += [40, -30, 50]
    # Add subtle random texture
    noise = rng.normal(0, 10, (256, 256, 3))
    scene = np.clip(scene + noise, 0, 255).astype(np.uint8)

    return {
        "Gradient (256x256)": img_grad,
        "Texture (256x256)": img_tex,
        "Naturalistic (256x256)": scene,
    }


def audit_algorithm_distinction():
    print("=" * 80)
    print("1. AUDIT: ALGORITHM COMPARISON & INDEPENDENCE VERIFICATION")
    print("=" * 80)
    images = generate_test_images()
    key = "master_audit_secret_key_2026"
    asset_id = 4455667788

    print(f"| Image | Algorithm | Alpha | PSNR (dB) | SSIM | NC | BER | Valid |")
    print(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for img_name, img in images.items():
        for algo in ["dct", "svd", "dct_svd"]:
            alpha = 0.10
            e_res = embed_watermark(img, asset_id, key, algorithm=algo, alpha=alpha)
            x_res = extract_watermark(e_res.watermarked_rgb, key, algorithm=algo, alpha=alpha, expected_asset_id=asset_id)
            psnr = e_res.metrics["psnr_db"]
            ssim = e_res.metrics["ssim"]
            print(f"| {img_name} | {algo.upper():7s} | {alpha:.2f} | {psnr:6.2f} dB | {ssim:.4f} | {x_res.nc:.4f} | {x_res.ber:.4f} | {x_res.valid} |")


def audit_jpeg_resilience():
    print("\n" + "=" * 80)
    print("2. AUDIT: REAL JPEG COMPRESSION ENCODING / DECODING EVALUATION")
    print("=" * 80)
    images = generate_test_images()
    key = "jpeg_resilience_test_key"
    asset_id = 9988776655
    test_img = images["Naturalistic (256x256)"]

    print(f"| Algorithm | JPEG Quality | PSNR after JPEG | Extracted NC | BER | Payload Auth |")
    print(f"| :--- | :--- | :--- | :--- | :--- | :--- |")

    for algo in ["dct", "svd", "dct_svd"]:
        alpha = 0.12
        e_res = embed_watermark(test_img, asset_id, key, algorithm=algo, alpha=alpha)
        watermarked_pil = Image.fromarray(e_res.watermarked_rgb)

        for quality in [95, 85, 75, 60]:
            # Simulate real JPEG compression through file byte stream
            buf = BytesIO()
            watermarked_pil.save(buf, format="JPEG", quality=quality)
            compressed_bytes = buf.getvalue()

            # Re-read compressed JPEG image
            decompressed_img = np.array(Image.open(BytesIO(compressed_bytes)), dtype=np.uint8)

            jpeg_psnr = calculate_psnr(test_img, decompressed_img)
            x_res = extract_watermark(decompressed_img, key, algorithm=algo, alpha=alpha, expected_asset_id=asset_id)

            print(f"| {algo.upper():7s} | Q={quality:2d}         | {jpeg_psnr:6.2f} dB        | {x_res.nc:6.4f}       | {x_res.ber:.4f} | {x_res.valid} |")


def audit_security_and_wrong_key():
    print("\n" + "=" * 80)
    print("3. AUDIT: CRYPTOGRAPHIC AUTHENTICATION & WRONG-KEY ISOLATION")
    print("=" * 80)
    images = generate_test_images()
    genuine_key = "genuine_creator_key_12345"
    attacker_key = "hostile_adversary_forgery_key"
    asset_id = 777888999
    test_img = images["Naturalistic (256x256)"]

    e_res = embed_watermark(test_img, asset_id, genuine_key, algorithm="dct_svd", alpha=0.10)

    # 1. Genuine extraction
    res_gen = extract_watermark(e_res.watermarked_rgb, genuine_key, algorithm="dct_svd", alpha=0.10, expected_asset_id=asset_id)
    print(f"[Genuine Key]   Status: {res_gen.status:22s} | Valid: {res_gen.valid} | Recovered ID: {res_gen.asset_id} | NC: {res_gen.nc}")

    # 2. Attacker extraction with wrong key
    res_att = extract_watermark(e_res.watermarked_rgb, attacker_key, algorithm="dct_svd", alpha=0.10, expected_asset_id=asset_id)
    print(f"[Attacker Key]  Status: {res_att.status:22s} | Valid: {res_att.valid} | Recovered ID: {res_att.asset_id} | NC: {res_att.nc}")

    # 3. Boundary check: Max 40-bit asset ID
    max_id = (1 << 40) - 1
    raw_b, bits = encode_payload(max_id, genuine_key, timestamp_nonce=1700000000)
    dec_res = decode_payload(bits, genuine_key)
    print(f"[Boundary ID]   Max 40-bit ID ({max_id}) -> Recovered: {dec_res.asset_id} | Valid: {dec_res.valid}")


if __name__ == "__main__":
    audit_algorithm_distinction()
    audit_jpeg_resilience()
    audit_security_and_wrong_key()
