# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelLoggingSubcontract.

Comprehensive tests for logging subcontract configuration and validation.
"""

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.models.contracts.subcontracts.model_log_level_override import (
    ModelLogLevelOverride,
)
from omnibase_core.models.contracts.subcontracts.model_logging_subcontract import (
    ModelLoggingSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelLoggingSubcontractInitialization:
    """Test ModelLoggingSubcontract initialization."""

    def test_create_default_logging_subcontract(self):
        """Test creating logging subcontract with default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract is not None
        assert isinstance(subcontract, ModelLoggingSubcontract)
        assert subcontract.log_level == "INFO"
        assert subcontract.log_format == "json"
        assert subcontract.enable_context_logging is True
        assert subcontract.enable_correlation_tracking is True
        assert subcontract.enable_performance_logging is True
        assert subcontract.enable_sensitive_data_redaction is True

    def test_logging_subcontract_with_custom_values(self):
        """Test creating logging subcontract with custom values."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            log_level="DEBUG",
            log_format="text",
            enable_context_logging=False,
            enable_correlation_tracking=False,
            performance_threshold_ms=500,
            async_logging=True,
        )
        assert subcontract.log_level == "DEBUG"
        assert subcontract.log_format == "text"
        assert subcontract.enable_context_logging is False
        assert subcontract.enable_correlation_tracking is False
        assert subcontract.performance_threshold_ms == 500
        assert subcontract.async_logging is True

    def test_logging_subcontract_inheritance(self):
        """Test that ModelLoggingSubcontract inherits from BaseModel."""
        from pydantic import BaseModel

        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert isinstance(subcontract, BaseModel)

    def test_interface_version_accessible(self):
        """Test that INTERFACE_VERSION is accessible as ClassVar."""
        assert hasattr(ModelLoggingSubcontract, "INTERFACE_VERSION")
        version = ModelLoggingSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0


@pytest.mark.unit
class TestModelLoggingSubcontractValidation:
    """Test ModelLoggingSubcontract field validation."""

    def test_log_level_valid_values(self):
        """Test log_level accepts valid values."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            subcontract = ModelLoggingSubcontract(
                version=DEFAULT_VERSION, log_level=level
            )
            assert subcontract.log_level == level

    def test_log_level_case_insensitive(self):
        """Test log_level is converted to uppercase."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_level="debug"
        )
        assert subcontract.log_level == "DEBUG"

        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION, log_level="Info")
        assert subcontract.log_level == "INFO"

    def test_log_level_invalid_value_raises_error(self):
        """Test log_level rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelLoggingSubcontract(version=DEFAULT_VERSION, log_level="INVALID")
        assert "log_level must be one of" in str(exc_info.value)

    def test_log_format_valid_values(self):
        """Test log_format accepts valid values."""
        for fmt in ["json", "text", "key-value"]:
            subcontract = ModelLoggingSubcontract(
                version=DEFAULT_VERSION, log_format=fmt
            )
            assert subcontract.log_format == fmt

    def test_log_format_invalid_value_raises_error(self):
        """Test log_format rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelLoggingSubcontract(version=DEFAULT_VERSION, log_format="xml")
        assert "log_format must be one of" in str(exc_info.value)

    def test_performance_threshold_constraints(self):
        """Test performance_threshold_ms field constraints."""
        # Valid values
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, performance_threshold_ms=1
        )
        assert subcontract.performance_threshold_ms == 1

        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, performance_threshold_ms=30000
        )
        assert subcontract.performance_threshold_ms == 30000

        # Exceeds recommended threshold
        with pytest.raises(ModelOnexError) as exc_info:
            ModelLoggingSubcontract(
                version=DEFAULT_VERSION, performance_threshold_ms=40000
            )
        assert "performance_threshold_ms exceeding 30 seconds" in str(exc_info.value)

    def test_sampling_rate_constraints(self):
        """Test sampling_rate field constraints."""
        # Valid values
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, sampling_rate=0.01
        )
        assert subcontract.sampling_rate == 0.01

        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, sampling_rate=1.0
        )
        assert subcontract.sampling_rate == 1.0

        # Below minimum recommended
        with pytest.raises(ModelOnexError) as exc_info:
            ModelLoggingSubcontract(version=DEFAULT_VERSION, sampling_rate=0.001)
        assert "sampling_rate below 0.01" in str(exc_info.value)

    def test_max_log_entry_size_constraints(self):
        """Test max_log_entry_size_kb field constraints."""
        # Valid values
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, max_log_entry_size_kb=1
        )
        assert subcontract.max_log_entry_size_kb == 1

        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, max_log_entry_size_kb=512
        )
        assert subcontract.max_log_entry_size_kb == 512

        # Exceeds recommended threshold
        with pytest.raises(ModelOnexError) as exc_info:
            ModelLoggingSubcontract(version=DEFAULT_VERSION, max_log_entry_size_kb=600)
        assert "max_log_entry_size_kb exceeding 512 KB" in str(exc_info.value)

    def test_log_buffer_size_constraints(self):
        """Test log_buffer_size field constraints."""
        # Valid values
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_buffer_size=100
        )
        assert subcontract.log_buffer_size == 100

        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_buffer_size=10000
        )
        assert subcontract.log_buffer_size == 10000


@pytest.mark.unit
class TestModelLoggingSubcontractSerialization:
    """Test ModelLoggingSubcontract serialization."""

    def test_logging_subcontract_serialization(self):
        """Test logging subcontract model_dump."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            log_level="ERROR",
            log_format="key-value",
            performance_threshold_ms=2000,
            async_logging=True,
        )
        data = subcontract.model_dump()
        assert isinstance(data, dict)
        assert data["log_level"] == "ERROR"
        assert data["log_format"] == "key-value"
        assert data["performance_threshold_ms"] == 2000
        assert data["async_logging"] is True

    def test_logging_subcontract_deserialization(self):
        """Test logging subcontract model_validate."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "log_level": "WARNING",
            "log_format": "text",
            "enable_audit_logging": True,
        }
        subcontract = ModelLoggingSubcontract.model_validate(data)
        assert subcontract.log_level == "WARNING"
        assert subcontract.log_format == "text"
        assert subcontract.enable_audit_logging is True

    def test_logging_subcontract_json_serialization(self):
        """Test logging subcontract JSON serialization."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        json_data = subcontract.model_dump_json()
        assert isinstance(json_data, str)
        assert "log_level" in json_data
        assert "log_format" in json_data

    def test_logging_subcontract_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            log_level="DEBUG",
            log_format="json",
            enable_performance_logging=True,
            performance_threshold_ms=5000,
            async_logging=True,
            log_buffer_size=2000,
        )
        data = original.model_dump()
        restored = ModelLoggingSubcontract.model_validate(data)
        assert restored.log_level == original.log_level
        assert restored.log_format == original.log_format
        assert (
            restored.enable_performance_logging == original.enable_performance_logging
        )
        assert restored.performance_threshold_ms == original.performance_threshold_ms
        assert restored.async_logging == original.async_logging
        assert restored.log_buffer_size == original.log_buffer_size


@pytest.mark.unit
class TestModelLoggingSubcontractDefaultValues:
    """Test ModelLoggingSubcontract default values."""

    def test_core_logging_defaults(self):
        """Test core logging default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.log_level == "INFO"
        assert subcontract.log_format == "json"

    def test_context_and_correlation_defaults(self):
        """Test context and correlation default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_context_logging is True
        assert subcontract.enable_correlation_tracking is True
        assert subcontract.correlation_id_field == "correlation_id"

    def test_performance_logging_defaults(self):
        """Test performance logging default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_performance_logging is True
        assert subcontract.performance_threshold_ms == 1000
        assert subcontract.track_function_entry_exit is False

    def test_security_defaults(self):
        """Test security default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_sensitive_data_redaction is True
        assert subcontract.enable_pii_detection is True
        assert len(subcontract.sensitive_field_patterns) > 0
        assert "password" in subcontract.sensitive_field_patterns
        assert "token" in subcontract.sensitive_field_patterns

    def test_structured_logging_defaults(self):
        """Test structured logging default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.structured_logging is True
        assert len(subcontract.required_log_fields) > 0
        assert "timestamp" in subcontract.required_log_fields
        assert "level" in subcontract.required_log_fields
        assert subcontract.include_stack_trace is True

    def test_audit_logging_defaults(self):
        """Test audit logging default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_audit_logging is False
        assert subcontract.audit_event_types == []

    def test_output_configuration_defaults(self):
        """Test output configuration default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.log_to_console is True
        assert subcontract.log_to_file is False
        assert subcontract.log_file_path is None

    def test_async_logging_defaults(self):
        """Test async logging default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.async_logging is False
        assert subcontract.log_buffer_size == 1000
        assert subcontract.flush_interval_ms == 5000

    def test_size_and_rotation_defaults(self):
        """Test size and rotation default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.max_log_entry_size_kb == 64
        assert subcontract.max_daily_log_size_mb == 1024
        assert subcontract.enable_log_rotation is True
        assert subcontract.rotation_size_mb == 100

    def test_filtering_and_sampling_defaults(self):
        """Test filtering and sampling default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_log_sampling is False
        assert subcontract.sampling_rate == 1.0
        assert subcontract.log_level_overrides == []

    def test_integration_defaults(self):
        """Test integration default values."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.include_environment_info is True
        assert subcontract.include_node_metadata is True
        assert subcontract.include_request_context is True


@pytest.mark.unit
class TestModelLoggingSubcontractEdgeCases:
    """Test logging subcontract edge cases."""

    def test_minimal_performance_threshold(self):
        """Test minimal performance threshold is accepted."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, performance_threshold_ms=1
        )
        assert subcontract.performance_threshold_ms == 1

    def test_minimal_sampling_rate(self):
        """Test minimal sampling rate is accepted."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, sampling_rate=0.01
        )
        assert subcontract.sampling_rate == 0.01

    def test_all_features_disabled(self):
        """Test creating subcontract with all features disabled."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            enable_context_logging=False,
            enable_correlation_tracking=False,
            enable_performance_logging=False,
            enable_sensitive_data_redaction=False,
            enable_pii_detection=False,
            structured_logging=False,
            include_stack_trace=False,
            enable_audit_logging=False,
            log_to_console=False,
            log_to_file=False,
            async_logging=False,
            enable_log_rotation=False,
            enable_log_sampling=False,
        )
        assert subcontract.enable_context_logging is False
        assert subcontract.enable_correlation_tracking is False
        assert subcontract.enable_performance_logging is False

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per ConfigDict."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "log_level": "INFO",
            "extra_unknown_field": "should_be_ignored",
        }
        subcontract = ModelLoggingSubcontract.model_validate(data)
        assert subcontract.log_level == "INFO"
        assert not hasattr(subcontract, "extra_unknown_field")

    def test_empty_sensitive_field_patterns(self):
        """Test creating subcontract with empty sensitive field patterns."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, sensitive_field_patterns=[]
        )
        assert subcontract.sensitive_field_patterns == []

    def test_custom_sensitive_field_patterns(self):
        """Test creating subcontract with custom sensitive patterns."""
        custom_patterns = ["custom_secret", "internal_token"]
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, sensitive_field_patterns=custom_patterns
        )
        assert subcontract.sensitive_field_patterns == custom_patterns

    def test_log_level_overrides(self):
        """Test creating subcontract with log level overrides."""
        overrides = [
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="module.submodule",
                log_level=EnumLogLevel.DEBUG,
            ),
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="other.module",
                log_level=EnumLogLevel.ERROR,
            ),
        ]
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_level_overrides=overrides
        )
        assert len(subcontract.log_level_overrides) == 2
        assert subcontract.log_level_overrides[0].logger_name == "module.submodule"
        assert subcontract.log_level_overrides[0].log_level == EnumLogLevel.DEBUG
        assert subcontract.log_level_overrides[1].logger_name == "other.module"
        assert subcontract.log_level_overrides[1].log_level == EnumLogLevel.ERROR

    def test_file_logging_with_path(self):
        """Test enabling file logging with path."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            log_to_file=True,
            log_file_path="/var/log/app/application.log",
        )
        assert subcontract.log_to_file is True
        assert subcontract.log_file_path == "/var/log/app/application.log"


@pytest.mark.unit
class TestModelLoggingSubcontractAttributes:
    """Test logging subcontract attributes and metadata."""

    def test_logging_subcontract_attributes(self):
        """Test that logging subcontract has expected attributes."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert hasattr(subcontract, "model_dump")
        assert callable(subcontract.model_dump)
        assert hasattr(ModelLoggingSubcontract, "model_validate")
        assert callable(ModelLoggingSubcontract.model_validate)

    def test_logging_subcontract_docstring(self):
        """Test logging subcontract docstring."""
        assert ModelLoggingSubcontract.__doc__ is not None
        assert "logging" in ModelLoggingSubcontract.__doc__.lower()

    def test_logging_subcontract_class_name(self):
        """Test logging subcontract class name."""
        assert ModelLoggingSubcontract.__name__ == "ModelLoggingSubcontract"

    def test_logging_subcontract_module(self):
        """Test logging subcontract module."""
        assert (
            ModelLoggingSubcontract.__module__
            == "omnibase_core.models.contracts.subcontracts.model_logging_subcontract"
        )

    def test_logging_subcontract_copy(self):
        """Test logging subcontract copying."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_level="ERROR"
        )
        copied = subcontract.model_copy()
        assert copied is not None
        assert copied.log_level == "ERROR"
        assert copied is not subcontract

    def test_logging_subcontract_equality(self):
        """Test logging subcontract equality."""
        subcontract1 = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_level="WARNING"
        )
        subcontract2 = ModelLoggingSubcontract(
            version=DEFAULT_VERSION, log_level="WARNING"
        )
        assert subcontract1 == subcontract2

    def test_logging_subcontract_str_repr(self):
        """Test logging subcontract string representations."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        str_repr = str(subcontract)
        assert isinstance(str_repr, str)

        repr_str = repr(subcontract)
        assert isinstance(repr_str, str)
        assert "ModelLoggingSubcontract" in repr_str

    def test_interface_version_format(self):
        """Test INTERFACE_VERSION format and accessibility."""
        version = ModelLoggingSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)
        assert str(version) == "1.0.0"
        assert version.major >= 1


@pytest.mark.unit
class TestModelLoggingSubcontractConfigDict:
    """Test ModelLoggingSubcontract ConfigDict settings."""

    def test_extra_fields_are_ignored(self):
        """Test that extra='ignore' allows extra fields."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "log_level": "INFO",
            "unknown_field_1": "value1",
            "unknown_field_2": "value2",
        }
        subcontract = ModelLoggingSubcontract.model_validate(data)
        assert subcontract.log_level == "INFO"

    def test_validate_assignment_enabled(self):
        """Test that validate_assignment=True validates on assignment."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        # This should validate the new value
        subcontract.log_level = "ERROR"
        assert subcontract.log_level == "ERROR"

        # This should raise validation error
        with pytest.raises(ModelOnexError):
            subcontract.log_level = "INVALID_LEVEL"


@pytest.mark.unit
class TestModelLoggingSubcontractSecurityFeatures:
    """Test logging subcontract security features."""

    def test_sensitive_data_redaction_enabled(self):
        """Test that sensitive data redaction is enabled by default."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_sensitive_data_redaction is True

    def test_pii_detection_enabled(self):
        """Test that PII detection is enabled by default."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        assert subcontract.enable_pii_detection is True

    def test_default_sensitive_patterns_comprehensive(self):
        """Test that default sensitive patterns cover common fields."""
        subcontract = ModelLoggingSubcontract(version=DEFAULT_VERSION)
        patterns = subcontract.sensitive_field_patterns
        assert "password" in patterns
        assert "token" in patterns
        assert "secret" in patterns
        assert "api_key" in patterns
        assert "private_key" in patterns

    def test_custom_security_configuration(self):
        """Test creating subcontract with custom security config."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            enable_sensitive_data_redaction=True,
            enable_pii_detection=True,
            sensitive_field_patterns=["custom_password", "custom_token"],
        )
        assert subcontract.enable_sensitive_data_redaction is True
        assert subcontract.enable_pii_detection is True
        assert len(subcontract.sensitive_field_patterns) == 2


@pytest.mark.unit
class TestModelLoggingSubcontractPerformanceFeatures:
    """Test logging subcontract performance features."""

    def test_async_logging_configuration(self):
        """Test async logging configuration."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            async_logging=True,
            log_buffer_size=5000,
            flush_interval_ms=10000,
        )
        assert subcontract.async_logging is True
        assert subcontract.log_buffer_size == 5000
        assert subcontract.flush_interval_ms == 10000

    def test_log_sampling_configuration(self):
        """Test log sampling configuration."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            enable_log_sampling=True,
            sampling_rate=0.1,
        )
        assert subcontract.enable_log_sampling is True
        assert subcontract.sampling_rate == 0.1

    def test_performance_threshold_configuration(self):
        """Test performance threshold configuration."""
        subcontract = ModelLoggingSubcontract(
            version=DEFAULT_VERSION,
            enable_performance_logging=True,
            performance_threshold_ms=2000,
        )
        assert subcontract.enable_performance_logging is True
        assert subcontract.performance_threshold_ms == 2000
