# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for contract drift detection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_drift_severity import (
    EnumDriftSeverity,
)
from omnibase_core.models.governance.model_field_change import ModelFieldChange


class ModelContractDriftOutput(BaseModel):
    """Full drift report produced by the contract drift COMPUTE node."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    contract_name: str
    severity: EnumDriftSeverity
    current_hash: str = Field(description="Canonical hash of the current contract.")
    pinned_hash: str = Field(description="Hash supplied in the input (baseline).")
    drift_detected: bool
    field_changes: list[ModelFieldChange]
    breaking_changes: list[str] = Field(
        description="Human-readable summaries of breaking changes."
    )
    additive_changes: list[str] = Field(
        description="Human-readable summaries of additive changes."
    )
    non_breaking_changes: list[str] = Field(
        description="Human-readable summaries of non-breaking changes."
    )
    summary: str = Field(description="One-line summary of the drift report.")
