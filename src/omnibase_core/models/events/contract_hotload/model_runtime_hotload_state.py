# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime state: what one runtime instance has observed and serves (OMN-21226)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_hotload.model_hotload_name_state import (
    ModelHotloadNameState,
)

__all__ = ["ModelRuntimeHotloadState"]


class ModelRuntimeHotloadState(BaseModel):
    """The compacted state record of one runtime instance (plan section 3.2).

    Published on the workload's own state topic, which only that workload's
    principal may write, so a reader takes the workload from the topic and never
    from this payload. It is not a response, so it carries no request id. A clean
    shutdown publishes a null for the key, which is a tombstone and not a record.

    Attributes:
        entity_id: The runtime instance id (the record's compaction key).
        incarnation_id: Fresh at each process start.
        profile: The runtime profile.
        lane: The lane the runtime serves.
        image_digest: Digest of the image the runtime runs.
        bootstrap_ready: True once the baseline is attached and the follower has
            caught up with the accepted topic.
        serving_ready: True once every owned accepted contract the image can serve
            is attached.
        names: For each owned name, what the runtime observed and what it serves.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    entity_id: str = Field(min_length=1)
    incarnation_id: UUID
    profile: str = Field(min_length=1)
    lane: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)
    bootstrap_ready: bool
    serving_ready: bool
    names: dict[str, ModelHotloadNameState]
