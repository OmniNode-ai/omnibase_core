# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelLaneLiteralBranchingViolation — one lane-literal branching finding.

Used by the lane-literal branching guard (OMN-19760). The fingerprint is the
sha256 of ``{path, rule, normalized snippet}``, so a finding keeps its identity
when the lines above it move and the ratchet baseline can grandfather it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelLaneLiteralBranchingViolation(BaseModel):
    """A single lane-literal branching finding with a content fingerprint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    line: int
    rule: str
    snippet: str
    fingerprint: str
