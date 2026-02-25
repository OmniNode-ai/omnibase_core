# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP scenario entry model.

Defines the manifest entry for a scenario bundled in a ``.oncp`` package.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP

.. versionadded:: 0.19.0
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOncpScenarioEntry"]


class ModelOncpScenarioEntry(BaseModel):
    """Manifest entry describing a scenario bundled in the package.

    Scenarios are event streams and fixtures used to exercise the contract
    under test. Each entry records the path inside the zip and a content
    hash for integrity checking.

    Attributes:
        id: Stable identifier for the scenario.
        path: Relative path inside the zip.
        content_hash: SHA-256 hex digest of the scenario YAML content.
        required: Whether this scenario must pass for the package to be
            considered valid.

    .. versionadded:: 0.19.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: scenario IDs are human-readable slugs, not database UUIDs
    id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this scenario.",
    )
    path: str = Field(
        ...,
        min_length=1,
        description="Relative path inside the zip archive.",
    )
    content_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hex digest of the scenario YAML content.",
    )
    required: bool = Field(
        default=True,
        description="Whether this scenario must pass for the package to be valid.",
    )
