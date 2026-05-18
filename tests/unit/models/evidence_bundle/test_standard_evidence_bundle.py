# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for standard evidence bundle models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.evidence_bundle.model_artifact_entry import (
    ModelArtifactEntry,
)
from omnibase_core.models.evidence_bundle.model_artifact_manifest import (
    ModelArtifactManifest,
)
from omnibase_core.models.evidence_bundle.model_contract_snapshot import (
    ModelContractSnapshot,
)
from omnibase_core.models.evidence_bundle.model_evidence_verifier_result import (
    ModelEvidenceVerifierResult,
)
from omnibase_core.models.evidence_bundle.model_standard_evidence_bundle import (
    ModelStandardEvidenceBundle,
)
from omnibase_core.models.evidence_bundle.model_standard_run_manifest import (
    ModelStandardRunManifest,
)

_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
_CID = "test-correlation-id-001"

_CANONICAL_ARTIFACTS = (
    "run_manifest.json",
    "contract_snapshot.json",
    "input.json",
    "output.json",
    "verifier_result.json",
    "artifact_manifest.json",
    "proof_summary.md",
)


def _make_run_manifest(
    expected: tuple[str, ...] = _CANONICAL_ARTIFACTS,
) -> ModelStandardRunManifest:
    return ModelStandardRunManifest(
        correlation_id=_CID,
        runner="test-runner",
        started_at=_NOW,
        expected_artifacts=expected,
    )


def _make_contract_snapshot() -> ModelContractSnapshot:
    return ModelContractSnapshot(
        correlation_id=_CID,
        contracts=({"name": "contract_a", "hash": "abc123"},),
    )


def _make_verifier_result() -> ModelEvidenceVerifierResult:
    return ModelEvidenceVerifierResult(
        correlation_id=_CID,
        status=EnumReceiptStatus.PASS,
        verifier="ci-verifier",
        checks=({"check": "artifact_present", "result": "pass"},),
    )


def _make_artifact_entry(filename: str, order: int) -> ModelArtifactEntry:
    return ModelArtifactEntry(
        filename=filename,
        sha256="a" * 64,
        write_order=order,
    )


def _make_artifact_manifest() -> ModelArtifactManifest:
    return ModelArtifactManifest(
        correlation_id=_CID,
        artifacts=(
            _make_artifact_entry("run_manifest.json", 0),
            _make_artifact_entry("output.json", 1),
        ),
    )


@pytest.mark.unit
def test_run_manifest_declares_expected_artifacts() -> None:
    manifest = _make_run_manifest()
    assert manifest.expected_artifacts == _CANONICAL_ARTIFACTS
    assert manifest.correlation_id == _CID
    assert manifest.runner == "test-runner"
    assert manifest.ticket_id is None


@pytest.mark.unit
def test_artifact_manifest_records_write_order_and_hashes() -> None:
    entry_a = ModelArtifactEntry(
        filename="run_manifest.json", sha256="b" * 64, write_order=0
    )
    entry_b = ModelArtifactEntry(filename="output.json", sha256="c" * 64, write_order=1)
    manifest = ModelArtifactManifest(
        correlation_id=_CID,
        artifacts=(entry_a, entry_b),
    )
    assert manifest.artifacts[0].write_order == 0
    assert manifest.artifacts[1].write_order == 1
    assert manifest.artifacts[0].sha256 == "b" * 64
    assert manifest.artifacts[1].sha256 == "c" * 64
    # bundle_hash is deterministic and based on sorted artifact hashes
    assert len(manifest.bundle_hash) == 64
    # Reversing insertion order must produce the same bundle_hash (sort-stable)
    manifest_reversed = ModelArtifactManifest(
        correlation_id=_CID,
        artifacts=(entry_b, entry_a),
    )
    assert manifest.bundle_hash == manifest_reversed.bundle_hash


@pytest.mark.unit
def test_bundle_complete_when_all_declared_present() -> None:
    run_manifest = _make_run_manifest(
        expected=(
            "run_manifest.json",
            "contract_snapshot.json",
            "input.json",
            "output.json",
            "verifier_result.json",
            "artifact_manifest.json",
            "proof_summary.md",
        )
    )
    bundle = ModelStandardEvidenceBundle(
        correlation_id=_CID,
        run_manifest=run_manifest,
        artifact_manifest=_make_artifact_manifest(),
        contract_snapshot=_make_contract_snapshot(),
        verifier_result=_make_verifier_result(),
        input_data={"key": "value"},
        output_data={"result": "ok"},
    )
    assert bundle.is_complete is True


@pytest.mark.unit
def test_bundle_incomplete_when_declared_artifact_missing() -> None:
    run_manifest = _make_run_manifest(
        expected=(
            "run_manifest.json",
            "contract_snapshot.json",
            "verifier_result.json",
        )
    )
    # contract_snapshot is declared but not provided
    bundle = ModelStandardEvidenceBundle(
        correlation_id=_CID,
        run_manifest=run_manifest,
        verifier_result=_make_verifier_result(),
        # contract_snapshot intentionally omitted
    )
    assert bundle.is_complete is False
