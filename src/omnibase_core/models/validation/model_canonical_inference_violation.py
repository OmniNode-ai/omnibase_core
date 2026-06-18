# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalInferenceViolation — one non-canonical-inference finding.

Used by the canonical-inference ratchet gate (OMN-13219). Each violation carries
a content fingerprint (sha256 of {repo, path, normalized-snippet}) so existing
violations can be grandfathered via the burn-down baseline while NEW ones fail
the gate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCanonicalInferenceViolation(BaseModel):
    """A single non-canonical-inference finding with a content fingerprint."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str
    path: str
    line: int
    rule: str
    snippet: str
    fingerprint: str
