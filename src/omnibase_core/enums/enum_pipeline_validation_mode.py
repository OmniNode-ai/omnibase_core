# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Pipeline Validation Mode Enum.

Defines validation modes for pipeline processing and testing.
"""

from enum import Enum

__all__ = ["EnumPipelineValidationMode"]


class EnumPipelineValidationMode(str, Enum):
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
