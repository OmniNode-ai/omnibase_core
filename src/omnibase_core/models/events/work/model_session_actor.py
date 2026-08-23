# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Session claimant identity (OMN-16177)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, field_validator

from omnibase_core.enums.enum_actor_kind import EnumActorKind
from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelSessionActor"]


class ModelSessionActor(ModelEventPayloadBase):
    """An LLM session acting as a claimant."""

    kind: Literal[EnumActorKind.SESSION] = Field(
        default=EnumActorKind.SESSION,
        frozen=True,
        description="Union discriminator.",
    )
    session_handle: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Lane handle, e.g. 'omn16177-build-1'. Unique per live lane.",
    )
    controller_id: uuid.UUID = Field(
        ...,
        description="Controller session that dispatched this lane.",
    )
    agent_kind: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Role the lane was dispatched as, e.g. 'build-lane'.",
    )

    @field_validator("session_handle", "agent_kind")
    @classmethod
    def _reject_blank(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("must not be blank or whitespace-only")
        return raw

    @property
    def actor_key(self) -> str:
        """Flat partition key for the narrative domain."""
        return f"{EnumActorKind.SESSION.value}:{self.session_handle}"
