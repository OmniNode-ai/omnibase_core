# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEvidenceBundle.

Tests cover: fingerprint determinism, create() factory, immutability,
and evidence item source enforcement. Part of OMN-2537.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.objective.model_evidence_bundle import ModelEvidenceBundle
from omnibase_core.models.objective.model_evidence_item import ModelEvidenceItem


def _make_item(item_id: str, value: float = 1.0) -> ModelEvidenceItem:
    """Helper: create a test evidence item."""
    return ModelEvidenceItem(
        item_id=item_id,
        source="test_output",
        key="tests_passed_count",
        value=value,
        unit="count",
        ref=None,
    )


@pytest.mark.unit
class TestModelEvidenceBundleFingerprint:
    """Test EvidenceBundle fingerprint determinism."""

    def test_fingerprint_is_deterministic(self) -> None:
        """Same items always produce the same fingerprint."""
        items = [_make_item("item-1"), _make_item("item-2")]
        fp1 = ModelEvidenceBundle.fingerprint(items)
        fp2 = ModelEvidenceBundle.fingerprint(items)
        assert fp1 == fp2

    def test_fingerprint_order_independent(self) -> None:
        """Fingerprint is the same regardless of item order."""
        items_forward = [_make_item("item-1", 1.0), _make_item("item-2", 2.0)]
        items_reversed = [_make_item("item-2", 2.0), _make_item("item-1", 1.0)]
        fp_forward = ModelEvidenceBundle.fingerprint(items_forward)
        fp_reversed = ModelEvidenceBundle.fingerprint(items_reversed)
        assert fp_forward == fp_reversed

    def test_fingerprint_changes_with_different_items(self) -> None:
        """Different items produce different fingerprints."""
        items_a = [_make_item("item-1", 1.0)]
        items_b = [_make_item("item-1", 2.0)]  # Different value
        fp_a = ModelEvidenceBundle.fingerprint(items_a)
        fp_b = ModelEvidenceBundle.fingerprint(items_b)
        assert fp_a != fp_b

    def test_fingerprint_is_sha256_hex(self) -> None:
        """Fingerprint is a 64-character hex string (SHA-256)."""
        items = [_make_item("item-1")]
        fp = ModelEvidenceBundle.fingerprint(items)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_empty_items(self) -> None:
        """Empty item list produces a valid deterministic fingerprint."""
        fp1 = ModelEvidenceBundle.fingerprint([])
        fp2 = ModelEvidenceBundle.fingerprint([])
        assert fp1 == fp2
        assert len(fp1) == 64


@pytest.mark.unit
class TestModelEvidenceBundleCreate:
    """Test ModelEvidenceBundle.create() factory method."""

    def test_create_computes_fingerprint(self) -> None:
        """create() computes bundle_fingerprint from items."""
        items = [_make_item("item-1"), _make_item("item-2")]
        bundle = ModelEvidenceBundle.create(
            run_id="run-001",
            items=items,
            collected_at_utc="2026-02-24T12:00:00Z",
        )
        expected_fp = ModelEvidenceBundle.fingerprint(items)
        assert bundle.bundle_fingerprint == expected_fp

    def test_create_sets_all_fields(self) -> None:
        """create() populates all bundle fields correctly."""
        items = [_make_item("item-1")]
        bundle = ModelEvidenceBundle.create(
            run_id="run-test-001",
            items=items,
            collected_at_utc="2026-02-24T10:00:00Z",
        )
        assert bundle.run_id == "run-test-001"
        assert bundle.collected_at_utc == "2026-02-24T10:00:00Z"
        assert bundle.items == items
        assert len(bundle.bundle_fingerprint) == 64

    def test_create_idempotent_fingerprint(self) -> None:
        """Two bundles with same items have same fingerprint."""
        items = [_make_item("item-1"), _make_item("item-2")]
        bundle1 = ModelEvidenceBundle.create(
            run_id="run-001",
            items=items,
            collected_at_utc="2026-02-24T10:00:00Z",
        )
        bundle2 = ModelEvidenceBundle.create(
            run_id="run-002",  # Different run_id
            items=items,
            collected_at_utc="2026-02-24T11:00:00Z",  # Different timestamp
        )
        # Fingerprint is content-based, not timestamp/run_id-based
        assert bundle1.bundle_fingerprint == bundle2.bundle_fingerprint


@pytest.mark.unit
class TestModelEvidenceBundleImmutability:
    """Test that ModelEvidenceBundle is frozen (immutable)."""

    def test_frozen_raises_on_mutation(self) -> None:
        """Mutating a frozen bundle raises ValidationError or TypeError."""
        bundle = ModelEvidenceBundle.create(
            run_id="run-001",
            items=[_make_item("item-1")],
            collected_at_utc="2026-02-24T10:00:00Z",
        )
        with pytest.raises((ValidationError, TypeError)):
            bundle.run_id = "mutated-id"  # type: ignore[misc]


@pytest.mark.unit
class TestModelEvidenceItemSource:
    """Test that ModelEvidenceItem enforces typed source literals."""

    def test_valid_sources_accepted(self) -> None:
        """All seven valid source types are accepted."""
        valid_sources = [
            "test_output",
            "validator_result",
            "static_analysis",
            "build_warnings",
            "structured_review_tag",
            "cost_telemetry",
            "latency_telemetry",
        ]
        for source in valid_sources:
            item = ModelEvidenceItem(
                item_id="item-1",
                source=source,  # type: ignore[arg-type]
                key="some_metric",
                value=1.0,
            )
            assert item.source == source

    def test_free_text_source_rejected(self) -> None:
        """Free-text source types are structurally rejected."""
        with pytest.raises(ValidationError):
            ModelEvidenceItem(
                item_id="item-1",
                source="free_text_review",  # Not in the allowed literal set
                key="some_metric",
                value=1.0,
            )

    def test_model_confidence_source_rejected(self) -> None:
        """Model confidence text is structurally rejected."""
        with pytest.raises(ValidationError):
            ModelEvidenceItem(
                item_id="item-1",
                source="model_confidence",  # Disallowed
                key="confidence",
                value=0.9,
            )
