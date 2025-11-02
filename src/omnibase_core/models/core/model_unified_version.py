from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelUnifiedVersion(BaseModel):
    """
    Version information model for unified results
    """

    protocol_version: ModelSemVer
    tool_version: ModelSemVer | None = None
    schema_version: ModelSemVer | None = None
    last_updated: datetime | None = None
