# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime state: what one runtime instance has observed and serves (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_hotload.model_hotload_observed_entry import (
    ModelHotloadObservedEntry,
)
from omnibase_core.models.events.contract_hotload.model_hotload_served_entry import (
    ModelHotloadServedEntry,
)

__all__ = ["ModelRuntimeHotloadState"]


class ModelRuntimeHotloadState(BaseModel):
    """The compacted state record of one runtime instance.

    It is not a response, so it carries no request id.

    Attributes:
        entity_id: The runtime instance id (the record's compaction key).
        incarnation_id: The incarnation of that instance (changes on restart).
        profile: The runtime profile.
        lane: The lane the runtime serves.
        image_digest: Digest of the image the runtime runs.
        readiness: Whether the runtime is ready to serve.
        observed: One entry per contract name the runtime has seen a change for.
        served: One entry per contract name the runtime is serving.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    incarnation_id: UUID
    profile: str = Field(min_length=1)
    lane: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)
    readiness: bool
    observed: dict[str, ModelHotloadObservedEntry]
    served: dict[str, ModelHotloadServedEntry]
