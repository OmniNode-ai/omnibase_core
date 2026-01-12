"""Contract compliance levels for validation results."""

from enum import Enum, unique


@unique
class EnumContractCompliance(str, Enum):
    """Contract compliance levels."""

    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    VALIDATION_PENDING = "validation_pending"
