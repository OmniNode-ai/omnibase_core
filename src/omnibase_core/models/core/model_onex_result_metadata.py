from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.types import MetadataValue


class ModelOnexResultMetadata(BaseModel):
    """
    Define canonical fields for result metadata, extend as needed
    """

    key: str | None = None
    value: MetadataValue = None
    # Add more fields as needed for protocol

    model_config = ConfigDict(arbitrary_types_allowed=True)
