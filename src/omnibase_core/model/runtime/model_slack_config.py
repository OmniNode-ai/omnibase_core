"""Slack notification configuration model."""

from typing import Optional

from pydantic import BaseModel, Field


class ModelSlackConfig(BaseModel):
    """Slack notification configuration."""

    webhook_url: str = Field(..., description="Slack webhook URL")
    channel: Optional[str] = Field(default=None, description="Slack channel")
    username: Optional[str] = Field(default=None, description="Bot username")
    icon_emoji: Optional[str] = Field(default=None, description="Bot icon emoji")
