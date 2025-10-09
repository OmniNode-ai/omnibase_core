"""
Unit tests for ModelNodeInformation.

Tests all aspects of the node information model including:
- Model instantiation with composed sub-models
- Property delegations
- Node status and health checks
- Capabilities and operations management
- Summary generation
- Factory methods
- Protocol implementations
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_registry_status import EnumRegistryStatus
from omnibase_core.models.core.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.models.nodes.model_node_capabilities_info import (
    ModelNodeCapabilitiesInfo,
)
from omnibase_core.models.nodes.model_node_configuration import ModelNodeConfiguration
from omnibase_core.models.nodes.model_node_core_info import ModelNodeCoreInfo
from omnibase_core.models.nodes.model_node_information import ModelNodeInformation


class TestModelNodeInformation:
    """Test cases for ModelNodeInformation."""

    def test_model_instantiation_with_core_info(self):
        """Test that model can be instantiated with core info."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.core_info is not None
        assert info.capabilities is not None
        assert info.configuration is not None

    def test_model_with_all_components(self):
        """Test model with all composed sub-models."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        capabilities = ModelNodeCapabilitiesInfo()
        configuration = ModelNodeConfiguration()

        info = ModelNodeInformation(
            core_info=core_info,
            capabilities=capabilities,
            configuration=configuration,
        )

        assert info.core_info == core_info
        assert info.capabilities == capabilities
        assert info.configuration == configuration

    def test_node_id_property_get(self):
        """Test node_id property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.node_id == core_info.node_id

    def test_node_id_property_set(self):
        """Test node_id property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        new_id = uuid4()
        info.node_id = new_id
        assert info.core_info.node_id == new_id

    def test_node_name_property_get(self):
        """Test node_name property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.node_name == "test_node"

    def test_node_name_property_set(self):
        """Test node_name property setter updates display name."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.node_name = "new_name"
        assert info.node_name == "new_name"

    def test_node_type_property_get(self):
        """Test node_type property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.METHOD,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.node_type == EnumMetadataNodeType.METHOD

    def test_node_type_property_set(self):
        """Test node_type property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.node_type = EnumMetadataNodeType.CLASS
        assert info.core_info.node_type == EnumMetadataNodeType.CLASS

    def test_node_version_property_get(self):
        """Test node_version property delegation."""
        version = parse_semver_from_string("2.1.3")
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=version,
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.node_version == version

    def test_node_version_property_set(self):
        """Test node_version property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        new_version = parse_semver_from_string("2.0.0")
        info.node_version = new_version
        assert info.core_info.node_version == new_version

    def test_description_property_get(self):
        """Test description property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
            description="Test description",
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.description == "Test description"

    def test_description_property_set(self):
        """Test description property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.description = "New description"
        assert info.core_info.description == "New description"

    def test_author_property_get(self):
        """Test author property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.author is None or isinstance(info.author, str)

    def test_author_property_set(self):
        """Test author property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.author = "Test Author"
        # Author updates display_name
        assert info.author == "Test Author"

    def test_created_at_property_get(self):
        """Test created_at property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        # create_streamlined sets timestamps to None by default
        assert info.created_at is None

    def test_created_at_property_set(self):
        """Test created_at property setter."""
        from datetime import datetime

        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        new_time = datetime.now()
        info.created_at = new_time
        assert info.core_info.created_at == new_time

    def test_updated_at_property_get(self):
        """Test updated_at property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        # create_streamlined sets timestamps to None by default
        assert info.updated_at is None

    def test_status_property_get(self):
        """Test status property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert isinstance(info.status, EnumMetadataNodeStatus)

    def test_status_property_set(self):
        """Test status property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.status = EnumMetadataNodeStatus.ACTIVE
        assert info.core_info.status == EnumMetadataNodeStatus.ACTIVE

    def test_health_property_get(self):
        """Test health property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert isinstance(info.health, EnumRegistryStatus)

    def test_health_property_set(self):
        """Test health property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.health = EnumRegistryStatus.HEALTHY
        assert info.core_info.health == EnumRegistryStatus.HEALTHY

    def test_supported_operations_property(self):
        """Test supported_operations property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)
        info.capabilities.add_operation("op1")

        assert "op1" in info.supported_operations

    def test_dependencies_property(self):
        """Test dependencies property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)
        dep = uuid4()
        info.capabilities.add_dependency(dep)

        assert dep in info.dependencies

    def test_performance_metrics_property_get(self):
        """Test performance_metrics property delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.performance_metrics is None or isinstance(
            info.performance_metrics, dict
        )

    def test_performance_metrics_property_set(self):
        """Test performance_metrics property setter."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.performance_metrics = {"latency": 10.5}
        assert info.capabilities.performance_metrics == {"latency": 10.5}

    def test_is_active_method(self):
        """Test is_active method delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)
        info.status = EnumMetadataNodeStatus.ACTIVE

        assert info.is_active() is True

    def test_is_healthy_method(self):
        """Test is_healthy method delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)
        info.health = EnumRegistryStatus.HEALTHY

        assert info.is_healthy() is True

    def test_has_capabilities_method(self):
        """Test has_capabilities method delegation."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)
        info.add_capability("cap1")

        assert info.has_capabilities() is True

    def test_add_capability_method(self):
        """Test add_capability method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.add_capability("new_capability")
        assert "new_capability" in info.capabilities.capabilities

    def test_add_operation_method(self):
        """Test add_operation method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info.add_operation("new_operation")
        assert "new_operation" in info.supported_operations

    def test_add_dependency_method(self):
        """Test add_dependency method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        dep = uuid4()
        info.add_dependency(dep)
        assert dep in info.dependencies

    def test_get_information_summary(self):
        """Test get_information_summary method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        summary = info.get_information_summary()

        assert summary.core_info is not None
        assert summary.capabilities is not None
        assert summary.configuration is not None

    def test_is_fully_configured_true(self):
        """Test is_fully_configured returns True when fully configured."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
            description="Description",
        )
        info = ModelNodeInformation(
            core_info=core_info,
            configuration=ModelNodeConfiguration.create_production(),
        )
        info.add_capability("cap1")

        assert info.is_fully_configured() is True

    def test_is_fully_configured_false(self):
        """Test is_fully_configured returns False when not configured."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.is_fully_configured() is False

    def test_create_simple_factory(self):
        """Test create_simple factory method."""
        info = ModelNodeInformation.create_simple(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
            description="Test description",
        )

        assert info.node_name == "test_node"
        assert info.node_type == EnumMetadataNodeType.FUNCTION
        assert info.description == "Test description"

    def test_create_with_capabilities_factory(self):
        """Test create_with_capabilities factory method."""
        info = ModelNodeInformation.create_with_capabilities(
            node_name="test_node",
            node_type=EnumMetadataNodeType.METHOD,
            node_version=parse_semver_from_string("1.0.0"),
            capabilities=["cap1", "cap2"],
            operations=["op1"],
        )

        assert info.node_name == "test_node"
        assert "cap1" in info.capabilities.capabilities
        assert "op1" in info.supported_operations

    def test_get_id_protocol(self):
        """Test get_id protocol method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        info_id = info.get_id()
        assert isinstance(info_id, str)

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        serialized = info.serialize()
        assert isinstance(serialized, dict)
        assert "core_info" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name="test_node",
            node_type=EnumMetadataNodeType.FUNCTION,
            node_version=parse_semver_from_string("1.0.0"),
        )
        info = ModelNodeInformation(core_info=core_info)

        assert info.validate_instance() is True
