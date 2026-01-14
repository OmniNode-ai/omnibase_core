"""Contract compliance levels for validation results."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContractCompliance(StrValueHelper, str, Enum):
    """Contract compliance levels."""

    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    VALIDATION_PENDING = "validation_pending"


__all__ = ["EnumContractCompliance"]
