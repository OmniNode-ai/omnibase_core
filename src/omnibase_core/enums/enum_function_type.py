"""
Function Type Enum.

Strongly typed function type values for configuration and processing.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFunctionType(StrValueHelper, str, Enum):
    """
    Strongly typed function type values.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    TRANSFORM = "transform"
    VALIDATE = "validate"
    COMPUTE = "compute"
    GATEWAY = "gateway"
    ORCHESTRATOR = "orchestrator"

    @classmethod
    def is_data_processing(cls, function_type: EnumFunctionType) -> bool:
        """Check if the function type is for data processing."""
        return function_type in {cls.TRANSFORM, cls.COMPUTE}

    @classmethod
    def is_control_flow(cls, function_type: EnumFunctionType) -> bool:
        """Check if the function type is for control flow."""
        return function_type in {cls.GATEWAY, cls.ORCHESTRATOR}

    @classmethod
    def is_quality_assurance(cls, function_type: EnumFunctionType) -> bool:
        """Check if the function type is for quality assurance."""
        return function_type == cls.VALIDATE

    @classmethod
    def requires_complex_logic(cls, function_type: EnumFunctionType) -> bool:
        """Check if the function type typically requires complex logic."""
        return function_type in {cls.COMPUTE, cls.ORCHESTRATOR}


# Export for use
__all__ = ["EnumFunctionType"]
