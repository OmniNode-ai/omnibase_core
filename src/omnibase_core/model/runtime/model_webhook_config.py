"""Webhook notification configuration model."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelWebhookConfig(BaseModel):
    """Webhook notification configuration."""

    url: str = Field(..., description="Webhook URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts on failure")
