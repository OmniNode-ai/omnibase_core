"""
Logging configuration model.
"""

import enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LogFormat(enum.StrEnum):
    """Log format enumeration."""

    JSON = "json"
    TEXT = "text"
    KEY_VALUE = "key-value"
    MARKDOWN = "markdown"
    YAML = "yaml"
    CSV = "csv"


class ModelLoggingConfig(BaseModel):
    """Logging configuration for nodes."""

    level: Optional[str] = None
    format: Optional[LogFormat] = None
    audit_events: List[str] = Field(default_factory=list)
