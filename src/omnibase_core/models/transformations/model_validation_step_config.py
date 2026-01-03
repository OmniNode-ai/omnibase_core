"""
Configuration for VALIDATION step type.

This module defines the configuration model for VALIDATION step types
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelValidationStepConfig(BaseModel):
    """
    Configuration for VALIDATION step type.

    NOTE: This is NOT a transformation config. It configures the VALIDATION step type.
    Schema validation is semantically distinct from data transformation.

    Attributes:
        config_type: Discriminator field for union type resolution.
        schema_ref: Reference to the schema to validate against.
        fail_on_error: If True, validation failure aborts the pipeline. Defaults to True.
    """

    config_type: Literal["validation"] = "validation"
    schema_ref: str
    fail_on_error: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
