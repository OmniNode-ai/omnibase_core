# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLearningMatch — a prior learning relevant to current context (OMN-11928)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.context.model_context_provenance import ModelContextProvenance
from omnibase_core.types.type_semantic_id import ExternalLearningId

__all__ = ["ModelLearningMatch"]


class ModelLearningMatch(BaseModel):
    """A prior learning relevant to the current context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    learning_id: ExternalLearningId = Field(
        description="Stable identifier in the external learning system"
    )
    summary: str = Field(description="One-to-two sentence learning summary")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Semantic relevance score in [0, 1]"
    )
    provenance: ModelContextProvenance = Field(description="Source provenance")
