# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelArtifactManifest — records all artifacts written during an evidence bundle run."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, computed_field

from omnibase_core.models.evidence_bundle.model_artifact_entry import ModelArtifactEntry


class ModelArtifactManifest(BaseModel):
    """Manifest of all artifacts produced during an evidence bundle run.

    ``bundle_hash`` is a SHA-256 digest computed over the sorted artifact
    hashes, providing a single fingerprint for the entire artifact set.
    Sorting by hash (not by write_order) ensures the digest is stable
    regardless of insertion ordering.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    artifacts: tuple[ModelArtifactEntry, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bundle_hash(self) -> str:
        sorted_hashes = sorted(a.sha256 for a in self.artifacts)
        combined = "".join(sorted_hashes).encode()
        return hashlib.sha256(combined).hexdigest()


__all__ = ["ModelArtifactManifest"]
