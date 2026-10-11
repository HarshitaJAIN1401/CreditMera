"""Unit tests for compact authenticated asset-ID payload encoder and decoder.
"""
import pytest
import numpy as np

from watermark.payload import (
    encode_payload,
    decode_payload,
    compute_crc16,
    compute_hmac32,
    scatter_and_repeat_bits,
    gather_and_vote_bits,
    PAYLOAD_BIT_LENGTH,
    PAYLOAD_BYTE_LENGTH,
)


@pytest.mark.unit
def test_payload_encode_decode_roundtrip():
    asset_id = 987654321
    secret_key = "correct_master_key_123"
    timestamp = 16987654

    raw_bytes, bits = encode_payload(asset_id, secret_key, timestamp)
    assert len(raw_bytes) == PAYLOAD_BYTE_LENGTH
    assert len(bits) == PAYLOAD_BIT_LENGTH

    result = decode_payload(bits, secret_key)
    assert result.valid is True
    assert result.asset_id == asset_id
    assert result.timestamp_nonce == timestamp
    assert result.crc_passed is True
    assert result.hmac_passed is True
    assert result.status == "AUTHENTICATED"


@pytest.mark.unit
def test_payload_wrong_secret_key_fails_hmac():
    asset_id = 123456
    correct_key = "my_private_key"
    wrong_key = "attacker_imposter_key"

    _, bits = encode_payload(asset_id, correct_key, timestamp_nonce=500)
    result = decode_payload(bits, wrong_key)

    # With wrong key, HMAC verification MUST fail
    assert result.valid is False
    assert result.hmac_passed is False
    # CRC might pass since CRC doesn't depend on key, proving CRC is not security:
    assert result.crc_passed is True
    assert result.status == "HMAC_FORGERY_DETECTED"


@pytest.mark.unit
def test_payload_corrupted_bits_detected():
    asset_id = 42
    secret_key = "test_key"

    _, bits = encode_payload(asset_id, secret_key)

    # Flip 3 bits in the asset ID portion (bits 10, 11, 12)
    corrupted_bits = bits.copy()
    corrupted_bits[10] ^= 1
    corrupted_bits[11] ^= 1
    corrupted_bits[12] ^= 1

    result = decode_payload(corrupted_bits, secret_key)
    assert result.valid is False
    assert result.crc_passed is False
    assert result.hmac_passed is False


@pytest.mark.unit
def test_scatter_and_gather_majority_voting():
    asset_id = 555666
    secret_key = "voting_key"
    num_blocks = 1024  # 1024 / 128 = 8 repetitions

    _, payload_bits = encode_payload(asset_id, secret_key)
    scattered_bits, repetition = scatter_and_repeat_bits(payload_bits, num_blocks, secret_key)
    assert repetition == 8
    assert len(scattered_bits) == num_blocks

    # Add random noise: flip 10% of scattered bits
    noisy_bits = scattered_bits.copy().astype(np.float64)
    rng = np.random.default_rng(123)
    flip_mask = rng.random(num_blocks) < 0.10
    noisy_bits[flip_mask] = 1.0 - noisy_bits[flip_mask]

    # Majority voting should successfully recover ground truth payload
    voted_bits, confidence = gather_and_vote_bits(noisy_bits, num_blocks, secret_key)
    np.testing.assert_array_equal(voted_bits, payload_bits)

    result = decode_payload(voted_bits, secret_key)
    assert result.valid is True
    assert result.asset_id == asset_id
