# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for graduated pipeline chain models (OMN-11675)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.pipeline.enum_closeout_failure import EnumCloseoutFailure
from omnibase_core.models.pipeline.model_chain_diff import ModelChainDiff
from omnibase_core.models.pipeline.model_closeout_result import ModelCloseoutResult
from omnibase_core.models.pipeline.model_evidence_artifact import ModelEvidenceArtifact
from omnibase_core.models.pipeline.model_golden_chain_entry import ModelGoldenChainEntry
from omnibase_core.models.pipeline.model_readiness_result import ModelReadinessResult


@pytest.mark.unit
class TestModelGoldenChainEntry:
    def test_construction(self) -> None:
        entry = ModelGoldenChainEntry(
            sequence=1,
            event_type="node.generated",
            topic="onex.evt.omnimarket.node-generated.v1",
            source_node="node_generation_consumer",
        )
        assert entry.sequence == 1
        assert entry.event_type == "node.generated"

    def test_frozen(self) -> None:
        entry = ModelGoldenChainEntry(
            sequence=0, event_type="e", topic="t", source_node="n"
        )
        with pytest.raises(Exception):
            entry.sequence = 99  # type: ignore[misc]


@pytest.mark.unit
class TestModelChainDiff:
    def test_matches_empty(self) -> None:
        diff = ModelChainDiff(matches=True, expected_count=0, observed_count=0)
        assert diff.matches
        assert diff.missing_events == ()
        assert diff.unexpected_events == ()

    def test_with_missing_events(self) -> None:
        entry = ModelGoldenChainEntry(
            sequence=1, event_type="e", topic="t", source_node="n"
        )
        diff = ModelChainDiff(
            matches=False,
            expected_count=2,
            observed_count=1,
            missing_events=(entry,),
        )
        assert not diff.matches
        assert len(diff.missing_events) == 1


@pytest.mark.unit
class TestModelEvidenceArtifact:
    def test_construction(self) -> None:
        artifact = ModelEvidenceArtifact(
            path=".onex_state/evidence/run.json",
            sha256="abc123",
            captured_at="2026-05-22T00:00:00Z",
            source_surface="pipeline_closeout",
            evidence_kind="chain_capture",
        )
        assert artifact.sha256 == "abc123"

    def test_frozen(self) -> None:
        artifact = ModelEvidenceArtifact(
            path="p",
            sha256="s",
            captured_at="t",
            source_surface="ss",
            evidence_kind="ek",
        )
        with pytest.raises(Exception):
            artifact.sha256 = "modified"  # type: ignore[misc]


@pytest.mark.unit
class TestEnumCloseoutFailure:
    def test_all_values_unique(self) -> None:
        values = [e.value for e in EnumCloseoutFailure]
        assert len(values) == len(set(values))

    def test_canonical_members(self) -> None:
        assert EnumCloseoutFailure.EVIDENCE_MISSING == "evidence_missing"
        assert EnumCloseoutFailure.TESTS_FAILED == "tests_failed"
        assert EnumCloseoutFailure.CHAIN_ORDER_MISMATCH == "chain_order_mismatch"


@pytest.mark.unit
class TestModelReadinessResult:
    def test_ready(self) -> None:
        r = ModelReadinessResult(ready=True)
        assert r.ready
        assert r.blocking == ()
        assert r.conditional == ()
        assert r.advisory == ()

    def test_not_ready_with_blockers(self) -> None:
        r = ModelReadinessResult(ready=False, blocking=("missing env var",))
        assert not r.ready
        assert len(r.blocking) == 1


@pytest.mark.unit
class TestModelCloseoutResult:
    def test_passed(self) -> None:
        result = ModelCloseoutResult(passed=True, chain_match=True)
        assert result.passed
        assert result.chain_diff is None
        assert result.failure_class is None
        assert result.evidence_artifacts == ()

    def test_failed_with_class(self) -> None:
        result = ModelCloseoutResult(
            passed=False,
            chain_match=False,
            failure_class=EnumCloseoutFailure.EVIDENCE_MISSING,
            verifier_identity="node_closeout_verifier",
        )
        assert not result.passed
        assert result.failure_class == EnumCloseoutFailure.EVIDENCE_MISSING
        assert result.verifier_identity == "node_closeout_verifier"

    def test_importable_from_package(self) -> None:
        from omnibase_core.models.pipeline import (
            ModelChainDiff,
            ModelCloseoutResult,
            ModelEvidenceArtifact,
            ModelGoldenChainEntry,
            ModelReadinessResult,
        )

        assert ModelCloseoutResult is not None
        assert ModelChainDiff is not None
        assert ModelEvidenceArtifact is not None
        assert ModelGoldenChainEntry is not None
        assert ModelReadinessResult is not None
