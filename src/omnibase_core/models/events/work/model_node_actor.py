# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node claimant identity (OMN-16177).

A merge-sweep node claiming a PR-drive is the same lock as a session claiming a
ticket, which is why this is a variant of the actor union rather than a set of
node fields bolted onto the session model.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, field_validator

from omnibase_core.enums.enum_actor_kind import EnumActorKind
from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelNodeActor"]


class ModelNodeActor(ModelEventPayloadBase):
    """A runtime node invocation acting as a claimant."""

    kind: Literal[EnumActorKind.NODE] = Field(
        default=EnumActorKind.NODE,
        frozen=True,
        description="Union discriminator.",
    )
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Node identifier, e.g. 'node_pr_lifecycle_orchestrator'.",
    )
    runtime_lane: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description=(
            "Lane id this invocation runs in, as the deployment's runtime.lane "
            "overlay declares it (OMN-19746). Load-bearing for arbitration: the "
            "same node runs in several lanes, and one lane's sweep must not be "
            "mistaken for another lane's holding a claim. Any deployment's lane "
            "id, not a closed set: core names no lane."
        ),
    )
    contract_version: ModelSemVer = Field(
        ...,
        description="Version of the node contract this invocation resolved.",
    )
    run_id: uuid.UUID = Field(
        ...,
        description="This invocation. Distinguishes concurrent runs of one node.",
    )

    @field_validator("node_id")
    @classmethod
    def _reject_blank(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("must not be blank or whitespace-only")
        return raw

    @property
    def actor_key(self) -> str:
        """Flat partition key for the narrative domain.

        Includes ``runtime_lane`` so two lanes running the same node do not
        share a narrative partition and interleave each other's ordering.
        """
        return f"{EnumActorKind.NODE.value}:{self.node_id}@{self.runtime_lane}"
