from enum import Enum


class EnumContractCompliance(str, Enum):
    """Contract compliance levels."""

    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    VALIDATION_PENDING = "validation_pending"
