from enum import Enum, unique


@unique
class EnumStampValidationType(Enum):
    """Types of stamp validation operations."""

    CONTENT_INTEGRITY = "CONTENT_INTEGRITY"
    TIMESTAMP_VALIDATION = "TIMESTAMP_VALIDATION"
    FORMAT_VALIDATION = "FORMAT_VALIDATION"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
