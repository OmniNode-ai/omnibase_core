from __future__ import annotations

from pydantic import BaseModel

from omnibase_core.models.types import MetadataValue


class ModelUnifiedSummaryDetails(BaseModel):
    """
    Define canonical fields for summary details, extend as needed
    """

    key: str | None = None
    value: MetadataValue = None
    # Add more fields as needed for protocol

    model_config = {"arbitrary_types_allowed": True}
