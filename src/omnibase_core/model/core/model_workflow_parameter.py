"""
Canonical Workflow Parameter Model

Single responsibility: Define type-safe workflow parameters with generic value types.
Replaces all duplicate ModelWorkflowParameter definitions across the codebase.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ModelWorkflowParameter(BaseModel, Generic[T]):
    """
    Type-safe workflow parameter with generic value type.

    This canonical model replaces all duplicate ModelWorkflowParameter definitions
    and eliminates the need for string-based type indicators.
    """

    name: str = Field(..., description="Parameter name")
    value: T = Field(..., description="Type-safe parameter value")
    is_required: bool = Field(
        default=False, description="Whether parameter is required"
    )
    source: str = Field(
        default="user", description="Source of parameter (user, system, default)"
    )
    description: Optional[str] = Field(
        default=None, description="Parameter description"
    )
    validated: bool = Field(
        default=False, description="Whether parameter was validated"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def __str__(self) -> str:
        """String representation of the parameter."""
        return f"{self.name}={self.value} ({'required' if self.is_required else 'optional'})"

    def __repr__(self) -> str:
        """Detailed representation of the parameter."""
        return f"ModelWorkflowParameter(name='{self.name}', value={repr(self.value)}, type={type(self.value).__name__})"
