# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence artifact model for pipeline closeout verification."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelEvidenceArtifact"]


class ModelEvidenceArtifact(BaseModel):
    """A single captured evidence artifact with hash and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    sha256: str
    captured_at: str
    source_surface: str
    evidence_kind: str
