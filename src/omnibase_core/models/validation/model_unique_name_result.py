"""
Unique Name Result Model.

Result of unique step name validation in workflow DAG validation.
"""

from pydantic import BaseModel, Field

__all__ = ["ModelUniqueNameResult"]


class ModelUniqueNameResult(BaseModel):
    """Result of unique step name validation."""

    model_config = {"frozen": True}

    is_valid: bool = Field(
        default=True,
        description="Whether all step names are unique",
    )
    duplicate_names: list[str] = Field(
        default_factory=list,
        description="List of step names that appear more than once",
    )
