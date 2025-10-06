from enum import Enum


class EnumChainValidationStatus(str, Enum):
    """Status of signature chain validation."""

    VALID = "valid"  # All signatures valid and chain complete
    PARTIAL = "partial"  # Some signatures valid, some invalid
    INVALID = "invalid"  # Chain broken or all signatures invalid
    INCOMPLETE = "incomplete"  # Chain missing required signatures
    TAMPERED = "tampered"  # Evidence of tampering detected
    EXPIRED = "expired"  # Signatures too old for policy
