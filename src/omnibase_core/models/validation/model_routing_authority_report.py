# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result model (COMPUTE output) for the routing-authority validator (OMN-13285)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

VALIDATOR_ID = "routing_authority"


class ModelRoutingAuthorityReport(BaseModel):
    """JSON-ledger-safe COMPUTE result: pass/fail + structured findings."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: human-readable validator name ('routing_authority'), not a UUID
    validator_id: str = Field(default=VALIDATOR_ID)
    passed: bool = Field(description="True iff no FAIL/ERROR findings were produced.")
    findings: tuple[ModelValidationFinding, ...] = Field(default_factory=tuple)


__all__ = ["ModelRoutingAuthorityReport", "VALIDATOR_ID"]
