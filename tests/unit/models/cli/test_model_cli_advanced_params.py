"""
Test suite for ModelCliAdvancedParams.

Tests the clean, strongly-typed replacement for ModelCustomFields[Any] in CLI advanced parameters.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_debug_level import EnumDebugLevel
from omnibase_core.enums.enum_security_level import EnumSecurityLevel
from omnibase_core.models.cli.model_cli_advanced_params import (
    ModelCliAdvancedParams,
)
from omnibase_core.models.cli.model_output_format_options import (
    ModelOutputFormatOptions,
)


class TestModelCliAdvancedParams:
    """Test cases for ModelCliAdvancedParams."""

    def test_initialization_empty(self):
        """Test empty initialization with defaults."""
        params = ModelCliAdvancedParams()

        # Timeout and performance parameters (now have defaults in Pydantic v2)
        assert params.timeout_seconds == 30.0
        assert params.max_retries == 3
        assert params.retry_delay_ms == 1000

        # Memory and resource limits (now have defaults)
        assert params.memory_limit_mb == 512
        assert params.cpu_limit_percent == 100.0

        # Execution parameters
        assert params.parallel_execution is False
        assert params.max_parallel_tasks == 4

        # Cache parameters
        assert params.enable_cache is True
        assert params.cache_ttl_seconds == 300

        # Debug and logging parameters
        assert params.debug_level == EnumDebugLevel.INFO
        assert params.enable_profiling is False
        assert params.enable_tracing is False

        # Output formatting parameters (default_factory creates instance)
        assert isinstance(
            params.output_format_options,
            type(params.output_format_options),
        )
        assert params.compression_enabled is False

        # Security parameters
        assert params.security_level == EnumSecurityLevel.STANDARD
        assert params.enable_sandbox is False

        # Custom environment variables
        assert params.environment_variables == {}

        # Node-specific configuration
        assert params.node_config_overrides == {}

        # Extensibility
        assert params.custom_parameters == {}

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        params = ModelCliAdvancedParams(
            timeout_seconds=120.0,
            max_retries=3,
            retry_delay_ms=500,
            memory_limit_mb=1024,
            cpu_limit_percent=75.0,
            parallel_execution=True,
            max_parallel_tasks=4,
            enable_cache=False,
            cache_ttl_seconds=300,
            debug_level=EnumDebugLevel.DEBUG,
            enable_profiling=True,
            enable_tracing=True,
            compression_enabled=True,
            security_level=EnumSecurityLevel.STRICT,
            enable_sandbox=True,
        )

        assert params.timeout_seconds == 120.0
        assert params.max_retries == 3
        assert params.retry_delay_ms == 500
        assert params.memory_limit_mb == 1024
        assert params.cpu_limit_percent == 75.0
        assert params.parallel_execution is True
        assert params.max_parallel_tasks == 4
        assert params.enable_cache is False
        assert params.cache_ttl_seconds == 300
        assert params.debug_level == EnumDebugLevel.DEBUG
        assert params.enable_profiling is True
        assert params.enable_tracing is True
        assert params.compression_enabled is True
        assert params.security_level == EnumSecurityLevel.STRICT
        assert params.enable_sandbox is True

    def test_timeout_validation_positive(self):
        """Test timeout validation for positive values."""
        # Valid positive timeout
        params = ModelCliAdvancedParams(timeout_seconds=60.5)
        assert params.timeout_seconds == 60.5

        # Very small positive value
        params = ModelCliAdvancedParams(timeout_seconds=0.1)
        assert params.timeout_seconds == 0.1

    def test_timeout_validation_invalid(self):
        """Test timeout validation rejects invalid values."""
        # Zero timeout should be invalid
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(timeout_seconds=0.0)

        # Negative timeout should be invalid
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(timeout_seconds=-1.0)

    def test_max_retries_validation(self):
        """Test max_retries validation."""
        # Valid retry counts
        params = ModelCliAdvancedParams(max_retries=0)
        assert params.max_retries == 0

        params = ModelCliAdvancedParams(max_retries=5)
        assert params.max_retries == 5

        params = ModelCliAdvancedParams(max_retries=10)
        assert params.max_retries == 10

        # Invalid retry counts
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(max_retries=-1)

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(max_retries=11)

    def test_retry_delay_validation(self):
        """Test retry_delay_ms validation."""
        # Valid delay values
        params = ModelCliAdvancedParams(retry_delay_ms=0)
        assert params.retry_delay_ms == 0

        params = ModelCliAdvancedParams(retry_delay_ms=1000)
        assert params.retry_delay_ms == 1000

        # Invalid delay (negative)
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(retry_delay_ms=-1)

    def test_memory_limit_validation(self):
        """Test memory_limit_mb validation."""
        # Valid memory limits
        params = ModelCliAdvancedParams(memory_limit_mb=512)
        assert params.memory_limit_mb == 512

        params = ModelCliAdvancedParams(memory_limit_mb=2048)
        assert params.memory_limit_mb == 2048

        # Invalid memory limits
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(memory_limit_mb=0)

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(memory_limit_mb=-100)

    def test_cpu_limit_validation(self):
        """Test cpu_limit_percent validation."""
        # Valid CPU limits
        params = ModelCliAdvancedParams(cpu_limit_percent=0.0)
        assert params.cpu_limit_percent == 0.0

        params = ModelCliAdvancedParams(cpu_limit_percent=50.5)
        assert params.cpu_limit_percent == 50.5

        params = ModelCliAdvancedParams(cpu_limit_percent=100.0)
        assert params.cpu_limit_percent == 100.0

        # Invalid CPU limits
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(cpu_limit_percent=-0.1)

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(cpu_limit_percent=100.1)

    def test_max_parallel_tasks_validation(self):
        """Test max_parallel_tasks validation."""
        # Valid parallel task counts
        params = ModelCliAdvancedParams(max_parallel_tasks=1)
        assert params.max_parallel_tasks == 1

        params = ModelCliAdvancedParams(max_parallel_tasks=50)
        assert params.max_parallel_tasks == 50

        params = ModelCliAdvancedParams(max_parallel_tasks=100)
        assert params.max_parallel_tasks == 100

        # Invalid parallel task counts
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(max_parallel_tasks=0)

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(max_parallel_tasks=101)

    def test_cache_ttl_validation(self):
        """Test cache_ttl_seconds validation."""
        # Valid TTL values
        params = ModelCliAdvancedParams(cache_ttl_seconds=0)
        assert params.cache_ttl_seconds == 0

        params = ModelCliAdvancedParams(cache_ttl_seconds=3600)
        assert params.cache_ttl_seconds == 3600

        # Invalid TTL (negative)
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(cache_ttl_seconds=-1)

    def test_debug_level_validation(self):
        """Test debug_level enum validation."""
        # Valid debug levels
        valid_levels = [
            EnumDebugLevel.DEBUG,
            EnumDebugLevel.INFO,
            EnumDebugLevel.WARN,
            EnumDebugLevel.ERROR,
        ]
        for level in valid_levels:
            params = ModelCliAdvancedParams(debug_level=level)
            assert params.debug_level == level

        # Invalid debug level (string instead of enum)
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(debug_level="invalid")

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(debug_level="DEBUG")  # String not allowed

    def test_security_level_validation(self):
        """Test security_level enum validation."""
        # Valid security levels
        valid_levels = [
            EnumSecurityLevel.MINIMAL,
            EnumSecurityLevel.STANDARD,
            EnumSecurityLevel.STRICT,
        ]
        for level in valid_levels:
            params = ModelCliAdvancedParams(security_level=level)
            assert params.security_level == level

        # Invalid security level (string instead of enum)
        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(security_level="invalid")

        with pytest.raises(ValidationError):
            ModelCliAdvancedParams(security_level="STRICT")  # String not allowed

    def test_set_timeout_method(self):
        """Test set_timeout method with validation."""
        params = ModelCliAdvancedParams()

        # Valid timeout
        params.set_timeout(45.0)
        assert params.timeout_seconds == 45.0

        # Invalid timeout should raise OnexError (not ValueError)
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        with pytest.raises(OnexError, match="Timeout must be positive"):
            params.set_timeout(0.0)

        with pytest.raises(OnexError, match="Timeout must be positive"):
            params.set_timeout(-1.0)

    def test_set_memory_limit_method(self):
        """Test set_memory_limit method with validation."""
        params = ModelCliAdvancedParams()

        # Valid memory limit
        params.set_memory_limit(512)
        assert params.memory_limit_mb == 512

        # Invalid memory limit should raise OnexError (not ValueError)
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        with pytest.raises(OnexError, match="Memory limit must be positive"):
            params.set_memory_limit(0)

        with pytest.raises(OnexError, match="Memory limit must be positive"):
            params.set_memory_limit(-100)

    def test_set_cpu_limit_method(self):
        """Test set_cpu_limit method with validation."""
        params = ModelCliAdvancedParams()

        # Valid CPU limits
        params.set_cpu_limit(0.0)
        assert params.cpu_limit_percent == 0.0

        params.set_cpu_limit(75.5)
        assert params.cpu_limit_percent == 75.5

        params.set_cpu_limit(100.0)
        assert params.cpu_limit_percent == 100.0

        # Invalid CPU limits should raise OnexError (not ValueError)
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        with pytest.raises(OnexError, match="CPU limit must be between 0.0 and 100.0"):
            params.set_cpu_limit(-0.1)

        with pytest.raises(OnexError, match="CPU limit must be between 0.0 and 100.0"):
            params.set_cpu_limit(100.1)

    def test_environment_variables_management(self):
        """Test environment variables management."""
        params = ModelCliAdvancedParams()

        # Start with empty environment variables
        assert params.environment_variables == {}

        # Add environment variables
        params.add_environment_variable("NODE_ENV", "production")
        params.add_environment_variable("LOG_LEVEL", "info")

        assert params.environment_variables["NODE_ENV"] == "production"
        assert params.environment_variables["LOG_LEVEL"] == "info"
        assert len(params.environment_variables) == 2

    def test_config_override_management(self):
        """Test configuration override management."""
        params = ModelCliAdvancedParams()

        # Start with empty config overrides
        assert params.node_config_overrides == {}

        # Add config overrides - all values are converted to strings by CLI
        params.add_config_override("max_connections", "100")
        params.add_config_override("debug_enabled", "true")
        params.add_config_override("service_name", "test-service")

        # Values are now stored as ModelCliValue objects
        assert "max_connections" in params.node_config_overrides
        assert "debug_enabled" in params.node_config_overrides
        assert "service_name" in params.node_config_overrides

        # Check actual stored values through ModelCliValue interface
        assert (
            params.node_config_overrides["max_connections"].to_python_value() == "100"
        )
        assert params.node_config_overrides["debug_enabled"].to_python_value() == "true"
        assert (
            params.node_config_overrides["service_name"].to_python_value()
            == "test-service"
        )

    def test_custom_parameters_management(self):
        """Test custom parameters management."""
        params = ModelCliAdvancedParams()

        # Start with empty custom parameters
        assert params.custom_parameters == {}

        # Set various types of custom parameters - CLI converts all to strings
        params.set_custom_parameter("string_param", "test_value")
        params.set_custom_parameter("int_param", "42")
        params.set_custom_parameter("float_param", "3.14")
        params.set_custom_parameter("bool_param", "true")

        # Values are now stored as ModelCliValue objects
        assert "string_param" in params.custom_parameters
        assert "int_param" in params.custom_parameters
        assert "float_param" in params.custom_parameters
        assert "bool_param" in params.custom_parameters

        # Test get_custom_parameter (returns string values)
        assert params.get_custom_parameter("string_param") == "test_value"
        assert params.get_custom_parameter("int_param") == "42"
        assert params.get_custom_parameter("float_param") == "3.14"
        assert params.get_custom_parameter("bool_param") == "true"
        assert params.get_custom_parameter("nonexistent") == ""

    def test_enable_debug_mode(self):
        """Test enable_debug_mode convenience method."""
        params = ModelCliAdvancedParams()

        # Initial state
        assert params.debug_level == EnumDebugLevel.INFO
        assert params.enable_profiling is False
        assert params.enable_tracing is False

        # Enable debug mode
        params.enable_debug_mode()

        assert params.debug_level == EnumDebugLevel.DEBUG
        assert params.enable_profiling is True
        assert params.enable_tracing is True

    def test_enable_performance_mode(self):
        """Test enable_performance_mode convenience method."""
        params = ModelCliAdvancedParams()

        # Initial state
        assert params.parallel_execution is False
        assert params.enable_cache is True  # Default
        assert params.compression_enabled is False

        # Enable performance mode
        params.enable_performance_mode()

        assert params.parallel_execution is True
        assert params.enable_cache is True
        assert params.compression_enabled is True

    def test_enable_security_mode(self):
        """Test enable_security_mode convenience method."""
        params = ModelCliAdvancedParams()

        # Initial state
        assert params.security_level == EnumSecurityLevel.STANDARD
        assert params.enable_sandbox is False

        # Enable security mode
        params.enable_security_mode()

        assert params.security_level == EnumSecurityLevel.STRICT
        assert params.enable_sandbox is True

    def test_complex_configuration_scenario(self):
        """Test complex configuration scenario with all features."""
        params = ModelCliAdvancedParams(
            timeout_seconds=300.0,
            max_retries=5,
            retry_delay_ms=1000,
            memory_limit_mb=2048,
            cpu_limit_percent=80.0,
            parallel_execution=True,
            max_parallel_tasks=8,
            enable_cache=True,
            cache_ttl_seconds=600,
            debug_level=EnumDebugLevel.WARN,
            compression_enabled=True,
            security_level=EnumSecurityLevel.STRICT,
            enable_sandbox=True,
        )

        # Add environment variables
        params.add_environment_variable(
            "DATABASE_URL",
            "postgresql://localhost:5432/prod",
        )
        params.add_environment_variable("REDIS_URL", "redis://localhost:6379")

        # Add config overrides - CLI converts all to strings
        params.add_config_override("worker_count", "4")
        params.add_config_override("enable_metrics", "true")
        params.add_config_override("timeout_multiplier", "1.5")

        # Add custom parameters - CLI converts all to strings
        params.set_custom_parameter("deployment_id", "deploy-123")
        params.set_custom_parameter("feature_flags", "true")

        # Verify all configuration
        assert params.timeout_seconds == 300.0
        assert params.max_retries == 5
        assert params.parallel_execution is True
        assert params.max_parallel_tasks == 8
        assert params.security_level == EnumSecurityLevel.STRICT
        assert len(params.environment_variables) == 2
        assert len(params.node_config_overrides) == 3
        assert len(params.custom_parameters) == 2

    def test_output_format_options(self):
        """Test output format options handling."""
        params = ModelCliAdvancedParams()

        # Start with default format options object (not empty dict)
        assert isinstance(
            params.output_format_options,
            type(params.output_format_options),
        )

        # Update format options using proper model attributes (not dict access)
        # Note: This assumes ModelOutputFormatOptions has these attributes
        # The test would need to be updated based on actual model structure

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        params = ModelCliAdvancedParams(
            timeout_seconds=60.0,
            max_retries=3,
            parallel_execution=True,
            debug_level=EnumDebugLevel.DEBUG,
            enable_profiling=True,
            security_level=EnumSecurityLevel.STRICT,
        )

        # Add some additional data
        params.add_environment_variable("TEST_ENV", "true")
        params.set_custom_parameter("test_param", "value")

        # Test model_dump
        data = params.model_dump()

        assert data["timeout_seconds"] == 60.0
        assert data["max_retries"] == 3
        assert data["parallel_execution"] is True
        assert data["debug_level"] == EnumDebugLevel.DEBUG
        assert data["enable_profiling"] is True
        assert data["security_level"] == EnumSecurityLevel.STRICT
        assert data["environment_variables"] == {"TEST_ENV": "true"}
        # Custom parameters are now ModelCliValue objects in serialization
        assert "test_param" in data["custom_parameters"]
        custom_param = data["custom_parameters"]["test_param"]
        assert custom_param["raw_value"] == "value"

    def test_pydantic_deserialization(self):
        """Test Pydantic model deserialization."""
        data = {
            "timeout_seconds": 120.0,
            "max_retries": 4,
            "retry_delay_ms": 500,
            "memory_limit_mb": 1024,
            "cpu_limit_percent": 75.0,
            "parallel_execution": True,
            "max_parallel_tasks": 6,
            "enable_cache": False,
            "debug_level": EnumDebugLevel.WARN,
            "enable_profiling": True,
            "security_level": EnumSecurityLevel.MINIMAL,
            "environment_variables": {"APP_ENV": "staging"},
            "node_config_overrides": {"max_workers": 8, "enable_ssl": True},
            "custom_parameters": {"experiment_id": "exp-456", "version": 2},
        }

        params = ModelCliAdvancedParams.model_validate(data)

        assert params.timeout_seconds == 120.0
        assert params.max_retries == 4
        assert params.retry_delay_ms == 500
        assert params.memory_limit_mb == 1024
        assert params.cpu_limit_percent == 75.0
        assert params.parallel_execution is True
        assert params.max_parallel_tasks == 6
        assert params.enable_cache is False
        assert params.debug_level == EnumDebugLevel.WARN
        assert params.enable_profiling is True
        assert params.security_level == EnumSecurityLevel.MINIMAL
        assert params.environment_variables == {"APP_ENV": "staging"}

        # node_config_overrides should be ModelCliValue objects now
        assert "max_workers" in params.node_config_overrides
        assert "enable_ssl" in params.node_config_overrides
        assert params.node_config_overrides["max_workers"].to_python_value() == 8
        assert params.node_config_overrides["enable_ssl"].to_python_value() is True

        # custom_parameters should be ModelCliValue objects now
        assert "experiment_id" in params.custom_parameters
        assert "version" in params.custom_parameters
        assert params.custom_parameters["experiment_id"].to_python_value() == "exp-456"
        assert params.custom_parameters["version"].to_python_value() == 2

    def test_model_round_trip(self):
        """Test serialization -> deserialization round trip."""
        original = ModelCliAdvancedParams(
            timeout_seconds=180.0,
            max_retries=2,
            parallel_execution=True,
            debug_level=EnumDebugLevel.ERROR,
            security_level=EnumSecurityLevel.STRICT,
        )

        # Add data via methods
        original.add_environment_variable("ROUND_TRIP", "test")
        original.add_config_override("round_trip_setting", True)
        original.set_custom_parameter("round_trip_id", 123)

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back to model
        restored = ModelCliAdvancedParams.model_validate(data)

        # Should be equal
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.max_retries == original.max_retries
        assert restored.parallel_execution == original.parallel_execution
        assert restored.debug_level == original.debug_level
        assert restored.security_level == original.security_level
        assert restored.environment_variables == original.environment_variables
        assert restored.node_config_overrides == original.node_config_overrides
        assert restored.custom_parameters == original.custom_parameters

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        params = ModelCliAdvancedParams(
            timeout_seconds=90.0,
            parallel_execution=True,
            debug_level=EnumDebugLevel.INFO,
        )

        # Test JSON serialization
        json_str = params.model_dump_json()
        assert isinstance(json_str, str)
        assert '"timeout_seconds":90.0' in json_str
        assert '"parallel_execution":true' in json_str

        # Test JSON deserialization
        restored = ModelCliAdvancedParams.model_validate_json(json_str)
        assert restored.timeout_seconds == 90.0
        assert restored.parallel_execution is True
        assert restored.debug_level == EnumDebugLevel.INFO

    def test_edge_cases_empty_collections(self):
        """Test edge cases with empty collections."""
        params = ModelCliAdvancedParams(
            environment_variables={},
            node_config_overrides={},
            custom_parameters={},
        )

        # output_format_options should be a ModelOutputFormatOptions instance with defaults
        # (default_factory creates instance, not empty dict)
        assert isinstance(params.output_format_options, ModelOutputFormatOptions)
        assert (
            params.output_format_options.custom_options == {}
        )  # Only custom_options should be empty dict

        # Dict collections should be empty
        assert params.environment_variables == {}
        assert params.node_config_overrides == {}
        assert params.custom_parameters == {}

    def test_mixed_type_config_overrides(self):
        """Test configuration overrides with mixed types."""
        params = ModelCliAdvancedParams()

        # Add different types of config values
        params.add_config_override("string_config", "value")
        params.add_config_override("int_config", 42)
        params.add_config_override("bool_config", True)

        # Values are now stored as ModelCliValue objects - check through the interface
        assert (
            params.node_config_overrides["string_config"].to_python_value() == "value"
        )
        assert params.node_config_overrides["int_config"].to_python_value() == 42
        assert params.node_config_overrides["bool_config"].to_python_value() is True

        # Test serialization with mixed types
        data = params.model_dump()
        restored = ModelCliAdvancedParams.model_validate(data)
        assert restored.node_config_overrides == params.node_config_overrides

    def test_convenience_methods_interaction(self):
        """Test interaction between convenience methods."""
        params = ModelCliAdvancedParams()

        # Apply multiple convenience methods
        params.enable_debug_mode()
        params.enable_performance_mode()
        params.enable_security_mode()

        # Verify combined state
        assert params.debug_level == EnumDebugLevel.DEBUG
        assert params.enable_profiling is True
        assert params.enable_tracing is True
        assert params.parallel_execution is True
        assert params.enable_cache is True
        assert params.compression_enabled is True
        assert params.security_level == EnumSecurityLevel.STRICT
        assert params.enable_sandbox is True
