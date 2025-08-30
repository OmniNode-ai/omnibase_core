"""
ModelRequiredAttributes: Required attributes for permission conditions.

This model provides structured required attributes without using Any types.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelRequiredAttributes(BaseModel):
    """Required attributes for permission conditions."""

    string_attributes: Dict[str, str] = Field(
        default_factory=dict, description="Required string attributes"
    )
    integer_attributes: Dict[str, int] = Field(
        default_factory=dict, description="Required integer attributes"
    )
    boolean_attributes: Dict[str, bool] = Field(
        default_factory=dict, description="Required boolean attributes"
    )
    list_attributes: Dict[str, List[str]] = Field(
        default_factory=dict, description="Required list attributes"
    )
