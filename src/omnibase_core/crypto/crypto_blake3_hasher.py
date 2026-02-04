"""
Blake3 hashing utilities for envelope payload verification.

Blake3 is chosen over SHA-256 for:
- Faster performance (especially on modern CPUs with SIMD)
- Tree-hashing support for parallel processing
- Designed for cryptographic security from the ground up

The canonical JSON serialization ensures deterministic hashing
regardless of key ordering in dictionaries.
"""

from __future__ import annotations

import json

import blake3


def hash_bytes(data: bytes) -> str:
    """
    Hash raw bytes using Blake3.

    Args:
        data: Raw bytes to hash.

    Returns:
        Hex-encoded Blake3 digest (64 characters).

    Example:
        >>> hash_bytes(b"hello world")
        'd74981efa70a0c880b8d8c1985d075dbcbf679b99a5f9914e5aaf96b831a9e24'
    """
    return blake3.blake3(data).hexdigest()


def hash_canonical_json(obj: dict[str, object]) -> str:
    """
    Hash a dictionary using canonical JSON serialization.

    Canonical JSON ensures deterministic ordering:
    - Keys are sorted alphabetically
    - No extra whitespace
    - UTF-8 encoding

    This is critical for signature verification where both
    signer and verifier must produce identical hashes.

    Args:
        obj: Dictionary to serialize and hash.

    Returns:
        Hex-encoded Blake3 digest of the canonical JSON.

    Example:
        >>> hash_canonical_json({"b": 2, "a": 1})
        '...'  # Same hash regardless of insertion order
    """
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hash_bytes(canonical.encode("utf-8"))


__all__ = ["hash_bytes", "hash_canonical_json"]
