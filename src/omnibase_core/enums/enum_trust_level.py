from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTrustLevel(StrValueHelper, str, Enum):
    """Trust level of the signature chain."""

    HIGH_TRUST = "high_trust"  # All signatures from high-trust nodes
    TRUSTED = "trusted"  # All signatures from trusted nodes
    STANDARD = "standard"  # Standard trust level
    PARTIAL_TRUST = "partial_trust"  # Mix of trusted and untrusted signatures
    UNTRUSTED = "untrusted"  # No trusted signatures
    COMPROMISED = "compromised"  # Evidence of compromise detected


__all__ = ["EnumTrustLevel"]
