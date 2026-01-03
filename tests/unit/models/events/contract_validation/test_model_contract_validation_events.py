# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for contract validation event models.

Tests the validation lifecycle event models:
- ModelContractValidationStartedEvent
- ModelContractValidationPassedEvent
- ModelContractValidationFailedEvent
- ModelContractMergeStartedEvent
- ModelContractMergeCompletedEvent

Related:
    - OMN-1146: Contract validation event models
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_validation_mode import EnumValidationMode
from omnibase_core.models.events.contract_validation import (
    CONTRACT_MERGE_COMPLETED_EVENT,
    CONTRACT_MERGE_STARTED_EVENT,
    CONTRACT_VALIDATION_FAILED_EVENT,
    CONTRACT_VALIDATION_PASSED_EVENT,
    CONTRACT_VALIDATION_STARTED_EVENT,
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
    ModelContractRef,
    ModelContractValidationContext,
    ModelContractValidationEventBase,
    ModelContractValidationFailedEvent,
    ModelContractValidationPassedEvent,
    ModelContractValidationStartedEvent,
)

# =============================================================================
# Base Event Model Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractValidationEventBase:
    """Tests for the base event model."""

    def test_base_event_creation_with_required_fields(self) -> None:
        """Test that base event can be created with required fields."""
        run_id = uuid4()
        event = ModelContractValidationEventBase(
            contract_name="test-contract",
            run_id=run_id,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.timestamp, datetime)
        assert event.actor is None
        assert event.contract_ref is None
        assert event.correlation_id is None

    def test_base_event_creation_with_all_fields(self) -> None:
        """Test that base event can be created with all fields."""
        run_id = uuid4()
        actor = uuid4()
        correlation_id = uuid4()
        event_id = uuid4()
        timestamp = datetime.now(UTC)
        contract_ref = ModelContractRef(contract_name="test-contract")

        event = ModelContractValidationEventBase(
            event_id=event_id,
            contract_name="test-contract",
            run_id=run_id,
            actor=actor,
            contract_ref=contract_ref,
            timestamp=timestamp,
            correlation_id=correlation_id,
        )

        assert event.event_id == event_id
        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.actor == actor
        assert event.contract_ref == contract_ref
        assert event.timestamp == timestamp
        assert event.correlation_id == correlation_id

    def test_base_event_contract_name_required(self) -> None:
        """Test that contract_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEventBase(run_id=uuid4())  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "contract_name" in error_str

    def test_base_event_run_id_required(self) -> None:
        """Test that run_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEventBase(contract_name="test")  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "run_id" in error_str

    def test_base_event_contract_name_min_length(self) -> None:
        """Test that contract_name enforces min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEventBase(
                contract_name="",  # Empty string
                run_id=uuid4(),
            )

        error_str = str(exc_info.value)
        assert "contract_name" in error_str or "min_length" in error_str.lower()


# =============================================================================
# Validation Started Event Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractValidationStartedEvent:
    """Tests for ModelContractValidationStartedEvent."""

    def test_started_event_creation_with_required_fields(self) -> None:
        """Test started event with required fields."""
        run_id = uuid4()
        context = ModelContractValidationContext()

        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=context,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.context == context
        assert event.event_type == CONTRACT_VALIDATION_STARTED_EVENT
        assert event.validator_set_name is None

    def test_started_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        assert event.event_type == "onex.contract.validation.started"
        assert event.event_type == CONTRACT_VALIDATION_STARTED_EVENT

    def test_started_event_context_required(self) -> None:
        """Test that context is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationStartedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "context" in error_str

    def test_started_event_with_validator_set_id(self) -> None:
        """Test started event with validator_set_id."""
        run_id = uuid4()
        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=ModelContractValidationContext(),
            validator_set_id="standard-v1",
        )

        assert event.validator_set_name == "standard-v1"

    def test_started_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        actor = uuid4()
        correlation_id = uuid4()
        context = ModelContractValidationContext(mode=EnumValidationMode.STRICT)

        event = ModelContractValidationStartedEvent.create(
            contract_name="factory-contract",
            run_id=run_id,
            context=context,
            validator_set_name="strict-v2",
            actor=actor,
            correlation_id=correlation_id,
        )

        assert event.contract_name == "factory-contract"
        assert event.run_id == run_id
        assert event.context == context
        assert event.validator_set_name == "strict-v2"
        assert event.actor == actor
        assert event.correlation_id == correlation_id

    def test_started_event_is_frozen(self) -> None:
        """Test that started event is frozen."""
        event = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=uuid4(),
            context=ModelContractValidationContext(),
        )

        with pytest.raises(ValidationError):
            event.contract_name = "new-id"  # type: ignore[misc]


@pytest.mark.unit
class TestModelContractValidationStartedEventSerialization:
    """Tests for started event serialization."""

    def test_started_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelContractValidationStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            context=ModelContractValidationContext(mode=EnumValidationMode.PERMISSIVE),
            validator_set_id="test-set",
        )

        json_str = original.model_dump_json()
        restored = ModelContractValidationStartedEvent.model_validate_json(json_str)

        assert restored.contract_name == original.contract_name
        assert restored.run_id == original.run_id
        assert restored.event_type == original.event_type
        assert restored.validator_set_name == original.validator_set_name


# =============================================================================
# Validation Passed Event Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractValidationPassedEvent:
    """Tests for ModelContractValidationPassedEvent."""

    def test_passed_event_creation_with_required_fields(self) -> None:
        """Test passed event with required fields."""
        run_id = uuid4()

        event = ModelContractValidationPassedEvent(
            contract_name="test-contract",
            run_id=run_id,
            duration_ms=250,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.duration_ms == 250
        assert event.event_type == CONTRACT_VALIDATION_PASSED_EVENT
        assert event.warnings_count == 0
        assert event.checks_run == 0
        assert event.warnings_refs == []
        assert event.validator_set_name is None

    def test_passed_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelContractValidationPassedEvent(
            contract_name="test-contract",
            run_id=uuid4(),
            duration_ms=100,
        )

        assert event.event_type == "onex.contract.validation.passed"
        assert event.event_type == CONTRACT_VALIDATION_PASSED_EVENT

    def test_passed_event_duration_ms_required(self) -> None:
        """Test that duration_ms is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationPassedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str

    def test_passed_event_duration_ms_ge_zero(self) -> None:
        """Test that duration_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationPassedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                duration_ms=-1,
            )

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str or "greater" in error_str.lower()

    def test_passed_event_warnings_count_ge_zero(self) -> None:
        """Test that warnings_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationPassedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                duration_ms=100,
                warnings_count=-1,
            )

        error_str = str(exc_info.value)
        assert "warnings_count" in error_str or "greater" in error_str.lower()

    def test_passed_event_checks_run_ge_zero(self) -> None:
        """Test that checks_run must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationPassedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                duration_ms=100,
                checks_run=-1,
            )

        error_str = str(exc_info.value)
        assert "checks_run" in error_str or "greater" in error_str.lower()

    def test_passed_event_warnings_refs_max_length(self) -> None:
        """Test that warnings_refs is bounded to 100 entries."""
        # Create 101 warning refs (exceeds limit)
        warnings_refs = [f"warn://ref/{i}" for i in range(101)]

        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationPassedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                duration_ms=100,
                warnings_refs=warnings_refs,
            )

        error_str = str(exc_info.value)
        assert (
            "warnings_refs" in error_str
            or "100" in error_str
            or "max" in error_str.lower()
        )

    def test_passed_event_with_warnings(self) -> None:
        """Test passed event with warnings."""
        run_id = uuid4()
        event = ModelContractValidationPassedEvent(
            contract_name="test-contract",
            run_id=run_id,
            duration_ms=300,
            warnings_count=3,
            checks_run=15,
            warnings_refs=[
                "warn://deprecation/field-x",
                "warn://style/naming",
                "warn://unused/param",
            ],
        )

        assert event.warnings_count == 3
        assert event.checks_run == 15
        assert len(event.warnings_refs) == 3

    def test_passed_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        actor = uuid4()

        event = ModelContractValidationPassedEvent.create(
            contract_name="factory-contract",
            run_id=run_id,
            duration_ms=500,
            validator_set_name="validator-v1",
            warnings_count=2,
            checks_run=20,
            warnings_refs=["warn://test1", "warn://test2"],
            actor=actor,
        )

        assert event.contract_name == "factory-contract"
        assert event.run_id == run_id
        assert event.duration_ms == 500
        assert event.warnings_count == 2
        assert event.checks_run == 20
        assert len(event.warnings_refs) == 2
        assert event.actor == actor


@pytest.mark.unit
class TestModelContractValidationPassedEventSerialization:
    """Tests for passed event serialization."""

    def test_passed_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelContractValidationPassedEvent(
            contract_name="test-contract",
            run_id=run_id,
            duration_ms=250,
            warnings_count=1,
            checks_run=10,
            warnings_refs=["warn://test"],
        )

        json_str = original.model_dump_json()
        restored = ModelContractValidationPassedEvent.model_validate_json(json_str)

        assert restored.contract_name == original.contract_name
        assert restored.run_id == original.run_id
        assert restored.duration_ms == original.duration_ms
        assert restored.warnings_count == original.warnings_count
        assert restored.checks_run == original.checks_run
        assert restored.warnings_refs == original.warnings_refs


# =============================================================================
# Validation Failed Event Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractValidationFailedEvent:
    """Tests for ModelContractValidationFailedEvent."""

    def test_failed_event_creation_with_required_fields(self) -> None:
        """Test failed event with required fields."""
        run_id = uuid4()

        event = ModelContractValidationFailedEvent(
            contract_name="test-contract",
            run_id=run_id,
            error_count=1,
            first_error_code="CONTRACT_SCHEMA_INVALID",
            duration_ms=150,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.error_count == 1
        assert event.first_error_code == "CONTRACT_SCHEMA_INVALID"
        assert event.duration_ms == 150
        assert event.event_type == CONTRACT_VALIDATION_FAILED_EVENT
        assert event.violations == []
        assert event.result_ref is None
        assert event.validator_set_name is None

    def test_failed_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelContractValidationFailedEvent(
            contract_name="test-contract",
            run_id=uuid4(),
            error_count=1,
            first_error_code="ERROR",
            duration_ms=100,
        )

        assert event.event_type == "onex.contract.validation.failed"
        assert event.event_type == CONTRACT_VALIDATION_FAILED_EVENT

    def test_failed_event_error_count_required(self) -> None:
        """Test that error_count is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                first_error_code="ERROR",
                duration_ms=100,
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "error_count" in error_str

    def test_failed_event_error_count_ge_one(self) -> None:
        """Test that error_count must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=0,  # Must be at least 1
                first_error_code="ERROR",
                duration_ms=100,
            )

        error_str = str(exc_info.value)
        assert "error_count" in error_str or "greater" in error_str.lower()

    def test_failed_event_first_error_code_required(self) -> None:
        """Test that first_error_code is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=1,
                duration_ms=100,
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "first_error_code" in error_str

    def test_failed_event_first_error_code_min_length(self) -> None:
        """Test that first_error_code has min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=1,
                first_error_code="",  # Empty string
                duration_ms=100,
            )

        error_str = str(exc_info.value)
        assert "first_error_code" in error_str or "min_length" in error_str.lower()

    def test_failed_event_duration_ms_required(self) -> None:
        """Test that duration_ms is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=1,
                first_error_code="ERROR",
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str

    def test_failed_event_duration_ms_ge_zero(self) -> None:
        """Test that duration_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=1,
                first_error_code="ERROR",
                duration_ms=-1,
            )

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str or "greater" in error_str.lower()

    def test_failed_event_violations_max_length(self) -> None:
        """Test that violations is bounded to 100 entries."""
        violations = [f"Violation {i}" for i in range(101)]

        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationFailedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                error_count=101,
                first_error_code="ERROR",
                duration_ms=100,
                violations=violations,
            )

        error_str = str(exc_info.value)
        assert (
            "violations" in error_str
            or "100" in error_str
            or "max" in error_str.lower()
        )

    def test_failed_event_with_violations(self) -> None:
        """Test failed event with violations."""
        run_id = uuid4()
        event = ModelContractValidationFailedEvent(
            contract_name="test-contract",
            run_id=run_id,
            error_count=3,
            first_error_code="MISSING_FIELD",
            duration_ms=200,
            violations=[
                "Missing required field: name",
                "Invalid type for field: version",
                "Unknown field: deprecated_field",
            ],
            result_ref="result://validation/123",
        )

        assert event.error_count == 3
        assert len(event.violations) == 3
        assert event.result_ref == "result://validation/123"

    def test_failed_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        actor = uuid4()

        event = ModelContractValidationFailedEvent.create(
            contract_name="factory-contract",
            run_id=run_id,
            error_count=2,
            first_error_code="VALIDATION_ERROR",
            duration_ms=300,
            validator_set_name="strict-v1",
            violations=["Error 1", "Error 2"],
            result_ref="result://ref/456",
            actor=actor,
        )

        assert event.contract_name == "factory-contract"
        assert event.run_id == run_id
        assert event.error_count == 2
        assert event.first_error_code == "VALIDATION_ERROR"
        assert event.duration_ms == 300
        assert len(event.violations) == 2
        assert event.result_ref == "result://ref/456"
        assert event.actor == actor


@pytest.mark.unit
class TestModelContractValidationFailedEventSerialization:
    """Tests for failed event serialization."""

    def test_failed_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelContractValidationFailedEvent(
            contract_name="test-contract",
            run_id=run_id,
            error_count=2,
            first_error_code="ERROR_CODE",
            duration_ms=150,
            violations=["Error 1", "Error 2"],
        )

        json_str = original.model_dump_json()
        restored = ModelContractValidationFailedEvent.model_validate_json(json_str)

        assert restored.contract_name == original.contract_name
        assert restored.run_id == original.run_id
        assert restored.error_count == original.error_count
        assert restored.first_error_code == original.first_error_code
        assert restored.violations == original.violations


# =============================================================================
# Merge Started Event Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractMergeStartedEvent:
    """Tests for ModelContractMergeStartedEvent."""

    def test_merge_started_event_creation_with_required_fields(self) -> None:
        """Test merge started event with required fields."""
        run_id = uuid4()

        event = ModelContractMergeStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.event_type == CONTRACT_MERGE_STARTED_EVENT
        assert event.merge_plan_name is None
        assert event.profile_names == []
        assert event.overlay_refs == []
        assert event.resolver_config_hash is None

    def test_merge_started_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelContractMergeStartedEvent(
            contract_name="test-contract",
            run_id=uuid4(),
        )

        assert event.event_type == "onex.contract.merge.started"
        assert event.event_type == CONTRACT_MERGE_STARTED_EVENT

    def test_merge_started_event_with_all_fields(self) -> None:
        """Test merge started event with all fields."""
        run_id = uuid4()
        event = ModelContractMergeStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            merge_plan_name="plan-001",
            profile_names=["production", "high-availability"],
            overlay_refs=["overlay://custom/timeout", "overlay://custom/retry"],
            resolver_config_hash="sha256:config123",
        )

        assert event.merge_plan_name == "plan-001"
        assert event.profile_names == ["production", "high-availability"]
        assert len(event.overlay_refs) == 2
        assert event.resolver_config_hash == "sha256:config123"

    def test_merge_started_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        actor = uuid4()

        event = ModelContractMergeStartedEvent.create(
            contract_name="factory-contract",
            run_id=run_id,
            merge_plan_name="plan-002",
            profile_names=["dev", "debug"],
            overlay_refs=["overlay://test"],
            resolver_config_hash="sha256:abc",
            actor=actor,
        )

        assert event.contract_name == "factory-contract"
        assert event.merge_plan_name == "plan-002"
        assert event.profile_names == ["dev", "debug"]
        assert event.overlay_refs == ["overlay://test"]
        assert event.actor == actor


@pytest.mark.unit
class TestModelContractMergeStartedEventSerialization:
    """Tests for merge started event serialization."""

    def test_merge_started_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelContractMergeStartedEvent(
            contract_name="test-contract",
            run_id=run_id,
            merge_plan_name="plan-test",
            profile_names=["profile1"],
        )

        json_str = original.model_dump_json()
        restored = ModelContractMergeStartedEvent.model_validate_json(json_str)

        assert restored.contract_name == original.contract_name
        assert restored.merge_plan_name == original.merge_plan_name
        assert restored.profile_names == original.profile_names


# =============================================================================
# Merge Completed Event Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractMergeCompletedEvent:
    """Tests for ModelContractMergeCompletedEvent."""

    def test_merge_completed_event_creation_with_required_fields(self) -> None:
        """Test merge completed event with required fields."""
        run_id = uuid4()

        event = ModelContractMergeCompletedEvent(
            contract_name="test-contract",
            run_id=run_id,
            effective_contract_name="test-contract-effective-001",
            duration_ms=50,
        )

        assert event.contract_name == "test-contract"
        assert event.run_id == run_id
        assert event.effective_contract_name == "test-contract-effective-001"
        assert event.duration_ms == 50
        assert event.event_type == CONTRACT_MERGE_COMPLETED_EVENT
        assert event.effective_contract_hash is None
        assert event.overlays_applied_count == 0
        assert event.defaults_applied is False
        assert event.warnings_count == 0
        assert event.diff_ref is None

    def test_merge_completed_event_event_type_constant(self) -> None:
        """Test that event_type has correct constant value."""
        event = ModelContractMergeCompletedEvent(
            contract_name="test-contract",
            run_id=uuid4(),
            effective_contract_name="effective-001",
            duration_ms=100,
        )

        assert event.event_type == "onex.contract.merge.completed"
        assert event.event_type == CONTRACT_MERGE_COMPLETED_EVENT

    def test_merge_completed_event_effective_contract_name_required(self) -> None:
        """Test that effective_contract_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                duration_ms=100,
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "effective_contract_name" in error_str

    def test_merge_completed_event_effective_contract_name_min_length(self) -> None:
        """Test that effective_contract_name has min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                effective_contract_name="",  # Empty string
                duration_ms=100,
            )

        error_str = str(exc_info.value)
        assert (
            "effective_contract_name" in error_str or "min_length" in error_str.lower()
        )

    def test_merge_completed_event_duration_ms_required(self) -> None:
        """Test that duration_ms is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                effective_contract_name="effective-001",
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str

    def test_merge_completed_event_duration_ms_ge_zero(self) -> None:
        """Test that duration_ms must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                effective_contract_name="effective-001",
                duration_ms=-1,
            )

        error_str = str(exc_info.value)
        assert "duration_ms" in error_str or "greater" in error_str.lower()

    def test_merge_completed_event_overlays_applied_count_ge_zero(self) -> None:
        """Test that overlays_applied_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                effective_contract_name="effective-001",
                duration_ms=100,
                overlays_applied_count=-1,
            )

        error_str = str(exc_info.value)
        assert "overlays_applied_count" in error_str or "greater" in error_str.lower()

    def test_merge_completed_event_warnings_count_ge_zero(self) -> None:
        """Test that warnings_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractMergeCompletedEvent(
                contract_name="test-contract",
                run_id=uuid4(),
                effective_contract_name="effective-001",
                duration_ms=100,
                warnings_count=-1,
            )

        error_str = str(exc_info.value)
        assert "warnings_count" in error_str or "greater" in error_str.lower()

    def test_merge_completed_event_with_all_fields(self) -> None:
        """Test merge completed event with all fields."""
        run_id = uuid4()
        event = ModelContractMergeCompletedEvent(
            contract_name="test-contract",
            run_id=run_id,
            effective_contract_name="effective-full-001",
            effective_contract_hash="sha256:effective123",
            overlays_applied_count=3,
            defaults_applied=True,
            duration_ms=75,
            warnings_count=2,
            diff_ref="diff://merge/001",
        )

        assert event.effective_contract_name == "effective-full-001"
        assert event.effective_contract_hash == "sha256:effective123"
        assert event.overlays_applied_count == 3
        assert event.defaults_applied is True
        assert event.duration_ms == 75
        assert event.warnings_count == 2
        assert event.diff_ref == "diff://merge/001"

    def test_merge_completed_event_create_factory_method(self) -> None:
        """Test the create() factory method."""
        run_id = uuid4()
        actor = uuid4()

        event = ModelContractMergeCompletedEvent.create(
            contract_name="factory-contract",
            run_id=run_id,
            effective_contract_name="effective-factory-001",
            duration_ms=60,
            effective_contract_hash="sha256:factory",
            overlays_applied_count=2,
            defaults_applied=True,
            warnings_count=1,
            diff_ref="diff://factory/001",
            actor=actor,
        )

        assert event.contract_name == "factory-contract"
        assert event.effective_contract_name == "effective-factory-001"
        assert event.duration_ms == 60
        assert event.effective_contract_hash == "sha256:factory"
        assert event.overlays_applied_count == 2
        assert event.defaults_applied is True
        assert event.warnings_count == 1
        assert event.diff_ref == "diff://factory/001"
        assert event.actor == actor


@pytest.mark.unit
class TestModelContractMergeCompletedEventSerialization:
    """Tests for merge completed event serialization."""

    def test_merge_completed_event_round_trip(self) -> None:
        """Test serialization round-trip."""
        run_id = uuid4()
        original = ModelContractMergeCompletedEvent(
            contract_name="test-contract",
            run_id=run_id,
            effective_contract_name="effective-001",
            duration_ms=100,
            defaults_applied=True,
            overlays_applied_count=2,
        )

        json_str = original.model_dump_json()
        restored = ModelContractMergeCompletedEvent.model_validate_json(json_str)

        assert restored.contract_name == original.contract_name
        assert restored.effective_contract_name == original.effective_contract_name
        assert restored.duration_ms == original.duration_ms
        assert restored.defaults_applied == original.defaults_applied
        assert restored.overlays_applied_count == original.overlays_applied_count


# =============================================================================
# Cross-Event Tests
# =============================================================================


@pytest.mark.unit
class TestEventTypeConstants:
    """Tests for event type constants."""

    def test_all_event_type_constants_are_defined(self) -> None:
        """Test that all event type constants are defined."""
        assert CONTRACT_VALIDATION_STARTED_EVENT == "onex.contract.validation.started"
        assert CONTRACT_VALIDATION_PASSED_EVENT == "onex.contract.validation.passed"
        assert CONTRACT_VALIDATION_FAILED_EVENT == "onex.contract.validation.failed"
        assert CONTRACT_MERGE_STARTED_EVENT == "onex.contract.merge.started"
        assert CONTRACT_MERGE_COMPLETED_EVENT == "onex.contract.merge.completed"

    def test_event_types_are_unique(self) -> None:
        """Test that all event type constants are unique."""
        event_types = [
            CONTRACT_VALIDATION_STARTED_EVENT,
            CONTRACT_VALIDATION_PASSED_EVENT,
            CONTRACT_VALIDATION_FAILED_EVENT,
            CONTRACT_MERGE_STARTED_EVENT,
            CONTRACT_MERGE_COMPLETED_EVENT,
        ]
        assert len(event_types) == len(set(event_types))


@pytest.mark.unit
class TestEventLifecycleCorrelation:
    """Tests for event lifecycle correlation via run_id."""

    def test_validation_lifecycle_correlation(self) -> None:
        """Test that validation events can be correlated via run_id."""
        run_id = uuid4()
        contract_name = "lifecycle-contract"

        started = ModelContractValidationStartedEvent(
            contract_name=contract_name,
            run_id=run_id,
            context=ModelContractValidationContext(),
        )

        passed = ModelContractValidationPassedEvent(
            contract_name=contract_name,
            run_id=run_id,
            duration_ms=200,
        )

        # Same run_id enables correlation
        assert started.run_id == passed.run_id
        assert started.contract_name == passed.contract_name

    def test_merge_lifecycle_correlation(self) -> None:
        """Test that merge events can be correlated via run_id."""
        run_id = uuid4()
        contract_name = "merge-contract"

        started = ModelContractMergeStartedEvent(
            contract_name=contract_name,
            run_id=run_id,
        )

        completed = ModelContractMergeCompletedEvent(
            contract_name=contract_name,
            run_id=run_id,
            effective_contract_name="effective-001",
            duration_ms=50,
        )

        # Same run_id enables correlation
        assert started.run_id == completed.run_id
        assert started.contract_name == completed.contract_name


@pytest.mark.unit
class TestEventImmutability:
    """Tests for immutability across all event types."""

    def test_all_events_are_frozen(self) -> None:
        """Test that all event types are frozen."""
        run_id = uuid4()

        events = [
            ModelContractValidationEventBase(contract_name="test", run_id=run_id),
            ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=run_id,
                context=ModelContractValidationContext(),
            ),
            ModelContractValidationPassedEvent(
                contract_name="test", run_id=run_id, duration_ms=100
            ),
            ModelContractValidationFailedEvent(
                contract_name="test",
                run_id=run_id,
                error_count=1,
                first_error_code="ERR",
                duration_ms=100,
            ),
            ModelContractMergeStartedEvent(contract_name="test", run_id=run_id),
            ModelContractMergeCompletedEvent(
                contract_name="test",
                run_id=run_id,
                effective_contract_name="eff",
                duration_ms=50,
            ),
        ]

        for event in events:
            assert event.model_config.get("frozen") is True

    def test_all_events_forbid_extra_fields(self) -> None:
        """Test that all event types forbid extra fields."""
        run_id = uuid4()

        events = [
            ModelContractValidationEventBase(contract_name="test", run_id=run_id),
            ModelContractValidationStartedEvent(
                contract_name="test",
                run_id=run_id,
                context=ModelContractValidationContext(),
            ),
            ModelContractValidationPassedEvent(
                contract_name="test", run_id=run_id, duration_ms=100
            ),
            ModelContractValidationFailedEvent(
                contract_name="test",
                run_id=run_id,
                error_count=1,
                first_error_code="ERR",
                duration_ms=100,
            ),
            ModelContractMergeStartedEvent(contract_name="test", run_id=run_id),
            ModelContractMergeCompletedEvent(
                contract_name="test",
                run_id=run_id,
                effective_contract_name="eff",
                duration_ms=50,
            ),
        ]

        for event in events:
            assert event.model_config.get("extra") == "forbid"
