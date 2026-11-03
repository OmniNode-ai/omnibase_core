# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The registry's change-sequence watermark (OMN-21226)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["REGISTRY_WATERMARK_ENTITY_ID", "ModelRegistryWatermark"]

#: The one key of the watermark topic.
REGISTRY_WATERMARK_ENTITY_ID = "registry-watermark"


class ModelRegistryWatermark(BaseModel):
    """The highest committed and highest published change sequence, and when.

    Attributes:
        entity_id: Fixed: ``registry-watermark``. The topic holds one key.
        committed_sequence: The highest change sequence the registry committed.
        published_sequence: The highest change sequence published to the bus.
        observed_at: When the registry read these two values (timezone-aware).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str
    committed_sequence: int = Field(ge=0)
    published_sequence: int = Field(ge=0)
    observed_at: datetime

    @field_validator("entity_id")
    @classmethod
    def _entity_id_is_fixed(cls, value: str) -> str:
        if value != REGISTRY_WATERMARK_ENTITY_ID:
            raise ValueError(f"entity_id must be {REGISTRY_WATERMARK_ENTITY_ID!r}")
        return value

    @field_validator("observed_at")
    @classmethod
    def _observed_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value
