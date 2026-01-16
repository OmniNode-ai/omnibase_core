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

import re
from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

# Compiled regex pattern for SHA256 validation (64 lowercase hex characters)
# Using regex instead of string membership check for O(n) vs O(n*m) performance
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@unique
class EnumHashAlgorithm(StrValueHelper, str, Enum):
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
        """
        Return expected hash length in hex characters.

        v1 Scope:
            - SHA256 only (64 lowercase hex characters)
        Future v2:
            - SHA384 (96 hex chars), SHA512 (128 hex chars)
            - Update expected_length property and validate_hash logic
            - Add corresponding _SHA384_PATTERN and _SHA512_PATTERN constants
        """
        lengths = {
            EnumHashAlgorithm.SHA256: 64,
            # Future v2: Add SHA384: 96, SHA512: 128
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
        # Use compiled regex for O(n) performance vs O(n*m) string membership check
        # Regex validates both length (64 chars) AND hex characters in one operation
        # Future v2: Add pattern selection based on self (SHA384, SHA512)
        return bool(_SHA256_PATTERN.match(hash_value))


__all__ = ["EnumHashAlgorithm"]
