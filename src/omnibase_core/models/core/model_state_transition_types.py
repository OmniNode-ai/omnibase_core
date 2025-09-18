"""
Types for state transition configurations.

Provides strongly typed models for different types of state transitions.
"""

from typing import Union

from pydantic import BaseModel, ConfigDict, Field


class ModelStateUpdate(BaseModel):
    """Single state field update."""

    model_config = ConfigDict(extra="forbid")

    field_path: str = Field(
        ...,
        description="JSONPath to the field to update (e.g., 'user.name', 'items[0].status')",
    )
    value: Union[str, int, float, bool, None] = Field(
        ...,
        description="New value for the field",
    )
    value_type: str = Field(
        default="literal",
        description="Type of value: 'literal', 'expression', 'template'",
    )


class ModelToolParameter(BaseModel):
    """Parameter for tool-based transitions."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Parameter name",
    )
    value: Union[str, int, float, bool, None] = Field(
        ...,
        description="Parameter value",
    )
    source: str = Field(
        default="literal",
        description="Value source: 'literal', 'state_field', 'input_field'",
    )


class ModelConditionalBranch(BaseModel):
    """Branch in a conditional transition."""

    model_config = ConfigDict(extra="forbid")

    condition: str = Field(
        ...,
        description="Condition expression to evaluate",
    )
    updates: list[ModelStateUpdate] = Field(
        default_factory=list,
        description="State updates to apply if condition matches",
    )
    description: str | None = Field(
        None,
        description="Description of this branch",
    )


class ModelDefaultTransition(BaseModel):
    """Default transition for conditional transitions."""

    model_config = ConfigDict(extra="forbid")

    updates: list[ModelStateUpdate] = Field(
        default_factory=list,
        description="State updates to apply as default",
    )
    description: str | None = Field(
        None,
        description="Description of the default transition",
    )
