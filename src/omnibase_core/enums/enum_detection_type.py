from enum import Enum, unique


@unique
class EnumDetectionType(str, Enum):
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
