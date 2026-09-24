# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result-recorded work event (OMN-16177).

Carries structured citations rather than the prose PR mentions the markdown
work ledger holds today, and quantitative claims that cannot exist without the
probe command that produced them.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, field_serializer, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.models.events.work.model_pr_ref import ModelPrRef
from omnibase_core.models.events.work.model_quant_claim import ModelQuantClaim
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkResultRecorded"]


class ModelWorkResultRecorded(ModelWorkEventBase):
    """An outcome, with structured citations rather than prose mentions."""

    kind: Literal[EnumWorkEventKind.RESULT_RECORDED] = Field(
        default=EnumWorkEventKind.RESULT_RECORDED, frozen=True
    )
    outcome: EnumWorkOutcome = Field(..., description="What happened to the work.")
    pr_refs: tuple[ModelPrRef, ...] = Field(
        default=(),
        description="Product PRs this result cites.",
    )
    occ_refs: tuple[ModelPrRef, ...] = Field(
        default=(),
        description="onex_change_control companion PRs this result cites.",
    )
    quantitative_claims: tuple[ModelQuantClaim, ...] = Field(
        default=(),
        description="Measured numbers, each carrying the probe that produced it.",
    )
    closes_claims: frozenset[uuid.UUID] = Field(
        default_factory=frozenset,
        description="event_ids of the work.claim.requested events this result closes.",
    )
    friction_refs: frozenset[uuid.UUID] = Field(
        default_factory=frozenset,
        description="event_ids of the work.friction.recorded events this result cites.",
    )
    friction_none: bool = Field(
        default=False,
        description="True when the work met no friction. Exclusive with friction_refs.",
    )

    @model_validator(mode="after")
    def _friction_recorded_exactly_one_way(self) -> ModelWorkResultRecorded:
        if self.friction_none and self.friction_refs:
            raise ValueError(
                "friction_none=True and a non-empty friction_refs contradict each "
                "other; record one"
            )
        if not self.friction_none and not self.friction_refs:
            raise ValueError(
                "a result records its friction: set friction_none=True or cite "
                "friction_refs"
            )
        return self

    @field_serializer("closes_claims", "friction_refs")
    def _serialize_ids_sorted(self, value: frozenset[uuid.UUID]) -> list[str]:
        return sorted(str(event_id) for event_id in value)
