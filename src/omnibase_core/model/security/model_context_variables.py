"""
ModelContextVariables: Context variables for permission scopes.

This model provides structured context variables without using Any types.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelContextVariables(BaseModel):
    """Context variables for permission scopes."""

    string_variables: Dict[str, str] = Field(
        default_factory=dict, description="String context variables"
    )
    integer_variables: Dict[str, int] = Field(
        default_factory=dict, description="Integer context variables"
    )
    boolean_variables: Dict[str, bool] = Field(
        default_factory=dict, description="Boolean context variables"
    )
    list_variables: Dict[str, List[str]] = Field(
        default_factory=dict, description="List context variables"
    )
