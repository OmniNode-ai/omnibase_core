"""
Test Node Information Model functionality.

Validates that the ModelNodeInformation works correctly with
configuration handling, validation, and metadata features.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional

from omnibase_core.models.nodes import ModelNodeInformation


class TestNodeInformationModel:
    """Test ModelNodeInformation functionality."""

    def test_basic_creation_with_required_fields(self):
        """Test basic creation with only required fields."""
        node_info = ModelNodeInformation(
            node_id="test_001",
            node_name="TEST_NODE",
            node_type="compute",
            node_version="1.0.0",
        )

        assert node_info.node_id == "test_001"
        assert node_info.node_name == "TEST_NODE"
        assert node_info.node_type == "compute"
        assert node_info.node_version == "1.0.0"

        # Check defaults
        assert node_info.description is None
        assert node_info.author is None
        assert node_info.created_at is None
        assert node_info.updated_at is None
        assert len(node_info.capabilities) == 0
        assert len(node_info.supported_operations) == 0
        assert node_info.status == "active"
        assert node_info.health == "healthy"
        assert node_info.performance_metrics is None
        assert len(node_info.dependencies) == 0

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        created_time = datetime.now()
        updated_time = datetime.now()

        node_info = ModelNodeInformation(
            node_id="full_001",
            node_name="FULL_NODE",
            node_type="orchestrator",
            node_version="2.1.0",
            description="Full-featured test node",
            author="Test Author",
            created_at=created_time,
            updated_at=updated_time,
            capabilities=["supports_dry_run", "supports_batch_processing"],
            supported_operations=["generate", "validate", "execute"],
            status="active",
            health="healthy",
            performance_metrics={"avg_response_time": 1.5, "success_rate": 0.98},
            dependencies=["NODE_A", "NODE_B"],
        )

        assert node_info.node_id == "full_001"
        assert node_info.node_name == "FULL_NODE"
        assert node_info.node_type == "orchestrator"
        assert node_info.node_version == "2.1.0"
        assert node_info.description == "Full-featured test node"
        assert node_info.author == "Test Author"
        assert node_info.created_at == created_time
        assert node_info.updated_at == updated_time
        assert "supports_dry_run" in node_info.capabilities
        assert "generate" in node_info.supported_operations
        assert node_info.status == "active"
        assert node_info.health == "healthy"
        assert node_info.performance_metrics["success_rate"] == 0.98
        assert "NODE_A" in node_info.dependencies

    def test_configuration_handling(self):
        """Test node configuration handling."""
        from omnibase_core.models.nodes.model_node_information import ModelNodeConfiguration

        # Test with custom configuration
        custom_config = ModelNodeConfiguration(
            max_retries=5,
            timeout_seconds=30,
            batch_size=100,
            parallel_execution=True,
            max_memory_mb=512,
            max_cpu_percent=80.0,
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=True,
            endpoint="http://test.example.com",
            port=8080,
            protocol="http",
        )

        node_info = ModelNodeInformation(
            node_id="config_test",
            node_name="CONFIG_NODE",
            node_type="effect",
            node_version="1.0.0",
            configuration=custom_config,
        )

        assert node_info.configuration.max_retries == 5
        assert node_info.configuration.timeout_seconds == 30
        assert node_info.configuration.batch_size == 100
        assert node_info.configuration.parallel_execution
        assert node_info.configuration.max_memory_mb == 512
        assert node_info.configuration.max_cpu_percent == 80.0
        assert node_info.configuration.enable_caching
        assert node_info.configuration.endpoint == "http://test.example.com"
        assert node_info.configuration.port == 8080

    def test_default_configuration(self):
        """Test default configuration creation."""
        node_info = ModelNodeInformation(
            node_id="default_config",
            node_name="DEFAULT_NODE",
            node_type="compute",
            node_version="1.0.0",
        )

        # Should have default configuration
        config = node_info.configuration
        assert config is not None
        assert config.max_retries is None
        assert config.timeout_seconds is None
        assert not config.parallel_execution
        assert not config.enable_caching
        assert config.enable_monitoring  # Default True

    def test_from_dict_method(self):
        """Test creating from dictionary."""
        data = {
            "id": "dict_001",
            "name": "DICT_NODE",
            "type": "reducer",
            "version": "1.5.0",
            "description": "Node from dict",
            "capabilities": ["supports_correlation_id"],
            "status": "active",
        }

        node_info = ModelNodeInformation.from_dict(data)
        assert node_info is not None
        assert node_info.node_id == "dict_001"
        assert node_info.node_name == "DICT_NODE"
        assert node_info.node_type == "reducer"
        assert node_info.node_version == "1.5.0"
        assert node_info.description == "Node from dict"

    def test_from_dict_with_field_mapping(self):
        """Test from_dict with field mapping."""
        data = {
            "id": "mapped_001",
            "name": "MAPPED_NODE",
            "type": "effect",
            # Missing version - should default
        }

        node_info = ModelNodeInformation.from_dict(data)
        assert node_info is not None
        assert node_info.node_id == "mapped_001"
        assert node_info.node_name == "MAPPED_NODE"
        assert node_info.node_type == "effect"
        assert node_info.node_version == "1.0.0"  # Default

    def test_from_dict_with_none(self):
        """Test from_dict with None input."""
        result = ModelNodeInformation.from_dict(None)
        assert result is None

    def test_from_dict_with_defaults(self):
        """Test from_dict applies defaults for missing fields."""
        minimal_data = {}

        node_info = ModelNodeInformation.from_dict(minimal_data)
        assert node_info is not None
        assert node_info.node_id == "unknown"
        assert node_info.node_name == "unknown"
        assert node_info.node_type == "generic"
        assert node_info.node_version == "1.0.0"

    def test_capabilities_list_handling(self):
        """Test capabilities list handling."""
        capabilities = [
            "supports_dry_run",
            "supports_batch_processing",
            "telemetry_enabled",
            "supports_correlation_id",
        ]

        node_info = ModelNodeInformation(
            node_id="cap_test",
            node_name="CAP_NODE",
            node_type="compute",
            node_version="1.0.0",
            capabilities=capabilities,
        )

        assert len(node_info.capabilities) == 4
        for cap in capabilities:
            assert cap in node_info.capabilities

    def test_supported_operations_handling(self):
        """Test supported operations list handling."""
        operations = ["generate", "validate", "transform", "execute"]

        node_info = ModelNodeInformation(
            node_id="ops_test",
            node_name="OPS_NODE",
            node_type="compute",
            node_version="1.0.0",
            supported_operations=operations,
        )

        assert len(node_info.supported_operations) == 4
        for op in operations:
            assert op in node_info.supported_operations

    def test_status_and_health_tracking(self):
        """Test status and health tracking."""
        statuses = ["active", "inactive", "maintenance", "deprecated"]
        health_states = ["healthy", "degraded", "unhealthy", "unknown"]

        for status in statuses:
            for health in health_states:
                node_info = ModelNodeInformation(
                    node_id=f"test_{status}_{health}",
                    node_name="TEST_NODE",
                    node_type="compute",
                    node_version="1.0.0",
                    status=status,
                    health=health,
                )

                assert node_info.status == status
                assert node_info.health == health

    def test_performance_metrics_handling(self):
        """Test performance metrics handling."""
        metrics = {
            "avg_response_time": 2.5,
            "success_rate": 0.95,
            "error_rate": 0.05,
            "throughput": 1000.0,
            "memory_usage": 256.7,
            "cpu_usage": 45.2,
        }

        node_info = ModelNodeInformation(
            node_id="perf_test",
            node_name="PERF_NODE",
            node_type="compute",
            node_version="1.0.0",
            performance_metrics=metrics,
        )

        assert node_info.performance_metrics is not None
        assert node_info.performance_metrics["avg_response_time"] == 2.5
        assert node_info.performance_metrics["success_rate"] == 0.95
        assert node_info.performance_metrics["throughput"] == 1000.0

    def test_dependencies_tracking(self):
        """Test dependencies tracking."""
        dependencies = [
            "TEMPLATE_ENGINE",
            "SCHEMA_VALIDATOR",
            "ERROR_HANDLER",
        ]

        node_info = ModelNodeInformation(
            node_id="deps_test",
            node_name="DEPS_NODE",
            node_type="effect",
            node_version="1.0.0",
            dependencies=dependencies,
        )

        assert len(node_info.dependencies) == 3
        for dep in dependencies:
            assert dep in node_info.dependencies

    def test_datetime_handling(self):
        """Test datetime field handling."""
        now = datetime.now()

        node_info = ModelNodeInformation(
            node_id="time_test",
            node_name="TIME_NODE",
            node_type="compute",
            node_version="1.0.0",
            created_at=now,
            updated_at=now,
        )

        assert node_info.created_at == now
        assert node_info.updated_at == now

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        original = ModelNodeInformation(
            node_id="serial_001",
            node_name="SERIAL_NODE",
            node_type="reducer",
            node_version="1.2.0",
            description="Serialization test",
            capabilities=["supports_dry_run"],
            supported_operations=["validate"],
            performance_metrics={"success_rate": 0.99},
        )

        # Serialize
        serialized = original.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["node_id"] == "serial_001"

        # Deserialize
        restored = ModelNodeInformation.model_validate(serialized)
        assert restored.node_id == original.node_id
        assert restored.node_name == original.node_name
        assert restored.node_type == original.node_type
        assert restored.description == original.description

    def test_configuration_custom_settings(self):
        """Test configuration with custom settings."""
        from omnibase_core.models.nodes.model_node_information import ModelNodeConfiguration

        custom_config = ModelNodeConfiguration(
            custom_settings={"api_key": "secret", "region": "us-west-1"},
            custom_flags={"debug_mode": True, "verbose_logging": False},
            custom_limits={"max_connections": 100, "rate_limit": 1000},
        )

        node_info = ModelNodeInformation(
            node_id="custom_test",
            node_name="CUSTOM_NODE",
            node_type="compute",
            node_version="1.0.0",
            configuration=custom_config,
        )

        config = node_info.configuration
        assert config.custom_settings["api_key"] == "secret"
        assert config.custom_flags["debug_mode"] is True
        assert config.custom_limits["max_connections"] == 100

    def test_edge_cases_and_validation(self):
        """Test edge cases and validation."""
        # Test with empty strings (should be allowed)
        node_info = ModelNodeInformation(
            node_id="",
            node_name="",
            node_type="",
            node_version="",
        )
        # Should create successfully with empty strings

        # Test with very long strings
        long_string = "x" * 1000
        node_info = ModelNodeInformation(
            node_id=long_string,
            node_name=long_string,
            node_type=long_string,
            node_version=long_string,
            description=long_string,
        )
        assert len(node_info.description) == 1000

    def test_archetype_specific_configurations(self):
        """Test configurations specific to node archetypes."""
        # COMPUTE node configuration
        compute_info = ModelNodeInformation(
            node_id="compute_001",
            node_name="CONTRACT_TO_MODEL",
            node_type="compute",
            node_version="1.0.0",
            capabilities=["supports_dry_run", "supports_schema_validation"],
            supported_operations=["generate", "validate", "transform"],
        )

        assert compute_info.node_type == "compute"
        assert "generate" in compute_info.supported_operations

        # EFFECT node configuration
        effect_info = ModelNodeInformation(
            node_id="effect_001",
            node_name="FILE_GENERATOR",
            node_type="effect",
            node_version="1.0.0",
            capabilities=["supports_batch_processing"],
            supported_operations=["write", "create", "modify"],
            dependencies=["TEMPLATE_ENGINE"],
        )

        assert effect_info.node_type == "effect"
        assert "TEMPLATE_ENGINE" in effect_info.dependencies

        # REDUCER node configuration
        reducer_info = ModelNodeInformation(
            node_id="reducer_001",
            node_name="VALIDATION_ENGINE",
            node_type="reducer",
            node_version="1.0.0",
            capabilities=["supports_error_recovery"],
            supported_operations=["validate", "aggregate", "check"],
        )

        assert reducer_info.node_type == "reducer"
        assert "validate" in reducer_info.supported_operations

        # ORCHESTRATOR node configuration
        orchestrator_info = ModelNodeInformation(
            node_id="orchestrator_001",
            node_name="NODE_MANAGER_RUNNER",
            node_type="orchestrator",
            node_version="1.0.0",
            capabilities=["telemetry_enabled", "supports_event_discovery"],
            supported_operations=["manage", "coordinate", "route"],
        )

        assert orchestrator_info.node_type == "orchestrator"
        assert "coordinate" in orchestrator_info.supported_operations

    @pytest.mark.parametrize("node_type", [
        "compute", "effect", "reducer", "orchestrator"
    ])
    def test_archetype_node_types(self, node_type):
        """Test different archetype node types."""
        node_info = ModelNodeInformation(
            node_id=f"{node_type}_test",
            node_name=f"{node_type.upper()}_NODE",
            node_type=node_type,
            node_version="1.0.0",
        )

        assert node_info.node_type == node_type
        assert node_info.node_name == f"{node_type.upper()}_NODE"

    def test_performance_with_large_data(self):
        """Test performance with large data sets."""
        # Large capabilities list
        large_capabilities = [f"capability_{i}" for i in range(100)]

        # Large operations list
        large_operations = [f"operation_{i}" for i in range(50)]

        # Large dependencies list
        large_dependencies = [f"dependency_{i}" for i in range(75)]

        # Large performance metrics
        large_metrics = {f"metric_{i}": float(i) for i in range(200)}

        node_info = ModelNodeInformation(
            node_id="large_test",
            node_name="LARGE_NODE",
            node_type="compute",
            node_version="1.0.0",
            capabilities=large_capabilities,
            supported_operations=large_operations,
            dependencies=large_dependencies,
            performance_metrics=large_metrics,
        )

        assert len(node_info.capabilities) == 100
        assert len(node_info.supported_operations) == 50
        assert len(node_info.dependencies) == 75
        assert len(node_info.performance_metrics) == 200

        # Should serialize efficiently
        serialized = node_info.model_dump()
        assert len(serialized["capabilities"]) == 100