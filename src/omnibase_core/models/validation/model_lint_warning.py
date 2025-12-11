"""
Lint warning model for workflow contract validation.

This module provides the LintWarning model used by the WorkflowContractLinter
to report non-semantic validation issues.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = ["ModelLintWarning"]


class ModelLintWarning(BaseModel):
    """
    Linting warning for workflow contracts.

    This model represents a single warning detected during workflow linting.
    Warnings are informational only and do not affect workflow execution.

    Attributes:
        code: Warning code (e.g., 'W001')
        message: Human-readable warning message
        step_reference: Step identifier for step-specific warnings (as string)
        severity: Warning severity level
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
    }

    code: str = Field(
        ...,
        description="Warning code (e.g., 'W001')",
        min_length=1,
        max_length=20,
    )

    message: str = Field(
        ...,
        description="Human-readable warning message",
        min_length=1,
    )

    step_reference: str | None = Field(
        default=None,
        description="Step reference for step-specific warnings (serialized UUID)",
    )

    severity: Literal["info", "warning"] = Field(
        default="warning",
        description="Warning severity level",
    )
