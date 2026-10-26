# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""State recovery declarations nested under contract placement."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_placement_state_store import EnumPlacementStateStore


class ModelContractPlacementState(BaseModel):
    """Durable state location and replay sources for a placed node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    store: EnumPlacementStateStore = Field(
        default=EnumPlacementStateStore.PROJECTION,
        description="State store; explicitly use none to declare a stateless node.",
    )
    table: str | None = Field(default=None, min_length=1)
    replay_topics: list[str] = Field(default_factory=list)
