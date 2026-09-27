# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Request-time authorization and current-state annotations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.execution_graph_replay.model_execution_graph_stored_chain_annotation import (
    ModelExecutionGraphStoredChainAnnotation,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_stored_verdict_annotation import (
    ModelExecutionGraphStoredVerdictAnnotation,
)


class ModelExecutionGraphAnnotations(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    read_at: datetime
    authorization_tenant_id: UUID
    authorization_ownership_source: Literal["delegation_events"]
    authorization_checked_over: Literal["full_correlation"]
    stored_chain: tuple[ModelExecutionGraphStoredChainAnnotation, ...]
    stored_verdicts: tuple[ModelExecutionGraphStoredVerdictAnnotation, ...]
