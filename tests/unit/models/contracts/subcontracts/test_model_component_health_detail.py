# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelComponentHealthDetail.

Comprehensive test coverage for component health detail model including:
- Field validation and constraints
- Enum type validation
- Timestamp validation
- Default values
- ConfigDict behavior
- Edge cases and error scenarios
"""

import time

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.enums.enum_health_detail_type import EnumHealthDetailType
from omnibase_core.models.contracts.subcontracts.model_component_health_detail import (
    ModelComponentHealthDetail,
)


@pytest.mark.unit
class TestModelComponentHealthDetailBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="memory_usage",
            detail_value="75%",
        )

        assert detail.detail_key == "memory_usage"
        assert detail.detail_value == "75%"
        assert detail.detail_type == EnumHealthDetailType.INFO
        assert detail.is_critical is False
        assert detail.timestamp_ms is None

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        timestamp = int(time.time() * 1000)

        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="cpu_usage",
            detail_value="95%",
            detail_type=EnumHealthDetailType.WARNING,
            is_critical=True,
            timestamp_ms=timestamp,
        )

        assert detail.detail_key == "cpu_usage"
        assert detail.detail_value == "95%"
        assert detail.detail_type == EnumHealthDetailType.WARNING
        assert detail.is_critical is True
        assert detail.timestamp_ms == timestamp

    def test_default_detail_type(self):
        """Test detail_type defaults to INFO."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status",
            detail_value="running",
        )

        assert detail.detail_type == EnumHealthDetailType.INFO

    def test_default_is_critical(self):
        """Test is_critical defaults to False."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status",
            detail_value="running",
        )

        assert detail.is_critical is False

    def test_default_timestamp(self):
        """Test timestamp_ms defaults to None."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status",
            detail_value="running",
        )

        assert detail.timestamp_ms is None


@pytest.mark.unit
class TestModelComponentHealthDetailValidation:
    """Test field validation and constraints."""

    def test_detail_key_required(self):
        """Test detail_key is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelComponentHealthDetail(version=DEFAULT_VERSION, detail_value="test")

        assert "detail_key" in str(exc_info.value)

    def test_detail_key_min_length(self):
        """Test detail_key has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ModelComponentHealthDetail(
                version=DEFAULT_VERSION,
                detail_key="",
                detail_value="test",
            )

        assert "detail_key" in str(exc_info.value)

    def test_detail_key_whitespace_accepted(self):
        """Test detail_key accepts whitespace (no strip validation)."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="   ",
            detail_value="test",
        )
        # Pydantic doesn't strip by default, so whitespace is accepted
        assert detail.detail_key == "   "

    def test_detail_value_required(self):
        """Test detail_value is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelComponentHealthDetail(version=DEFAULT_VERSION, detail_key="test")

        assert "detail_value" in str(exc_info.value)

    def test_detail_value_accepts_empty_string(self):
        """Test detail_value accepts empty string (no min_length constraint)."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status",
            detail_value="",
        )

        assert detail.detail_value == ""

    def test_detail_type_enum_values(self):
        """Test detail_type accepts all enum values."""
        for detail_type in EnumHealthDetailType:
            detail = ModelComponentHealthDetail(
                version=DEFAULT_VERSION,
                detail_key="test",
                detail_value="value",
                detail_type=detail_type,
            )
            assert detail.detail_type == detail_type

    def test_detail_type_invalid_value(self):
        """Test detail_type rejects invalid values."""
        with pytest.raises(ValidationError):
            ModelComponentHealthDetail(
                version=DEFAULT_VERSION,
                detail_key="test",
                detail_value="value",
                detail_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_timestamp_ms_non_negative(self):
        """Test timestamp_ms must be non-negative."""
        # Valid zero
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            timestamp_ms=0,
        )
        assert detail.timestamp_ms == 0

        # Valid positive
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            timestamp_ms=1000000,
        )
        assert detail.timestamp_ms == 1000000

        # Invalid negative
        with pytest.raises(ValidationError) as exc_info:
            ModelComponentHealthDetail(
                version=DEFAULT_VERSION,
                detail_key="test",
                detail_value="value",
                timestamp_ms=-1,
            )

        assert "timestamp_ms" in str(exc_info.value)

    def test_timestamp_ms_large_values(self):
        """Test timestamp_ms accepts large timestamp values."""
        large_timestamp = 9999999999999  # Far future timestamp
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            timestamp_ms=large_timestamp,
        )

        assert detail.timestamp_ms == large_timestamp

    def test_is_critical_boolean(self):
        """Test is_critical accepts boolean values."""
        detail_true = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            is_critical=True,
        )
        assert detail_true.is_critical is True

        detail_false = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            is_critical=False,
        )
        assert detail_false.is_critical is False


@pytest.mark.unit
class TestModelComponentHealthDetailEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_info_detail_non_critical(self):
        """Test typical INFO level detail."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="service_version",
            detail_value="1.2.3",
            detail_type=EnumHealthDetailType.INFO,
            is_critical=False,
        )

        assert detail.detail_type == EnumHealthDetailType.INFO
        assert detail.is_critical is False

    def test_metric_detail(self):
        """Test METRIC type detail."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="response_time_ms",
            detail_value="150",
            detail_type=EnumHealthDetailType.METRIC,
            is_critical=False,
        )

        assert detail.detail_type == EnumHealthDetailType.METRIC
        assert detail.is_critical is False

    def test_warning_detail_non_critical(self):
        """Test WARNING level detail that's not critical."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="memory_usage",
            detail_value="80%",
            detail_type=EnumHealthDetailType.WARNING,
            is_critical=False,
        )

        assert detail.detail_type == EnumHealthDetailType.WARNING
        assert detail.is_critical is False

    def test_error_detail_critical(self):
        """Test ERROR level detail marked as critical."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="database_connection",
            detail_value="connection_failed",
            detail_type=EnumHealthDetailType.ERROR,
            is_critical=True,
        )

        assert detail.detail_type == EnumHealthDetailType.ERROR
        assert detail.is_critical is True

    def test_diagnostic_detail(self):
        """Test DIAGNOSTIC type detail."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="thread_count",
            detail_value="42",
            detail_type=EnumHealthDetailType.DIAGNOSTIC,
            is_critical=False,
        )

        assert detail.detail_type == EnumHealthDetailType.DIAGNOSTIC

    def test_current_timestamp(self):
        """Test with current timestamp."""
        before = int(time.time() * 1000)
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status_check",
            detail_value="healthy",
            timestamp_ms=before,
        )
        after = int(time.time() * 1000)

        assert before <= detail.timestamp_ms <= after

    def test_long_detail_key(self):
        """Test with very long detail key."""
        long_key = "a" * 1000
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key=long_key,
            detail_value="value",
        )

        assert detail.detail_key == long_key

    def test_long_detail_value(self):
        """Test with very long detail value."""
        long_value = "x" * 10000
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="stacktrace",
            detail_value=long_value,
        )

        assert detail.detail_value == long_value

    def test_special_characters_in_detail_key(self):
        """Test detail_key with special characters."""
        special_key = "metric.http.response_time.p99"
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key=special_key,
            detail_value="250ms",
        )

        assert detail.detail_key == special_key

    def test_json_value_as_string(self):
        """Test detail_value containing JSON-like string."""
        json_value = '{"status": "ok", "count": 42}'
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="config",
            detail_value=json_value,
        )

        assert detail.detail_value == json_value

    def test_multiline_detail_value(self):
        """Test detail_value with multiline text."""
        multiline_value = "Line 1\nLine 2\nLine 3"
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="error_trace",
            detail_value=multiline_value,
        )

        assert detail.detail_value == multiline_value


@pytest.mark.unit
class TestModelComponentHealthDetailConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert detail.detail_key == "test"
        assert not hasattr(detail, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
        )

        # Valid assignment
        detail.detail_key = "new_key"
        assert detail.detail_key == "new_key"

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            detail.detail_key = ""

    def test_use_enum_values_false(self):
        """Test use_enum_values=False preserves enum objects."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="test",
            detail_value="value",
            detail_type=EnumHealthDetailType.WARNING,
        )

        # Should be enum object, not string value
        assert isinstance(detail.detail_type, EnumHealthDetailType)
        assert detail.detail_type == EnumHealthDetailType.WARNING
        assert detail.detail_type.value == "warning"

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        timestamp = int(time.time() * 1000)
        original = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="cpu_usage",
            detail_value="85%",
            detail_type=EnumHealthDetailType.WARNING,
            is_critical=True,
            timestamp_ms=timestamp,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelComponentHealthDetail(**data)

        assert restored.detail_key == original.detail_key
        assert restored.detail_value == original.detail_value
        assert restored.detail_type == original.detail_type
        assert restored.is_critical == original.is_critical
        assert restored.timestamp_ms == original.timestamp_ms

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="status",
            detail_value="healthy",
            detail_type=EnumHealthDetailType.INFO,
        )

        json_str = detail.model_dump_json()
        assert isinstance(json_str, str)
        assert "status" in json_str
        assert "healthy" in json_str

    def test_model_json_deserialization(self):
        """Test model JSON deserialization."""
        json_data = """{
            "version": {"major": 1, "minor": 0, "patch": 0},
            "detail_key": "memory",
            "detail_value": "1024MB",
            "detail_type": "metric",
            "is_critical": false,
            "timestamp_ms": 1234567890
        }"""

        detail = ModelComponentHealthDetail.model_validate_json(json_data)

        assert detail.detail_key == "memory"
        assert detail.detail_value == "1024MB"
        assert detail.detail_type == EnumHealthDetailType.METRIC
        assert detail.is_critical is False
        assert detail.timestamp_ms == 1234567890


@pytest.mark.unit
class TestModelComponentHealthDetailDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has docstring."""
        assert ModelComponentHealthDetail.__doc__ is not None
        assert len(ModelComponentHealthDetail.__doc__) > 20

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelComponentHealthDetail.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )

    def test_required_fields_documented(self):
        """Test required fields are properly documented in schema."""
        schema = ModelComponentHealthDetail.model_json_schema()

        required_fields = schema.get("required", [])
        assert "detail_key" in required_fields
        assert "detail_value" in required_fields

    def test_optional_fields_documented(self):
        """Test optional fields are not in required list."""
        schema = ModelComponentHealthDetail.model_json_schema()

        required_fields = schema.get("required", [])
        assert "detail_type" not in required_fields
        assert "is_critical" not in required_fields
        assert "timestamp_ms" not in required_fields


@pytest.mark.unit
class TestModelComponentHealthDetailUseCases:
    """Test real-world use case scenarios."""

    def test_database_health_metric(self):
        """Test database connection pool metric."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="db.connection_pool.active",
            detail_value="15",
            detail_type=EnumHealthDetailType.METRIC,
            timestamp_ms=int(time.time() * 1000),
        )

        assert detail.detail_type == EnumHealthDetailType.METRIC
        assert detail.is_critical is False

    def test_api_health_error(self):
        """Test API health check error."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="api.health_check",
            detail_value="Connection timeout after 5s",
            detail_type=EnumHealthDetailType.ERROR,
            is_critical=True,
            timestamp_ms=int(time.time() * 1000),
        )

        assert detail.detail_type == EnumHealthDetailType.ERROR
        assert detail.is_critical is True

    def test_memory_warning(self):
        """Test memory usage warning."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="system.memory.usage_percent",
            detail_value="85.5",
            detail_type=EnumHealthDetailType.WARNING,
            is_critical=False,
            timestamp_ms=int(time.time() * 1000),
        )

        assert detail.detail_type == EnumHealthDetailType.WARNING
        assert float(detail.detail_value) > 80.0

    def test_service_version_info(self):
        """Test service version information."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="service.version",
            detail_value="2.5.0",
            detail_type=EnumHealthDetailType.INFO,
        )

        assert detail.detail_type == EnumHealthDetailType.INFO
        assert detail.timestamp_ms is None  # Version info doesn't need timestamp

    def test_diagnostic_thread_dump(self):
        """Test diagnostic thread information."""
        detail = ModelComponentHealthDetail(
            version=DEFAULT_VERSION,
            detail_key="jvm.thread.dump",
            detail_value="Thread pool: 25 active, 50 max",
            detail_type=EnumHealthDetailType.DIAGNOSTIC,
            timestamp_ms=int(time.time() * 1000),
        )

        assert detail.detail_type == EnumHealthDetailType.DIAGNOSTIC
