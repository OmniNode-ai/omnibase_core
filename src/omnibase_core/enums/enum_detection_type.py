"""Detection types for sensitive information classification."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDetectionType(StrValueHelper, str, Enum):
    """Types of sensitive information detection."""

    PII = "pii"
    SECRET = "secret"
    PROPRIETARY = "proprietary"
    CREDENTIAL = "credential"
    API_KEY = "api_key"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    GOVERNMENT_ID = "government_id"
    CUSTOM = "custom"


__all__ = ["EnumDetectionType"]
