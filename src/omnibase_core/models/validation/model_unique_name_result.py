"""
Unique Name Result Model.

Result of unique step name validation in workflow DAG validation.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelUniqueNameResult"]


class ModelUniqueNameResult(BaseModel):
    """
    Result of unique step name validation in workflow DAG.

    This model captures the outcome of checking that all workflow steps have
    unique names. Duplicate step names are invalid because they create
    ambiguity in step references and make debugging difficult.

    This model is immutable (frozen=True) after creation, making it safe
    for use as dictionary keys and in thread-safe contexts.

    Attributes:
        is_valid: Whether all step names in the workflow are unique.
        duplicate_names: List of step names that appear more than once,
            allowing identification of which names need to be made unique.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_valid: bool = Field(
        default=True,
        description="Whether all step names are unique",
    )
    duplicate_names: list[str] = Field(
        default_factory=list,
        description="List of step names that appear more than once",
    )
