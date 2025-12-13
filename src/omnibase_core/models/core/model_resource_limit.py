"""
Resource limit model for resource allocation specifications.
"""

from pydantic import BaseModel, Field


class ModelResourceLimit(BaseModel):
    """Individual resource limit specification."""

    min: float | None = Field(default=None, description="Minimum resource amount")
    max: float | None = Field(default=None, description="Maximum resource amount")
    reserved: float | None = Field(default=None, description="Reserved resource amount")
    burst: float | None = Field(default=None, description="Burst limit")
