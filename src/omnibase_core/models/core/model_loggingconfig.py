from enum import Enum

from pydantic import BaseModel, Field


class ModelLoggingConfig(BaseModel):
    """Logging configuration for nodes."""

    level: str | None = None
    format: ModelEnumLogFormat | None = None
    audit_events: list[str] = Field(default_factory=list)
