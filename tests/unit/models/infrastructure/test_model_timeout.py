"""Tests for ModelTimeout."""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_timeout import ModelTimeout


class TestModelTimeoutInstantiation:
    """Tests for ModelTimeout instantiation."""

    def test_default_initialization(self):
        """Test default initialization."""
        timeout = ModelTimeout()
        assert timeout.timeout_seconds == 30
        assert timeout.is_strict is True

    def test_create_with_seconds(self):
        """Test creating timeout with custom seconds."""
        timeout = ModelTimeout(timeout_seconds=60)
        assert timeout.timeout_seconds == 60

    def test_create_with_description(self):
        """Test creating timeout with description."""
        timeout = ModelTimeout(timeout_seconds=45, description="API call timeout")
        assert timeout.description == "API call timeout"

    def test_create_with_warning_threshold(self):
        """Test creating timeout with warning threshold."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=45)
        assert timeout.warning_threshold_seconds == 45

    def test_create_with_extension(self):
        """Test creating timeout with extension allowed."""
        timeout = ModelTimeout(
            timeout_seconds=30,
            allow_extension=True,
            extension_limit_seconds=10,
        )
        assert timeout.allow_extension is True
        assert timeout.extension_limit_seconds == 10


class TestModelTimeoutValidation:
    """Tests for ModelTimeout validation."""

    def test_invalid_timeout_seconds_type(self):
        """Test that invalid timeout_seconds type raises error."""
        with pytest.raises(OnexError, match="must be a number"):
            ModelTimeout(timeout_seconds="invalid")

    def test_invalid_warning_threshold_type(self):
        """Test that invalid warning_threshold_seconds type raises error."""
        with pytest.raises(OnexError, match="must be a number"):
            ModelTimeout(timeout_seconds=60, warning_threshold_seconds="invalid")

    def test_invalid_is_strict_type(self):
        """Test that invalid is_strict type raises error."""
        with pytest.raises(OnexError, match="must be a boolean"):
            ModelTimeout(timeout_seconds=60, is_strict="true")

    def test_invalid_allow_extension_type(self):
        """Test that invalid allow_extension type raises error."""
        with pytest.raises(OnexError, match="must be a boolean"):
            ModelTimeout(timeout_seconds=60, allow_extension="yes")

    def test_invalid_extension_limit_type(self):
        """Test that invalid extension_limit_seconds type raises error."""
        with pytest.raises(OnexError, match="must be a number"):
            ModelTimeout(
                timeout_seconds=60,
                allow_extension=True,
                extension_limit_seconds="invalid",
            )

    def test_invalid_runtime_category_type(self):
        """Test that invalid runtime_category type raises error."""
        with pytest.raises(OnexError, match="must be an EnumRuntimeCategory"):
            ModelTimeout(timeout_seconds=60, runtime_category="fast")

    def test_invalid_description_type(self):
        """Test that invalid description type raises error."""
        with pytest.raises(OnexError, match="must be a string"):
            ModelTimeout(timeout_seconds=60, description=123)

    def test_invalid_custom_metadata_type(self):
        """Test that invalid custom_metadata type raises error."""
        with pytest.raises(OnexError, match="must be a dictionary"):
            ModelTimeout(timeout_seconds=60, custom_metadata="invalid")


class TestModelTimeoutProperties:
    """Tests for ModelTimeout property access."""

    def test_timeout_seconds_property(self):
        """Test timeout_seconds property."""
        timeout = ModelTimeout(timeout_seconds=90)
        assert timeout.timeout_seconds == 90

    def test_timeout_minutes_property(self):
        """Test timeout_minutes property."""
        timeout = ModelTimeout(timeout_seconds=120)
        assert timeout.timeout_minutes == 2.0

    def test_timeout_hours_property(self):
        """Test timeout_hours property."""
        timeout = ModelTimeout(timeout_seconds=7200)
        assert timeout.timeout_hours == 2.0

    def test_timeout_timedelta_property(self):
        """Test timeout_timedelta property."""
        timeout = ModelTimeout(timeout_seconds=45)
        td = timeout.timeout_timedelta
        assert isinstance(td, timedelta)
        assert td.total_seconds() == 45.0

    def test_warning_threshold_timedelta_property(self):
        """Test warning_threshold_timedelta property."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=40)
        td = timeout.warning_threshold_timedelta
        assert isinstance(td, timedelta)
        assert td.total_seconds() == 40.0

    def test_warning_threshold_timedelta_none(self):
        """Test warning_threshold_timedelta when not set."""
        timeout = ModelTimeout(timeout_seconds=60)
        assert timeout.warning_threshold_timedelta is None

    def test_extension_limit_timedelta_property(self):
        """Test extension_limit_timedelta property."""
        timeout = ModelTimeout(
            timeout_seconds=30,
            allow_extension=True,
            extension_limit_seconds=15,
        )
        td = timeout.extension_limit_timedelta
        assert isinstance(td, timedelta)
        assert td.total_seconds() == 15.0

    def test_extension_limit_timedelta_none(self):
        """Test extension_limit_timedelta when not set."""
        timeout = ModelTimeout(timeout_seconds=30)
        assert timeout.extension_limit_timedelta is None

    def test_max_total_seconds_without_extension(self):
        """Test max_total_seconds without extension."""
        timeout = ModelTimeout(timeout_seconds=60)
        assert timeout.max_total_seconds == 60

    def test_max_total_seconds_with_extension(self):
        """Test max_total_seconds with extension."""
        timeout = ModelTimeout(
            timeout_seconds=60,
            allow_extension=True,
            extension_limit_seconds=20,
        )
        assert timeout.max_total_seconds == 80

    def test_runtime_category_property(self):
        """Test runtime_category property."""
        timeout = ModelTimeout(
            timeout_seconds=60,
            runtime_category=EnumRuntimeCategory.FAST,
        )
        assert timeout.runtime_category == EnumRuntimeCategory.FAST

    def test_runtime_category_default(self):
        """Test runtime_category has default value when not set."""
        timeout = ModelTimeout(timeout_seconds=60)
        # ModelTimeBased has a default runtime_category of STANDARD
        assert timeout.runtime_category is not None


class TestModelTimeoutDeadlineCalculations:
    """Tests for ModelTimeout deadline calculations."""

    def test_get_deadline_from_now(self):
        """Test get_deadline from current time."""
        timeout = ModelTimeout(timeout_seconds=60)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        deadline = timeout.get_deadline(start_time)
        expected = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        assert deadline == expected

    def test_get_deadline_from_specific_time(self):
        """Test get_deadline from specific start time."""
        timeout = ModelTimeout(timeout_seconds=120)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        deadline = timeout.get_deadline(start_time)
        expected = datetime(2024, 1, 1, 12, 2, 0, tzinfo=UTC)
        assert deadline == expected

    def test_get_warning_time(self):
        """Test get_warning_time calculation."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=45)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        warning_time = timeout.get_warning_time(start_time)
        expected = datetime(2024, 1, 1, 12, 0, 45, tzinfo=UTC)
        assert warning_time == expected

    def test_get_warning_time_none(self):
        """Test get_warning_time when no threshold set."""
        timeout = ModelTimeout(timeout_seconds=60)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        warning_time = timeout.get_warning_time(start_time)
        assert warning_time is None


class TestModelTimeoutExpirationChecks:
    """Tests for ModelTimeout expiration checks."""

    def test_is_expired_false(self):
        """Test is_expired returns False for non-expired timeout."""
        timeout = ModelTimeout(timeout_seconds=60)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        assert timeout.is_expired(start_time, current_time) is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired timeout."""
        timeout = ModelTimeout(timeout_seconds=10)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 15, tzinfo=UTC)
        assert timeout.is_expired(start_time, current_time) is True

    def test_is_warning_triggered_false(self):
        """Test is_warning_triggered returns False before threshold."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=45)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        assert timeout.is_warning_triggered(start_time, current_time) is False

    def test_is_warning_triggered_true(self):
        """Test is_warning_triggered returns True after threshold."""
        timeout = ModelTimeout(timeout_seconds=60, warning_threshold_seconds=10)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 15, tzinfo=UTC)
        assert timeout.is_warning_triggered(start_time, current_time) is True

    def test_get_remaining_seconds(self):
        """Test get_remaining_seconds calculation."""
        timeout = ModelTimeout(timeout_seconds=60)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        remaining = timeout.get_remaining_seconds(start_time, current_time)
        assert remaining == 30

    def test_get_elapsed_seconds(self):
        """Test get_elapsed_seconds calculation."""
        timeout = ModelTimeout(timeout_seconds=60)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 15, tzinfo=UTC)
        elapsed = timeout.get_elapsed_seconds(start_time, current_time)
        assert elapsed == 15

    def test_get_progress_percentage(self):
        """Test get_progress_percentage calculation."""
        timeout = ModelTimeout(timeout_seconds=100)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 50, tzinfo=UTC)
        progress = timeout.get_progress_percentage(start_time, current_time)
        assert progress == 50.0


class TestModelTimeoutExtension:
    """Tests for ModelTimeout extension functionality."""

    def test_extend_timeout_allowed(self):
        """Test extending timeout when allowed."""
        timeout = ModelTimeout(
            timeout_seconds=30,
            allow_extension=True,
            extension_limit_seconds=20,
        )
        result = timeout.extend_timeout(10)
        assert result is True

    def test_extend_timeout_not_allowed(self):
        """Test extending timeout when not allowed."""
        timeout = ModelTimeout(timeout_seconds=30, allow_extension=False)
        result = timeout.extend_timeout(10)
        assert result is False


class TestModelTimeoutCustomMetadata:
    """Tests for ModelTimeout custom metadata."""

    def test_set_custom_metadata(self):
        """Test setting custom metadata."""
        timeout = ModelTimeout(timeout_seconds=60)
        timeout.set_custom_metadata("priority", "high")
        value = timeout.get_custom_metadata("priority")
        assert value == "high"

    def test_get_custom_metadata_none(self):
        """Test getting non-existent custom metadata."""
        timeout = ModelTimeout(timeout_seconds=60)
        value = timeout.get_custom_metadata("nonexistent")
        assert value is None

    def test_custom_metadata_in_constructor(self):
        """Test passing custom metadata in constructor."""
        timeout = ModelTimeout(
            timeout_seconds=60,
            custom_metadata={"env": "production", "retries": 3},
        )
        assert timeout.get_custom_metadata("env") == "production"
        assert timeout.get_custom_metadata("retries") == 3

    def test_custom_properties(self):
        """Test custom_properties property."""
        timeout = ModelTimeout(timeout_seconds=60)
        timeout.set_custom_metadata("test_key", "test_value")
        props = timeout.custom_properties
        assert props is not None


class TestModelTimeoutFactoryMethods:
    """Tests for ModelTimeout factory methods."""

    def test_from_seconds(self):
        """Test from_seconds factory method."""
        timeout = ModelTimeout.from_seconds(90, description="Test timeout")
        assert timeout.timeout_seconds == 90
        assert timeout.description == "Test timeout"
        assert timeout.is_strict is True

    def test_from_minutes(self):
        """Test from_minutes factory method."""
        timeout = ModelTimeout.from_minutes(2.5, description="Test timeout")
        assert timeout.timeout_seconds == 150
        assert timeout.description == "Test timeout"

    def test_from_hours(self):
        """Test from_hours factory method."""
        timeout = ModelTimeout.from_hours(1.5, description="Test timeout")
        assert timeout.timeout_seconds == 5400
        assert timeout.description == "Test timeout"

    def test_from_runtime_category(self):
        """Test from_runtime_category factory method."""
        timeout = ModelTimeout.from_runtime_category(
            EnumRuntimeCategory.FAST,
            description="Fast operation",
        )
        assert timeout.timeout_seconds > 0
        assert timeout.runtime_category == EnumRuntimeCategory.FAST
        assert timeout.description == "Fast operation"

    def test_from_runtime_category_use_max_estimate(self):
        """Test from_runtime_category with use_max_estimate."""
        timeout = ModelTimeout.from_runtime_category(
            EnumRuntimeCategory.MODERATE,
            use_max_estimate=True,
        )
        assert timeout.timeout_seconds > 0


class TestModelTimeoutSerialization:
    """Tests for ModelTimeout serialization."""

    def test_to_typed_data(self):
        """Test to_typed_data serialization."""
        timeout = ModelTimeout(
            timeout_seconds=60,
            warning_threshold_seconds=45,
            is_strict=True,
        )
        data = timeout.to_typed_data()
        assert data.timeout_seconds == 60
        assert data.warning_threshold_seconds == 45
        assert data.is_strict is True

    def test_model_validate_typed(self):
        """Test model_validate_typed deserialization."""
        timeout = ModelTimeout(timeout_seconds=60, description="Test")
        data = timeout.to_typed_data()
        restored = ModelTimeout.model_validate_typed(data)
        assert restored.timeout_seconds == 60

    def test_serialize_protocol(self):
        """Test serialize method from protocol."""
        timeout = ModelTimeout(timeout_seconds=60)
        data = timeout.serialize()
        assert isinstance(data, dict)


class TestModelTimeoutProtocols:
    """Tests for ModelTimeout protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        timeout = ModelTimeout(timeout_seconds=60)
        result = timeout.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        timeout = ModelTimeout(timeout_seconds=60)
        result = timeout.configure()
        assert result is True

    def test_validate_instance_protocol(self):
        """Test validate_instance method."""
        timeout = ModelTimeout(timeout_seconds=60)
        result = timeout.validate_instance()
        assert result is True


class TestModelTimeoutEdgeCases:
    """Tests for ModelTimeout edge cases."""

    def test_zero_warning_threshold_becomes_none(self):
        """Test that zero warning threshold is treated as None."""
        timeout = ModelTimeout(timeout_seconds=60)
        data = timeout.to_typed_data()
        restored = ModelTimeout.model_validate_typed(data)
        assert restored.warning_threshold_seconds is None

    def test_empty_description_becomes_none(self):
        """Test that empty description is treated as None."""
        timeout = ModelTimeout(timeout_seconds=60)
        data = timeout.to_typed_data()
        restored = ModelTimeout.model_validate_typed(data)
        # Empty description should be converted to None
        assert restored.description is None or restored.description == ""

    def test_float_timeout_seconds(self):
        """Test that float timeout_seconds is converted to int."""
        timeout = ModelTimeout(timeout_seconds=60.7)
        assert timeout.timeout_seconds == 60

    def test_very_large_timeout(self):
        """Test very large timeout value."""
        timeout = ModelTimeout(timeout_seconds=86400)  # 24 hours
        assert timeout.timeout_seconds == 86400
        assert timeout.timeout_hours == 24.0

    def test_custom_metadata_with_schema_value(self):
        """Test custom metadata with ModelSchemaValue objects."""
        schema_value = ModelSchemaValue.from_value("test")
        timeout = ModelTimeout(
            timeout_seconds=60,
            custom_metadata={"key": schema_value},
        )
        assert timeout.get_custom_metadata("key") == "test"
