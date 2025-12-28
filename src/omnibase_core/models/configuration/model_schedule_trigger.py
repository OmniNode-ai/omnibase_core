"""
Schedule trigger model.
"""

from pydantic import BaseModel, Field

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH


class ModelScheduleTrigger(BaseModel):
    """Schedule trigger configuration."""

    cron: str = Field(
        ...,
        description="Cron expression for scheduling (e.g., '0 0 * * *')",
        max_length=MAX_IDENTIFIER_LENGTH,
    )
