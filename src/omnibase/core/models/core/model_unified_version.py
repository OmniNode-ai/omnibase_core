from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelUnifiedVersion(BaseModel):
    """
    Version information model for unified results
    """

    protocol_version: str
    tool_version: Optional[str] = None
    schema_version: Optional[str] = None
    last_updated: Optional[datetime] = None
