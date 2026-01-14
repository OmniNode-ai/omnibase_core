"""Chain validation status for signature verification."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumChainValidationStatus(StrValueHelper, str, Enum):
    """Status of signature chain validation."""

    VALID = "valid"  # All signatures valid and chain complete
    PARTIAL = "partial"  # Some signatures valid, some invalid
    INVALID = "invalid"  # Chain broken or all signatures invalid
    INCOMPLETE = "incomplete"  # Chain missing required signatures
    TAMPERED = "tampered"  # Evidence of tampering detected
    EXPIRED = "expired"  # Signatures too old for policy


__all__ = ["EnumChainValidationStatus"]
