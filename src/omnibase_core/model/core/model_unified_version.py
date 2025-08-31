from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class ModelUnifiedVersion(BaseModel):
    """
    Version information model for unified results
    """

    protocol_version: str
    tool_version: str | None = None
    schema_version: str | None = None
    last_updated: datetime | None = None
