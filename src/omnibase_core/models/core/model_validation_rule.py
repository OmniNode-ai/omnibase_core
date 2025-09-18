"""
Validation rule models for contract content.

Provides strongly typed validation rule specifications.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationRule(BaseModel):
    """Single validation rule specification."""

    model_config = ConfigDict(extra="forbid")

    rule_type: str = Field(
        ...,
        description="Type of validation rule (required, format, range, etc.)",
    )
    field_path: str = Field(
        ...,
        description="JSONPath or field path this rule applies to",
    )
    constraint: Any = Field(
        ...,
        description="Validation constraint value",
    )
    error_message: str | None = Field(
        None,
        description="Custom error message for validation failure",
    )
    severity: str = Field(
        default="error",
        description="Validation severity (error, warning, info)",
    )


class ModelValidationRuleSet(BaseModel):
    """Collection of validation rules."""

    model_config = ConfigDict(extra="forbid")

    rules: list[ModelValidationRule] = Field(
        ...,
        description="List of validation rules",
    )
    description: str | None = Field(
        None,
        description="Description of this validation rule set",
    )
