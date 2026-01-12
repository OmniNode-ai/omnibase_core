"""Pipeline step types for contract-driven NodeCompute operations."""

from enum import Enum, unique


@unique
class EnumComputeStepType(str, Enum):
    """Pipeline step types for compute operations.

    Types: VALIDATION, TRANSFORMATION, MAPPING.
    """

    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    # v1.2+: CONDITIONAL = "conditional"
    # v1.2+: PARALLEL = "parallel"
