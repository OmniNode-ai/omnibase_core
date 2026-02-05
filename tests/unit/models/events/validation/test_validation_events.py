# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for cross-repo validation event models.

Tests the validation lifecycle event models:
- ModelValidationEventBase
- ModelValidationRunStartedEvent
- ModelValidationViolationsBatchEvent
- ModelValidationRunCompletedEvent
- ModelViolationRecord

Related:
    - OMN-1776: Cross-repo validation orchestrator
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.validation import (
    VALIDATION_RUN_COMPLETED_EVENT,
    VALIDATION_RUN_STARTED_EVENT,
    VALIDATION_VIOLATIONS_BATCH_EVENT,
    ModelValidationEventBase,
    ModelValidationRunCompletedEvent,
    ModelValidationRunStartedEvent,
    ModelValidationViolationsBatchEvent,
    ModelViolationRecord,
)

# All tests in this module are unit tests
pytestmark = pytest.mark.unit

# =============================================================================
# Base Event Model Tests
# =============================================================================


class TestModelValidationEventBase:
    """Tests for the base event model."""

    def test_base_event_creation_with_required_fields(self) -> None:
        """Test that base event can be created with required fields."""
        run_id = uuid4()
        event = ModelValidationEventBase(
            run_id=run_id,
            repo_id="omnibase_core",
        )

        assert event.repo_id == "omnibase_core"
        assert event.run_id == run_id
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.timestamp, datetime)
        assert event.correlation_id is None

    def test_base_event_creation_with_all_fields(self) -> None:
        """Test that base event can be created with all fields."""
        run_id = uuid4()
        correlation_id = uuid4()
        event_id = uuid4()
        timestamp = datetime.now(UTC)

        event = ModelValidationEventBase(
            event_id=event_id,
            run_id=run_id,
            repo_id="omnibase_core",
            timestamp=timestamp,
            correlation_id=correlation_id,
        )

        assert event.event_id == event_id
        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.timestamp == timestamp
        assert event.correlation_id == correlation_id

    def test_base_event_run_id_required(self) -> None:
        """Test that run_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE(OMN-1776): Testing validation of required field run_id.
            ModelValidationEventBase(repo_id="test")  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "run_id" in error_str

    def test_base_event_repo_id_required(self) -> None:
        """Test that repo_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE(OMN-1776): Testing validation of required field repo_id.
            ModelValidationEventBase(run_id=uuid4())  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "repo_id" in error_str

    def test_base_event_repo_id_min_length(self) -> None:
        """Test that repo_id enforces min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationEventBase(
                repo_id="",  # Empty string
                run_id=uuid4(),
            )

        error_str = str(exc_info.value)
        assert "repo_id" in error_str or "min_length" in error_str.lower()


# =============================================================================
# Validation Run Started Event Tests
# =============================================================================


class TestModelValidationRunStartedEvent:
    """Tests for ModelValidationRunStartedEvent."""

    def test_started_event_creation_with_required_fields(self) -> None:
        """Test started event with required fields."""
        run_id = uuid4()
        started_at = datetime.now(UTC)

        event = ModelValidationRunStartedEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            root_path="/workspace/omnibase_core",
            policy_name="omnibase_core_policy",
            started_at=started_at,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.root_path == "/workspace/omnibase_core"
        assert event.policy_name == "omnibase_core_policy"
        assert event.started_at == started_at
        assert event.event_type == VALIDATION_RUN_STARTED_EVENT
        assert event.rules_enabled == ()
        assert event.baseline_applied is False

    def test_started_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelValidationRunStartedEvent(
            run_id=uuid4(),
            repo_id="test",
            root_path="/test",
            policy_name="test_policy",
            started_at=datetime.now(UTC),
        )

        assert event.event_type == "onex.validation.cross_repo.run.started.v1"
        assert event.event_type == VALIDATION_RUN_STARTED_EVENT

    def test_started_event_event_type_validation(self) -> None:
        """Test that event_type cannot be set to wrong value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationRunStartedEvent(
                run_id=uuid4(),
                repo_id="test",
                root_path="/test",
                policy_name="test_policy",
                started_at=datetime.now(UTC),
                event_type="wrong.event.type",
            )

        error_str = str(exc_info.value)
        assert "event_type" in error_str

    def test_started_event_with_rules_enabled(self) -> None:
        """Test started event with rules_enabled."""
        event = ModelValidationRunStartedEvent(
            run_id=uuid4(),
            repo_id="omnibase_core",
            root_path="/workspace",
            policy_name="policy",
            started_at=datetime.now(UTC),
            rules_enabled=("repo_boundaries", "forbidden_imports", "topic_naming"),
            baseline_applied=True,
        )

        assert event.rules_enabled == (
            "repo_boundaries",
            "forbidden_imports",
            "topic_naming",
        )
        assert event.baseline_applied is True

    def test_started_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        correlation_id = uuid4()
        started_at = datetime.now(UTC)

        event = ModelValidationRunStartedEvent.create(
            run_id=run_id,
            repo_id="omnibase_core",
            root_path="/workspace/omnibase_core",
            policy_name="omnibase_core_policy",
            started_at=started_at,
            rules_enabled=["rule1", "rule2"],
            baseline_applied=True,
            correlation_id=correlation_id,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.rules_enabled == ("rule1", "rule2")
        assert event.baseline_applied is True
        assert event.correlation_id == correlation_id

    def test_started_event_is_frozen(self) -> None:
        """Test that started event is frozen."""
        event = ModelValidationRunStartedEvent(
            run_id=uuid4(),
            repo_id="test",
            root_path="/test",
            policy_name="policy",
            started_at=datetime.now(UTC),
        )

        with pytest.raises(ValidationError):
            # NOTE(OMN-1776): Testing frozen model immutability.
            event.repo_id = "new-id"  # type: ignore[misc]


class TestModelValidationRunStartedEventSerialization:
    """Tests for started event serialization."""

    def test_started_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelValidationRunStartedEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            root_path="/workspace",
            policy_name="policy",
            started_at=datetime.now(UTC),
            rules_enabled=("rule1", "rule2"),
        )

        json_str = original.model_dump_json()
        restored = ModelValidationRunStartedEvent.model_validate_json(json_str)

        assert restored.run_id == original.run_id
        assert restored.repo_id == original.repo_id
        assert restored.event_type == original.event_type
        assert restored.rules_enabled == original.rules_enabled


# =============================================================================
# Violation Record Tests
# =============================================================================


class TestModelViolationRecord:
    """Tests for ModelViolationRecord."""

    def test_violation_record_creation_with_required_fields(self) -> None:
        """Test violation record with required fields."""
        record = ModelViolationRecord(
            severity="ERROR",
            message="Forbidden import: omnibase_infra",
        )

        assert record.severity == "ERROR"
        assert record.message == "Forbidden import: omnibase_infra"
        assert record.code is None
        assert record.file_path is None
        assert record.line_number is None
        assert record.rule_name is None
        assert record.fingerprint is None
        assert record.suppressed is False

    def test_violation_record_creation_with_all_fields(self) -> None:
        """Test violation record with all fields."""
        record = ModelViolationRecord(
            severity="WARNING",
            message="Non-standard topic name",
            code="TOPIC_NAMING_001",
            file_path="/src/events.py",
            line_number=42,
            rule_name="topic_naming",
            fingerprint="abc123",
            suppressed=True,
        )

        assert record.severity == "WARNING"
        assert record.message == "Non-standard topic name"
        assert record.code == "TOPIC_NAMING_001"
        assert record.file_path == "/src/events.py"
        assert record.line_number == 42
        assert record.rule_name == "topic_naming"
        assert record.fingerprint == "abc123"
        assert record.suppressed is True

    def test_violation_record_is_frozen(self) -> None:
        """Test that violation record is frozen."""
        record = ModelViolationRecord(
            severity="ERROR",
            message="Test message",
        )

        with pytest.raises(ValidationError):
            # NOTE(OMN-1776): Testing frozen model immutability.
            record.message = "new message"  # type: ignore[misc]


# =============================================================================
# Validation Violations Batch Event Tests
# =============================================================================


class TestModelValidationViolationsBatchEvent:
    """Tests for ModelValidationViolationsBatchEvent."""

    def test_batch_event_creation_with_required_fields(self) -> None:
        """Test batch event with required fields."""
        run_id = uuid4()
        violations = (
            ModelViolationRecord(severity="ERROR", message="Error 1"),
            ModelViolationRecord(severity="WARNING", message="Warning 1"),
        )

        event = ModelValidationViolationsBatchEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            batch_index=0,
            batch_size=2,
            total_batches=1,
            violations=violations,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.batch_index == 0
        assert event.batch_size == 2
        assert event.total_batches == 1
        assert len(event.violations) == 2
        assert event.event_type == VALIDATION_VIOLATIONS_BATCH_EVENT

    def test_batch_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelValidationViolationsBatchEvent(
            run_id=uuid4(),
            repo_id="test",
            batch_index=0,
            batch_size=0,
            total_batches=1,
            violations=(),
        )

        assert event.event_type == "onex.validation.cross_repo.violations.batch.v1"
        assert event.event_type == VALIDATION_VIOLATIONS_BATCH_EVENT

    def test_batch_event_batch_index_ge_zero(self) -> None:
        """Test that batch_index must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationViolationsBatchEvent(
                run_id=uuid4(),
                repo_id="test",
                batch_index=-1,  # Invalid
                batch_size=0,
                total_batches=1,
                violations=(),
            )

        error_str = str(exc_info.value)
        assert "batch_index" in error_str or "greater" in error_str.lower()

    def test_batch_event_total_batches_ge_one(self) -> None:
        """Test that total_batches must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationViolationsBatchEvent(
                run_id=uuid4(),
                repo_id="test",
                batch_index=0,
                batch_size=0,
                total_batches=0,  # Invalid
                violations=(),
            )

        error_str = str(exc_info.value)
        assert "total_batches" in error_str or "greater" in error_str.lower()

    def test_batch_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        correlation_id = uuid4()
        violations = [
            ModelViolationRecord(severity="ERROR", message="Error 1"),
            ModelViolationRecord(severity="WARNING", message="Warning 1"),
        ]

        event = ModelValidationViolationsBatchEvent.create(
            run_id=run_id,
            repo_id="omnibase_core",
            batch_index=0,
            total_batches=1,
            violations=violations,
            correlation_id=correlation_id,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.batch_index == 0
        assert event.batch_size == 2  # Calculated from violations
        assert event.total_batches == 1
        assert len(event.violations) == 2
        assert event.correlation_id == correlation_id


class TestModelValidationViolationsBatchEventSerialization:
    """Tests for batch event serialization."""

    def test_batch_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        violations = (
            ModelViolationRecord(
                severity="ERROR",
                message="Forbidden import",
                rule_name="forbidden_imports",
            ),
        )

        original = ModelValidationViolationsBatchEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            batch_index=0,
            batch_size=1,
            total_batches=1,
            violations=violations,
        )

        json_str = original.model_dump_json()
        restored = ModelValidationViolationsBatchEvent.model_validate_json(json_str)

        assert restored.run_id == original.run_id
        assert restored.batch_index == original.batch_index
        assert len(restored.violations) == 1
        assert restored.violations[0].severity == "ERROR"
        assert restored.violations[0].message == "Forbidden import"


# =============================================================================
# Validation Run Completed Event Tests
# =============================================================================


class TestModelValidationRunCompletedEvent:
    """Tests for ModelValidationRunCompletedEvent."""

    def test_completed_event_creation_with_required_fields(self) -> None:
        """Test completed event with required fields."""
        run_id = uuid4()
        completed_at = datetime.now(UTC)

        event = ModelValidationRunCompletedEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            is_valid=True,
            total_violations=5,
            error_count=0,
            warning_count=3,
            suppressed_count=2,
            files_processed=150,
            rules_applied=5,
            duration_ms=1250,
            completed_at=completed_at,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.is_valid is True
        assert event.total_violations == 5
        assert event.error_count == 0
        assert event.warning_count == 3
        assert event.suppressed_count == 2
        assert event.files_processed == 150
        assert event.rules_applied == 5
        assert event.duration_ms == 1250
        assert event.completed_at == completed_at
        assert event.event_type == VALIDATION_RUN_COMPLETED_EVENT

    def test_completed_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelValidationRunCompletedEvent(
            run_id=uuid4(),
            repo_id="test",
            is_valid=True,
            total_violations=0,
            error_count=0,
            warning_count=0,
            suppressed_count=0,
            files_processed=0,
            rules_applied=0,
            duration_ms=0,
            completed_at=datetime.now(UTC),
        )

        assert event.event_type == "onex.validation.cross_repo.run.completed.v1"
        assert event.event_type == VALIDATION_RUN_COMPLETED_EVENT

    def test_completed_event_counts_ge_zero(self) -> None:
        """Test that count fields must be >= 0."""
        # Test each count field
        count_fields = [
            ("total_violations", -1),
            ("error_count", -1),
            ("warning_count", -1),
            ("suppressed_count", -1),
            ("files_processed", -1),
            ("rules_applied", -1),
            ("duration_ms", -1),
        ]

        for field_name, invalid_value in count_fields:
            kwargs = {
                "run_id": uuid4(),
                "repo_id": "test",
                "is_valid": True,
                "total_violations": 0,
                "error_count": 0,
                "warning_count": 0,
                "suppressed_count": 0,
                "files_processed": 0,
                "rules_applied": 0,
                "duration_ms": 0,
                "completed_at": datetime.now(UTC),
            }
            kwargs[field_name] = invalid_value

            with pytest.raises(ValidationError) as exc_info:
                # NOTE(OMN-1776): Dynamic kwargs construction for parameterized validation testing.
                ModelValidationRunCompletedEvent(**kwargs)  # type: ignore[arg-type]

            error_str = str(exc_info.value)
            assert field_name in error_str or "greater" in error_str.lower()

    def test_completed_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        correlation_id = uuid4()
        completed_at = datetime.now(UTC)

        event = ModelValidationRunCompletedEvent.create(
            run_id=run_id,
            repo_id="omnibase_core",
            is_valid=False,
            total_violations=10,
            error_count=3,
            warning_count=5,
            suppressed_count=2,
            files_processed=200,
            rules_applied=7,
            duration_ms=2500,
            completed_at=completed_at,
            correlation_id=correlation_id,
        )

        assert event.run_id == run_id
        assert event.repo_id == "omnibase_core"
        assert event.is_valid is False
        assert event.total_violations == 10
        assert event.error_count == 3
        assert event.correlation_id == correlation_id


class TestModelValidationRunCompletedEventSerialization:
    """Tests for completed event serialization."""

    def test_completed_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        completed_at = datetime.now(UTC)

        original = ModelValidationRunCompletedEvent(
            run_id=run_id,
            repo_id="omnibase_core",
            is_valid=True,
            total_violations=5,
            error_count=0,
            warning_count=3,
            suppressed_count=2,
            files_processed=150,
            rules_applied=5,
            duration_ms=1250,
            completed_at=completed_at,
        )

        json_str = original.model_dump_json()
        restored = ModelValidationRunCompletedEvent.model_validate_json(json_str)

        assert restored.run_id == original.run_id
        assert restored.is_valid == original.is_valid
        assert restored.total_violations == original.total_violations
        assert restored.error_count == original.error_count
        assert restored.duration_ms == original.duration_ms


# =============================================================================
# Cross-Event Tests
# =============================================================================


class TestEventTypeConstants:
    """Tests for event type constants."""

    def test_all_event_type_constants_are_defined(self) -> None:
        """Test that all event type constants are defined."""
        assert (
            VALIDATION_RUN_STARTED_EVENT == "onex.validation.cross_repo.run.started.v1"
        )
        assert (
            VALIDATION_VIOLATIONS_BATCH_EVENT
            == "onex.validation.cross_repo.violations.batch.v1"
        )
        assert (
            VALIDATION_RUN_COMPLETED_EVENT
            == "onex.validation.cross_repo.run.completed.v1"
        )

    def test_event_types_are_unique(self) -> None:
        """Test that all event type constants are unique."""
        event_types = [
            VALIDATION_RUN_STARTED_EVENT,
            VALIDATION_VIOLATIONS_BATCH_EVENT,
            VALIDATION_RUN_COMPLETED_EVENT,
        ]
        assert len(event_types) == len(set(event_types))


class TestEventLifecycleCorrelation:
    """Tests for event lifecycle correlation via run_id."""

    def test_validation_lifecycle_correlation(self) -> None:
        """Test that validation events can be correlated via run_id."""
        run_id = uuid4()
        repo_id = "omnibase_core"
        started_at = datetime.now(UTC)
        completed_at = datetime.now(UTC)

        started = ModelValidationRunStartedEvent(
            run_id=run_id,
            repo_id=repo_id,
            root_path="/workspace",
            policy_name="policy",
            started_at=started_at,
        )

        batch = ModelValidationViolationsBatchEvent(
            run_id=run_id,
            repo_id=repo_id,
            batch_index=0,
            batch_size=0,
            total_batches=1,
            violations=(),
        )

        completed = ModelValidationRunCompletedEvent(
            run_id=run_id,
            repo_id=repo_id,
            is_valid=True,
            total_violations=0,
            error_count=0,
            warning_count=0,
            suppressed_count=0,
            files_processed=100,
            rules_applied=5,
            duration_ms=500,
            completed_at=completed_at,
        )

        # Same run_id enables correlation
        assert started.run_id == batch.run_id == completed.run_id
        assert started.repo_id == batch.repo_id == completed.repo_id


class TestEventImmutability:
    """Tests for immutability across all event types."""

    def test_all_events_are_frozen(self) -> None:
        """Test that all event types are frozen."""
        run_id = uuid4()
        now = datetime.now(UTC)

        events = [
            ModelValidationEventBase(run_id=run_id, repo_id="test"),
            ModelValidationRunStartedEvent(
                run_id=run_id,
                repo_id="test",
                root_path="/test",
                policy_name="policy",
                started_at=now,
            ),
            ModelValidationViolationsBatchEvent(
                run_id=run_id,
                repo_id="test",
                batch_index=0,
                batch_size=0,
                total_batches=1,
                violations=(),
            ),
            ModelValidationRunCompletedEvent(
                run_id=run_id,
                repo_id="test",
                is_valid=True,
                total_violations=0,
                error_count=0,
                warning_count=0,
                suppressed_count=0,
                files_processed=0,
                rules_applied=0,
                duration_ms=0,
                completed_at=now,
            ),
            ModelViolationRecord(severity="ERROR", message="test"),
        ]

        for event in events:
            assert event.model_config.get("frozen") is True

    def test_all_events_forbid_extra_fields(self) -> None:
        """Test that all event types forbid extra fields."""
        run_id = uuid4()
        now = datetime.now(UTC)

        events = [
            ModelValidationEventBase(run_id=run_id, repo_id="test"),
            ModelValidationRunStartedEvent(
                run_id=run_id,
                repo_id="test",
                root_path="/test",
                policy_name="policy",
                started_at=now,
            ),
            ModelValidationViolationsBatchEvent(
                run_id=run_id,
                repo_id="test",
                batch_index=0,
                batch_size=0,
                total_batches=1,
                violations=(),
            ),
            ModelValidationRunCompletedEvent(
                run_id=run_id,
                repo_id="test",
                is_valid=True,
                total_violations=0,
                error_count=0,
                warning_count=0,
                suppressed_count=0,
                files_processed=0,
                rules_applied=0,
                duration_ms=0,
                completed_at=now,
            ),
            ModelViolationRecord(severity="ERROR", message="test"),
        ]

        for event in events:
            assert event.model_config.get("extra") == "forbid"
