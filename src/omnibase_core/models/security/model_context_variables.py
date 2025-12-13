"""
ModelContextVariables: Context variables for permission scopes.

This model provides structured context variables without using Any types.
"""

from pydantic import BaseModel, Field


class ModelContextVariables(BaseModel):
    """Context variables for permission scopes."""

    string_variables: dict[str, str] = Field(
        default_factory=dict,
        description="String context variables",
    )
    integer_variables: dict[str, int] = Field(
        default_factory=dict,
        description="Integer context variables",
    )
    boolean_variables: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean context variables",
    )
    list_variables: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List context variables",
    )
