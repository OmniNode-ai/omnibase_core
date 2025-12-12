"""
Test suite for MixinIntrospectionPublisher.

Tests introspection data gathering, event publishing, and capability extraction.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.mixins.mixin_introspection_publisher import (
    MixinIntrospectionPublisher,
)
from omnibase_core.mixins.mixin_node_introspection_data import (
    MixinNodeIntrospectionData,
)
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.models.discovery.model_nodeintrospectionevent import (
    ModelNodeIntrospectionEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class MockNode(MixinIntrospectionPublisher):
    """Mock node class that uses MixinIntrospectionPublisher."""

    def __init__(self):
        self._node_id = uuid4()
        self.event_bus = None
        self.metadata_loader = None

    def get_node_type(self) -> str:
        """Return valid ONEX node type for testing."""
        return "compute"


class TestMixinIntrospectionPublisher:
    """Test MixinIntrospectionPublisher functionality."""

    def test_initialization(self):
        """Test mixin provides required methods."""
        node = MockNode()

        assert hasattr(node, "_publish_introspection_event")
        assert hasattr(node, "_gather_introspection_data")
        assert hasattr(node, "_extract_node_name")
        assert hasattr(node, "_extract_node_version")
        assert hasattr(node, "_extract_node_capabilities")

    def test_extract_node_name_from_class(self):
        """Test extracting node name from class name."""
        node = MockNode()

        name = node._extract_node_name()

        assert isinstance(name, str)
        assert len(name) > 0

    def test_extract_node_name_with_node_prefix(self):
        """Test extracting node name when class starts with 'Node'."""

        class NodeTestTool(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()

        node = NodeTestTool()
        name = node._extract_node_name()

        assert isinstance(name, str)
        # Should convert CamelCase to snake_case
        assert "_" in name or name.islower()

    def test_extract_node_name_with_metadata_loader(self):
        """Test extracting node name from metadata loader."""
        node = MockNode()

        # Create mock metadata loader
        mock_metadata = Mock()
        mock_metadata.name = "custom_node_name"

        mock_loader = Mock()
        mock_loader.metadata = mock_metadata

        node.metadata_loader = mock_loader

        name = node._extract_node_name()

        assert name == "custom_node_name"

    def test_extract_node_name_with_namespace(self):
        """Test extracting node name from namespace."""
        node = MockNode()

        # Create mock metadata with namespace
        mock_metadata = Mock()
        mock_metadata.name = None
        mock_metadata.namespace = "omnibase.tools.node_test_tool"

        mock_loader = Mock()
        mock_loader.metadata = mock_metadata

        node.metadata_loader = mock_loader

        name = node._extract_node_name()

        assert isinstance(name, str)

    def test_extract_node_version_default(self):
        """Test extracting default node version."""
        node = MockNode()

        version = node._extract_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_extract_node_version_from_metadata(self):
        """Test extracting node version from metadata loader."""
        node = MockNode()

        # Create mock metadata with version
        mock_metadata = Mock()
        mock_metadata.version = "2.5.3"

        mock_loader = Mock()
        mock_loader.metadata = mock_metadata

        node.metadata_loader = mock_loader

        version = node._extract_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 2
        assert version.minor == 5
        assert version.patch == 3

    def test_extract_node_version_invalid_format(self):
        """Test extracting node version with invalid format falls back to default."""
        node = MockNode()

        # Create mock metadata with invalid version
        mock_metadata = Mock()
        mock_metadata.version = "invalid"

        mock_loader = Mock()
        mock_loader.metadata = mock_metadata

        node.metadata_loader = mock_loader

        version = node._extract_node_version()

        # Should fall back to default
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_extract_node_capabilities_basic(self):
        """Test extracting basic node capabilities."""
        from omnibase_core.models.common.model_typed_metadata import (
            ModelNodeCapabilitiesMetadata,
        )

        node = MockNode()

        capabilities = node._extract_node_capabilities()

        assert isinstance(capabilities, ModelNodeCapabilities)
        assert isinstance(capabilities.actions, list)
        assert isinstance(capabilities.protocols, list)
        # metadata is now a typed Pydantic model, not a dict
        assert isinstance(capabilities.metadata, ModelNodeCapabilitiesMetadata)

    def test_extract_node_capabilities_with_metadata(self):
        """Test extracting capabilities with metadata loader."""
        node = MockNode()

        # Create mock metadata
        mock_metadata = Mock()
        mock_metadata.description = "Test node description"
        mock_metadata.author = "Test Author"
        mock_metadata.copyright = "Test Copyright"

        mock_loader = Mock()
        mock_loader.metadata = mock_metadata

        node.metadata_loader = mock_loader

        capabilities = node._extract_node_capabilities()

        assert capabilities.metadata.description == "Test node description"
        assert capabilities.metadata.author == "Test Author"
        assert capabilities.metadata.copyright == "Test Copyright"

    def test_extract_node_actions_from_methods(self):
        """Test extracting actions from node methods."""

        class NodeWithActions(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()

            def health_check(self):
                pass

            def validate(self):
                pass

            def process(self):
                pass

        node = NodeWithActions()
        actions = node._extract_node_actions()

        assert "health_check" in actions
        assert "validate" in actions
        assert "process" in actions

    def test_extract_node_actions_default(self):
        """Test that health_check is always in actions."""
        node = MockNode()

        actions = node._extract_node_actions()

        assert "health_check" in actions

    def test_detect_supported_protocols_basic(self):
        """Test detecting basic supported protocols."""
        node = MockNode()

        protocols = node._detect_supported_protocols()

        assert isinstance(protocols, list)
        assert "event_bus" in protocols

    def test_detect_supported_protocols_with_mcp(self):
        """Test detecting MCP protocol support."""

        class NodeWithMCP(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()
                self.supports_mcp = True

        node = NodeWithMCP()
        protocols = node._detect_supported_protocols()

        assert "mcp" in protocols

    def test_detect_supported_protocols_with_http(self):
        """Test detecting HTTP protocol support."""

        class NodeWithHTTP(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()
                self.supports_http = True

        node = NodeWithHTTP()
        protocols = node._detect_supported_protocols()

        assert "http" in protocols

    def test_generate_discovery_tags_basic(self):
        """Test generating basic discovery tags."""
        node = MockNode()

        tags = node._generate_discovery_tags()

        assert isinstance(tags, list)
        assert "event_driven" in tags

    def test_generate_discovery_tags_from_class_name(self):
        """Test generating tags from class name patterns."""

        class NodeGeneratorTool(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()

        node = NodeGeneratorTool()
        tags = node._generate_discovery_tags()

        assert "node" in tags
        assert "generator" in tags

    def test_generate_discovery_tags_with_mcp(self):
        """Test generating tags with MCP support."""

        class NodeWithMCP(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()
                self.supports_mcp = True

        node = NodeWithMCP()
        tags = node._generate_discovery_tags()

        assert "mcp" in tags

    def test_detect_health_endpoint_with_method(self):
        """Test detecting health endpoint when health_check method exists."""

        class NodeWithHealth(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()

            def health_check(self):
                pass

        node = NodeWithHealth()
        endpoint = node._detect_health_endpoint()

        assert endpoint is not None
        assert "/health/" in endpoint

    def test_detect_health_endpoint_without_method(self):
        """Test detecting health endpoint when health_check method doesn't exist."""
        node = MockNode()

        endpoint = node._detect_health_endpoint()

        # Should return None if no health_check method
        assert endpoint is None or "/health/" in endpoint

    def test_gather_introspection_data_basic(self):
        """Test gathering basic introspection data."""
        node = MockNode()

        data = node._gather_introspection_data()

        assert isinstance(data, MixinNodeIntrospectionData)
        assert isinstance(data.node_name, str)
        assert isinstance(data.version, ModelSemVer)
        assert isinstance(data.capabilities, ModelNodeCapabilities)
        assert isinstance(data.tags, list)

    def test_gather_introspection_data_with_error(self):
        """Test gathering introspection data with error falls back gracefully."""
        node = MockNode()

        # Force an error in extraction
        with patch.object(
            node, "_extract_node_name", side_effect=RuntimeError("Test error")
        ):
            data = node._gather_introspection_data()

        # Should return fallback data
        assert isinstance(data, MixinNodeIntrospectionData)
        assert data.version.major == 1

    def test_publish_introspection_event_without_event_bus(self):
        """Test publishing introspection event without event bus."""
        node = MockNode()
        node.event_bus = None

        # Should not raise, just return early
        node._publish_introspection_event()

    def test_publish_introspection_event_with_event_bus(self):
        """Test publishing introspection event with event bus."""
        node = MockNode()

        # Create mock event bus
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        node.event_bus = mock_event_bus

        # Publish introspection event
        node._publish_introspection_event()

        # Verify event bus publish was called
        assert mock_event_bus.publish.called

    def test_publish_with_retry_basic(self):
        """Test publishing with retry logic."""
        node = MockNode()

        # Create mock event bus
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        node.event_bus = mock_event_bus

        # Create real introspection event
        introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
            node_id=node._node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type="compute",
            actions=["health_check"],
            tags=["test"],
            correlation_id=uuid4(),
        )

        node._publish_with_retry(introspection_event)

        # Verify publish was called
        mock_event_bus.publish.assert_called_once()

    def test_publish_with_retry_on_failure(self):
        """Test publishing with retry on failure."""
        node = MockNode()

        # Create mock event bus that fails first, then succeeds
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock(
            side_effect=[RuntimeError("Publish failed"), None]
        )

        node.event_bus = mock_event_bus

        # Create real introspection event
        introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
            node_id=node._node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type="compute",
            actions=["health_check"],
            tags=["test"],
            correlation_id=uuid4(),
        )

        node._publish_with_retry(introspection_event, max_retries=2)

        # Verify publish was retried
        assert mock_event_bus.publish.call_count == 2

    def test_publish_with_retry_max_retries_exceeded(self):
        """Test publishing with retry when max retries exceeded."""
        node = MockNode()

        # Create mock event bus that always fails
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock(side_effect=RuntimeError("Publish failed"))

        node.event_bus = mock_event_bus

        # Create real introspection event
        introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
            node_id=node._node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type="compute",
            actions=["health_check"],
            tags=["test"],
            correlation_id=uuid4(),
        )

        with pytest.raises(RuntimeError):
            node._publish_with_retry(introspection_event, max_retries=2)

    def test_publish_with_retry_without_event_bus(self):
        """Test publishing with retry without event bus."""
        node = MockNode()
        node.event_bus = None

        # Create real introspection event
        introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
            node_id=node._node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            node_type="compute",
            actions=["health_check"],
            tags=["test"],
            correlation_id=uuid4(),
        )

        # Should not raise
        node._publish_with_retry(introspection_event)

    def test_extract_node_name_exception_handling(self):
        """Test extract_node_name handles exceptions gracefully."""
        node = MockNode()

        # Create mock metadata that raises exception
        mock_loader = Mock()
        mock_loader.metadata = Mock(side_effect=RuntimeError("Metadata error"))

        node.metadata_loader = mock_loader

        # Should fall back to class name
        name = node._extract_node_name()

        assert isinstance(name, str)
        assert len(name) > 0

    def test_extract_node_version_exception_handling(self):
        """Test extract_node_version handles exceptions gracefully."""
        node = MockNode()

        # Create mock metadata that raises exception
        mock_loader = Mock()
        mock_loader.metadata = Mock(side_effect=RuntimeError("Metadata error"))

        node.metadata_loader = mock_loader

        # Should fall back to default version
        version = node._extract_node_version()

        assert isinstance(version, ModelSemVer)
        assert version.major == 1

    def test_publish_introspection_event_with_validation_error(self):
        """Test publishing introspection event with validation error."""
        node = MockNode()

        # Create mock event bus
        mock_event_bus = Mock()
        node.event_bus = mock_event_bus

        # Mock _gather_introspection_data to raise ValidationError
        with patch.object(
            node,
            "_gather_introspection_data",
            side_effect=ValidationError.from_exception_data(
                "test_error",
                [
                    {
                        "type": "missing",
                        "loc": ("field",),
                        "msg": "Field required",
                        "input": {},
                    }
                ],
            ),
        ):
            with pytest.raises(ValidationError):
                node._publish_introspection_event()

    def test_publish_introspection_event_with_generic_exception(self):
        """Test publishing introspection event with generic exception."""
        node = MockNode()

        # Create mock event bus
        mock_event_bus = Mock()
        node.event_bus = mock_event_bus

        # Mock _gather_introspection_data to raise exception
        with patch.object(
            node, "_gather_introspection_data", side_effect=RuntimeError("Test error")
        ):
            with pytest.raises(RuntimeError):
                node._publish_introspection_event()

    def test_extract_node_capabilities_exception_handling(self):
        """Test extract_node_capabilities handles exceptions gracefully."""
        node = MockNode()

        # Create mock metadata that raises exception
        mock_loader = Mock()
        mock_loader.metadata = Mock(side_effect=RuntimeError("Metadata error"))

        node.metadata_loader = mock_loader

        # Should still return capabilities with defaults
        capabilities = node._extract_node_capabilities()

        assert isinstance(capabilities, ModelNodeCapabilities)

    def test_node_id_as_string(self):
        """Test handling node_id as string."""
        node = MockNode()
        node._node_id = "test-node-id"

        # Should handle string node_id gracefully
        data = node._gather_introspection_data()

        assert isinstance(data, MixinNodeIntrospectionData)

    def test_node_id_as_uuid(self):
        """Test handling node_id as UUID."""
        node = MockNode()
        node._node_id = uuid4()

        # Should handle UUID node_id
        data = node._gather_introspection_data()

        assert isinstance(data, MixinNodeIntrospectionData)

    def test_generate_discovery_tags_uniqueness(self):
        """Test that discovery tags are unique."""

        class NodeWithDuplicateTags(MixinIntrospectionPublisher):
            def __init__(self):
                self._node_id = uuid4()
                # Force some duplicate characteristics
                self.supports_mcp = True

        node = NodeWithDuplicateTags()
        tags = node._generate_discovery_tags()

        # Tags should be unique (list converted to set internally)
        assert len(tags) == len(set(tags))
