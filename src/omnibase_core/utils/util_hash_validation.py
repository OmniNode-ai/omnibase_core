"""Shared hash format validation utilities.

This module provides reusable hash format validation for Pydantic models
that need to validate hash strings in the "algorithm:hexdigest" format.

The pattern supports various hash algorithms (sha256, md5, sha1, etc.)
and validates that the digest portion contains only hexadecimal characters.

Thread Safety:
    All functions in this module are stateless and thread-safe.

Example:
    >>> from omnibase_core.utils.util_hash_validation import validate_hash_format
    >>> validate_hash_format("sha256:abc123def456")
    'sha256:abc123def456'
    >>> validate_hash_format("invalid")  # Raises ValueError
"""

import re

# Pattern for validating hash format: "algorithm:hexdigest"
# - Algorithm: alphanumeric (allows uppercase for flexibility, e.g., "SHA256" or "sha256")
# - Separator: colon
# - Digest: hexadecimal characters (0-9, a-f, A-F)
HASH_FORMAT_PATTERN = re.compile(r"^[a-zA-Z0-9]+:[a-fA-F0-9]+$")

# Maximum length for hash strings to prevent ReDoS attacks.
# Covers SHA-512 (128 hex chars) + algorithm prefix (e.g., "sha512:") with margin.
MAX_HASH_LENGTH = 256


def validate_hash_format(v: str) -> str:
    """Validate that a hash string follows the 'algorithm:hexdigest' format.

    This function can be used directly in Pydantic field validators to ensure
    hash strings conform to the expected format.

    Args:
        v: The hash string to validate.

    Returns:
        The validated hash string (unchanged if valid).

    Raises:
        ValueError: If the hash format is invalid or too long.

    Examples:
        Valid formats:
        - "sha256:abc123def456"
        - "md5:d41d8cd98f00b204e9800998ecf8427e"
        - "SHA256:ABC123" (uppercase algorithm and mixed-case digest allowed)

        Invalid formats:
        - "abc123" (missing algorithm prefix)
        - "sha256:" (empty digest)
        - ":abc123" (empty algorithm)
        - "sha-256:abc123" (hyphen not allowed in algorithm)
        - "sha256:xyz123" (non-hex characters in digest)
    """
    # Length check before regex to prevent ReDoS attacks
    if len(v) > MAX_HASH_LENGTH:
        raise ValueError(  # error-ok: Pydantic validator requires ValueError
            f"Hash too long: {len(v)} characters (max {MAX_HASH_LENGTH}). "
            "This may indicate malformed or malicious input."
        )
    if not HASH_FORMAT_PATTERN.match(v):
        raise ValueError(  # error-ok: Pydantic validator requires ValueError
            f"Invalid hash format: '{v}'. "
            "Must be 'algorithm:hexdigest' format (e.g., 'sha256:abc123'). "
            "Algorithm must be alphanumeric, digest must be hexadecimal."
        )
    return v


__all__ = [
    "HASH_FORMAT_PATTERN",
    "MAX_HASH_LENGTH",
    "validate_hash_format",
]
