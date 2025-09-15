from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ModelUnifiedVersion(BaseModel):
    """
    Version information model for unified results
    """

    protocol_version: str
    tool_version: str | None = None
    schema_version: str | None = None
    last_updated: datetime | None = None
