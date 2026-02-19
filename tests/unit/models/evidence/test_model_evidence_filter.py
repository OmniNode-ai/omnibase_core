# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelEvidenceFilter (OMN-1200)."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelEvidenceFilterDefaults:
    """Tests for ModelEvidenceFilter default values."""

    def test_default_values(self) -> None:
        """Default filter should match everything."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter()
        assert filter_.invariant_ids is None
        assert filter_.status == "all"
        assert filter_.min_confidence == 0.0
        assert filter_.start_date is None
        assert filter_.end_date is None


@pytest.mark.unit
class TestModelEvidenceFilterCustomValues:
    """Tests for ModelEvidenceFilter custom values."""

    def test_custom_values(self) -> None:
        """Custom filter values should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        filter_ = ModelEvidenceFilter(
            invariant_ids=("inv-1", "inv-2"),
            status="failed",
            min_confidence=0.5,
            start_date=now - timedelta(days=1),
            end_date=now,
        )
        assert filter_.invariant_ids == ("inv-1", "inv-2")
        assert filter_.status == "failed"
        assert filter_.min_confidence == 0.5
        assert filter_.start_date is not None
        assert filter_.end_date is not None

    def test_status_passed(self) -> None:
        """Status 'passed' should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(status="passed")
        assert filter_.status == "passed"

    def test_status_failed(self) -> None:
        """Status 'failed' should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(status="failed")
        assert filter_.status == "failed"

    def test_status_all(self) -> None:
        """Status 'all' should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(status="all")
        assert filter_.status == "all"


@pytest.mark.unit
class TestModelEvidenceFilterConfidenceValidation:
    """Tests for ModelEvidenceFilter confidence validation."""

    def test_confidence_validation_valid_min(self) -> None:
        """Confidence should accept minimum value 0.0."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(min_confidence=0.0)
        assert filter_.min_confidence == 0.0

    def test_confidence_validation_valid_max(self) -> None:
        """Confidence should accept maximum value 1.0."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(min_confidence=1.0)
        assert filter_.min_confidence == 1.0

    def test_confidence_validation_invalid_below_min(self) -> None:
        """Confidence should reject values below minimum."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        with pytest.raises(ValidationError):
            ModelEvidenceFilter(min_confidence=-0.1)

    def test_confidence_validation_invalid_above_max(self) -> None:
        """Confidence should reject values above maximum."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        with pytest.raises(ValidationError):
            ModelEvidenceFilter(min_confidence=1.1)


@pytest.mark.unit
class TestModelEvidenceFilterDateValidation:
    """Tests for ModelEvidenceFilter date range validation."""

    def test_date_range_validation_valid(self) -> None:
        """Valid date range should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        filter_ = ModelEvidenceFilter(
            start_date=now - timedelta(days=1),
            end_date=now,
        )
        assert filter_.start_date is not None
        assert filter_.end_date is not None

    def test_date_range_validation_start_equals_end(self) -> None:
        """start_date equal to end_date should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        filter_ = ModelEvidenceFilter(
            start_date=now,
            end_date=now,
        )
        assert filter_.start_date == filter_.end_date

    def test_date_range_validation_invalid_start_after_end(self) -> None:
        """start_date after end_date should raise ValidationError."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            ModelEvidenceFilter(
                start_date=now,
                end_date=now - timedelta(days=1),
            )

    def test_date_range_only_start_date(self) -> None:
        """Only start_date should be valid."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        filter_ = ModelEvidenceFilter(start_date=now)
        assert filter_.start_date is not None
        assert filter_.end_date is None

    def test_date_range_only_end_date(self) -> None:
        """Only end_date should be valid."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        filter_ = ModelEvidenceFilter(end_date=now)
        assert filter_.start_date is None
        assert filter_.end_date is not None


@pytest.mark.unit
class TestModelEvidenceFilterInvariantIdsValidation:
    """Tests for ModelEvidenceFilter invariant_ids validation."""

    def test_invariant_ids_rejects_empty_tuple(self) -> None:
        """Empty tuple for invariant_ids should raise ValidationError."""
        from pydantic import ValidationError

        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        with pytest.raises(ValidationError, match="non-empty"):
            ModelEvidenceFilter(invariant_ids=())

    def test_invariant_ids_accepts_non_empty_tuple(self) -> None:
        """Non-empty tuple for invariant_ids should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(invariant_ids=("inv-1", "inv-2"))
        assert filter_.invariant_ids == ("inv-1", "inv-2")

    def test_invariant_ids_accepts_none(self) -> None:
        """None for invariant_ids should be accepted (means all)."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(invariant_ids=None)
        assert filter_.invariant_ids is None

    def test_invariant_ids_accepts_single_item_tuple(self) -> None:
        """Single-item tuple for invariant_ids should be accepted."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(invariant_ids=("inv-1",))
        assert filter_.invariant_ids == ("inv-1",)


@pytest.mark.unit
class TestModelEvidenceFilterMatchesConfidence:
    """Tests for ModelEvidenceFilter.matches_confidence method."""

    def test_matches_confidence_equal(self) -> None:
        """Confidence equal to threshold should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(min_confidence=0.5)
        assert filter_.matches_confidence(0.5) is True

    def test_matches_confidence_above(self) -> None:
        """Confidence above threshold should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(min_confidence=0.5)
        assert filter_.matches_confidence(0.6) is True

    def test_matches_confidence_below(self) -> None:
        """Confidence below threshold should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(min_confidence=0.5)
        assert filter_.matches_confidence(0.4) is False

    def test_matches_confidence_default(self) -> None:
        """Default filter should match any confidence."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter()
        assert filter_.matches_confidence(0.0) is True
        assert filter_.matches_confidence(1.0) is True


@pytest.mark.unit
class TestModelEvidenceFilterMatchesStatus:
    """Tests for ModelEvidenceFilter.matches_status method."""

    def test_matches_status_all_passed(self) -> None:
        """Status 'all' should match passed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        all_filter = ModelEvidenceFilter(status="all")
        assert all_filter.matches_status(True) is True

    def test_matches_status_all_failed(self) -> None:
        """Status 'all' should match failed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        all_filter = ModelEvidenceFilter(status="all")
        assert all_filter.matches_status(False) is True

    def test_matches_status_passed_filter_passed(self) -> None:
        """Status 'passed' should match passed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        passed_filter = ModelEvidenceFilter(status="passed")
        assert passed_filter.matches_status(True) is True

    def test_matches_status_passed_filter_failed(self) -> None:
        """Status 'passed' should not match failed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        passed_filter = ModelEvidenceFilter(status="passed")
        assert passed_filter.matches_status(False) is False

    def test_matches_status_failed_filter_passed(self) -> None:
        """Status 'failed' should not match passed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        failed_filter = ModelEvidenceFilter(status="failed")
        assert failed_filter.matches_status(True) is False

    def test_matches_status_failed_filter_failed(self) -> None:
        """Status 'failed' should match failed."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        failed_filter = ModelEvidenceFilter(status="failed")
        assert failed_filter.matches_status(False) is True


@pytest.mark.unit
class TestModelEvidenceFilterMatchesInvariantId:
    """Tests for ModelEvidenceFilter.matches_invariant method."""

    def test_matches_invariant_none_filter(self) -> None:
        """None invariant_ids should match any ID."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        all_filter = ModelEvidenceFilter()
        assert all_filter.matches_invariant("any-id") is True
        assert all_filter.matches_invariant("another-id") is True

    def test_matches_invariant_specific_match(self) -> None:
        """Specific IDs should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(invariant_ids=("inv-1", "inv-2"))
        assert filter_.matches_invariant("inv-1") is True
        assert filter_.matches_invariant("inv-2") is True

    def test_matches_invariant_specific_no_match(self) -> None:
        """Non-matching IDs should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(invariant_ids=("inv-1", "inv-2"))
        assert filter_.matches_invariant("inv-3") is False


@pytest.mark.unit
class TestModelEvidenceFilterMatchesDate:
    """Tests for ModelEvidenceFilter.matches_date method."""

    def test_matches_date_no_filter(self) -> None:
        """No date filter should match any date."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        no_filter = ModelEvidenceFilter()
        now = datetime.now(UTC)
        assert no_filter.matches_date(now) is True

    def test_matches_date_start_only_match(self) -> None:
        """Date at or after start_date should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        tomorrow = now + timedelta(days=1)
        start_filter = ModelEvidenceFilter(start_date=now)
        assert start_filter.matches_date(now) is True
        assert start_filter.matches_date(tomorrow) is True

    def test_matches_date_start_only_no_match(self) -> None:
        """Date before start_date should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        start_filter = ModelEvidenceFilter(start_date=now)
        assert start_filter.matches_date(yesterday) is False

    def test_matches_date_end_only_match(self) -> None:
        """Date at or before end_date should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        end_filter = ModelEvidenceFilter(end_date=now)
        assert end_filter.matches_date(now) is True
        assert end_filter.matches_date(yesterday) is True

    def test_matches_date_end_only_no_match(self) -> None:
        """Date after end_date should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        tomorrow = now + timedelta(days=1)
        end_filter = ModelEvidenceFilter(end_date=now)
        assert end_filter.matches_date(tomorrow) is False

    def test_matches_date_range_match(self) -> None:
        """Date within range should match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        range_filter = ModelEvidenceFilter(start_date=yesterday, end_date=tomorrow)
        assert range_filter.matches_date(now) is True
        assert range_filter.matches_date(yesterday) is True
        assert range_filter.matches_date(tomorrow) is True

    def test_matches_date_range_no_match_before(self) -> None:
        """Date before range should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        range_filter = ModelEvidenceFilter(start_date=yesterday, end_date=tomorrow)
        assert range_filter.matches_date(two_days_ago) is False

    def test_matches_date_range_no_match_after(self) -> None:
        """Date after range should not match."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        two_days_from_now = now + timedelta(days=2)
        range_filter = ModelEvidenceFilter(start_date=yesterday, end_date=tomorrow)
        assert range_filter.matches_date(two_days_from_now) is False


@pytest.mark.unit
class TestModelEvidenceFilterImmutability:
    """Tests for ModelEvidenceFilter immutability."""

    def test_frozen_model(self) -> None:
        """Model should be immutable."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter()
        with pytest.raises(ValidationError):
            filter_.status = "passed"  # type: ignore[misc]

    def test_frozen_model_min_confidence(self) -> None:
        """min_confidence should not be mutable."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter()
        with pytest.raises(ValidationError):
            filter_.min_confidence = 0.5  # type: ignore[misc]


@pytest.mark.unit
class TestModelEvidenceFilterExtraFields:
    """Tests for ModelEvidenceFilter extra field handling."""

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        with pytest.raises(ValidationError):
            ModelEvidenceFilter(unknown_field=True)  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelEvidenceFilterSerialization:
    """Tests for ModelEvidenceFilter serialization."""

    def test_model_dump(self) -> None:
        """Model can be serialized to dict."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        filter_ = ModelEvidenceFilter(
            invariant_ids=("inv-1", "inv-2"),
            status="failed",
            min_confidence=0.5,
        )

        data = filter_.model_dump()

        assert data["invariant_ids"] == ("inv-1", "inv-2")
        assert data["status"] == "failed"
        assert data["min_confidence"] == 0.5

    def test_model_validate_from_dict(self) -> None:
        """Model can be created from dict."""
        from omnibase_core.models.evidence.model_evidence_filter import (
            ModelEvidenceFilter,
        )

        data = {
            "invariant_ids": ("inv-1", "inv-2"),
            "status": "passed",
            "min_confidence": 0.75,
        }

        filter_ = ModelEvidenceFilter.model_validate(data)

        assert filter_.invariant_ids == ("inv-1", "inv-2")
        assert filter_.status == "passed"
        assert filter_.min_confidence == 0.75
