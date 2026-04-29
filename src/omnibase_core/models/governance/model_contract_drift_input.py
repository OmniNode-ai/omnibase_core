# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for contract drift detection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_drift_sensitivity import EnumDriftSensitivity


class ModelContractDriftInput(BaseModel):
    """Input to the contract drift detector COMPUTE node."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    contract_name: str = Field(
        description="Human-readable identifier for the contract being checked."
    )
    current_contract: dict[str, object] = Field(
        description="Current contract content, e.g. as loaded by ContractLoader."
    )
    pinned_hash: str = Field(
        description="SHA-256 hex digest of the previously accepted canonical form."
    )
    sensitivity: EnumDriftSensitivity = Field(
        default=EnumDriftSensitivity.STANDARD,
        description="Controls which change categories produce a non-NONE severity.",
    )
