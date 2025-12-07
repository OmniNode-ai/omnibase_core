"""
v1.0 Pipeline step types for contract-driven NodeCompute.

This module defines the step types available in v1.0 compute pipelines.
Only 3 types are supported in v1.0 - CONDITIONAL and PARALLEL are deferred to v1.2+.
"""

from enum import Enum


class EnumComputeStepType(str, Enum):
    """
    v1.0 Pipeline step types.

    Only 3 types for v1.0 - CONDITIONAL and PARALLEL deferred to v1.2+.

    Attributes:
        VALIDATION: Validates input data against a schema.
        TRANSFORMATION: Applies a transformation to the data.
        MAPPING: Maps fields from input or previous step outputs.
    """

    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    # v1.2+: CONDITIONAL = "conditional"
    # v1.2+: PARALLEL = "parallel"
