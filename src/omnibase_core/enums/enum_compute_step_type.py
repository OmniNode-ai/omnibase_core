"""Pipeline step types for contract-driven NodeCompute operations."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComputeStepType(StrValueHelper, str, Enum):
    """Pipeline step types for compute operations.

    Types: VALIDATION, TRANSFORMATION, MAPPING.
    """

    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    # v1.2+: CONDITIONAL = "conditional"
    # v1.2+: PARALLEL = "parallel"


__all__ = ["EnumComputeStepType"]
