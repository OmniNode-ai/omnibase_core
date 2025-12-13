"""
Tool validation result model.
"""

from pydantic import BaseModel, Field


class ModelToolValidationResult(BaseModel):
    """Result of tool validation checks."""

    is_valid: bool = Field(default=True, description="Whether tool is valid")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation error messages",
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )
    interface_compliance: bool = Field(
        default=True,
        description="Whether tool complies with ProtocolTool interface",
    )
    signature_valid: bool = Field(
        default=True, description="Whether tool signature is valid"
    )
    dependencies_satisfied: bool = Field(
        default=True,
        description="Whether tool dependencies are satisfied",
    )
