#!/usr/bin/env python3
"""
Validation Rules Model - ONEX Standards Compliant.

Contract validation rules and constraint definitions providing:
- Runtime validation rules for input/output models
- Configuration constraints and compliance checking
- Strict typing enforcement and validation policies
- Custom constraint definitions with validation support

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelValidationRules(BaseModel):
    """
    Contract validation rules and constraint definitions.

    Defines runtime validation rules for input/output models,
    configuration constraints, and compliance checking.
    """

    strict_typing_enabled: bool = Field(
        default=True,
        description="Enforce strict type checking for all operations",
    )

    input_validation_enabled: bool = Field(
        default=True,
        description="Enable input model validation",
    )

    output_validation_enabled: bool = Field(
        default=True,
        description="Enable output model validation",
    )

    performance_validation_enabled: bool = Field(
        default=True,
        description="Enable performance requirement validation",
    )

    constraint_definitions: dict[str, str] = Field(
        default_factory=dict,
        description="Custom constraint definitions for validation",
    )
