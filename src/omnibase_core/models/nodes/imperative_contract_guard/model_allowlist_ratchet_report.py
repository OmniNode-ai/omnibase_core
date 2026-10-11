# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Report of the allowlist shrink-only ratchet."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelAllowlistRatchetReport"]


class ModelAllowlistRatchetReport(BaseModel):
    """Which allowlisted paths a change adds and removes, and whether it is admitted."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    added: list[str] = Field(
        default_factory=list,
        description="Paths in the head allowlist that the merge base does not carry.",
    )
    removed: list[str] = Field(
        default_factory=list,
        description="Paths in the merge-base allowlist that the head no longer carries.",
    )
    bootstrap: bool = Field(
        default=False,
        description="The allowlist file is absent at the merge base: nothing to ratchet against.",
    )

    @property
    def admitted(self) -> bool:
        """True when the change adds no path (a bootstrap admits the first landing)."""
        return self.bootstrap or not self.added
