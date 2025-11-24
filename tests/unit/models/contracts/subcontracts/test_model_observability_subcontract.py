"""
Tests for ModelObservabilitySubcontract.

Comprehensive tests for observability subcontract configuration and validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_observability_subcontract import (
    ModelObservabilitySubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelObservabilitySubcontractInitialization:
    """Test ModelObservabilitySubcontract initialization."""

    def test_create_default_observability_subcontract(self):
        """Test creating observability subcontract with default values."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION)
        assert obs is not None
        assert isinstance(obs, ModelObservabilitySubcontract)
        assert obs.enabled is True
        assert obs.log_level == "INFO"
        assert obs.enable_tracing is False
        assert obs.trace_sampling_rate == 0.1
        assert obs.enable_profiling is False
        assert obs.export_format == "json"

    def test_observability_subcontract_with_custom_values(self):
        """Test creating observability subcontract with custom values."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enabled=True,
            log_level="DEBUG",
            enable_tracing=True,
            trace_sampling_rate=0.1,
            trace_exporter_endpoint="http://localhost:4317",
            enable_profiling=True,
            profiling_sampling_rate=0.01,
            export_format="opentelemetry",
        )
        assert obs.enabled is True
        assert obs.log_level == "DEBUG"
        assert obs.enable_tracing is True
        assert obs.trace_exporter_endpoint == "http://localhost:4317"
        assert obs.enable_profiling is True
        assert obs.profiling_sampling_rate == 0.01

    def test_observability_subcontract_inheritance(self):
        """Test that ModelObservabilitySubcontract inherits from BaseModel."""
        from pydantic import BaseModel

        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION)
        assert isinstance(obs, BaseModel)

    def test_interface_version_present(self):
        """Test that INTERFACE_VERSION is present and correct."""
        assert hasattr(ModelObservabilitySubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelObservabilitySubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelObservabilitySubcontract.INTERFACE_VERSION.major == 1
        assert ModelObservabilitySubcontract.INTERFACE_VERSION.minor == 0
        assert ModelObservabilitySubcontract.INTERFACE_VERSION.patch == 0


class TestModelObservabilitySubcontractLogLevelValidation:
    """Test log level validation."""

    def test_log_level_validation_debug(self):
        """Test log_level accepts DEBUG."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION, log_level="DEBUG")
        assert obs.log_level == "DEBUG"

    def test_log_level_validation_info(self):
        """Test log_level accepts INFO."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION, log_level="INFO")
        assert obs.log_level == "INFO"

    def test_log_level_validation_warning(self):
        """Test log_level accepts WARNING."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, log_level="WARNING"
        )
        assert obs.log_level == "WARNING"

    def test_log_level_validation_error(self):
        """Test log_level accepts ERROR."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION, log_level="ERROR")
        assert obs.log_level == "ERROR"

    def test_log_level_validation_critical(self):
        """Test log_level accepts CRITICAL."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, log_level="CRITICAL"
        )
        assert obs.log_level == "CRITICAL"

    def test_log_level_validation_case_insensitive(self):
        """Test log_level accepts lowercase and converts to uppercase."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION, log_level="debug")
        assert obs.log_level == "DEBUG"

    def test_log_level_validation_invalid(self):
        """Test log_level rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(version=DEFAULT_VERSION, log_level="INVALID")
        assert "must be one of" in str(exc_info.value)


class TestModelObservabilitySubcontractTracingValidation:
    """Test distributed tracing validation."""

    def test_trace_propagation_format_w3c(self):
        """Test trace_propagation_format accepts w3c."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, trace_propagation_format="w3c"
        )
        assert obs.trace_propagation_format == "w3c"

    def test_trace_propagation_format_b3(self):
        """Test trace_propagation_format accepts b3."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, trace_propagation_format="b3"
        )
        assert obs.trace_propagation_format == "b3"

    def test_trace_propagation_format_jaeger(self):
        """Test trace_propagation_format accepts jaeger."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, trace_propagation_format="jaeger"
        )
        assert obs.trace_propagation_format == "jaeger"

    def test_trace_propagation_format_invalid(self):
        """Test trace_propagation_format rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, trace_propagation_format="invalid"
            )
        assert "must be one of" in str(exc_info.value)

    def test_tracing_enabled_without_endpoint_fails(self):
        """Test that enabling tracing without exporter endpoint fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION,
                enable_tracing=True,
                trace_sampling_rate=0.1,
            )
        assert "trace_exporter_endpoint must be provided" in str(exc_info.value)

    def test_tracing_enabled_with_endpoint_succeeds(self):
        """Test that enabling tracing with exporter endpoint succeeds."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_tracing=True,
            trace_sampling_rate=0.1,
            trace_exporter_endpoint="http://localhost:4317",
        )
        assert obs.enable_tracing is True
        assert obs.trace_exporter_endpoint == "http://localhost:4317"

    def test_trace_sampling_rate_minimum(self):
        """Test trace_sampling_rate accepts minimum value."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            trace_sampling_rate=0.0,
        )
        assert obs.trace_sampling_rate == 0.0

    def test_trace_sampling_rate_maximum(self):
        """Test trace_sampling_rate accepts maximum value (but warns if tracing enabled)."""
        # Without tracing enabled, should accept 1.0
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_tracing=False,
            trace_sampling_rate=1.0,
        )
        assert obs.trace_sampling_rate == 1.0

    def test_trace_sampling_rate_high_with_tracing_enabled_fails(self):
        """Test trace_sampling_rate above 0.5 with tracing enabled fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION,
                enable_tracing=True,
                trace_sampling_rate=0.8,
                trace_exporter_endpoint="http://localhost:4317",
            )
        assert "above 0.5" in str(exc_info.value)

    def test_trace_sampling_rate_below_minimum_fails(self):
        """Test trace_sampling_rate below minimum fails."""
        with pytest.raises(ValidationError):
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, trace_sampling_rate=-0.1
            )

    def test_trace_sampling_rate_above_maximum_fails(self):
        """Test trace_sampling_rate above maximum fails."""
        with pytest.raises(ValidationError):
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, trace_sampling_rate=1.5
            )


class TestModelObservabilitySubcontractProfilingValidation:
    """Test performance profiling validation."""

    def test_profiling_enabled_without_profilers_fails(self):
        """Test that enabling profiling without any profiler fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION,
                enable_profiling=True,
                profile_cpu=False,
                profile_memory=False,
                profile_io=False,
            )
        assert "At least one profiler" in str(exc_info.value)

    def test_profiling_enabled_with_cpu_succeeds(self):
        """Test that enabling profiling with CPU profiler succeeds."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_profiling=True,
            profile_cpu=True,
            profile_memory=False,
            profile_io=False,
        )
        assert obs.enable_profiling is True
        assert obs.profile_cpu is True

    def test_profiling_enabled_with_memory_succeeds(self):
        """Test that enabling profiling with memory profiler succeeds."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_profiling=True,
            profile_cpu=False,
            profile_memory=True,
            profile_io=False,
        )
        assert obs.enable_profiling is True
        assert obs.profile_memory is True

    def test_profiling_enabled_with_io_succeeds(self):
        """Test that enabling profiling with I/O profiler succeeds."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_profiling=True,
            profile_cpu=False,
            profile_memory=False,
            profile_io=True,
        )
        assert obs.enable_profiling is True
        assert obs.profile_io is True

    def test_profiling_sampling_rate_minimum(self):
        """Test profiling_sampling_rate accepts minimum value."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, profiling_sampling_rate=0.0
        )
        assert obs.profiling_sampling_rate == 0.0

    def test_profiling_sampling_rate_maximum(self):
        """Test profiling_sampling_rate accepts maximum value (but warns if profiling enabled)."""
        # Without profiling enabled, should accept 1.0
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enable_profiling=False,
            profiling_sampling_rate=1.0,
        )
        assert obs.profiling_sampling_rate == 1.0

    def test_profiling_sampling_rate_high_with_profiling_enabled_fails(self):
        """Test profiling_sampling_rate above 0.1 with profiling enabled fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION,
                enable_profiling=True,
                profiling_sampling_rate=0.2,
                profile_cpu=True,
            )
        assert "above 0.1" in str(exc_info.value)


class TestModelObservabilitySubcontractExportValidation:
    """Test export configuration validation."""

    def test_export_format_json(self):
        """Test export_format accepts json."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_format="json"
        )
        assert obs.export_format == "json"

    def test_export_format_opentelemetry(self):
        """Test export_format accepts opentelemetry."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_format="opentelemetry"
        )
        assert obs.export_format == "opentelemetry"

    def test_export_format_prometheus(self):
        """Test export_format accepts prometheus."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_format="prometheus"
        )
        assert obs.export_format == "prometheus"

    def test_export_format_invalid(self):
        """Test export_format rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, export_format="invalid"
            )
        assert "must be one of" in str(exc_info.value)

    def test_export_interval_minimum_fails(self):
        """Test export_interval_seconds below minimum fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, export_interval_seconds=3
            )
        assert "below 5 seconds" in str(exc_info.value)

    def test_export_interval_minimum_succeeds(self):
        """Test export_interval_seconds at minimum succeeds."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_interval_seconds=5
        )
        assert obs.export_interval_seconds == 5

    def test_export_interval_maximum(self):
        """Test export_interval_seconds at maximum."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_interval_seconds=3600
        )
        assert obs.export_interval_seconds == 3600

    def test_export_batch_size_minimum(self):
        """Test export_batch_size at minimum."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_batch_size=1, export_interval_seconds=5
        )
        assert obs.export_batch_size == 1

    def test_export_batch_size_maximum(self):
        """Test export_batch_size at maximum."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, export_batch_size=10000, export_interval_seconds=5
        )
        assert obs.export_batch_size == 10000


class TestModelObservabilitySubcontractComprehensive:
    """Test comprehensive observability configurations."""

    def test_full_observability_enabled(self):
        """Test full observability with all features enabled."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enabled=True,
            log_level="DEBUG",
            enable_structured_logging=True,
            enable_correlation_tracking=True,
            enable_tracing=True,
            trace_sampling_rate=0.1,
            trace_exporter_endpoint="http://localhost:4317",
            trace_propagation_format="w3c",
            enable_profiling=True,
            profiling_sampling_rate=0.01,
            profile_cpu=True,
            profile_memory=True,
            profile_io=False,
            export_format="opentelemetry",
            export_interval_seconds=60,
            enable_sensitive_data_redaction=True,
        )
        assert obs.enabled is True
        assert obs.enable_tracing is True
        assert obs.enable_profiling is True
        assert obs.export_format == "opentelemetry"

    def test_minimal_observability(self):
        """Test minimal observability configuration."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            enabled=True,
            log_level="WARNING",
            enable_tracing=False,
            enable_profiling=False,
        )
        assert obs.enabled is True
        assert obs.enable_tracing is False
        assert obs.enable_profiling is False

    def test_observability_disabled(self):
        """Test observability completely disabled."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION, enabled=False)
        assert obs.enabled is False

    def test_sensitive_field_patterns_default(self):
        """Test default sensitive field patterns."""
        obs = ModelObservabilitySubcontract(version=DEFAULT_VERSION)
        assert "password" in obs.sensitive_field_patterns
        assert "token" in obs.sensitive_field_patterns
        assert "secret" in obs.sensitive_field_patterns
        assert "api_key" in obs.sensitive_field_patterns

    def test_custom_resource_attributes(self):
        """Test custom resource attributes."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION,
            custom_resource_attributes={
                "service.namespace": "production",
                "deployment.environment": "us-west-2",
            },
        )
        assert obs.custom_resource_attributes["service.namespace"] == "production"
        assert obs.custom_resource_attributes["deployment.environment"] == "us-west-2"

    def test_diagnostics_log_level_validation(self):
        """Test diagnostics_log_level validation."""
        obs = ModelObservabilitySubcontract(
            version=DEFAULT_VERSION, diagnostics_log_level="ERROR"
        )
        assert obs.diagnostics_log_level == "ERROR"

        with pytest.raises(ModelOnexError) as exc_info:
            ModelObservabilitySubcontract(
                version=DEFAULT_VERSION, diagnostics_log_level="INVALID"
            )
        assert "must be one of" in str(exc_info.value)
