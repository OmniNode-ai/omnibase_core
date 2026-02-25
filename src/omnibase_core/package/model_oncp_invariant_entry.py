# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP invariant entry model.

Defines the manifest entry for an invariant suite bundled in a ``.oncp`` package.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP

.. versionadded:: 0.19.0
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOncpInvariantEntry"]


class ModelOncpInvariantEntry(BaseModel):
    """Manifest entry describing an invariant suite bundled in the package.

    Invariants are declarative assertion suites that must hold after overlay
    application. Each entry records the path and content hash.

    Attributes:
        id: Stable identifier for the invariant suite.
        path: Relative path inside the zip.
        content_hash: SHA-256 hex digest of the invariant YAML content.
        required: Whether this invariant suite must pass.

    .. versionadded:: 0.19.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: invariant IDs are human-readable slugs, not database UUIDs
    id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this invariant suite.",
    )
    path: str = Field(
        ...,
        min_length=1,
        description="Relative path inside the zip archive.",
    )
    content_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the invariant YAML content.",
    )
    required: bool = Field(
        default=True,
        description="Whether this invariant suite must pass.",
    )
