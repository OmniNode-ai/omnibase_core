# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Ed25519 signing utilities for envelope authentication.

Ed25519 is chosen for envelope signing because:
- Fast key generation and signing
- Small keys (32 bytes) and signatures (64 bytes)
- Deterministic signatures (no random nonce needed)
- Strong security guarantees

The cryptography library is used as it's already a dependency
and provides a well-audited Ed25519 implementation.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


@dataclass(frozen=True)
class Ed25519KeyPair:
    """
    An Ed25519 key pair for signing and verification.

    Attributes:
        private_key_bytes: Raw 32-byte private key.
        public_key_bytes: Raw 32-byte public key.
    """

    private_key_bytes: bytes
    public_key_bytes: bytes

    def get_private_key(self) -> Ed25519PrivateKey:
        """Load the private key object from raw bytes."""
        return Ed25519PrivateKey.from_private_bytes(self.private_key_bytes)

    def get_public_key(self) -> Ed25519PublicKey:
        """Load the public key object from raw bytes."""
        return Ed25519PublicKey.from_public_bytes(self.public_key_bytes)

    def public_key_base64(self) -> str:
        """Return the public key as URL-safe base64."""
        return base64.urlsafe_b64encode(self.public_key_bytes).decode("ascii")


def generate_keypair() -> Ed25519KeyPair:
    """
    Generate a new Ed25519 key pair.

    Returns:
        Ed25519KeyPair containing private and public key bytes.

    Example:
        >>> keypair = generate_keypair()
        >>> len(keypair.private_key_bytes)
        32
        >>> len(keypair.public_key_bytes)
        32
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Extract raw bytes for storage/transmission
    private_bytes = private_key.private_bytes_raw()
    public_bytes = public_key.public_bytes_raw()

    return Ed25519KeyPair(
        private_key_bytes=private_bytes,
        public_key_bytes=public_bytes,
    )


def sign(private_key_bytes: bytes, data: bytes) -> bytes:
    """
    Sign data using Ed25519.

    Args:
        private_key_bytes: 32-byte Ed25519 private key.
        data: Data to sign.

    Returns:
        64-byte Ed25519 signature.

    Raises:
        ValueError: If private key is invalid.
    """
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private_key.sign(data)


def verify(public_key_bytes: bytes, data: bytes, signature: bytes) -> bool:
    """
    Verify an Ed25519 signature.

    Args:
        public_key_bytes: 32-byte Ed25519 public key.
        data: Original data that was signed.
        signature: 64-byte signature to verify.

    Returns:
        True if signature is valid, False otherwise.

    Note:
        This function returns False on invalid signatures rather than
        raising an exception, making it safe for use in validation logic.
    """
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, data)
        return True
    except InvalidSignature:
        return False
    except (ValueError, TypeError):
        # Invalid key format (wrong length, wrong type) returns False for safe validation
        return False


def sign_base64(private_key_bytes: bytes, data: bytes) -> str:
    """
    Sign data and return URL-safe base64 encoded signature.

    Args:
        private_key_bytes: 32-byte Ed25519 private key.
        data: Data to sign.

    Returns:
        URL-safe base64 encoded signature.
    """
    signature = sign(private_key_bytes, data)
    return base64.urlsafe_b64encode(signature).decode("ascii")


def verify_base64(public_key_bytes: bytes, data: bytes, signature_b64: str) -> bool:
    """
    Verify a base64-encoded Ed25519 signature.

    Args:
        public_key_bytes: 32-byte Ed25519 public key.
        data: Original data that was signed.
        signature_b64: URL-safe base64 encoded signature.

    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        signature = base64.urlsafe_b64decode(signature_b64)
        return verify(public_key_bytes, data, signature)
    except (ValueError, TypeError, InvalidSignature):
        # Invalid base64 or key format returns False for safe validation
        return False


__all__ = [
    "Ed25519KeyPair",
    "generate_keypair",
    "sign",
    "sign_base64",
    "verify",
    "verify_base64",
]
