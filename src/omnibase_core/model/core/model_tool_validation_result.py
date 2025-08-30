"""
Tool validation result model.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelToolValidationResult(BaseModel):
    """Result of tool validation checks."""

    is_valid: bool = Field(True, description="Whether tool is valid")
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, description="Validation warnings"
    )
    interface_compliance: bool = Field(
        True, description="Whether tool complies with ProtocolTool interface"
    )
    signature_valid: bool = Field(True, description="Whether tool signature is valid")
    dependencies_satisfied: bool = Field(
        True, description="Whether tool dependencies are satisfied"
    )
