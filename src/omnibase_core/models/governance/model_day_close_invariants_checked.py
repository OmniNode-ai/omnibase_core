# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayCloseInvariantsChecked — invariants checked in daily close report."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus


class ModelDayCloseInvariantsChecked(BaseModel):
    """Invariants checked in daily close report."""

    model_config = ConfigDict(frozen=True)

    reducers_pure: EnumInvariantStatus = Field(
        ..., description="Reducers are pure (no I/O)"
    )
    orchestrators_no_io: EnumInvariantStatus = Field(
        ..., description="Orchestrators perform no I/O"
    )
    topic_governance: EnumInvariantStatus = Field(
        default=EnumInvariantStatus.UNKNOWN,
        description="No raw topic literals in production code (OMN-3342)",
    )
    effects_do_io_only: EnumInvariantStatus = Field(
        ..., description="Effects perform I/O only"
    )
    real_infra_proof_progressing: EnumInvariantStatus = Field(
        ..., description="Real infrastructure proof is progressing"
    )
    integration_sweep: EnumInvariantStatus = Field(
        default=EnumInvariantStatus.UNKNOWN,
        description="Integration sweep result",
    )
