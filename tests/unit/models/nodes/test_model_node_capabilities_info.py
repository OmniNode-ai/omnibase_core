"""
Unit tests for ModelNodeCapabilitiesInfo.

Tests all aspects of the node capabilities info model including:
- Model instantiation and validation
- Capabilities, operations, and dependencies management
- Performance metrics handling
- Summary generation
- Factory methods
- Protocol implementations
"""

from uuid import uuid4

import pytest

from omnibase_core.models.nodes.model_node_capabilities_info import (
    ModelNodeCapabilitiesInfo,
)


class TestModelNodeCapabilitiesInfo:
    """Test cases for ModelNodeCapabilitiesInfo."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        info = ModelNodeCapabilitiesInfo()

        assert info.capabilities == []
        assert info.supported_operations == []
        assert info.dependencies == []
        assert info.performance_metrics is None

    def test_model_instantiation_with_data(self):
        """Test model instantiation with data."""
        dep1 = uuid4()
        dep2 = uuid4()

        info = ModelNodeCapabilitiesInfo(
            capabilities=["cap1", "cap2"],
            supported_operations=["op1", "op2"],
            dependencies=[dep1, dep2],
            performance_metrics={"latency": 10.5, "throughput": 100.0},
        )

        assert info.capabilities == ["cap1", "cap2"]
        assert info.supported_operations == ["op1", "op2"]
        assert info.dependencies == [dep1, dep2]
        assert info.performance_metrics == {"latency": 10.5, "throughput": 100.0}

    def test_has_capabilities_true(self):
        """Test has_capabilities returns True when capabilities exist."""
        info = ModelNodeCapabilitiesInfo(capabilities=["cap1"])
        assert info.has_capabilities() is True

    def test_has_capabilities_false(self):
        """Test has_capabilities returns False when no capabilities."""
        info = ModelNodeCapabilitiesInfo()
        assert info.has_capabilities() is False

    def test_has_operations_true(self):
        """Test has_operations returns True when operations exist."""
        info = ModelNodeCapabilitiesInfo(supported_operations=["op1"])
        assert info.has_operations() is True

    def test_has_operations_false(self):
        """Test has_operations returns False when no operations."""
        info = ModelNodeCapabilitiesInfo()
        assert info.has_operations() is False

    def test_has_dependencies_true(self):
        """Test has_dependencies returns True when dependencies exist."""
        dep = uuid4()
        info = ModelNodeCapabilitiesInfo(dependencies=[dep])
        assert info.has_dependencies() is True

    def test_has_dependencies_false(self):
        """Test has_dependencies returns False when no dependencies."""
        info = ModelNodeCapabilitiesInfo()
        assert info.has_dependencies() is False

    def test_has_performance_metrics_true(self):
        """Test has_performance_metrics returns True when metrics exist."""
        info = ModelNodeCapabilitiesInfo(performance_metrics={"latency": 10.0})
        assert info.has_performance_metrics() is True

    def test_has_performance_metrics_false_none(self):
        """Test has_performance_metrics returns False when None."""
        info = ModelNodeCapabilitiesInfo()
        assert info.has_performance_metrics() is False

    def test_has_performance_metrics_false_empty(self):
        """Test has_performance_metrics returns False when empty dict."""
        info = ModelNodeCapabilitiesInfo(performance_metrics={})
        assert info.has_performance_metrics() is False

    def test_add_capability(self):
        """Test add_capability method."""
        info = ModelNodeCapabilitiesInfo()

        info.add_capability("cap1")
        assert "cap1" in info.capabilities
        assert len(info.capabilities) == 1

    def test_add_capability_no_duplicate(self):
        """Test add_capability doesn't add duplicates."""
        info = ModelNodeCapabilitiesInfo(capabilities=["cap1"])

        info.add_capability("cap1")
        assert info.capabilities.count("cap1") == 1

    def test_add_multiple_capabilities(self):
        """Test adding multiple capabilities."""
        info = ModelNodeCapabilitiesInfo()

        info.add_capability("cap1")
        info.add_capability("cap2")
        info.add_capability("cap3")

        assert len(info.capabilities) == 3
        assert "cap1" in info.capabilities
        assert "cap2" in info.capabilities
        assert "cap3" in info.capabilities

    def test_add_operation(self):
        """Test add_operation method."""
        info = ModelNodeCapabilitiesInfo()

        info.add_operation("op1")
        assert "op1" in info.supported_operations
        assert len(info.supported_operations) == 1

    def test_add_operation_no_duplicate(self):
        """Test add_operation doesn't add duplicates."""
        info = ModelNodeCapabilitiesInfo(supported_operations=["op1"])

        info.add_operation("op1")
        assert info.supported_operations.count("op1") == 1

    def test_add_dependency(self):
        """Test add_dependency method."""
        info = ModelNodeCapabilitiesInfo()
        dep = uuid4()

        info.add_dependency(dep)
        assert dep in info.dependencies
        assert len(info.dependencies) == 1

    def test_add_dependency_no_duplicate(self):
        """Test add_dependency doesn't add duplicates."""
        dep = uuid4()
        info = ModelNodeCapabilitiesInfo(dependencies=[dep])

        info.add_dependency(dep)
        assert info.dependencies.count(dep) == 1

    def test_set_performance_metric(self):
        """Test set_performance_metric method."""
        info = ModelNodeCapabilitiesInfo()

        info.set_performance_metric("latency", 10.5)
        assert info.performance_metrics is not None
        assert info.performance_metrics["latency"] == 10.5

    def test_set_performance_metric_updates_existing(self):
        """Test set_performance_metric updates existing metric."""
        info = ModelNodeCapabilitiesInfo(performance_metrics={"latency": 10.0})

        info.set_performance_metric("latency", 15.0)
        assert info.performance_metrics["latency"] == 15.0

    def test_set_multiple_performance_metrics(self):
        """Test setting multiple performance metrics."""
        info = ModelNodeCapabilitiesInfo()

        info.set_performance_metric("latency", 10.5)
        info.set_performance_metric("throughput", 100.0)
        info.set_performance_metric("error_rate", 0.01)

        assert len(info.performance_metrics) == 3

    def test_get_performance_metric_exists(self):
        """Test get_performance_metric for existing metric."""
        info = ModelNodeCapabilitiesInfo(performance_metrics={"latency": 10.5})

        value = info.get_performance_metric("latency")
        assert value == 10.5

    def test_get_performance_metric_not_exists(self):
        """Test get_performance_metric for non-existing metric."""
        info = ModelNodeCapabilitiesInfo(performance_metrics={"latency": 10.5})

        value = info.get_performance_metric("throughput")
        assert value is None

    def test_get_performance_metric_no_metrics(self):
        """Test get_performance_metric when no metrics exist."""
        info = ModelNodeCapabilitiesInfo()

        value = info.get_performance_metric("latency")
        assert value is None

    def test_get_capabilities_summary(self):
        """Test get_capabilities_summary method."""
        dep = uuid4()
        info = ModelNodeCapabilitiesInfo(
            capabilities=["cap1", "cap2"],
            supported_operations=["op1"],
            dependencies=[dep],
            performance_metrics={"latency": 10.0, "throughput": 100.0},
        )

        summary = info.get_capabilities_summary()

        assert summary["capabilities_count"] == 2
        assert summary["operations_count"] == 1
        assert summary["dependencies_count"] == 1
        assert summary["has_capabilities"] is True
        assert summary["has_operations"] is True
        assert summary["has_dependencies"] is True
        assert summary["has_performance_metrics"] is True
        assert summary["primary_capability"] == "cap1"
        assert summary["metrics_count"] == 2

    def test_get_capabilities_summary_empty(self):
        """Test get_capabilities_summary with empty data."""
        info = ModelNodeCapabilitiesInfo()

        summary = info.get_capabilities_summary()

        assert summary["capabilities_count"] == 0
        assert summary["operations_count"] == 0
        assert summary["dependencies_count"] == 0
        assert summary["has_capabilities"] is False
        assert summary["has_operations"] is False
        assert summary["has_dependencies"] is False
        assert summary["has_performance_metrics"] is False
        assert summary["primary_capability"] is None
        assert summary["metrics_count"] == 0

    def test_create_with_capabilities_factory(self):
        """Test create_with_capabilities factory method."""
        info = ModelNodeCapabilitiesInfo.create_with_capabilities(
            capabilities=["cap1", "cap2"],
            operations=["op1", "op2"],
        )

        assert info.capabilities == ["cap1", "cap2"]
        assert info.supported_operations == ["op1", "op2"]
        assert info.performance_metrics is None

    def test_create_with_capabilities_no_operations(self):
        """Test create_with_capabilities without operations."""
        info = ModelNodeCapabilitiesInfo.create_with_capabilities(
            capabilities=["cap1"],
        )

        assert info.capabilities == ["cap1"]
        assert info.supported_operations == []

    def test_create_with_dependencies_factory(self):
        """Test create_with_dependencies factory method."""
        dep1 = uuid4()
        dep2 = uuid4()

        info = ModelNodeCapabilitiesInfo.create_with_dependencies(
            dependencies=[dep1, dep2],
        )

        assert info.dependencies == [dep1, dep2]
        assert info.performance_metrics is None

    def test_get_id_protocol(self):
        """Test get_id protocol method raises OnexError without ID field."""
        from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError

        info = ModelNodeCapabilitiesInfo()

        with pytest.raises(OnexError) as exc_info:
            info.get_id()

        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        info = ModelNodeCapabilitiesInfo()

        metadata = info.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        info = ModelNodeCapabilitiesInfo()

        result = info.set_metadata({"capabilities": ["new_cap"]})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        info = ModelNodeCapabilitiesInfo(capabilities=["cap1"])

        serialized = info.serialize()
        assert isinstance(serialized, dict)
        assert "capabilities" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        info = ModelNodeCapabilitiesInfo()

        assert info.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        # Should not raise error with extra fields
        info = ModelNodeCapabilitiesInfo(
            capabilities=["cap1"],
            extra_field="ignored",
        )
        assert info.capabilities == ["cap1"]

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        info = ModelNodeCapabilitiesInfo()

        # Should validate new assignments
        info.capabilities = ["new_cap"]
        assert info.capabilities == ["new_cap"]
