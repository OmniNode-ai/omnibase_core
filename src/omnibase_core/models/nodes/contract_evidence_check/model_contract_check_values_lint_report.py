# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The blocking findings and the advisory warnings of a contract check value lint (OMN-17427)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.contract_evidence_check.model_contract_check_values_finding import (
    ModelContractCheckValuesFinding,
)

__all__ = ["ModelContractCheckValuesLintReport"]


class ModelContractCheckValuesLintReport(BaseModel):
    """The blocking findings and the advisory warnings of a contract check value lint (OMN-17427)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelContractCheckValuesFinding, ...] = ()
    warnings: tuple[ModelContractCheckValuesFinding, ...] = ()
