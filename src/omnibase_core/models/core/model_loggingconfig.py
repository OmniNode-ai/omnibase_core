from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_format import EnumLogFormat


class ModelLoggingConfig(BaseModel):
    """Logging configuration for nodes."""

    level: str | None = None
    format: EnumLogFormat | None = None
    audit_events: list[str] = Field(default_factory=list)
