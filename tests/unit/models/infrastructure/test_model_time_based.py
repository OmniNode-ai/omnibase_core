"""
Tests for ModelTimeBased.

Comprehensive tests for the unified time-based model that replaces ModelDuration,
ModelTimeout, and timing aspects of ModelProgress.
"""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.enums.enum_time_unit import EnumTimeUnit
from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.infrastructure.model_time_based import ModelTimeBased


class TestEnumTimeUnit:
    """Test EnumTimeUnit enum."""

    def test_string_representation(self) -> None:
        """Test string representation of time units."""
        assert str(EnumTimeUnit.MILLISECONDS) == "ms"
        assert str(EnumTimeUnit.SECONDS) == "s"
        assert str(EnumTimeUnit.MINUTES) == "m"
        assert str(EnumTimeUnit.HOURS) == "h"
        assert str(EnumTimeUnit.DAYS) == "d"

    def test_display_names(self) -> None:
        """Test display names of time units."""
        assert EnumTimeUnit.MILLISECONDS.display_name == "Milliseconds"
        assert EnumTimeUnit.SECONDS.display_name == "Seconds"
        assert EnumTimeUnit.MINUTES.display_name == "Minutes"
        assert EnumTimeUnit.HOURS.display_name == "Hours"
        assert EnumTimeUnit.DAYS.display_name == "Days"

    def test_milliseconds_multipliers(self) -> None:
        """Test conversion multipliers to milliseconds."""
        assert EnumTimeUnit.MILLISECONDS.to_milliseconds_multiplier() == 1
        assert EnumTimeUnit.SECONDS.to_milliseconds_multiplier() == 1000
        assert EnumTimeUnit.MINUTES.to_milliseconds_multiplier() == 60 * 1000
        assert EnumTimeUnit.HOURS.to_milliseconds_multiplier() == 60 * 60 * 1000
        assert EnumTimeUnit.DAYS.to_milliseconds_multiplier() == 24 * 60 * 60 * 1000


class TestModelTimeBasedBasic:
    """Test basic ModelTimeBased functionality."""

    def test_creation_with_int(self) -> None:
        """Test creation with integer value."""
        time_based = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        assert time_based.value == 30
        assert time_based.unit == EnumTimeUnit.SECONDS
        assert time_based.to_seconds() == 30.0
        assert time_based.to_milliseconds() == 30000

    def test_creation_with_float(self) -> None:
        """Test creation with float value."""
        time_based = ModelTimeBased(value=30.5, unit=EnumTimeUnit.SECONDS)
        assert time_based.value == 30.5
        assert time_based.unit == EnumTimeUnit.SECONDS
        assert time_based.to_seconds() == 30.5
        assert time_based.to_milliseconds() == 30500

    def test_default_unit(self) -> None:
        """Test default unit is seconds."""
        time_based = ModelTimeBased(value=30)
        assert time_based.unit == EnumTimeUnit.SECONDS

    def test_metadata(self) -> None:
        """Test metadata handling."""
        metadata = {"type": "test", "description": "Test duration"}
        time_based = ModelTimeBased(value=30, metadata=metadata)
        assert time_based.metadata == metadata

    def test_runtime_category_auto_assignment(self) -> None:
        """Test automatic runtime category assignment."""
        time_based = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        assert time_based.runtime_category == EnumRuntimeCategory.MODERATE


class TestModelTimeBasedConversions:
    """Test time conversion methods."""

    def test_milliseconds_conversion(self) -> None:
        """Test conversion to milliseconds."""
        test_cases = [
            (1500, EnumTimeUnit.MILLISECONDS, 1500),
            (1.5, EnumTimeUnit.SECONDS, 1500),
            (0.5, EnumTimeUnit.MINUTES, 30000),
            (1, EnumTimeUnit.HOURS, 3600000),
            (0.5, EnumTimeUnit.DAYS, 43200000),
        ]

        for value, unit, expected_ms in test_cases:
            time_based = ModelTimeBased(value=value, unit=unit)
            assert time_based.to_milliseconds() == expected_ms

    def test_seconds_conversion(self) -> None:
        """Test conversion to seconds."""
        test_cases = [
            (1500, EnumTimeUnit.MILLISECONDS, 1.5),
            (30, EnumTimeUnit.SECONDS, 30.0),
            (2, EnumTimeUnit.MINUTES, 120.0),
            (1, EnumTimeUnit.HOURS, 3600.0),
            (1, EnumTimeUnit.DAYS, 86400.0),
        ]

        for value, unit, expected_seconds in test_cases:
            time_based = ModelTimeBased(value=value, unit=unit)
            assert time_based.to_seconds() == expected_seconds

    def test_minutes_conversion(self) -> None:
        """Test conversion to minutes."""
        time_based = ModelTimeBased(value=90, unit=EnumTimeUnit.SECONDS)
        assert time_based.to_minutes() == 1.5

        time_based = ModelTimeBased(value=2, unit=EnumTimeUnit.HOURS)
        assert time_based.to_minutes() == 120.0

    def test_hours_conversion(self) -> None:
        """Test conversion to hours."""
        time_based = ModelTimeBased(value=90, unit=EnumTimeUnit.MINUTES)
        assert time_based.to_hours() == 1.5

        time_based = ModelTimeBased(value=2, unit=EnumTimeUnit.DAYS)
        assert time_based.to_hours() == 48.0

    def test_days_conversion(self) -> None:
        """Test conversion to days."""
        time_based = ModelTimeBased(value=36, unit=EnumTimeUnit.HOURS)
        assert time_based.to_days() == 1.5

    def test_timedelta_conversion(self) -> None:
        """Test conversion to timedelta."""
        time_based = ModelTimeBased(value=90, unit=EnumTimeUnit.SECONDS)
        delta = time_based.to_timedelta()
        assert isinstance(delta, timedelta)
        assert delta.total_seconds() == 90.0


class TestModelTimeBasedValidation:
    """Test validation features."""

    def test_warning_threshold_validation(self) -> None:
        """Test warning threshold validation."""
        # Valid warning threshold
        time_based = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            warning_threshold_value=45,
        )
        assert time_based.warning_threshold_value == 45

        # Invalid warning threshold (greater than main value)
        with pytest.raises(
            OnexError,
            match="Warning threshold must be less than main value",
        ):
            ModelTimeBased(
                value=60,
                unit=EnumTimeUnit.SECONDS,
                warning_threshold_value=70,
            )

    def test_extension_limit_validation(self) -> None:
        """Test extension limit validation."""
        # Valid extension limit with extension allowed
        time_based = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            allow_extension=True,
            extension_limit_value=30,
        )
        assert time_based.extension_limit_value == 30

        # Invalid extension limit without extension allowed
        with pytest.raises(
            OnexError,
            match="Extension limit requires allow_extension=True",
        ):
            ModelTimeBased(
                value=60,
                unit=EnumTimeUnit.SECONDS,
                allow_extension=False,
                extension_limit_value=30,
            )


class TestModelTimeBasedProperties:
    """Test property methods."""

    def test_is_zero(self) -> None:
        """Test is_zero property."""
        zero_time = ModelTimeBased(value=0, unit=EnumTimeUnit.SECONDS)
        assert zero_time.is_zero() is True

        non_zero_time = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        assert non_zero_time.is_zero() is False

    def test_is_positive(self) -> None:
        """Test is_positive property."""
        zero_time = ModelTimeBased(value=0, unit=EnumTimeUnit.SECONDS)
        assert zero_time.is_positive() is False

        positive_time = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        assert positive_time.is_positive() is True

    def test_string_representation(self) -> None:
        """Test string representation."""
        # Zero time
        zero_time = ModelTimeBased(value=0, unit=EnumTimeUnit.SECONDS)
        assert str(zero_time) == "0s"

        # Simple seconds
        simple_time = ModelTimeBased(value=45, unit=EnumTimeUnit.SECONDS)
        assert str(simple_time) == "45s"

        # Complex time (1 hour, 30 minutes, 45 seconds)
        complex_time = ModelTimeBased(value=5445, unit=EnumTimeUnit.SECONDS)
        assert str(complex_time) == "1h30m45s"

        # With milliseconds
        ms_time = ModelTimeBased(value=1500, unit=EnumTimeUnit.MILLISECONDS)
        assert str(ms_time) == "1s500ms"


class TestModelTimeBasedTimeout:
    """Test timeout-specific functionality."""

    def test_get_deadline(self) -> None:
        """Test deadline calculation."""
        timeout = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        expected_deadline = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)

        deadline = timeout.get_deadline(start_time)
        assert deadline == expected_deadline

    def test_get_warning_time(self) -> None:
        """Test warning time calculation."""
        timeout = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            warning_threshold_value=45,
        )
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        expected_warning = datetime(2024, 1, 1, 12, 0, 45, tzinfo=UTC)

        warning_time = timeout.get_warning_time(start_time)
        assert warning_time == expected_warning

    def test_get_warning_time_none(self) -> None:
        """Test warning time when no threshold set."""
        timeout = ModelTimeBased(value=60, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        warning_time = timeout.get_warning_time(start_time)
        assert warning_time is None

    def test_is_expired(self) -> None:
        """Test expiration checking."""
        timeout = ModelTimeBased(value=30, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Not expired
        current_time = datetime(2024, 1, 1, 12, 0, 20, tzinfo=UTC)
        assert timeout.is_expired(start_time, current_time) is False

        # Expired
        current_time = datetime(2024, 1, 1, 12, 0, 35, tzinfo=UTC)
        assert timeout.is_expired(start_time, current_time) is True

    def test_is_warning_triggered(self) -> None:
        """Test warning trigger checking."""
        timeout = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            warning_threshold_value=45,
        )
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Warning not triggered
        current_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        assert timeout.is_warning_triggered(start_time, current_time) is False

        # Warning triggered
        current_time = datetime(2024, 1, 1, 12, 0, 50, tzinfo=UTC)
        assert timeout.is_warning_triggered(start_time, current_time) is True

    def test_get_remaining_seconds(self) -> None:
        """Test remaining seconds calculation."""
        timeout = ModelTimeBased(value=60, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # 20 seconds remaining
        current_time = datetime(2024, 1, 1, 12, 0, 40, tzinfo=UTC)
        remaining = timeout.get_remaining_seconds(start_time, current_time)
        assert remaining == 20.0

        # Already expired
        current_time = datetime(2024, 1, 1, 12, 1, 10, tzinfo=UTC)
        remaining = timeout.get_remaining_seconds(start_time, current_time)
        assert remaining == 0.0

    def test_get_elapsed_seconds(self) -> None:
        """Test elapsed seconds calculation."""
        timeout = ModelTimeBased(value=60, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = datetime(2024, 1, 1, 12, 0, 35, tzinfo=UTC)

        elapsed = timeout.get_elapsed_seconds(start_time, current_time)
        assert elapsed == 35.0

    def test_get_progress_percentage(self) -> None:
        """Test progress percentage calculation."""
        timeout = ModelTimeBased(value=60, unit=EnumTimeUnit.SECONDS)
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        # 50% progress
        current_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        progress = timeout.get_progress_percentage(start_time, current_time)
        assert progress == 50.0

        # Over 100% (capped at 100)
        current_time = datetime(2024, 1, 1, 12, 1, 30, tzinfo=UTC)
        progress = timeout.get_progress_percentage(start_time, current_time)
        assert progress == 100.0

    def test_extend_time(self) -> None:
        """Test time extension."""
        # Extension allowed
        timeout = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            allow_extension=True,
            extension_limit_value=30,
        )

        # Valid extension
        result = timeout.extend_time(20)
        assert result is True
        assert timeout.value == 80

        # Another valid extension (individual extension <= limit)
        result = timeout.extend_time(25)  # 25 <= 30, so allowed
        assert result is True
        assert timeout.value == 105

        # Extension exceeds individual limit
        result = timeout.extend_time(35)  # 35 > 30, so not allowed
        assert result is False
        assert timeout.value == 105  # Unchanged

        # Extension not allowed
        timeout_no_ext = ModelTimeBased(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            allow_extension=False,
        )
        result = timeout_no_ext.extend_time(10)
        assert result is False


class TestModelTimeBasedFactoryMethods:
    """Test factory and class methods."""

    def test_duration_factory(self) -> None:
        """Test duration factory method."""
        duration = ModelTimeBased.duration(30, EnumTimeUnit.SECONDS, "Test duration")
        assert duration.value == 30
        assert duration.unit == EnumTimeUnit.SECONDS
        assert duration.metadata["type"] == "duration"
        assert duration.metadata["description"] == "Test duration"

    def test_timeout_factory(self) -> None:
        """Test timeout factory method."""
        timeout = ModelTimeBased.timeout(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            description="Test timeout",
            is_strict=False,
            warning_threshold_value=45,
            allow_extension=True,
            extension_limit_value=30,
        )
        assert timeout.value == 60
        assert timeout.unit == EnumTimeUnit.SECONDS
        assert timeout.metadata["type"] == "timeout"
        assert timeout.metadata["description"] == "Test timeout"
        assert timeout.is_strict is False
        assert timeout.warning_threshold_value == 45
        assert timeout.allow_extension is True
        assert timeout.extension_limit_value == 30

    def test_from_milliseconds(self) -> None:
        """Test creation from milliseconds."""
        time_based = ModelTimeBased.from_milliseconds(1500)
        assert time_based.value == 1500
        assert time_based.unit == EnumTimeUnit.MILLISECONDS
        assert time_based.to_seconds() == 1.5

    def test_from_seconds(self) -> None:
        """Test creation from seconds."""
        time_based = ModelTimeBased.from_seconds(30.5)
        assert time_based.value == 30.5
        assert time_based.unit == EnumTimeUnit.SECONDS
        assert time_based.to_seconds() == 30.5

    def test_from_minutes(self) -> None:
        """Test creation from minutes."""
        time_based = ModelTimeBased.from_minutes(2.5)
        assert time_based.value == 2.5
        assert time_based.unit == EnumTimeUnit.MINUTES
        assert time_based.to_seconds() == 150.0

    def test_from_hours(self) -> None:
        """Test creation from hours."""
        time_based = ModelTimeBased.from_hours(1.5)
        assert time_based.value == 1.5
        assert time_based.unit == EnumTimeUnit.HOURS
        assert time_based.to_seconds() == 5400.0

    def test_from_days(self) -> None:
        """Test creation from days."""
        time_based = ModelTimeBased.from_days(2.5)
        assert time_based.value == 2.5
        assert time_based.unit == EnumTimeUnit.DAYS
        assert time_based.to_seconds() == 216000.0

    def test_zero(self) -> None:
        """Test zero factory method."""
        zero_time = ModelTimeBased.zero()
        assert zero_time.value == 0
        assert zero_time.unit == EnumTimeUnit.MILLISECONDS
        assert zero_time.is_zero() is True

    def test_from_timedelta(self) -> None:
        """Test creation from timedelta."""
        delta = timedelta(seconds=90, milliseconds=500)
        time_based = ModelTimeBased.from_timedelta(delta)
        assert time_based.unit == EnumTimeUnit.SECONDS
        assert time_based.to_seconds() == 90.5

    def test_from_runtime_category(self) -> None:
        """Test creation from runtime category."""
        timeout = ModelTimeBased.from_runtime_category(
            EnumRuntimeCategory.FAST,
            description="Fast operation timeout",
        )
        assert timeout.runtime_category == EnumRuntimeCategory.FAST
        assert timeout.metadata["description"] == "Fast operation timeout"
        assert timeout.to_seconds() <= 5  # Fast category max


class TestExplicitGenericTypes:
    """Test explicit generic types instead of type aliases."""

    def test_float_based_duration(self) -> None:
        """Test ModelTimeBased[float] for duration use cases."""
        duration: ModelTimeBased[float] = ModelTimeBased.from_seconds(30.5)
        assert duration.value == 30.5
        assert isinstance(duration.value, float)

    def test_int_based_timeout(self) -> None:
        """Test ModelTimeBased[int] for timeout use cases."""
        timeout: ModelTimeBased[int] = ModelTimeBased.from_seconds(30)
        assert timeout.value == 30
        # Note: Type checking would ensure this is int, but runtime it's float

    def test_int_based_millisecond_duration(self) -> None:
        """Test ModelTimeBased[int] for millisecond duration use cases."""
        ms_duration: ModelTimeBased[int] = ModelTimeBased.from_milliseconds(1500)
        assert ms_duration.value == 1500
        assert isinstance(ms_duration.value, int)


class TestModelTimeBasedEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_large_values(self) -> None:
        """Test handling of very large values."""
        large_time = ModelTimeBased(value=1000000, unit=EnumTimeUnit.SECONDS)
        assert large_time.to_days() > 11  # Over 11 days

    def test_very_small_values(self) -> None:
        """Test handling of very small values."""
        small_time = ModelTimeBased(value=0.001, unit=EnumTimeUnit.SECONDS)
        assert small_time.to_milliseconds() == 1

    def test_runtime_category_update_on_extension(self) -> None:
        """Test runtime category updates when time is extended."""
        timeout = ModelTimeBased(
            value=1,  # FAST category
            unit=EnumTimeUnit.SECONDS,
            allow_extension=True,
            extension_limit_value=300,
        )

        original_category = timeout.runtime_category
        assert original_category == EnumRuntimeCategory.FAST

        # Extend to STANDARD category range
        timeout.extend_time(120)  # Now 121 seconds
        assert timeout.runtime_category == EnumRuntimeCategory.STANDARD


class TestModelTimeBasedIntegration:
    """Integration tests with other components."""

    def test_compatibility_with_datetime_operations(self) -> None:
        """Test compatibility with datetime operations."""
        timeout = ModelTimeBased.from_minutes(5)
        start_time = datetime.now(UTC)

        # Should work with datetime arithmetic
        deadline = start_time + timeout.to_timedelta()
        assert isinstance(deadline, datetime)
        assert deadline > start_time

    def test_serialization_compatibility(self) -> None:
        """Test serialization works correctly."""
        timeout = ModelTimeBased.timeout(
            value=60,
            unit=EnumTimeUnit.SECONDS,
            description="Test timeout",
            warning_threshold_value=45,
        )

        # Should be serializable
        data = timeout.model_dump()
        assert isinstance(data, dict)
        assert "value" in data
        assert "unit" in data
        assert "metadata" in data
        assert "warning_threshold_value" in data

    def test_multiple_time_units_consistency(self) -> None:
        """Test consistency across different time units."""
        # Same duration in different units should convert to same values
        one_hour_seconds = ModelTimeBased(value=3600, unit=EnumTimeUnit.SECONDS)
        one_hour_minutes = ModelTimeBased(value=60, unit=EnumTimeUnit.MINUTES)
        one_hour_hours = ModelTimeBased(value=1, unit=EnumTimeUnit.HOURS)

        assert one_hour_seconds.to_seconds() == one_hour_minutes.to_seconds()
        assert one_hour_minutes.to_seconds() == one_hour_hours.to_seconds()
        assert one_hour_seconds.to_milliseconds() == one_hour_hours.to_milliseconds()
