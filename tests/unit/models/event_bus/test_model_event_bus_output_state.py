# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventBusOutputState.

Comprehensive tests for event bus output state model including:
- Construction with valid inputs
- Field validation
- Factory methods
- Status checking methods
- Performance analysis methods
- Error handling methods
- Serialization and deserialization
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_bus_output_field import (
    ModelEventBusOutputField,
)
from omnibase_core.models.event_bus.model_event_bus_output_state import (
    ModelEventBusOutputState,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelEventBusOutputStateConstruction:
    """Test ModelEventBusOutputState construction."""

    def test_create_with_required_fields(self) -> None:
        """Test creating output state with required fields only."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Operation completed",
        )

        assert state.status == EnumOnexStatus.SUCCESS
        assert state.message == "Operation completed"

    def test_create_with_all_fields(self) -> None:
        """Test creating output state with all fields."""
        correlation_id = uuid4()
        event_id = uuid4()

        state = ModelEventBusOutputState(
            version="1.2.3",
            status=EnumOnexStatus.SUCCESS,
            message="Complete",
            correlation_id=correlation_id,
            event_id=event_id,
            processing_time_ms=100,
            retry_attempt=0,
        )

        assert state.version.major == 1
        assert state.status == EnumOnexStatus.SUCCESS
        assert state.message == "Complete"
        assert state.correlation_id == correlation_id
        assert state.event_id == event_id
        assert state.processing_time_ms == 100
        assert state.retry_attempt == 0

    def test_create_with_output_field(self) -> None:
        """Test creating output state with output_field."""
        output_field = ModelEventBusOutputField(
            backend="kafka",
            processed="done",
        )

        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Complete",
            output_field=output_field,
        )

        assert state.output_field is not None
        assert state.output_field.backend == "kafka"


@pytest.mark.unit
class TestModelEventBusOutputStateValidation:
    """Test ModelEventBusOutputState validation."""

    def test_missing_status_raises_error(self) -> None:
        """Test that missing status raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(message="Test")  # type: ignore[call-arg]

    def test_missing_message_raises_error(self) -> None:
        """Test that missing message raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(status=EnumOnexStatus.SUCCESS)  # type: ignore[call-arg]

    def test_empty_message_raises_error(self) -> None:
        """Test that empty message raises error (min_length=1)."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.SUCCESS,
                message="",
            )

    def test_whitespace_message_raises_error(self) -> None:
        """Test that whitespace-only message raises error."""
        with pytest.raises(ModelOnexError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.SUCCESS,
                message="   ",
            )

    def test_message_strips_whitespace(self) -> None:
        """Test that message strips leading/trailing whitespace."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="  Test message  ",
        )

        assert state.message == "Test message"

    def test_processing_time_ms_non_negative(self) -> None:
        """Test that processing_time_ms must be non-negative."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.SUCCESS,
                message="Test",
                processing_time_ms=-1,
            )

    def test_retry_attempt_non_negative(self) -> None:
        """Test that retry_attempt must be non-negative."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.SUCCESS,
                message="Test",
                retry_attempt=-1,
            )

    def test_retry_attempt_max_value(self) -> None:
        """Test that retry_attempt has maximum value."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.SUCCESS,
                message="Test",
                retry_attempt=11,
            )


@pytest.mark.unit
class TestModelEventBusOutputStateErrorCodeValidation:
    """Test ModelEventBusOutputState error_code validation."""

    def test_error_code_valid_format(self) -> None:
        """Test that valid error_code formats are accepted."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="CONNECTION_FAILED",
        )

        assert state.error_code == "CONNECTION_FAILED"

    def test_error_code_converts_to_uppercase(self) -> None:
        """Test that error_code is converted to uppercase."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="connection_failed",
        )

        assert state.error_code == "CONNECTION_FAILED"

    def test_error_code_strips_whitespace(self) -> None:
        """Test that error_code strips whitespace."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="  ERROR_CODE  ",
        )

        assert state.error_code == "ERROR_CODE"

    def test_error_code_empty_becomes_none(self) -> None:
        """Test that empty error_code becomes None."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="   ",
        )

        assert state.error_code is None

    def test_error_code_invalid_format_raises_error(self) -> None:
        """Test that invalid error_code format raises error."""
        with pytest.raises(ModelOnexError):
            ModelEventBusOutputState(
                status=EnumOnexStatus.ERROR,
                message="Failed",
                error_code="invalid-code",  # Contains hyphen
            )


@pytest.mark.unit
class TestModelEventBusOutputStateStatusMethods:
    """Test ModelEventBusOutputState status checking methods."""

    def test_is_successful_true(self) -> None:
        """Test is_successful returns True for SUCCESS."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.is_successful() is True

    def test_is_successful_false(self) -> None:
        """Test is_successful returns False for non-SUCCESS."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
        )

        assert state.is_successful() is False

    def test_is_failed_true_for_error(self) -> None:
        """Test is_failed returns True for ERROR."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
        )

        assert state.is_failed() is True

    def test_is_failed_true_for_unknown(self) -> None:
        """Test is_failed returns True for UNKNOWN."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.UNKNOWN,
            message="Unknown",
        )

        assert state.is_failed() is True

    def test_is_failed_false_for_success(self) -> None:
        """Test is_failed returns False for SUCCESS."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.is_failed() is False

    def test_is_retryable_true_for_error(self) -> None:
        """Test is_retryable returns True for ERROR with retries left."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            retry_attempt=2,
        )

        assert state.is_retryable() is True

    def test_is_retryable_false_when_max_retries_reached(self) -> None:
        """Test is_retryable returns False when max retries reached."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            retry_attempt=5,
        )

        assert state.is_retryable() is False

    def test_is_warning_only_true(self) -> None:
        """Test is_warning_only returns True for WARNING."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.WARNING,
            message="Warning",
        )

        assert state.is_warning_only() is True

    def test_has_warnings_true(self) -> None:
        """Test has_warnings returns True when warnings present."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            warnings=["Warning 1", "Warning 2"],
        )

        assert state.has_warnings() is True

    def test_has_warnings_false(self) -> None:
        """Test has_warnings returns False when no warnings."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.has_warnings() is False


@pytest.mark.unit
class TestModelEventBusOutputStateSeverityLevel:
    """Test ModelEventBusOutputState severity level methods."""

    @pytest.mark.parametrize(
        ("status", "expected_severity"),
        [
            (EnumOnexStatus.SUCCESS, "info"),
            (EnumOnexStatus.WARNING, "warning"),
            (EnumOnexStatus.ERROR, "error"),
            (EnumOnexStatus.SKIPPED, "info"),
            (EnumOnexStatus.FIXED, "info"),
            (EnumOnexStatus.PARTIAL, "warning"),
            (EnumOnexStatus.INFO, "info"),
            (EnumOnexStatus.UNKNOWN, "error"),
        ],
    )
    def test_get_severity_level(
        self, status: EnumOnexStatus, expected_severity: str
    ) -> None:
        """Test get_severity_level returns correct severity for each status."""
        state = ModelEventBusOutputState(
            status=status,
            message="Test",
        )

        assert state.get_severity_level() == expected_severity


@pytest.mark.unit
class TestModelEventBusOutputStatePerformanceMethods:
    """Test ModelEventBusOutputState performance analysis methods."""

    def test_get_performance_category_unknown(self) -> None:
        """Test get_performance_category returns unknown when no time."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.get_performance_category() == "unknown"

    @pytest.mark.parametrize(
        ("time_ms", "expected_category"),
        [
            (50, "excellent"),
            (100, "good"),
            (500, "acceptable"),
            (2000, "slow"),
            (10000, "very_slow"),
        ],
    )
    def test_get_performance_category(
        self, time_ms: int, expected_category: str
    ) -> None:
        """Test get_performance_category returns correct category."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=time_ms,
        )

        assert state.get_performance_category() == expected_category

    def test_is_performance_concerning_true(self) -> None:
        """Test is_performance_concerning returns True for slow operations."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=5000,  # slow
        )

        assert state.is_performance_concerning() is True

    def test_is_performance_concerning_false(self) -> None:
        """Test is_performance_concerning returns False for fast operations."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=100,  # good
        )

        assert state.is_performance_concerning() is False

    def test_get_processing_time_human_ms(self) -> None:
        """Test get_processing_time_human for milliseconds."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=500,
        )

        assert state.get_processing_time_human() == "500ms"

    def test_get_processing_time_human_seconds(self) -> None:
        """Test get_processing_time_human for seconds."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=2500,
        )

        assert state.get_processing_time_human() == "2.50s"

    def test_get_processing_time_human_unknown(self) -> None:
        """Test get_processing_time_human returns unknown when no time."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.get_processing_time_human() == "unknown"

    def test_get_performance_recommendations_empty(self) -> None:
        """Test get_performance_recommendations returns empty for good state."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=100,
        )

        recommendations = state.get_performance_recommendations()

        assert len(recommendations) == 0

    def test_get_performance_recommendations_with_issues(self) -> None:
        """Test get_performance_recommendations returns items for issues."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=5000,  # slow
            retry_attempt=3,
            warnings=["warning1"],
        )

        recommendations = state.get_performance_recommendations()

        assert len(recommendations) > 0


@pytest.mark.unit
class TestModelEventBusOutputStateErrorMethods:
    """Test ModelEventBusOutputState error handling methods."""

    def test_get_error_summary_returns_none_for_success(self) -> None:
        """Test get_error_summary returns None for successful state."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        summary = state.get_error_summary()

        assert summary is None

    def test_get_error_summary_returns_summary_for_error(self) -> None:
        """Test get_error_summary returns summary for error state."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="CONNECTION_FAILED",
        )

        summary = state.get_error_summary()

        assert summary is not None
        assert summary.error_code == "CONNECTION_FAILED"
        assert summary.error_message == "Failed"

    def test_get_troubleshooting_steps_empty_for_success(self) -> None:
        """Test get_troubleshooting_steps returns empty for success."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        steps = state.get_troubleshooting_steps()

        # May have some steps but should be empty for basic success
        assert isinstance(steps, list)

    def test_get_troubleshooting_steps_with_error_code(self) -> None:
        """Test get_troubleshooting_steps includes error code reference."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
            error_code="CONNECTION_FAILED",
        )

        steps = state.get_troubleshooting_steps()

        assert any("CONNECTION_FAILED" in step for step in steps)


@pytest.mark.unit
class TestModelEventBusOutputStateMonitoringMethods:
    """Test ModelEventBusOutputState monitoring methods."""

    def test_get_monitoring_metrics(self) -> None:
        """Test get_monitoring_metrics returns metrics object."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=100,
        )

        metrics = state.get_monitoring_metrics()

        assert metrics is not None
        assert metrics.response_time_ms == 100.0
        assert metrics.success_rate == 100.0

    def test_get_log_context(self) -> None:
        """Test get_log_context returns context dict."""
        correlation_id = uuid4()

        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            correlation_id=correlation_id,
            processing_time_ms=100,
        )

        context = state.get_log_context()

        assert "status" in context
        assert "correlation_id" in context
        assert context["correlation_id"] == str(correlation_id)

    def test_get_business_impact(self) -> None:
        """Test get_business_impact returns impact assessment."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
        )

        impact = state.get_business_impact()

        assert impact is not None
        assert impact.sla_violated is True


@pytest.mark.unit
class TestModelEventBusOutputStateFactoryMethods:
    """Test ModelEventBusOutputState factory methods."""

    def test_create_success(self) -> None:
        """Test create_success factory method."""
        state = ModelEventBusOutputState.create_success("1.0.0", "Done")

        assert state.status == EnumOnexStatus.SUCCESS
        assert state.message == "Done"

    def test_create_success_with_processing_time(self) -> None:
        """Test create_success with processing_time_ms."""
        state = ModelEventBusOutputState.create_success(
            "1.0.0",
            processing_time_ms=100,
        )

        assert state.processing_time_ms == 100

    def test_create_error(self) -> None:
        """Test create_error factory method."""
        state = ModelEventBusOutputState.create_error(
            "1.0.0",
            "Connection failed",
            error_code="CONNECTION_FAILED",
        )

        assert state.status == EnumOnexStatus.ERROR
        assert state.message == "Connection failed"
        assert state.error_code == "CONNECTION_FAILED"

    def test_create_warning(self) -> None:
        """Test create_warning factory method."""
        state = ModelEventBusOutputState.create_warning(
            "1.0.0",
            "Completed with warnings",
            warnings=["Warning 1", "Warning 2"],
        )

        assert state.status == EnumOnexStatus.WARNING
        assert len(state.warnings or []) == 2

    def test_create_retry(self) -> None:
        """Test create_retry factory method."""
        state = ModelEventBusOutputState.create_retry(
            "1.0.0",
            "Retrying...",
            retry_attempt=2,
        )

        assert state.status == EnumOnexStatus.ERROR
        assert state.retry_attempt == 2
        assert state.next_retry_at is not None

    def test_create_with_tracking(self) -> None:
        """Test create_with_tracking factory method."""
        correlation_id = uuid4()
        event_id = uuid4()

        state = ModelEventBusOutputState.create_with_tracking(
            version="1.0.0",
            status="success",
            message="Done",
            correlation_id=correlation_id,
            event_id=event_id,
        )

        assert state.correlation_id == correlation_id
        assert state.event_id == event_id


@pytest.mark.unit
class TestModelEventBusOutputStateSerialization:
    """Test ModelEventBusOutputState serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump() serialization."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
            processing_time_ms=100,
        )

        data = state.model_dump()

        assert isinstance(data, dict)
        assert data["message"] == "Done"
        assert data["processing_time_ms"] == 100

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "status": "success",
            "message": "Done",
        }

        state = ModelEventBusOutputState.model_validate(data)

        assert state.status == EnumOnexStatus.SUCCESS
        assert state.message == "Done"

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusOutputState(
            version="1.2.3",
            status=EnumOnexStatus.SUCCESS,
            message="Complete",
            processing_time_ms=150,
        )

        data = original.model_dump()
        restored = ModelEventBusOutputState.model_validate(data)

        assert restored.message == original.message
        assert restored.processing_time_ms == original.processing_time_ms

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        json_data = state.model_dump_json()

        assert isinstance(json_data, str)
        assert "message" in json_data


@pytest.mark.unit
class TestModelEventBusOutputStateVersionParsing:
    """Test ModelEventBusOutputState version parsing."""

    def test_version_from_string(self) -> None:
        """Test version parsing from string."""
        state = ModelEventBusOutputState(
            version="2.1.0",
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.version.major == 2
        assert state.version.minor == 1
        assert state.version.patch == 0

    def test_version_from_model_semver(self) -> None:
        """Test version parsing from ModelSemVer."""
        version = ModelSemVer(major=3, minor=0, patch=1)

        state = ModelEventBusOutputState(
            version=version,
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.version == version

    def test_version_from_dict(self) -> None:
        """Test version parsing from dict."""
        state = ModelEventBusOutputState(
            version={"major": 1, "minor": 2, "patch": 3},
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        assert state.version.major == 1
        assert state.version.minor == 2
        assert state.version.patch == 3
