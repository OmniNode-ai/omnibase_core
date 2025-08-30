"""
Model for alert data.

Data for quota alerts.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelAlertData(BaseModel):
    """Data for quota alerts."""

    utilization: Optional[float] = Field(None, description="Utilization percentage")
    remaining: Optional[int] = Field(None, description="Remaining tokens")
    cost: Optional[float] = Field(None, description="Current cost")
    budget: Optional[float] = Field(None, description="Budget limit")
