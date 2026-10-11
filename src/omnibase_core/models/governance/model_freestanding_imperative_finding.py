# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A single imperative-IO finding inside a freestanding module (OMN-20918)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_reachability import EnumReachability


class ModelFreestandingImperativeFinding(BaseModel):
    """A single imperative-IO finding inside a freestanding module."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violation: EnumComplianceViolation = Field(
        ...,
        description="The kind of imperative-IO violation detected.",
    )
    line: int = Field(
        ...,
        ge=1,
        description="1-based source line of the offending node.",
    )
    detail: str = Field(
        ...,
        description="Human-readable description of the finding.",
    )
    suppressed: bool = Field(
        default=False,
        description=(
            "Whether an inline '# no-contract-check: <reason>' comment on the "
            "finding's line suppresses it."
        ),
    )
    reachability: EnumReachability = Field(
        default=EnumReachability.LIVE,
        description="Reachability of the module containing this finding.",
    )
