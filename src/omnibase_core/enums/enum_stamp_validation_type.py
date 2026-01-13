from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStampValidationType(StrValueHelper, str, Enum):
    """Types of stamp validation operations."""

    CONTENT_INTEGRITY = "CONTENT_INTEGRITY"
    TIMESTAMP_VALIDATION = "TIMESTAMP_VALIDATION"
    FORMAT_VALIDATION = "FORMAT_VALIDATION"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
