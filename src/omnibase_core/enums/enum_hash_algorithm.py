# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Hash Algorithm Enumeration.

Defines supported cryptographic hash algorithms for artifact integrity verification.

v1 Scope:
    - SHA256 only (64 lowercase hex characters)
    - Additional algorithms (SHA384, SHA512) may be added in v2

Thread Safety:
    Enum values are immutable and thread-safe.

Example:
    >>> from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm
    >>> algo = EnumHashAlgorithm.SHA256
    >>> algo.expected_length
    64
    >>> algo.validate_hash("a" * 64)
    True
"""

from enum import Enum


class EnumHashAlgorithm(str, Enum):
    """
    Supported cryptographic hash algorithms for integrity verification.

    Each algorithm defines:
        - The algorithm identifier (value)
        - Expected hash output length in hex characters

    v1 supports only SHA256 for simplicity and security.
    Future versions may add SHA384, SHA512, etc.

    Attributes:
        SHA256: SHA-256 hash algorithm (64 hex chars output)
    """

    SHA256 = "sha256"

    @property
    def expected_length(self) -> int:
        """Return expected hash length in hex characters."""
        lengths = {
            EnumHashAlgorithm.SHA256: 64,
        }
        return lengths[self]

    def validate_hash(self, hash_value: str) -> bool:
        """
        Validate that a hash value matches expected format for this algorithm.

        Args:
            hash_value: The hash string to validate

        Returns:
            True if hash matches expected format (lowercase hex, correct length)

        Example:
            >>> EnumHashAlgorithm.SHA256.validate_hash("a" * 64)
            True
            >>> EnumHashAlgorithm.SHA256.validate_hash("A" * 64)  # uppercase
            False
            >>> EnumHashAlgorithm.SHA256.validate_hash("a" * 63)  # wrong length
            False
        """
        if len(hash_value) != self.expected_length:
            return False
        # Must be lowercase hex only
        return all(c in "0123456789abcdef" for c in hash_value)


__all__ = ["EnumHashAlgorithm"]
