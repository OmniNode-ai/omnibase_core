from __future__ import annotations

from pydantic import BaseModel

from omnibase_core.models.types.model_onex_common_types import MetadataValue


class ModelOnexMessageContext(BaseModel):
    """
    Define canonical fields for message context, extend as needed
    """

    key: str | None = None
    value: MetadataValue = None
    # Add more fields as needed for protocol

    model_config = {"arbitrary_types_allowed": True}
