# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Optional session anchor recorded for a delegation graph."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphAnchorKind,
    EnumExecutionGraphAnchorState,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
    ModelExecutionGraphSourceRef,
)


class ModelExecutionGraphAnchor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumExecutionGraphAnchorKind
    session_id: str | None = Field(  # string-id-ok: Claude session identifier
        default=None, min_length=1
    )
    evidence_ref: ModelExecutionGraphSourceRef | None = None
    state: EnumExecutionGraphAnchorState

    @model_validator(mode="after")
    def validate_anchor_shape(self) -> ModelExecutionGraphAnchor:
        if (
            self.kind is EnumExecutionGraphAnchorKind.NONE
            and self.session_id is not None
        ):
            raise ValueError("an absent anchor cannot carry a session_id")
        if self.state is EnumExecutionGraphAnchorState.RESOLVED and (
            self.kind is not EnumExecutionGraphAnchorKind.SESSION
            or self.session_id is None
            or self.evidence_ref is None
        ):
            raise ValueError("a resolved anchor requires session identity and evidence")
        return self
