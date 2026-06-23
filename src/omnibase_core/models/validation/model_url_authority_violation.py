# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelUrlAuthorityViolation — a single url-authority finding.

A frozen value object describing one URL-authority rule hit (OMN-12818),
carrying a content fingerprint (sha256 of {repo, path, normalized-snippet})
used by the burn-down ratchet to grandfather pre-existing violations.

Consumed by ``omnibase_core.validation.validator_url_authority``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelUrlAuthorityViolation(BaseModel):
    """A single url-authority finding with a content fingerprint for the ratchet."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str
    path: str
    line: int
    rule: str
    snippet: str
    fingerprint: str


__all__ = ["ModelUrlAuthorityViolation"]
