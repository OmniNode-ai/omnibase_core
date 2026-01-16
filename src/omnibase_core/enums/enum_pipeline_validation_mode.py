"""
Pipeline Validation Mode Enum.

Defines validation modes for pipeline processing and testing.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPipelineValidationMode"]


@unique
class EnumPipelineValidationMode(StrValueHelper, str, Enum):
    """Validation modes for pipeline processing.

    Controls the validation strategy applied during pipeline execution,
    ranging from strict enforcement to various testing modes.

    Values:
        STRICT: Full validation with all rules enforced.
        LENIENT: Relaxed validation that allows minor issues.
        SMOKE: Quick validation for basic functionality checks.
        REGRESSION: Validation focused on catching regressions.
        INTEGRATION: Validation mode for integration testing.
    """

    STRICT = "strict"
    """Full validation with all rules enforced."""

    LENIENT = "lenient"
    """Relaxed validation that allows minor issues."""

    SMOKE = "smoke"
    """Quick validation for basic functionality checks."""

    REGRESSION = "regression"
    """Validation focused on catching regressions."""

    INTEGRATION = "integration"
    """Validation mode for integration testing."""
