from pydantic import Field

"""
Resource limit model for resource allocation specifications.
"""

from pydantic import BaseModel, Field


class ModelResourceLimit(BaseModel):
    """Individual resource limit specification."""

    min: float | None = Field(None, description="Minimum resource amount")
    max: float | None = Field(None, description="Maximum resource amount")
    reserved: float | None = Field(None, description="Reserved resource amount")
    burst: float | None = Field(None, description="Burst limit")
