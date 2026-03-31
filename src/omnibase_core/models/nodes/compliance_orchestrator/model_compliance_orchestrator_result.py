# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of orchestrator fan-out."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_orchestrator.model_check_request_intent import (
    ModelCheckRequestIntent,
)

__all__ = ["ModelComplianceOrchestratorResult"]


class ModelComplianceOrchestratorResult(BaseModel):
    """Result of orchestrator fan-out — list of intents emitted."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    intents: list[ModelCheckRequestIntent] = Field(default_factory=list)
    contracts_discovered: int = 0
    run_id: str = ""
