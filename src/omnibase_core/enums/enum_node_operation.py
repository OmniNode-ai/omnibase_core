from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeOperation(StrValueHelper, str, Enum):
    """Types of operations a node can perform on an envelope."""

    SOURCE = "source"  # Original envelope creation
    ROUTE = "route"  # Routing decision and forwarding
    TRANSFORM = "transform"  # Data transformation or enrichment
    VALIDATE = "validate"  # Validation or compliance checking
    DESTINATION = "destination"  # Final delivery and processing
    ENCRYPTION = "encryption"  # Payload encryption/decryption
    AUDIT = "audit"  # Audit logging and compliance


__all__ = ["EnumNodeOperation"]
