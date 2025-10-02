"""Tests for ModelDuration."""

import pytest

from omnibase_core.enums.enum_time_unit import EnumTimeUnit
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.models.infrastructure.model_duration import ModelDuration


class TestModelDurationInstantiation:
    """Tests for ModelDuration instantiation."""

    def test_create_from_milliseconds(self):
        """Test creating duration from milliseconds."""
        duration = ModelDuration(milliseconds=5000)
        assert duration.milliseconds == 5000
        assert duration.total_milliseconds() == 5000

    def test_create_from_seconds(self):
        """Test creating duration from seconds."""
        duration = ModelDuration(seconds=5)
        assert duration.total_seconds() == 5.0
        assert duration.milliseconds == 5000

    def test_create_from_minutes(self):
        """Test creating duration from minutes."""
        duration = ModelDuration(minutes=2)
        assert duration.total_minutes() == 2.0
        assert duration.milliseconds == 120000

    def test_create_from_hours(self):
        """Test creating duration from hours."""
        duration = ModelDuration(hours=1)
        assert duration.total_hours() == 1.0
        assert duration.milliseconds == 3600000

    def test_create_from_days(self):
        """Test creating duration from days."""
        duration = ModelDuration(days=1)
        assert duration.total_days() == 1.0
        assert duration.milliseconds == 86400000

    def test_default_initialization(self):
        """Test default initialization creates zero duration."""
        duration = ModelDuration()
        assert duration.milliseconds == 0
        assert duration.is_zero()


class TestModelDurationFactoryMethods:
    """Tests for ModelDuration factory methods."""

    def test_from_milliseconds(self):
        """Test from_milliseconds factory method."""
        duration = ModelDuration.from_milliseconds(1500)
        assert duration.milliseconds == 1500

    def test_from_seconds(self):
        """Test from_seconds factory method."""
        duration = ModelDuration.from_seconds(3.5)
        assert duration.total_seconds() == 3.5
        assert duration.milliseconds == 3500

    def test_from_minutes(self):
        """Test from_minutes factory method."""
        duration = ModelDuration.from_minutes(1.5)
        assert duration.total_minutes() == 1.5
        assert duration.milliseconds == 90000

    def test_from_hours(self):
        """Test from_hours factory method."""
        duration = ModelDuration.from_hours(0.5)
        assert duration.total_hours() == 0.5
        assert duration.milliseconds == 1800000

    def test_zero(self):
        """Test zero factory method."""
        duration = ModelDuration.zero()
        assert duration.is_zero()
        assert duration.milliseconds == 0


class TestModelDurationConversions:
    """Tests for ModelDuration time unit conversions."""

    def test_to_seconds(self):
        """Test conversion to seconds."""
        duration = ModelDuration(milliseconds=5000)
        assert duration.total_seconds() == 5.0

    def test_to_minutes(self):
        """Test conversion to minutes."""
        duration = ModelDuration(seconds=120)
        assert duration.total_minutes() == 2.0

    def test_to_hours(self):
        """Test conversion to hours."""
        duration = ModelDuration(minutes=90)
        assert duration.total_hours() == 1.5

    def test_to_days(self):
        """Test conversion to days."""
        duration = ModelDuration(hours=48)
        assert duration.total_days() == 2.0

    def test_fractional_conversions(self):
        """Test fractional time conversions."""
        duration = ModelDuration(milliseconds=1500)
        assert duration.total_seconds() == 1.5
        assert duration.total_minutes() == 0.025
        assert duration.total_hours() == pytest.approx(0.0004166666)


class TestModelDurationValidation:
    """Tests for ModelDuration validation."""

    def test_invalid_milliseconds_type(self):
        """Test that non-numeric milliseconds raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelDuration(milliseconds="invalid")
        assert "must be a number" in str(exc_info.value)

    def test_invalid_seconds_type(self):
        """Test that non-numeric seconds raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelDuration(seconds="invalid")
        assert "must be a number" in str(exc_info.value)

    def test_invalid_minutes_type(self):
        """Test that non-numeric minutes raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelDuration(minutes="invalid")
        assert "must be a number" in str(exc_info.value)

    def test_invalid_hours_type(self):
        """Test that non-numeric hours raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelDuration(hours=[1, 2, 3])
        assert "must be a number" in str(exc_info.value)

    def test_invalid_days_type(self):
        """Test that non-numeric days raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelDuration(days={"days": 1})
        assert "must be a number" in str(exc_info.value)


class TestModelDurationProperties:
    """Tests for ModelDuration properties and methods."""

    def test_is_zero(self):
        """Test is_zero for zero duration."""
        duration = ModelDuration.zero()
        assert duration.is_zero() is True

    def test_is_not_zero(self):
        """Test is_zero for non-zero duration."""
        duration = ModelDuration(seconds=1)
        assert duration.is_zero() is False

    def test_is_positive(self):
        """Test is_positive for positive duration."""
        duration = ModelDuration(seconds=5)
        assert duration.is_positive() is True

    def test_is_positive_zero(self):
        """Test is_positive for zero duration."""
        duration = ModelDuration.zero()
        assert duration.is_positive() is False

    def test_get_time_based(self):
        """Test get_time_based returns underlying model."""
        duration = ModelDuration(seconds=10)
        time_based = duration.get_time_based()
        assert time_based is not None
        assert time_based.unit == EnumTimeUnit.MILLISECONDS


class TestModelDurationSerialization:
    """Tests for ModelDuration serialization."""

    def test_model_dump(self):
        """Test model_dump serialization."""
        duration = ModelDuration(seconds=5)
        data = duration.model_dump()
        assert data == {"milliseconds": 5000}

    def test_serialize_protocol(self):
        """Test serialize method from protocol."""
        duration = ModelDuration(minutes=2)
        data = duration.serialize()
        assert "milliseconds" in data
        assert data["milliseconds"] == 120000


class TestModelDurationProtocols:
    """Tests for ModelDuration protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        duration = ModelDuration(seconds=5)
        result = duration.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        duration = ModelDuration(seconds=5)
        result = duration.configure()
        assert result is True

    def test_str_representation(self):
        """Test string representation."""
        duration = ModelDuration(seconds=5)
        str_repr = str(duration)
        assert str_repr is not None
        assert len(str_repr) > 0


class TestModelDurationEdgeCases:
    """Tests for ModelDuration edge cases."""

    def test_float_milliseconds(self):
        """Test creating duration with float milliseconds."""
        duration = ModelDuration(milliseconds=1500.5)
        assert duration.milliseconds == 1500

    def test_float_seconds(self):
        """Test creating duration with float seconds."""
        duration = ModelDuration(seconds=1.5)
        assert duration.total_seconds() == 1.5
        assert duration.milliseconds == 1500

    def test_zero_milliseconds(self):
        """Test creating duration with zero milliseconds."""
        duration = ModelDuration(milliseconds=0)
        assert duration.is_zero()

    def test_large_duration(self):
        """Test creating large duration."""
        duration = ModelDuration(days=365)
        assert duration.total_days() == 365.0
        assert duration.milliseconds == 365 * 24 * 60 * 60 * 1000

    def test_very_small_duration(self):
        """Test creating very small duration."""
        duration = ModelDuration(milliseconds=1)
        assert duration.milliseconds == 1
        assert duration.total_seconds() == 0.001
