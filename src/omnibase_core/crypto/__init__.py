"""
Cryptographic utilities for ONEX envelope signing and verification.

This module provides Blake3 hashing and Ed25519 signing capabilities
for secure message envelope handling.
"""

from omnibase_core.crypto.blake3_hasher import (
    hash_bytes,
    hash_canonical_json,
)
from omnibase_core.crypto.ed25519_signer import (
    Ed25519KeyPair,
    generate_keypair,
    sign,
    verify,
)
from omnibase_core.crypto.file_key_provider import FileKeyProvider

__all__ = [
    "Ed25519KeyPair",
    "FileKeyProvider",
    "generate_keypair",
    "hash_bytes",
    "hash_canonical_json",
    "sign",
    "verify",
]
