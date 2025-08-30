"""
Model for alert data.

Data for quota alerts.
"""

from pydantic import BaseModel, Field


class ModelAlertData(BaseModel):
    """Data for quota alerts."""

    utilization: float | None = Field(None, description="Utilization percentage")
    remaining: int | None = Field(None, description="Remaining tokens")
    cost: float | None = Field(None, description="Current cost")
    budget: float | None = Field(None, description="Budget limit")
