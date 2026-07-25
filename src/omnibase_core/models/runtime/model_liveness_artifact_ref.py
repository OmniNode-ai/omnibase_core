# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deployed-artifact identity a liveness registry entry's proof is scoped to.

OMN-15126 implementation of the OMN-14845 design (design §4). Named
``model_liveness_artifact_ref.py`` (rather than ``model_artifact_ref.py``) to
avoid a filename collision with the unrelated
``omnibase_core.models.artifacts.model_artifact_ref`` (a content-addressed
blob reference for the skill-output artifact store, OMN-13091) — the two
``ModelArtifactRef`` classes describe different concepts and live in
different modules, but the repo's duplicate-model-filename pre-commit gate
checks basenames across the whole tree.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelArtifactRef"]


class ModelArtifactRef(BaseModel):
    """Deployed-artifact identity a registry entry's proof is scoped to (design §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(..., min_length=1)
    contract_path: str = Field(..., min_length=1)
    expected_image_digest: str | None = Field(default=None)
