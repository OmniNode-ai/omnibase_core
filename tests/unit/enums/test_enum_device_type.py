"""
Unit tests for Device Type enums.

Tests all device-related enums including:
- EnumDeviceType
- EnumDeviceLocation
- EnumDeviceStatus
- EnumAgentHealth
- EnumPriority
- EnumRoutingStrategy

Tests cover:
- Enum value validation
- String representation
- JSON/YAML serialization
- Pydantic integration
- Comprehensive scenarios
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_device_type import (
    EnumAgentHealth,
    EnumDeviceLocation,
    EnumDeviceStatus,
    EnumDeviceType,
    EnumPriority,
    EnumRoutingStrategy,
)


@pytest.mark.unit
class TestEnumDeviceType:
    """Test EnumDeviceType enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "MAC_STUDIO": "mac_studio",
            "MACBOOK_AIR": "macbook_air",
            "MAC_MINI": "mac_mini",
            "GENERIC_MAC": "generic_mac",
            "LINUX_SERVER": "linux_server",
            "WINDOWS_SERVER": "windows_server",
            "DOCKER_CONTAINER": "docker_container",
            "KUBERNETES_POD": "kubernetes_pod",
            "CLOUD_INSTANCE": "cloud_instance",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            device_type = getattr(EnumDeviceType, name)
            assert device_type.value == value

    def test_device_categories(self):
        """Test different device categories."""
        # Mac devices
        mac_devices = [
            EnumDeviceType.MAC_STUDIO,
            EnumDeviceType.MACBOOK_AIR,
            EnumDeviceType.MAC_MINI,
            EnumDeviceType.GENERIC_MAC,
        ]
        for device in mac_devices:
            assert "mac" in device.value

        # Server devices
        assert "server" in EnumDeviceType.LINUX_SERVER.value
        assert "server" in EnumDeviceType.WINDOWS_SERVER.value

        # Container/orchestration devices
        assert "container" in EnumDeviceType.DOCKER_CONTAINER.value
        assert "pod" in EnumDeviceType.KUBERNETES_POD.value

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DeviceModel(BaseModel):
            device_type: EnumDeviceType

        model = DeviceModel(device_type=EnumDeviceType.MAC_STUDIO)
        assert model.device_type == EnumDeviceType.MAC_STUDIO

        # Test string assignment
        model = DeviceModel(device_type="docker_container")
        assert model.device_type == EnumDeviceType.DOCKER_CONTAINER


@pytest.mark.unit
class TestEnumDeviceLocation:
    """Test EnumDeviceLocation enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "HOME": "at_home",
            "REMOTE": "remote",
            "OFFICE": "office",
            "CLOUD": "cloud",
            "EDGE": "edge",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            location = getattr(EnumDeviceLocation, name)
            assert location.value == value

    def test_location_types(self):
        """Test different location types."""
        assert EnumDeviceLocation.HOME == "at_home"
        assert EnumDeviceLocation.CLOUD == "cloud"
        assert EnumDeviceLocation.EDGE == "edge"

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        locations = list(EnumDeviceLocation)
        assert len(locations) == 6


@pytest.mark.unit
class TestEnumDeviceStatus:
    """Test EnumDeviceStatus enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "ONLINE": "online",
            "OFFLINE": "offline",
            "MAINTENANCE": "maintenance",
            "DEGRADED": "degraded",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            status = getattr(EnumDeviceStatus, name)
            assert status.value == value

    def test_status_states(self):
        """Test different status states."""
        # Operational states
        assert EnumDeviceStatus.ONLINE == "online"
        assert EnumDeviceStatus.OFFLINE == "offline"

        # Warning/error states
        assert EnumDeviceStatus.MAINTENANCE == "maintenance"
        assert EnumDeviceStatus.DEGRADED == "degraded"

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class StatusModel(BaseModel):
            status: EnumDeviceStatus

        model = StatusModel(status=EnumDeviceStatus.ONLINE)
        assert model.status == EnumDeviceStatus.ONLINE

        # Test invalid value
        with pytest.raises(ValidationError):
            StatusModel(status="invalid_status")


@pytest.mark.unit
class TestEnumAgentHealth:
    """Test EnumAgentHealth enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "HEALTHY": "healthy",
            "DEGRADED": "degraded",
            "UNHEALTHY": "unhealthy",
            "CRITICAL": "critical",
            "STARTING": "starting",
            "STOPPING": "stopping",
            "ERROR": "error",
            "UNKNOWN": "unknown",
        }

        for name, value in expected_values.items():
            health = getattr(EnumAgentHealth, name)
            assert health.value == value

    def test_health_severity_levels(self):
        """Test different health severity levels."""
        # Good health
        assert EnumAgentHealth.HEALTHY == "healthy"

        # Degraded states
        assert EnumAgentHealth.DEGRADED == "degraded"
        assert EnumAgentHealth.UNHEALTHY == "unhealthy"

        # Critical states
        assert EnumAgentHealth.CRITICAL == "critical"
        assert EnumAgentHealth.ERROR == "error"

        # Transitional states
        assert EnumAgentHealth.STARTING == "starting"
        assert EnumAgentHealth.STOPPING == "stopping"

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        health_states = list(EnumAgentHealth)
        assert len(health_states) == 8


@pytest.mark.unit
class TestEnumPriority:
    """Test EnumPriority enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "NORMAL": "normal",
            "LOW": "low",
            "BACKGROUND": "background",
        }

        for name, value in expected_values.items():
            priority = getattr(EnumPriority, name)
            assert priority.value == value

    def test_priority_ordering(self):
        """Test that priorities are ordered correctly."""
        priorities = list(EnumPriority)
        assert len(priorities) == 5

        # Verify order from highest to lowest priority
        assert priorities[0] == EnumPriority.CRITICAL
        assert priorities[-1] == EnumPriority.BACKGROUND

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class PriorityModel(BaseModel):
            priority: EnumPriority

        model = PriorityModel(priority=EnumPriority.HIGH)
        model_dict = model.model_dump()
        assert model_dict == {"priority": "high"}


@pytest.mark.unit
class TestEnumRoutingStrategy:
    """Test EnumRoutingStrategy enum."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "ROUND_ROBIN": "round_robin",
            "LEAST_LOADED": "least_loaded",
            "CLOSEST": "closest",
            "FASTEST": "fastest",
            "RANDOM": "random",
            "CAPABILITY_MATCH": "capability_match",
        }

        for name, value in expected_values.items():
            strategy = getattr(EnumRoutingStrategy, name)
            assert strategy.value == value

    def test_routing_strategies(self):
        """Test different routing strategies."""
        # Load-based strategies
        assert EnumRoutingStrategy.LEAST_LOADED == "least_loaded"
        assert EnumRoutingStrategy.ROUND_ROBIN == "round_robin"

        # Performance-based strategies
        assert EnumRoutingStrategy.FASTEST == "fastest"
        assert EnumRoutingStrategy.CLOSEST == "closest"

        # Selection-based strategies
        assert EnumRoutingStrategy.RANDOM == "random"
        assert EnumRoutingStrategy.CAPABILITY_MATCH == "capability_match"

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        strategies = list(EnumRoutingStrategy)
        assert len(strategies) == 6


@pytest.mark.unit
class TestDeviceEnumsIntegration:
    """Test integration scenarios with multiple device enums."""

    def test_comprehensive_device_model(self):
        """Test a comprehensive model using multiple device enums."""

        class DeviceConfiguration(BaseModel):
            device_type: EnumDeviceType
            location: EnumDeviceLocation
            status: EnumDeviceStatus
            agent_health: EnumAgentHealth
            priority: EnumPriority
            routing_strategy: EnumRoutingStrategy

        # Create a comprehensive device configuration
        config = DeviceConfiguration(
            device_type=EnumDeviceType.MAC_STUDIO,
            location=EnumDeviceLocation.HOME,
            status=EnumDeviceStatus.ONLINE,
            agent_health=EnumAgentHealth.HEALTHY,
            priority=EnumPriority.HIGH,
            routing_strategy=EnumRoutingStrategy.CAPABILITY_MATCH,
        )

        # Verify all fields
        assert config.device_type == EnumDeviceType.MAC_STUDIO
        assert config.location == EnumDeviceLocation.HOME
        assert config.status == EnumDeviceStatus.ONLINE
        assert config.agent_health == EnumAgentHealth.HEALTHY
        assert config.priority == EnumPriority.HIGH
        assert config.routing_strategy == EnumRoutingStrategy.CAPABILITY_MATCH

        # Test serialization
        config_dict = config.model_dump()
        assert config_dict["device_type"] == "mac_studio"
        assert config_dict["location"] == "at_home"
        assert config_dict["status"] == "online"

    def test_device_status_health_correlation(self):
        """Test correlation between device status and agent health."""
        # Online device should ideally have healthy agent
        online_status = EnumDeviceStatus.ONLINE
        healthy_agent = EnumAgentHealth.HEALTHY
        assert online_status == "online"
        assert healthy_agent == "healthy"

        # Degraded device might have degraded agent
        degraded_status = EnumDeviceStatus.DEGRADED
        degraded_agent = EnumAgentHealth.DEGRADED
        assert degraded_status == "degraded"
        assert degraded_agent == "degraded"

    def test_json_serialization_all_enums(self):
        """Test JSON serialization for all device enums."""
        data = {
            "device_type": EnumDeviceType.KUBERNETES_POD.value,
            "location": EnumDeviceLocation.CLOUD.value,
            "status": EnumDeviceStatus.ONLINE.value,
            "agent_health": EnumAgentHealth.HEALTHY.value,
            "priority": EnumPriority.CRITICAL.value,
            "routing_strategy": EnumRoutingStrategy.FASTEST.value,
        }

        json_str = json.dumps(data)
        loaded_data = json.loads(json_str)

        # Verify all values survived serialization
        assert loaded_data["device_type"] == "kubernetes_pod"
        assert loaded_data["location"] == "cloud"
        assert loaded_data["status"] == "online"
        assert loaded_data["agent_health"] == "healthy"
        assert loaded_data["priority"] == "critical"
        assert loaded_data["routing_strategy"] == "fastest"

    def test_yaml_serialization_all_enums(self):
        """Test YAML serialization for all device enums."""
        import yaml

        data = {
            "device_type": EnumDeviceType.DOCKER_CONTAINER.value,
            "location": EnumDeviceLocation.EDGE.value,
            "status": EnumDeviceStatus.MAINTENANCE.value,
        }

        yaml_str = yaml.dump(data, default_flow_style=False)
        loaded_data = yaml.safe_load(yaml_str)

        assert loaded_data["device_type"] == "docker_container"
        assert loaded_data["location"] == "edge"
        assert loaded_data["status"] == "maintenance"


@pytest.mark.unit
class TestDeviceEnumsEdgeCases:
    """Test edge cases across all device enums."""

    def test_all_enums_inherit_from_str(self):
        """Test that all enums inherit from str for JSON compatibility."""
        enums_to_test = [
            EnumDeviceType,
            EnumDeviceLocation,
            EnumDeviceStatus,
            EnumAgentHealth,
            EnumPriority,
            EnumRoutingStrategy,
        ]

        for enum_class in enums_to_test:
            # Get first enum value
            first_value = next(iter(enum_class))
            # Should be comparable to string
            assert first_value == first_value.value

    def test_no_duplicate_values_in_any_enum(self):
        """Test that no enum has duplicate values."""
        enums_to_test = [
            EnumDeviceType,
            EnumDeviceLocation,
            EnumDeviceStatus,
            EnumAgentHealth,
            EnumPriority,
            EnumRoutingStrategy,
        ]

        for enum_class in enums_to_test:
            values = [e.value for e in enum_class]
            assert len(values) == len(set(values)), (
                f"{enum_class.__name__} has duplicate values"
            )

    def test_case_sensitivity_all_enums(self):
        """Test that all enum values use lowercase with underscores."""
        enums_to_test = [
            EnumDeviceType,
            EnumDeviceLocation,
            EnumDeviceStatus,
            EnumAgentHealth,
            EnumPriority,
            EnumRoutingStrategy,
        ]

        for enum_class in enums_to_test:
            for enum_value in enum_class:
                # All values should be lowercase
                assert enum_value.value == enum_value.value.lower()
                # Should not contain spaces
                assert " " not in enum_value.value

    def test_unknown_values_present(self):
        """Test that appropriate enums have UNKNOWN values."""
        # Device type, location, status, and agent health should have UNKNOWN
        assert hasattr(EnumDeviceType, "UNKNOWN")
        assert hasattr(EnumDeviceLocation, "UNKNOWN")
        assert hasattr(EnumDeviceStatus, "UNKNOWN")
        assert hasattr(EnumAgentHealth, "UNKNOWN")

        # Verify UNKNOWN values
        assert EnumDeviceType.UNKNOWN == "unknown"
        assert EnumDeviceLocation.UNKNOWN == "unknown"
        assert EnumDeviceStatus.UNKNOWN == "unknown"
        assert EnumAgentHealth.UNKNOWN == "unknown"


@pytest.mark.unit
class TestDeviceEnumsComprehensiveScenarios:
    """Test comprehensive real-world scenarios."""

    def test_cloud_deployment_scenario(self):
        """Test cloud deployment device configuration."""
        cloud_config = {
            "device_type": EnumDeviceType.KUBERNETES_POD,
            "location": EnumDeviceLocation.CLOUD,
            "status": EnumDeviceStatus.ONLINE,
            "agent_health": EnumAgentHealth.HEALTHY,
            "priority": EnumPriority.HIGH,
            "routing_strategy": EnumRoutingStrategy.LEAST_LOADED,
        }

        # Verify cloud configuration makes sense
        assert cloud_config["device_type"] == EnumDeviceType.KUBERNETES_POD
        assert cloud_config["location"] == EnumDeviceLocation.CLOUD
        assert "pod" in cloud_config["device_type"].value
        assert cloud_config["location"].value == "cloud"

    def test_edge_device_scenario(self):
        """Test edge device configuration."""
        edge_config = {
            "device_type": EnumDeviceType.LINUX_SERVER,
            "location": EnumDeviceLocation.EDGE,
            "status": EnumDeviceStatus.ONLINE,
            "agent_health": EnumAgentHealth.HEALTHY,
            "priority": EnumPriority.NORMAL,
            "routing_strategy": EnumRoutingStrategy.CLOSEST,
        }

        # Verify edge configuration
        assert edge_config["location"] == EnumDeviceLocation.EDGE
        assert edge_config["routing_strategy"] == EnumRoutingStrategy.CLOSEST
        assert edge_config["location"].value == "edge"

    def test_maintenance_scenario(self):
        """Test device in maintenance scenario."""
        maintenance_device = {
            "status": EnumDeviceStatus.MAINTENANCE,
            "agent_health": EnumAgentHealth.STOPPING,
            "priority": EnumPriority.LOW,
        }

        # Verify maintenance state
        assert maintenance_device["status"] == EnumDeviceStatus.MAINTENANCE
        assert maintenance_device["agent_health"] == EnumAgentHealth.STOPPING
        assert maintenance_device["status"].value == "maintenance"

    def test_routing_strategy_selection(self):
        """Test selecting appropriate routing strategies."""
        # High-priority tasks should use capability matching
        high_priority_strategy = EnumRoutingStrategy.CAPABILITY_MATCH
        assert high_priority_strategy == "capability_match"

        # Balanced load distribution
        balanced_strategy = EnumRoutingStrategy.ROUND_ROBIN
        assert balanced_strategy == "round_robin"

        # Performance-critical tasks
        performance_strategy = EnumRoutingStrategy.FASTEST
        assert performance_strategy == "fastest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
