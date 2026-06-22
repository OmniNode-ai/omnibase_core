# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Authorization context for artifact reads (OMN-13152).

``ModelArtifactAuthContext`` carries the caller's identity and the set of
artifact kinds the caller is authorized to read. Restricted artifact kinds
(``session_transcript``, ``hook_trace``) require the requested kind to appear
in :attr:`authorized_kinds`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelArtifactAuthContext"]


class ModelArtifactAuthContext(BaseModel):
    """Caller authorization context for a restricted artifact read.

    A read of a restricted artifact kind is permitted only when that kind is
    present in :attr:`authorized_kinds`. There is no implicit wildcard: an
    empty set authorizes nothing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    principal: str = Field(
        ...,
        min_length=1,
        description="Stable identity of the caller requesting the read.",
    )
    authorized_kinds: frozenset[str] = Field(
        default_factory=frozenset,
        description=(
            "Artifact kinds this principal may read. Restricted kinds "
            "(session_transcript, hook_trace) require membership here."
        ),
    )

    def is_authorized_for(self, artifact_kind: str) -> bool:
        """Return whether this context authorizes reading ``artifact_kind``."""
        return artifact_kind in self.authorized_kinds
