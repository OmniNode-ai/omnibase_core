# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelStandardEvidenceBundle — canonical 7-file evidence bundle."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, computed_field

from omnibase_core.models.evidence_bundle.model_artifact_manifest import (
    ModelArtifactManifest,
)
from omnibase_core.models.evidence_bundle.model_contract_snapshot import (
    ModelContractSnapshot,
)
from omnibase_core.models.evidence_bundle.model_evidence_verifier_result import (
    ModelEvidenceVerifierResult,
)
from omnibase_core.models.evidence_bundle.model_standard_run_manifest import (
    ModelStandardRunManifest,
)

# Maps canonical artifact filenames to ModelStandardEvidenceBundle field names.
# Used by is_complete to check presence without inspecting file contents.
_ARTIFACT_TO_FIELD: dict[str, str] = {
    "run_manifest.json": "run_manifest",
    "contract_snapshot.json": "contract_snapshot",
    "input.json": "input_data",
    "output.json": "output_data",
    "verifier_result.json": "verifier_result",
    "artifact_manifest.json": "artifact_manifest",
}


class ModelStandardEvidenceBundle(BaseModel):
    """Complete evidence bundle for a single ONEX workflow run.

    ``is_complete`` is True only when every filename declared in
    ``run_manifest.expected_artifacts`` maps to a non-None field on this model.
    Filenames not in ``_ARTIFACT_TO_FIELD`` (e.g., ``proof_summary.md``) are
    considered present by default since they are not represented as typed fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    run_manifest: ModelStandardRunManifest
    artifact_manifest: ModelArtifactManifest | None = None
    contract_snapshot: ModelContractSnapshot | None = None
    verifier_result: ModelEvidenceVerifierResult | None = None
    input_data: dict[str, object] | None = None
    output_data: dict[str, object] | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        for artifact in self.run_manifest.expected_artifacts:
            field_name = _ARTIFACT_TO_FIELD.get(artifact)
            if field_name is not None and getattr(self, field_name) is None:
                return False
        return True


__all__ = ["ModelStandardEvidenceBundle"]
