"""
Resource limit model for resource allocation specifications.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelResourceLimit(BaseModel):
    """Individual resource limit specification."""

    min: Optional[float] = Field(None, description="Minimum resource amount")
    max: Optional[float] = Field(None, description="Maximum resource amount")
    reserved: Optional[float] = Field(None, description="Reserved resource amount")
    burst: Optional[float] = Field(None, description="Burst limit")
