# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodSweepCheckResult — result for a single DoD compliance check."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_dod_sweep_check import EnumDodSweepCheck
from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus

_MAX_STRING_LENGTH = 10000


class ModelDodSweepCheckResult(BaseModel):
    """Result for a single DoD compliance check."""

    model_config = ConfigDict(frozen=True)

    check: EnumDodSweepCheck = Field(
        ..., description="Which of the 6 DoD checks this result is for"
    )
    status: EnumInvariantStatus = Field(
        ..., description="Check result: PASS, FAIL, or UNKNOWN"
    )
    unknown_subtype: Literal[
        "exempt", "linkage_inconclusive", "mixed_evidence", None
    ] = Field(
        default=None,
        description="Structured subtype when status is UNKNOWN",
    )
    detail: Annotated[str | None, Field(max_length=_MAX_STRING_LENGTH)] = Field(
        default=None, description="Human-readable detail about the check outcome"
    )

    @model_validator(mode="after")
    def validate_unknown_subtype_consistency(self) -> "ModelDodSweepCheckResult":
        if self.status == EnumInvariantStatus.UNKNOWN and self.unknown_subtype is None:
            msg = "unknown_subtype is required when status is UNKNOWN"
            raise ValueError(msg)
        if (
            self.status != EnumInvariantStatus.UNKNOWN
            and self.unknown_subtype is not None
        ):
            msg = "unknown_subtype is only allowed when status is UNKNOWN"
            raise ValueError(msg)
        return self
