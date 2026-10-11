"""Authenticated compact Asset-ID payload encoder and decoder.

Defines a 128-bit (16-byte) cryptographically authenticated payload format:
- Magic & Protocol Version (1 byte): Magic prefix 0xC0 | Version 0x01 = 0xC1
- Asset ID (6 bytes / 48 bits): Unique numerical identifier up to 2.8e14
- Timestamp / Nonce (3 bytes / 24 bits): Epoch timestamp modulo 2^24 for freshness
- Error-Detection CRC-16 (2 bytes / 16 bits): Standard CCITT CRC for channel transmission errors
- Cryptographic MAC (4 bytes / 32 bits): Truncated HMAC-SHA256 for cryptographic tamper-proofing

CRITICAL SECURITY DISTINCTION:
- CRC-16 is used exclusively for detecting random transmission/bit-flip noise.
- Truncated HMAC-SHA256 provides actual cryptographic authenticity and integrity.
An attacker without the secret key cannot forge or alter the asset ID.
"""
import hmac
import hashlib
import struct
from typing import Tuple, Optional, NamedTuple
import numpy as np


PAYLOAD_BIT_LENGTH = 128
PAYLOAD_BYTE_LENGTH = 16

MAGIC_HEADER = 0xC0
PROTOCOL_VERSION = 0x01
MAGIC_VERSION_BYTE = MAGIC_HEADER | PROTOCOL_VERSION  # 0xC1


class PayloadVerificationResult(NamedTuple):
    valid: bool
    asset_id: Optional[int]
    timestamp_nonce: Optional[int]
    crc_passed: bool
    hmac_passed: bool
    bit_error_rate: float
    confidence: float
    status: str
    raw_bytes: bytes


def compute_crc16(data: bytes) -> int:
    """Compute CRC-16-CCITT (polynomial 0x1021, init 0xFFFF).

    Used for physical channel error detection only (NOT cryptographic authentication).
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def compute_hmac32(data: bytes, secret_key: str) -> bytes:
    """Compute 32-bit (4-byte) truncated HMAC-SHA256 over data.

    Provides cryptographic authenticity preventing unauthorized payload forgery.
    """
    key_bytes = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
    h = hmac.new(key_bytes, data, hashlib.sha256).digest()
    return h[:4]


def derive_key_seed(secret_key: str, salt: bytes = b"creditmera_block_permutation_v1") -> int:
    """Derive a deterministic 64-bit integer seed for pseudo-random block permutation."""
    key_bytes = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
    derived = hashlib.sha256(key_bytes + salt).digest()
    # Unpack first 8 bytes as unsigned 64-bit integer
    return struct.unpack(">Q", derived[:8])[0]


def encode_payload(
    asset_id: int,
    secret_key: str,
    timestamp_nonce: int = 0,
) -> Tuple[bytes, np.ndarray]:
    """Encode asset ID and metadata into a 128-bit authenticated payload.

    Format:
    [0:1]   Magic & Version (1 byte)
    [1:6]   Asset ID (5 bytes / 40 bits, big-endian)
    [6:10]  Timestamp Nonce (4 bytes / 32 bits, big-endian)
    [10:12] CRC-16 (2 bytes, big-endian)
    [12:16] Truncated HMAC-SHA256 (4 bytes)

    Args:
        asset_id: Integer asset ID (0 <= asset_id < 2^40).
        secret_key: Secret key string for HMAC derivation.
        timestamp_nonce: 32-bit timestamp or nonce integer (0 <= val < 2^32).

    Returns:
        Tuple[bytes, np.ndarray]: (16-byte raw payload, 128-element 1D uint8 array of bits [0, 1]).
    """
    if asset_id < 0 or asset_id >= (1 << 40):
        raise ValueError(f"Asset ID {asset_id} exceeds 40-bit range [0, 2^40 - 1].")

    ts = int(timestamp_nonce) & 0xFFFFFFFF

    # Pack Header (1B) + Asset ID (5B) + Timestamp (4B) = 10 bytes
    header_byte = bytes([MAGIC_VERSION_BYTE])
    asset_bytes = asset_id.to_bytes(5, byteorder="big")
    ts_bytes = ts.to_bytes(4, byteorder="big")
    core_data = header_byte + asset_bytes + ts_bytes

    # CRC-16 over first 10 bytes
    crc_val = compute_crc16(core_data)
    crc_bytes = crc_val.to_bytes(2, byteorder="big")
    pre_hmac_data = core_data + crc_bytes  # 12 bytes

    # Truncated HMAC-SHA256 over first 12 bytes
    hmac_bytes = compute_hmac32(pre_hmac_data, secret_key)  # 4 bytes

    raw_payload = pre_hmac_data + hmac_bytes  # Total: 16 bytes = 128 bits
    assert len(raw_payload) == PAYLOAD_BYTE_LENGTH, f"Invalid payload length: {len(raw_payload)}"

    # Convert bytes to binary array of bits (0 and 1)
    bits = np.unpackbits(np.frombuffer(raw_payload, dtype=np.uint8))
    return raw_payload, bits


def decode_payload(
    extracted_bits: np.ndarray,
    secret_key: str,
) -> PayloadVerificationResult:
    """Decode a 128-bit array into asset metadata and verify CRC and HMAC.

    Args:
        extracted_bits: 1D array of 128 bits (0 or 1).
        secret_key: Secret key for verifying HMAC authentication.

    Returns:
        PayloadVerificationResult: Structured validation outcome.
    """
    if len(extracted_bits) < PAYLOAD_BIT_LENGTH:
        return PayloadVerificationResult(
            valid=False,
            asset_id=None,
            timestamp_nonce=None,
            crc_passed=False,
            hmac_passed=False,
            bit_error_rate=1.0,
            confidence=0.0,
            status="INSUFFICIENT_BITS",
            raw_bytes=b"",
        )

    # Take first 128 bits and pack into 16 bytes
    bits_128 = (extracted_bits[:PAYLOAD_BIT_LENGTH] > 0.5).astype(np.uint8)
    raw_bytes = np.packbits(bits_128).tobytes()

    magic_ver = raw_bytes[0]
    if magic_ver != MAGIC_VERSION_BYTE:
        return PayloadVerificationResult(
            valid=False,
            asset_id=None,
            timestamp_nonce=None,
            crc_passed=False,
            hmac_passed=False,
            bit_error_rate=1.0,
            confidence=0.0,
            status=f"UNRECOGNIZED_HEADER (0x{magic_ver:02X})",
            raw_bytes=raw_bytes,
        )

    core_data = raw_bytes[:10]
    asset_id = int.from_bytes(core_data[1:6], byteorder="big")
    timestamp_nonce = int.from_bytes(core_data[6:10], byteorder="big")

    stored_crc = int.from_bytes(raw_bytes[10:12], byteorder="big")
    computed_crc = compute_crc16(core_data)
    crc_passed = (stored_crc == computed_crc)

    stored_hmac = raw_bytes[12:16]
    computed_hmac = compute_hmac32(raw_bytes[:12], secret_key)
    hmac_passed = hmac.compare_digest(stored_hmac, computed_hmac)

    if hmac_passed and crc_passed:
        status = "AUTHENTICATED"
        valid = True
    elif crc_passed and not hmac_passed:
        status = "HMAC_FORGERY_DETECTED"
        valid = False
    elif not crc_passed and hmac_passed:
        status = "CRC_ANOMALY"
        valid = False
    else:
        status = "CORRUPTED_OR_WRONG_KEY"
        valid = False

    return PayloadVerificationResult(
        valid=valid,
        asset_id=asset_id if (crc_passed or hmac_passed) else None,
        timestamp_nonce=timestamp_nonce if (crc_passed or hmac_passed) else None,
        crc_passed=crc_passed,
        hmac_passed=hmac_passed,
        bit_error_rate=0.0 if valid else 0.5,
        confidence=1.0 if valid else 0.0,
        status=status,
        raw_bytes=raw_bytes,
    )


def scatter_and_repeat_bits(
    payload_bits: np.ndarray,
    num_blocks: int,
    secret_key: str,
) -> Tuple[np.ndarray, int]:
    """Spread payload bits across available image blocks using repetition and key-permutation.

    Args:
        payload_bits: 128-element 1D array of bits [0, 1].
        num_blocks: Total number of 8x8 blocks available in the image.
        secret_key: Secret key used to seed the pseudo-random permutation.

    Returns:
        Tuple[np.ndarray, int]: (scattered_bits array of shape (num_blocks,), repetition_factor)
    """
    if num_blocks < PAYLOAD_BIT_LENGTH:
        raise ValueError(
            f"Image has only {num_blocks} blocks, but at least {PAYLOAD_BIT_LENGTH} blocks "
            f"are required to embed a 128-bit payload."
        )

    repetition_factor = num_blocks // PAYLOAD_BIT_LENGTH
    active_capacity = repetition_factor * PAYLOAD_BIT_LENGTH

    # Tile the 128 bits across active capacity
    repeated_bits = np.tile(payload_bits, repetition_factor)

    # Pad any remainder blocks with repeated bits from the beginning
    remainder = num_blocks - active_capacity
    if remainder > 0:
        full_stream = np.concatenate([repeated_bits, payload_bits[:remainder]])
    else:
        full_stream = repeated_bits

    # Generate cryptographic pseudo-random permutation of block positions
    seed = derive_key_seed(secret_key)
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(num_blocks)

    # Permute the bitstream so bits are scattered non-sequentially across the image
    scattered = np.zeros(num_blocks, dtype=np.uint8)
    scattered[permutation] = full_stream

    return scattered, repetition_factor


def gather_and_vote_bits(
    extracted_block_bits: np.ndarray,
    num_blocks: int,
    secret_key: str,
) -> Tuple[np.ndarray, float]:
    """Inverse of scatter_and_repeat_bits: un-permute and apply majority voting.

    Args:
        extracted_block_bits: Array of shape (num_blocks,) with values in [0, 1] or soft scores.
        num_blocks: Total block count.
        secret_key: Secret key used to reconstruct the exact permutation.

    Returns:
        Tuple[np.ndarray, float]: (128-bit decoded array, average_channel_agreement)
    """
    seed = derive_key_seed(secret_key)
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(num_blocks)

    # Un-permute: inverse mapping
    unpermuted = np.zeros(num_blocks, dtype=np.float64)
    unpermuted = extracted_block_bits[permutation]

    # Gather observations for each of the 128 bit positions
    accumulated = [[] for _ in range(PAYLOAD_BIT_LENGTH)]
    for idx, bit_val in enumerate(unpermuted):
        pos = idx % PAYLOAD_BIT_LENGTH
        accumulated[pos].append(bit_val)

    voted_bits = np.zeros(PAYLOAD_BIT_LENGTH, dtype=np.uint8)
    agreement_scores = []

    for bit_idx in range(PAYLOAD_BIT_LENGTH):
        obs = np.array(accumulated[bit_idx], dtype=np.float64)
        mean_val = np.mean(obs)
        # Decision threshold at 0.5
        voted_bits[bit_idx] = 1 if mean_val >= 0.5 else 0
        # Agreement is how far from random 0.5 the consensus is
        agreement = abs(mean_val - 0.5) * 2.0
        agreement_scores.append(agreement)

    avg_agreement = float(np.mean(agreement_scores)) if agreement_scores else 0.0
    return voted_bits, avg_agreement
