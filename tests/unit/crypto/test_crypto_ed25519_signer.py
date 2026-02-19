# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Ed25519 signing utilities."""

from __future__ import annotations

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import (
    Ed25519KeyPair,
    generate_keypair,
    sign,
    sign_base64,
    verify,
    verify_base64,
)


@pytest.mark.unit
class TestGenerateKeypair:
    """Tests for generate_keypair function."""

    def test_generate_keypair_returns_keypair(self) -> None:
        """generate_keypair returns Ed25519KeyPair."""
        keypair = generate_keypair()
        assert isinstance(keypair, Ed25519KeyPair)

    def test_generate_keypair_private_key_length(self) -> None:
        """Private key is 32 bytes."""
        keypair = generate_keypair()
        assert len(keypair.private_key_bytes) == 32

    def test_generate_keypair_public_key_length(self) -> None:
        """Public key is 32 bytes."""
        keypair = generate_keypair()
        assert len(keypair.public_key_bytes) == 32

    def test_generate_keypair_unique_keys(self) -> None:
        """Each call generates unique keys."""
        keypair1 = generate_keypair()
        keypair2 = generate_keypair()
        assert keypair1.private_key_bytes != keypair2.private_key_bytes
        assert keypair1.public_key_bytes != keypair2.public_key_bytes


@pytest.mark.unit
class TestEd25519KeyPair:
    """Tests for Ed25519KeyPair class."""

    def test_keypair_get_private_key(self) -> None:
        """get_private_key returns usable private key object."""
        keypair = generate_keypair()
        private_key = keypair.get_private_key()
        # Verify we can use it for signing
        signature = private_key.sign(b"test data")
        assert len(signature) == 64

    def test_keypair_get_public_key(self) -> None:
        """get_public_key returns usable public key object."""
        keypair = generate_keypair()
        public_key = keypair.get_public_key()
        # Verify the key object exists and has expected method
        assert hasattr(public_key, "verify")

    def test_keypair_public_key_base64(self) -> None:
        """public_key_base64 returns URL-safe base64 string."""
        keypair = generate_keypair()
        b64 = keypair.public_key_base64()
        assert isinstance(b64, str)
        # URL-safe base64 for 32 bytes should be 43-44 characters
        assert 40 <= len(b64) <= 48


@pytest.mark.unit
class TestSignAndVerify:
    """Tests for sign and verify functions."""

    def test_sign_returns_64_bytes(self) -> None:
        """sign returns 64-byte signature."""
        keypair = generate_keypair()
        signature = sign(keypair.private_key_bytes, b"test data")
        assert isinstance(signature, bytes)
        assert len(signature) == 64

    def test_sign_deterministic(self) -> None:
        """Ed25519 signatures are deterministic."""
        keypair = generate_keypair()
        data = b"test data"
        sig1 = sign(keypair.private_key_bytes, data)
        sig2 = sign(keypair.private_key_bytes, data)
        assert sig1 == sig2

    def test_verify_valid_signature(self) -> None:
        """verify returns True for valid signature."""
        keypair = generate_keypair()
        data = b"test data"
        signature = sign(keypair.private_key_bytes, data)
        assert verify(keypair.public_key_bytes, data, signature) is True

    def test_verify_invalid_signature(self) -> None:
        """verify returns False for tampered signature."""
        keypair = generate_keypair()
        data = b"test data"
        signature = sign(keypair.private_key_bytes, data)
        # Tamper with signature
        bad_signature = bytes([signature[0] ^ 0xFF]) + signature[1:]
        assert verify(keypair.public_key_bytes, data, bad_signature) is False

    def test_verify_wrong_data(self) -> None:
        """verify returns False for wrong data."""
        keypair = generate_keypair()
        data = b"original data"
        signature = sign(keypair.private_key_bytes, data)
        assert verify(keypair.public_key_bytes, b"different data", signature) is False

    def test_verify_wrong_key(self) -> None:
        """verify returns False for wrong public key."""
        keypair1 = generate_keypair()
        keypair2 = generate_keypair()
        data = b"test data"
        signature = sign(keypair1.private_key_bytes, data)
        assert verify(keypair2.public_key_bytes, data, signature) is False

    def test_verify_invalid_key_format(self) -> None:
        """verify returns False for invalid key format."""
        keypair = generate_keypair()
        data = b"test data"
        signature = sign(keypair.private_key_bytes, data)
        # Invalid key (wrong length)
        assert verify(b"invalid", data, signature) is False


@pytest.mark.unit
class TestBase64Functions:
    """Tests for base64 sign/verify functions."""

    def test_sign_base64_returns_string(self) -> None:
        """sign_base64 returns base64 string."""
        keypair = generate_keypair()
        signature = sign_base64(keypair.private_key_bytes, b"test data")
        assert isinstance(signature, str)

    def test_verify_base64_valid(self) -> None:
        """verify_base64 returns True for valid signature."""
        keypair = generate_keypair()
        data = b"test data"
        signature_b64 = sign_base64(keypair.private_key_bytes, data)
        assert verify_base64(keypair.public_key_bytes, data, signature_b64) is True

    def test_verify_base64_invalid_signature(self) -> None:
        """verify_base64 returns False for invalid signature."""
        keypair = generate_keypair()
        assert (
            verify_base64(keypair.public_key_bytes, b"data", "invalid_base64!") is False
        )

    def test_sign_verify_base64_roundtrip(self) -> None:
        """sign_base64 and verify_base64 work together."""
        keypair = generate_keypair()
        messages = [
            b"hello",
            b"world",
            b"",
            b"x" * 10000,
        ]
        for msg in messages:
            sig = sign_base64(keypair.private_key_bytes, msg)
            assert verify_base64(keypair.public_key_bytes, msg, sig) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
