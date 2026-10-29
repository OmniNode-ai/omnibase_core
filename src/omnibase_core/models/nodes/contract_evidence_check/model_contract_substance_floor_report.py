# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The substance floor verdicts of the requested contracts (OMN-14409)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_verdict import (
    ModelContractSubstanceFloorVerdict,
)

__all__ = ["ModelContractSubstanceFloorReport"]


class ModelContractSubstanceFloorReport(BaseModel):
    """The substance floor verdicts of the requested contracts (OMN-14409)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    verdicts: tuple[ModelContractSubstanceFloorVerdict, ...] = ()
