"""Slack notification configuration model."""

from pydantic import BaseModel, Field


class ModelSlackConfig(BaseModel):
    """Slack notification configuration."""

    webhook_url: str = Field(..., description="Slack webhook URL")
    channel: str | None = Field(default=None, description="Slack channel")
    username: str | None = Field(default=None, description="Bot username")
    icon_emoji: str | None = Field(default=None, description="Bot icon emoji")
