"""
Schedule trigger model.
"""

from pydantic import BaseModel


class ModelScheduleTrigger(BaseModel):
    """Schedule trigger configuration."""

    cron: str
