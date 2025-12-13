"""
ModelRequiredAttributes: Required attributes for permission conditions.

This model provides structured required attributes without using Any types.
"""

from pydantic import BaseModel, Field


class ModelRequiredAttributes(BaseModel):
    """Required attributes for permission conditions."""

    string_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Required string attributes",
    )
    integer_attributes: dict[str, int] = Field(
        default_factory=dict,
        description="Required integer attributes",
    )
    boolean_attributes: dict[str, bool] = Field(
        default_factory=dict,
        description="Required boolean attributes",
    )
    list_attributes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Required list[Any]attributes",
    )
