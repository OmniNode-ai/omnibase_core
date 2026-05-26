# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_stable_proof_kind import EnumStableProofKind
from omnibase_core.models.contracts.evidence import (
    ModelContractEvidenceProof,
    ModelContractEvidenceSpec,
    ModelEvidenceProvenance,
)


@pytest.mark.unit
def test_contract_evidence_spec_accepts_artifact_first_proof() -> None:
    spec = ModelContractEvidenceSpec(
        ticket_id="OMN-11262",
        summary="Migrate contract evidence models into omnibase_core.",
        artifact_names=("ModelContractEvidenceSpec",),
        repository_surfaces=("omnibase_core.models.contracts.evidence",),
        acceptance_criteria=("stable proof validates the canonical model import",),
        stable_proofs=(
            ModelContractEvidenceProof(
                proof_id="model-import",
                proof_kind=EnumStableProofKind.MODEL_IMPORT,
                description="Model imports from the canonical core package.",
                target="omnibase_core.models.contracts.evidence.ModelContractEvidenceSpec",
                model_path="omnibase_core.models.contracts.evidence.ModelContractEvidenceSpec",
            ),
        ),
        provenance=(
            ModelEvidenceProvenance(
                repo="omnibase_core",
                branch="jonah/omn-11262-core-contract-evidence-model",
                pr_number=1,
            ),
        ),
        legacy_contract_path="onex_change_control/contracts/OMN-11261.yaml",
        migration_ticket_id="OMN-11262",
    )

    assert spec.schema_version == "1.0.0"
    assert spec.stable_proofs[0].proof_kind == EnumStableProofKind.MODEL_IMPORT
    assert spec.provenance[0].pr_number == 1


@pytest.mark.unit
def test_stable_proof_rejects_pr_number_bound_command() -> None:
    with pytest.raises(ValidationError, match="PR-number or PR-state bound"):
        ModelContractEvidenceProof(
            proof_id="pr-open",
            proof_kind=EnumStableProofKind.COMMAND,
            description="PR is open against main.",
            target="gh pr view 123 --repo OmniNode-ai/onex_change_control",
            command="gh pr view 123 --repo OmniNode-ai/onex_change_control",
        )


@pytest.mark.unit
def test_stable_proof_rejects_github_pull_url() -> None:
    with pytest.raises(ValidationError, match="PR-number or PR-state bound"):
        ModelContractEvidenceProof(
            proof_id="pr-url",
            proof_kind=EnumStableProofKind.COMMAND,
            description="PR URL is not stable proof.",
            target="https://github.com/OmniNode-ai/onex_change_control/pull/1138",
            command="test -n https://github.com/OmniNode-ai/onex_change_control/pull/1138",
        )


@pytest.mark.unit
def test_stable_proof_allows_non_pr_github_artifact_url() -> None:
    proof = ModelContractEvidenceProof(
        proof_id="github-artifact",
        proof_kind=EnumStableProofKind.COMMAND,
        description="GitHub blob URL can identify a stable artifact path.",
        target="https://github.com/OmniNode-ai/omnibase_core/blob/main/pyproject.toml",
        command="test -n https://github.com/OmniNode-ai/omnibase_core/blob/main/pyproject.toml",
    )

    assert proof.target.endswith("pyproject.toml")


@pytest.mark.unit
def test_pr_metadata_is_allowed_as_provenance() -> None:
    provenance = ModelEvidenceProvenance(
        repo="omnibase_core",
        commit_sha="abcdef1",
        pr_number=123,
        pr_url="https://github.com/OmniNode-ai/omnibase_core/pull/123",
    )

    assert provenance.pr_number == 123
    assert provenance.commit_sha == "abcdef1"


@pytest.mark.unit
def test_spec_requires_at_least_one_stable_proof() -> None:
    with pytest.raises(ValidationError):
        ModelContractEvidenceSpec(
            ticket_id="OMN-11262",
            summary="Invalid spec.",
            artifact_names=("ModelContractEvidenceSpec",),
            repository_surfaces=("omnibase_core.models.contracts.evidence",),
            acceptance_criteria=("has proof",),
            stable_proofs=(),
        )


@pytest.mark.unit
def test_artifact_validation_requires_model_and_artifact_path() -> None:
    with pytest.raises(ValidationError, match="requires model_path and artifact_path"):
        ModelContractEvidenceProof(
            proof_id="validate-artifact",
            proof_kind=EnumStableProofKind.ARTIFACT_VALIDATION,
            description="Validate artifact against model.",
            target="artifact_manifest.json",
            model_path="omnibase_core.models.evidence_bundle.ModelArtifactManifest",
        )


@pytest.mark.unit
def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelEvidenceProvenance(
            repo="omnibase_core",
            branch="main",
            unexpected=True,  # type: ignore[call-arg]
        )


@pytest.mark.unit
def test_provenance_requires_at_least_one_trace_field() -> None:
    with pytest.raises(ValidationError, match="at least one trace field"):
        ModelEvidenceProvenance(repo="omnibase_core")


@pytest.mark.unit
def test_evidence_models_support_from_attributes() -> None:
    class _FakeORM:
        repo = "omnibase_core"
        commit_sha = "abc1234"
        branch = None
        pr_number = None
        pr_url = None
        ci_run_url = None
        notes = None

    provenance = ModelEvidenceProvenance.model_validate(
        _FakeORM(), from_attributes=True
    )
    assert provenance.repo == "omnibase_core"
    assert provenance.commit_sha == "abc1234"


@pytest.mark.unit
def test_file_exists_proof_requires_artifact_path() -> None:
    with pytest.raises(
        ValidationError, match="file_exists proof requires artifact_path"
    ):
        ModelContractEvidenceProof(
            proof_id="file-check",
            proof_kind=EnumStableProofKind.FILE_EXISTS,
            description="Check artifact file exists.",
            target="some/path/artifact.json",
        )


@pytest.mark.unit
def test_command_proof_requires_command_field() -> None:
    with pytest.raises(ValidationError, match="command proof requires command"):
        ModelContractEvidenceProof(
            proof_id="run-cmd",
            proof_kind=EnumStableProofKind.COMMAND,
            description="Run a verification command.",
            target="some-target",
        )
