# Generated from contract: file_stamps_contract.yaml
from enum import Enum


class EnumStampValidationType(Enum):
    """Types of stamp validation operations."""

    CONTENT_INTEGRITY = "CONTENT_INTEGRITY"
    TIMESTAMP_VALIDATION = "TIMESTAMP_VALIDATION"
    FORMAT_VALIDATION = "FORMAT_VALIDATION"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
