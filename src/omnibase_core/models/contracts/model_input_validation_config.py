"""
Input Validation Configuration Model - ONEX Standards Compliant.

Input validation and transformation rules defining validation rules,
constraints, and transformation logic for input data processing.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelInputValidationConfig(BaseModel):
    """
    Input validation and transformation rules.

    Defines validation rules, constraints, and transformation
    logic for input data processing.
    """

    strict_validation: bool = Field(
        default=True,
        description="Enable strict input validation",
    )

    required_fields: list[str] = Field(
        default_factory=list,
        description="Required input fields",
    )

    field_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Field-specific validation constraints",
    )

    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Input transformation rules",
    )

    sanitization_enabled: bool = Field(
        default=True,
        description="Enable input sanitization",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
