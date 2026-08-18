# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result-recorded work event (OMN-16177).

Carries structured citations rather than the prose PR mentions the markdown
work ledger holds today, and quantitative claims that cannot exist without the
probe command that produced them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

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
