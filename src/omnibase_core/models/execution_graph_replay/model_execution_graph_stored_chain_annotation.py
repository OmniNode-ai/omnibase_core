# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Current ledger-chain comparison annotation, not replay truth."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphStoredChainAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: UUID
    hop_index: int = Field(ge=0)
    replay_green: bool | None
    verifier_verdict: str | None = None
