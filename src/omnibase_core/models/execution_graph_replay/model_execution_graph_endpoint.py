# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Typed node, verdict, or session-anchor identity used by graph edges."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphEndpointKind,
)


class ModelExecutionGraphEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumExecutionGraphEndpointKind
    node_id: UUID | None = None
    verdict_id: UUID | None = None
    session_id: str | None = None  # string-id-ok: Claude session identifier

    @model_validator(mode="after")
    def require_matching_identity(self) -> ModelExecutionGraphEndpoint:
        fields = (self.node_id, self.verdict_id, self.session_id)
        if sum(value is not None for value in fields) != 1:
            raise ValueError("endpoint must carry exactly one identity")
        expected = {
            EnumExecutionGraphEndpointKind.NODE: self.node_id,
            EnumExecutionGraphEndpointKind.VERDICT: self.verdict_id,
            EnumExecutionGraphEndpointKind.SESSION_ANCHOR: self.session_id,
        }[self.kind]
        if expected is None:
            raise ValueError("endpoint identity does not match endpoint kind")
        return self
