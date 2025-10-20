"""
Unit tests for ModelNodeConfiguration.

Tests all aspects of the node configuration model including:
- Model instantiation with composed sub-models
- Property delegations to sub-models
- Custom properties handling
- Configuration summaries and checks
- Factory methods
- Protocol implementations
"""

import pytest

from omnibase_core.enums.enum_protocol_type import EnumProtocolType
from omnibase_core.models.nodes.model_node_configuration import ModelNodeConfiguration
from omnibase_core.models.nodes.model_node_connection_settings import (
    ModelNodeConnectionSettings,
)
from omnibase_core.models.nodes.model_node_execution_settings import (
    ModelNodeExecutionSettings,
)
from omnibase_core.models.nodes.model_node_feature_flags import ModelNodeFeatureFlags
from omnibase_core.models.nodes.model_node_resource_limits import (
    ModelNodeResourceLimits,
)


class TestModelNodeConfiguration:
    """Test cases for ModelNodeConfiguration."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        config = ModelNodeConfiguration()

        assert config.execution is not None
        assert config.resources is not None
        assert config.features is not None
        assert config.connection is not None
        assert config.custom_properties is not None

    def test_model_instantiation_with_components(self):
        """Test model instantiation with all components."""
        execution = ModelNodeExecutionSettings()
        resources = ModelNodeResourceLimits()
        features = ModelNodeFeatureFlags()
        connection = ModelNodeConnectionSettings()

        config = ModelNodeConfiguration(
            execution=execution,
            resources=resources,
            features=features,
            connection=connection,
        )

        assert config.execution == execution
        assert config.resources == resources
        assert config.features == features
        assert config.connection == connection

    def test_max_retries_property_get(self):
        """Test max_retries property delegation."""
        config = ModelNodeConfiguration()
        assert config.max_retries == config.execution.max_retries

    def test_max_retries_property_set(self):
        """Test max_retries property setter."""
        config = ModelNodeConfiguration()
        config.max_retries = 5
        assert config.execution.max_retries == 5

    def test_max_retries_property_set_none(self):
        """Test max_retries setter with None defaults to 3."""
        config = ModelNodeConfiguration()
        config.max_retries = None
        assert config.execution.max_retries == 3

    def test_timeout_seconds_property_get(self):
        """Test timeout_seconds property delegation."""
        config = ModelNodeConfiguration()
        assert config.timeout_seconds == config.execution.timeout_seconds

    def test_timeout_seconds_property_set(self):
        """Test timeout_seconds property setter."""
        config = ModelNodeConfiguration()
        config.timeout_seconds = 60
        assert config.execution.timeout_seconds == 60

    def test_timeout_seconds_property_set_none(self):
        """Test timeout_seconds setter with None defaults to 30."""
        config = ModelNodeConfiguration()
        config.timeout_seconds = None
        assert config.execution.timeout_seconds == 30

    def test_batch_size_property_get(self):
        """Test batch_size property delegation."""
        config = ModelNodeConfiguration()
        assert config.batch_size == config.execution.batch_size

    def test_batch_size_property_set(self):
        """Test batch_size property setter."""
        config = ModelNodeConfiguration()
        config.batch_size = 10
        assert config.execution.batch_size == 10

    def test_batch_size_property_set_none(self):
        """Test batch_size setter with None defaults to 1."""
        config = ModelNodeConfiguration()
        config.batch_size = None
        assert config.execution.batch_size == 1

    def test_parallel_execution_property_get(self):
        """Test parallel_execution property delegation."""
        config = ModelNodeConfiguration()
        assert config.parallel_execution == config.execution.parallel_execution

    def test_parallel_execution_property_set(self):
        """Test parallel_execution property setter."""
        config = ModelNodeConfiguration()
        config.parallel_execution = True
        assert config.execution.parallel_execution is True

    def test_max_memory_mb_property_get(self):
        """Test max_memory_mb property delegation."""
        config = ModelNodeConfiguration()
        assert config.max_memory_mb == config.resources.max_memory_mb

    def test_max_memory_mb_property_set(self):
        """Test max_memory_mb property setter."""
        config = ModelNodeConfiguration()
        config.max_memory_mb = 2048
        assert config.resources.max_memory_mb == 2048

    def test_max_memory_mb_property_set_none(self):
        """Test max_memory_mb setter with None defaults to 1024."""
        config = ModelNodeConfiguration()
        config.max_memory_mb = None
        assert config.resources.max_memory_mb == 1024

    def test_max_cpu_percent_property_get(self):
        """Test max_cpu_percent property delegation."""
        config = ModelNodeConfiguration()
        assert config.max_cpu_percent == config.resources.max_cpu_percent

    def test_max_cpu_percent_property_set(self):
        """Test max_cpu_percent property setter."""
        config = ModelNodeConfiguration()
        config.max_cpu_percent = 75.0
        assert config.resources.max_cpu_percent == 75.0

    def test_max_cpu_percent_property_set_none(self):
        """Test max_cpu_percent setter with None defaults to 100.0."""
        config = ModelNodeConfiguration()
        config.max_cpu_percent = None
        assert config.resources.max_cpu_percent == 100.0

    def test_enable_caching_property_get(self):
        """Test enable_caching property delegation."""
        config = ModelNodeConfiguration()
        assert config.enable_caching == config.features.enable_caching

    def test_enable_caching_property_set(self):
        """Test enable_caching property setter."""
        config = ModelNodeConfiguration()
        config.enable_caching = True
        assert config.features.enable_caching is True

    def test_enable_monitoring_property_get(self):
        """Test enable_monitoring property delegation."""
        config = ModelNodeConfiguration()
        assert config.enable_monitoring == config.features.enable_monitoring

    def test_enable_monitoring_property_set(self):
        """Test enable_monitoring property setter."""
        config = ModelNodeConfiguration()
        config.enable_monitoring = True
        assert config.features.enable_monitoring is True

    def test_enable_tracing_property_get(self):
        """Test enable_tracing property delegation."""
        config = ModelNodeConfiguration()
        assert config.enable_tracing == config.features.enable_tracing

    def test_enable_tracing_property_set(self):
        """Test enable_tracing property setter."""
        config = ModelNodeConfiguration()
        config.enable_tracing = True
        assert config.features.enable_tracing is True

    def test_endpoint_property_get(self):
        """Test endpoint property delegation."""
        config = ModelNodeConfiguration()
        assert config.endpoint == config.connection.endpoint

    def test_endpoint_property_set(self):
        """Test endpoint property setter."""
        config = ModelNodeConfiguration()
        config.endpoint = "http://localhost:8080"
        assert config.connection.endpoint == "http://localhost:8080"

    def test_port_property_get(self):
        """Test port property delegation."""
        config = ModelNodeConfiguration()
        assert config.port == config.connection.port

    def test_port_property_set(self):
        """Test port property setter."""
        config = ModelNodeConfiguration()
        config.port = 8080
        assert config.connection.port == 8080

    def test_protocol_property_get(self):
        """Test protocol property delegation (converted to string)."""
        config = ModelNodeConfiguration()
        config.connection.protocol = EnumProtocolType.HTTP
        assert config.protocol == "http"

    def test_protocol_property_get_none(self):
        """Test protocol property get when None."""
        config = ModelNodeConfiguration()
        config.connection.protocol = None
        assert config.protocol is None

    def test_protocol_property_set(self):
        """Test protocol property setter from string."""
        config = ModelNodeConfiguration()
        config.protocol = "http"
        assert config.connection.protocol == EnumProtocolType.HTTP

    def test_protocol_property_set_none(self):
        """Test protocol property setter with None."""
        config = ModelNodeConfiguration()
        config.protocol = None
        assert config.connection.protocol is None

    def test_protocol_property_set_invalid(self):
        """Test protocol property setter with invalid value."""
        config = ModelNodeConfiguration()
        config.protocol = "INVALID"
        assert config.connection.protocol is None

    def test_custom_settings_property_get(self):
        """Test custom_settings property backward compatibility."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_strings["key1"] = "value1"

        assert config.custom_settings == {"key1": "value1"}

    def test_custom_settings_property_get_empty(self):
        """Test custom_settings property get when empty."""
        config = ModelNodeConfiguration()
        assert config.custom_settings is None

    def test_custom_settings_property_set(self):
        """Test custom_settings property setter."""
        config = ModelNodeConfiguration()
        config.custom_settings = {"key1": "value1", "key2": "value2"}

        assert "key1" in config.custom_properties.custom_strings
        assert config.custom_properties.custom_strings["key1"] == "value1"

    def test_custom_settings_property_set_none(self):
        """Test custom_settings property setter with None clears."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_strings["key1"] = "value1"

        config.custom_settings = None
        assert len(config.custom_properties.custom_strings) == 0

    def test_custom_flags_property_get(self):
        """Test custom_flags property backward compatibility."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_flags["flag1"] = True

        assert config.custom_flags == {"flag1": True}

    def test_custom_flags_property_get_empty(self):
        """Test custom_flags property get when empty."""
        config = ModelNodeConfiguration()
        assert config.custom_flags is None

    def test_custom_flags_property_set(self):
        """Test custom_flags property setter."""
        config = ModelNodeConfiguration()
        config.custom_flags = {"flag1": True, "flag2": False}

        assert config.custom_properties.custom_flags["flag1"] is True

    def test_custom_flags_property_set_none(self):
        """Test custom_flags property setter with None clears."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_flags["flag1"] = True

        config.custom_flags = None
        assert len(config.custom_properties.custom_flags) == 0

    def test_custom_limits_property_get(self):
        """Test custom_limits property converts float to int."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_numbers["limit1"] = 100.0

        limits = config.custom_limits
        assert limits == {"limit1": 100}
        assert isinstance(limits["limit1"], int)

    def test_custom_limits_property_get_empty(self):
        """Test custom_limits property get when empty."""
        config = ModelNodeConfiguration()
        assert config.custom_limits is None

    def test_custom_limits_property_set(self):
        """Test custom_limits property setter converts int to float."""
        config = ModelNodeConfiguration()
        config.custom_limits = {"limit1": 100, "limit2": 200}

        assert config.custom_properties.custom_numbers["limit1"] == 100.0
        assert isinstance(config.custom_properties.custom_numbers["limit1"], float)

    def test_custom_limits_property_set_none(self):
        """Test custom_limits property setter with None clears."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_numbers["limit1"] = 100.0

        config.custom_limits = None
        assert len(config.custom_properties.custom_numbers) == 0

    def test_get_configuration_summary(self):
        """Test get_configuration_summary method."""
        config = ModelNodeConfiguration()

        summary = config.get_configuration_summary()

        assert "execution" in summary
        assert "resources" in summary
        assert "features" in summary
        assert "connection" in summary
        assert "is_production_ready" in summary
        assert "is_performance_optimized" in summary
        assert "has_custom_settings" in summary

    def test_is_production_ready_true(self):
        """Test is_production_ready returns True when ready."""
        config = ModelNodeConfiguration(
            features=ModelNodeFeatureFlags.create_production(),
        )
        config.features.enable_monitoring = True

        assert config.is_production_ready() is True

    def test_is_production_ready_false(self):
        """Test is_production_ready returns False when not ready."""
        config = ModelNodeConfiguration()
        # Set features that make it NOT production ready
        # (either disable monitoring or enable tracing)
        config.features.enable_monitoring = False

        assert config.is_production_ready() is False

    def test_is_performance_optimized_true(self):
        """Test is_performance_optimized returns True when optimized."""
        config = ModelNodeConfiguration(
            execution=ModelNodeExecutionSettings.create_performance_optimized(),
        )
        config.features.enable_caching = True

        assert config.is_performance_optimized() is True

    def test_is_performance_optimized_false(self):
        """Test is_performance_optimized returns False when not optimized."""
        config = ModelNodeConfiguration()

        assert config.is_performance_optimized() is False

    def test_has_custom_settings_true(self):
        """Test has_custom_settings returns True when settings exist."""
        config = ModelNodeConfiguration()
        config.custom_properties.custom_strings["key1"] = "value1"

        assert config.has_custom_settings() is True

    def test_has_custom_settings_false(self):
        """Test has_custom_settings returns False when no settings."""
        config = ModelNodeConfiguration()

        assert config.has_custom_settings() is False

    def test_create_default_factory(self):
        """Test create_default factory method."""
        config = ModelNodeConfiguration.create_default()

        assert config.execution is not None
        assert config.resources is not None
        assert config.features is not None
        assert config.connection is not None

    def test_create_production_factory(self):
        """Test create_production factory method."""
        config = ModelNodeConfiguration.create_production(
            endpoint="http://api.example.com",
            port=8080,
        )

        assert config.is_production_ready() is True
        assert config.connection.endpoint == "http://api.example.com"
        assert config.connection.port == 8080

    def test_create_production_factory_no_endpoint(self):
        """Test create_production without endpoint."""
        config = ModelNodeConfiguration.create_production()

        assert config.is_production_ready() is True
        assert config.connection.endpoint is None

    def test_get_id_protocol(self):
        """Test get_id protocol method raises OnexError without ID field."""
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        config = ModelNodeConfiguration()

        with pytest.raises(OnexError) as exc_info:
            config.get_id()

        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        config = ModelNodeConfiguration()

        metadata = config.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        config = ModelNodeConfiguration()

        result = config.set_metadata({})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        config = ModelNodeConfiguration()

        serialized = config.serialize()
        assert isinstance(serialized, dict)
        assert "execution" in serialized
        assert "resources" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        config = ModelNodeConfiguration()

        assert config.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        # Should not raise error with extra fields
        config = ModelNodeConfiguration(extra_field="ignored")
        assert config.execution is not None

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        config = ModelNodeConfiguration()

        # Should validate new assignments
        config.execution = ModelNodeExecutionSettings()
        assert config.execution is not None
