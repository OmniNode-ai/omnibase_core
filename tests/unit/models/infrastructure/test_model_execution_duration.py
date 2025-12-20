"""Tests for ModelExecutionDuration."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.infrastructure.model_execution_duration import (
    ModelExecutionDuration,
)


@pytest.mark.unit
class TestModelExecutionDurationInstantiation:
    """Tests for ModelExecutionDuration instantiation."""

    def test_default_initialization(self):
        """Test default initialization creates zero duration."""
        duration = ModelExecutionDuration()
        assert duration.milliseconds == 0

    def test_create_with_milliseconds(self):
        """Test creating duration with milliseconds."""
        duration = ModelExecutionDuration(milliseconds=5000)
        assert duration.milliseconds == 5000

    def test_create_with_zero(self):
        """Test creating duration with zero milliseconds."""
        duration = ModelExecutionDuration(milliseconds=0)
        assert duration.milliseconds == 0

    def test_validation_negative_milliseconds(self):
        """Test that negative milliseconds raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionDuration(milliseconds=-100)
        assert "greater than or equal to 0" in str(exc_info.value)


@pytest.mark.unit
class TestModelExecutionDurationConversions:
    """Tests for ModelExecutionDuration time conversions."""

    def test_total_milliseconds(self):
        """Test total_milliseconds method."""
        duration = ModelExecutionDuration(milliseconds=3500)
        assert duration.total_milliseconds() == 3500

    def test_total_seconds_from_milliseconds(self):
        """Test total_seconds conversion."""
        duration = ModelExecutionDuration(milliseconds=5000)
        assert duration.total_seconds() == 5.0

    def test_total_seconds_fractional(self):
        """Test total_seconds with fractional result."""
        duration = ModelExecutionDuration(milliseconds=1500)
        assert duration.total_seconds() == 1.5

    def test_total_seconds_zero(self):
        """Test total_seconds for zero duration."""
        duration = ModelExecutionDuration(milliseconds=0)
        assert duration.total_seconds() == 0.0


@pytest.mark.unit
class TestModelExecutionDurationStringRepresentation:
    """Tests for ModelExecutionDuration string representation."""

    def test_str_zero_milliseconds(self):
        """Test string representation for zero milliseconds."""
        duration = ModelExecutionDuration(milliseconds=0)
        assert str(duration) == "0ms"

    def test_str_milliseconds_only(self):
        """Test string representation for milliseconds only."""
        duration = ModelExecutionDuration(milliseconds=500)
        assert str(duration) == "500ms"

    def test_str_seconds_only(self):
        """Test string representation for seconds."""
        duration = ModelExecutionDuration(milliseconds=5000)
        assert str(duration) == "5.0s"

    def test_str_fractional_seconds(self):
        """Test string representation for fractional seconds."""
        duration = ModelExecutionDuration(milliseconds=2500)
        assert str(duration) == "2.5s"

    def test_str_minutes_and_seconds(self):
        """Test string representation for minutes and seconds."""
        duration = ModelExecutionDuration(milliseconds=125000)  # 2m 5s
        result = str(duration)
        assert result.startswith("2m")
        assert "5.0s" in result

    def test_str_exact_minute(self):
        """Test string representation for exact minute."""
        duration = ModelExecutionDuration(milliseconds=60000)  # 1m 0s
        result = str(duration)
        assert result.startswith("1m")

    def test_str_multiple_minutes(self):
        """Test string representation for multiple minutes."""
        duration = ModelExecutionDuration(milliseconds=180000)  # 3m 0s
        result = str(duration)
        assert result.startswith("3m")


@pytest.mark.unit
class TestModelExecutionDurationSerialization:
    """Tests for ModelExecutionDuration serialization."""

    def test_model_dump(self):
        """Test model_dump serialization."""
        duration = ModelExecutionDuration(milliseconds=3000)
        data = duration.model_dump()
        assert data["milliseconds"] == 3000

    def test_model_dump_zero(self):
        """Test model_dump for zero duration."""
        duration = ModelExecutionDuration()
        data = duration.model_dump()
        assert data["milliseconds"] == 0

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        duration = ModelExecutionDuration(milliseconds=1000)
        data = duration.model_dump(exclude_none=True)
        assert "milliseconds" in data


@pytest.mark.unit
class TestModelExecutionDurationEdgeCases:
    """Tests for ModelExecutionDuration edge cases."""

    def test_very_large_duration(self):
        """Test very large duration value."""
        duration = ModelExecutionDuration(milliseconds=86400000)  # 24 hours
        assert duration.total_seconds() == 86400.0
        assert duration.total_milliseconds() == 86400000

    def test_one_millisecond(self):
        """Test single millisecond duration."""
        duration = ModelExecutionDuration(milliseconds=1)
        assert duration.total_milliseconds() == 1
        assert duration.total_seconds() == 0.001

    def test_boundary_999_milliseconds(self):
        """Test boundary at 999 milliseconds."""
        duration = ModelExecutionDuration(milliseconds=999)
        assert str(duration) == "999ms"

    def test_boundary_1000_milliseconds(self):
        """Test boundary at 1000 milliseconds."""
        duration = ModelExecutionDuration(milliseconds=1000)
        assert str(duration) == "1.0s"

    def test_boundary_59999_milliseconds(self):
        """Test boundary just under 1 minute."""
        duration = ModelExecutionDuration(milliseconds=59999)
        assert str(duration) == "60.0s"

    def test_boundary_60000_milliseconds(self):
        """Test boundary at exactly 1 minute."""
        duration = ModelExecutionDuration(milliseconds=60000)
        result = str(duration)
        assert result.startswith("1m")


@pytest.mark.unit
class TestModelExecutionDurationModelConfig:
    """Tests for ModelExecutionDuration model configuration."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        duration = ModelExecutionDuration(milliseconds=1000, extra_field="ignored")
        assert duration.milliseconds == 1000
        assert not hasattr(duration, "extra_field")

    def test_validate_assignment(self):
        """Test that assignment validation is enabled."""
        duration = ModelExecutionDuration(milliseconds=1000)
        duration.milliseconds = 2000
        assert duration.milliseconds == 2000

    def test_validate_assignment_negative_fails(self):
        """Test that assigning negative value fails validation."""
        duration = ModelExecutionDuration(milliseconds=1000)
        with pytest.raises(ValidationError):
            duration.milliseconds = -500
