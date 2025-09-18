"""
Node validation result model.
"""

from pydantic import BaseModel, Field


class ModelNodeValidationResult(BaseModel):
    """Result of node validation checks."""

    is_valid: bool = Field(True, description="Whether node is valid")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation error messages",
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )
    interface_compliance: bool = Field(
        True,
        description="Whether node complies with ProtocolNode interface",
    )
    signature_valid: bool = Field(True, description="Whether node signature is valid")
    dependencies_satisfied: bool = Field(
        True,
        description="Whether node dependencies are satisfied",
    )
