# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EvidenceRequirementContract — evidence gating UI render/commit.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6).

Built on the OCC ``ModelEvidenceRequirement`` shape (composed, not duplicated)
plus the ``displayContract`` notion. Declares the evidence that must exist
before an action commits or a panel renders, and how the requirement is shown
to the operator when unmet.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_evidence_gate_moment import EnumEvidenceGateMoment
from omnibase_core.models.ticket.model_evidence_requirement import (
    ModelEvidenceRequirement,
)

__all__ = ["ModelEvidenceRequirementContract"]


class ModelEvidenceRequirementContract(BaseModel):
    """Declares evidence required before an action commits or a panel renders.

    Composes the canonical OCC ``ModelEvidenceRequirement`` rather than
    redefining its fields. ``gate_moment`` says whether the evidence gates a
    render or a commit; ``unmet_display_message`` is the operator-facing message
    surfaced when the requirement is not satisfied.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_id: str = Field(  # string-id-ok: semantic evidence-contract label, not a UUID
        ...,
        description="Stable semantic identifier for this evidence requirement contract",
        min_length=1,
    )
    requirement: ModelEvidenceRequirement = Field(
        ...,
        description="Canonical OCC evidence requirement composed into this UI contract",
    )
    gate_moment: EnumEvidenceGateMoment = Field(
        ...,
        description="Whether the evidence gates a panel render or an action commit",
    )
    unmet_display_message: str = Field(
        ...,
        description="Operator-facing message shown when the requirement is unmet",
        min_length=1,
    )
