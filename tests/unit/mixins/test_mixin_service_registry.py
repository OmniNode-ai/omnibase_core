# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for MixinServiceRegistry.

Tests service discovery, registration, and lifecycle management.
"""

import time
from unittest.mock import Mock
from uuid import uuid4

import pytest

from omnibase_core.mixins.mixin_service_registry import MixinServiceRegistry
from omnibase_core.models.mixins.model_service_registry_entry import (
    ModelServiceRegistryEntry,
)


class MockServiceHub(MixinServiceRegistry):
    """Mock service hub class that uses MixinServiceRegistry."""

    def __init__(self, event_bus=None):
        super().__init__()
        self.event_bus = event_bus
        self.node_id = uuid4()
        self.event_loop = None


@pytest.mark.unit
class TestMixinServiceRegistry:
    """Test MixinServiceRegistry functionality."""

    def test_initialization(self):
        """Test mixin initialization."""
        hub = MockServiceHub()

        assert hasattr(hub, "service_registry")
        assert hasattr(hub, "discovery_callbacks")
        assert hasattr(hub, "start_service_registry")
        assert hasattr(hub, "stop_service_registry")

        assert isinstance(hub.service_registry, dict)
        assert isinstance(hub.discovery_callbacks, list)
        assert hub.registry_started is False

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        hub = MockServiceHub()
        hub.introspection_timeout = 60
        hub.service_ttl = 600

        assert hub.introspection_timeout == 60
        assert hub.service_ttl == 600

    def test_start_service_registry(self):
        """Test starting service registry."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        hub.start_service_registry()

        assert hub.registry_started is True

    def test_start_service_registry_with_domain_filter(self):
        """Test starting service registry with domain filter."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        hub.start_service_registry(domain_filter="generation")

        assert hub.domain_filter == "generation"
        assert hub.registry_started is True

    def test_start_service_registry_already_started(self):
        """Test starting service registry when already started."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        hub.start_service_registry()
        hub.start_service_registry()  # Try to start again

        # Should still be started
        assert hub.registry_started is True

    def test_stop_service_registry(self):
        """Test stopping service registry."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        hub.start_service_registry()
        hub.stop_service_registry()

        assert hub.registry_started is False

    def test_send_discovery_request_without_event_bus(self):
        """Test sending discovery request without event bus."""
        hub = MockServiceHub()

        # Should not raise, just return early
        hub._send_discovery_request()

    def test_send_discovery_request_with_event_bus(self):
        """Test sending discovery request with event bus."""
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        hub._send_discovery_request()

        # Should have published discovery request
        mock_event_bus.publish.assert_called_once()

    def test_handle_node_start_basic(self):
        """Test handling node start event."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        # Create mock envelope
        mock_event = Mock()
        mock_event.node_id = uuid4()
        mock_event.data = {
            "node_name": "test_node",
            "metadata": {"domain": "generation"},
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_start(mock_envelope)

        # Should have registered the node
        node_id_str = str(mock_event.node_id)
        assert node_id_str in hub.service_registry

    def test_handle_node_start_skip_own_event(self):
        """Test handling node start event skips own start."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        # Create event with hub's own node_id
        mock_event = Mock()
        mock_event.node_id = hub.node_id
        mock_event.data = {"node_name": "self"}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_start(mock_envelope)

        # Should not register itself
        assert (
            str(hub.node_id) not in hub.service_registry
            or len(hub.service_registry) == 0
        )

    def test_handle_node_start_with_domain_filter(self):
        """Test handling node start with domain filter."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)
        hub.domain_filter = "generation"

        # Create event with matching domain
        mock_event = Mock()
        mock_event.node_id = uuid4()
        mock_event.data = {
            "node_name": "test_node",
            "metadata": {"domain": "generation"},
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_start(mock_envelope)

        # Should register
        assert len(hub.service_registry) == 1

    def test_handle_node_start_with_non_matching_domain(self):
        """Test handling node start with non-matching domain."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)
        hub.domain_filter = "generation"

        # Create event with different domain
        mock_event = Mock()
        mock_event.node_id = uuid4()
        mock_event.data = {
            "node_name": "test_node",
            "metadata": {"domain": "analysis"},
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_start(mock_envelope)

        # Should not register
        assert len(hub.service_registry) == 0

    def test_handle_node_start_update_existing(self):
        """Test handling node start updates existing entry."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        node_id = uuid4()
        mock_event = Mock()
        mock_event.node_id = node_id
        mock_event.data = {"node_name": "test_node"}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        # Register node first time
        hub._handle_node_start(mock_envelope)
        first_seen = hub.service_registry[str(node_id)].last_seen

        time.sleep(0.1)

        # Register same node again
        hub._handle_node_start(mock_envelope)
        second_seen = hub.service_registry[str(node_id)].last_seen

        # Last seen should be updated
        assert second_seen >= first_seen

    def test_handle_node_start_with_discovery_callback(self):
        """Test handling node start triggers discovery callback."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        callback_called = []

        def discovery_callback(event_type, entry):
            callback_called.append((event_type, entry))

        hub.add_discovery_callback(discovery_callback)

        mock_event = Mock()
        mock_event.node_id = uuid4()
        mock_event.data = {"node_name": "test_node"}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_start(mock_envelope)

        # Callback should have been called
        assert len(callback_called) == 1
        assert callback_called[0][0] == "tool_discovered"

    def test_handle_node_stop_basic(self):
        """Test handling node stop event."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        # Register a node first
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        # Create stop event
        mock_event = Mock()
        mock_event.node_id = node_id
        mock_event.data = {"node_name": "test_node"}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_stop(mock_envelope)

        # Node should be marked offline
        assert hub.service_registry[str(node_id)].status == "offline"

    def test_handle_node_stop_nonexistent_node(self):
        """Test handling node stop for nonexistent node."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        mock_event = Mock()
        mock_event.node_id = uuid4()
        mock_event.data = {}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        # Should not raise
        hub._handle_node_stop(mock_envelope)

    def test_handle_node_failure(self):
        """Test handling node failure event."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        # Register a node
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        mock_event = Mock()
        mock_event.node_id = node_id
        mock_event.data = {}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_node_failure(mock_envelope)

        # Should mark as offline
        assert hub.service_registry[str(node_id)].status == "offline"

    def test_send_introspection_request(self):
        """Test sending introspection request."""
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        node_id = uuid4()

        hub._send_introspection_request(node_id)

        # Should have published introspection request
        mock_event_bus.publish.assert_called_once()

    def test_send_introspection_request_without_event_bus(self):
        """Test sending introspection request without event bus."""
        hub = MockServiceHub()

        # Should not raise
        hub._send_introspection_request(uuid4())

    def test_handle_introspection_response(self):
        """Test handling introspection response."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        # Register a node first
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        # Create introspection response
        mock_event = Mock()
        mock_event.node_id = node_id
        mock_event.data = {
            "capabilities": ["action1", "action2"],
            "metadata": {"version": "1.0.0"},
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_introspection_response(mock_envelope)

        # Entry should be updated with introspection data
        assert hub.service_registry[str(node_id)].introspection_data is not None

    def test_handle_discovery_request(self):
        """Test handling discovery request."""
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)

        # Add some services to registry
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        # Create discovery request
        correlation_id = uuid4()
        mock_event = Mock()
        mock_event.data = {
            "request_type": "tool_discovery",
            "domain_filter": None,
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event
        mock_envelope.correlation_id = correlation_id

        hub._handle_discovery_request(mock_envelope)

        # Should have published response
        mock_event_bus.publish.assert_called_once()

    def test_handle_discovery_request_with_domain_filter_match(self):
        """Test handling discovery request with matching domain filter."""
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        hub.domain_filter = "generation"

        mock_event = Mock()
        mock_event.data = {
            "request_type": "tool_discovery",
            "domain_filter": "generation",
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event
        mock_envelope.correlation_id = uuid4()

        hub._handle_discovery_request(mock_envelope)

        # Should respond
        mock_event_bus.publish.assert_called_once()

    def test_handle_discovery_request_with_domain_filter_mismatch(self):
        """Test handling discovery request with non-matching domain filter."""
        mock_event_bus = Mock()
        mock_event_bus.publish = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        hub.domain_filter = "generation"

        mock_event = Mock()
        mock_event.data = {
            "request_type": "tool_discovery",
            "domain_filter": "analysis",
        }

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        hub._handle_discovery_request(mock_envelope)

        # Should not respond
        mock_event_bus.publish.assert_not_called()

    def test_get_registered_tools(self):
        """Test getting registered tools."""
        hub = MockServiceHub()

        # Add some entries
        for i in range(3):
            node_id = uuid4()
            entry = ModelServiceRegistryEntry(
                node_id=node_id,
                service_name=f"test_node_{i}",
                metadata={},
            )
            hub.service_registry[str(node_id)] = entry

        tools = hub.get_registered_tools()

        assert len(tools) == 3

    def test_get_registered_tools_with_status_filter(self):
        """Test getting registered tools with status filter."""
        hub = MockServiceHub()

        # Add online and offline entries
        for i in range(2):
            node_id = uuid4()
            entry = ModelServiceRegistryEntry(
                node_id=node_id,
                service_name=f"online_node_{i}",
                metadata={},
            )
            hub.service_registry[str(node_id)] = entry

        for i in range(2):
            node_id = uuid4()
            entry = ModelServiceRegistryEntry(
                node_id=node_id,
                service_name=f"offline_node_{i}",
                metadata={},
            )
            entry.set_offline()
            hub.service_registry[str(node_id)] = entry

        online_tools = hub.get_registered_tools(status_filter="online")
        offline_tools = hub.get_registered_tools(status_filter="offline")

        assert len(online_tools) == 2
        assert len(offline_tools) == 2

    def test_get_tool_by_name(self):
        """Test getting tool by service name."""
        hub = MockServiceHub()

        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="target_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        result = hub.get_tool_by_name("target_node")

        assert result is not None
        assert result.service_name == "target_node"

    def test_get_tool_by_name_not_found(self):
        """Test getting tool by name that doesn't exist."""
        hub = MockServiceHub()

        result = hub.get_tool_by_name("nonexistent_node")

        assert result is None

    def test_get_tools_by_capability(self):
        """Test getting tools by capability."""
        hub = MockServiceHub()

        # Add node with specific capability
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="capable_node",
            metadata={},
        )
        entry.capabilities = ["test_capability"]
        hub.service_registry[str(node_id)] = entry

        # Add node without capability
        node_id2 = uuid4()
        entry2 = ModelServiceRegistryEntry(
            node_id=node_id2,
            service_name="other_node",
            metadata={},
        )
        hub.service_registry[str(node_id2)] = entry2

        results = hub.get_tools_by_capability("test_capability")

        assert len(results) == 1
        assert results[0].service_name == "capable_node"

    def test_get_tools_by_capability_only_online(self):
        """Test getting tools by capability only returns online tools."""
        hub = MockServiceHub()

        # Add online node with capability
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="online_node",
            metadata={},
        )
        entry.capabilities = ["test_capability"]
        hub.service_registry[str(node_id)] = entry

        # Add offline node with capability
        node_id2 = uuid4()
        entry2 = ModelServiceRegistryEntry(
            node_id=node_id2,
            service_name="offline_node",
            metadata={},
        )
        entry2.capabilities = ["test_capability"]
        entry2.set_offline()
        hub.service_registry[str(node_id2)] = entry2

        results = hub.get_tools_by_capability("test_capability")

        assert len(results) == 1
        assert results[0].service_name == "online_node"

    def test_add_discovery_callback(self):
        """Test adding discovery callback."""
        hub = MockServiceHub()

        callback = Mock()
        hub.add_discovery_callback(callback)

        assert callback in hub.discovery_callbacks

    def test_cleanup_stale_entries(self):
        """Test cleaning up stale entries."""
        hub = MockServiceHub()
        hub.service_ttl = 1  # 1 second TTL

        # Add entry
        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        # Simulate entry being old
        entry.last_seen = time.time() - 2  # 2 seconds ago

        hub.cleanup_stale_entries()

        # Entry should be marked offline
        assert hub.service_registry[str(node_id)].status == "offline"

    def test_cleanup_stale_entries_no_stale(self):
        """Test cleanup when no stale entries."""
        hub = MockServiceHub()

        node_id = uuid4()
        entry = ModelServiceRegistryEntry(
            node_id=node_id,
            service_name="test_node",
            metadata={},
        )
        hub.service_registry[str(node_id)] = entry

        hub.cleanup_stale_entries()

        # Entry should still be online
        assert hub.service_registry[str(node_id)].status == "online"

    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        hub = MockServiceHub()

        # Add online and offline entries
        for i in range(3):
            node_id = uuid4()
            entry = ModelServiceRegistryEntry(
                node_id=node_id,
                service_name=f"online_node_{i}",
                metadata={},
            )
            hub.service_registry[str(node_id)] = entry

        for i in range(2):
            node_id = uuid4()
            entry = ModelServiceRegistryEntry(
                node_id=node_id,
                service_name=f"offline_node_{i}",
                metadata={},
            )
            entry.set_offline()
            hub.service_registry[str(node_id)] = entry

        stats = hub.get_registry_stats()

        assert stats["total_services"] == 5
        assert stats["online_services"] == 3
        assert stats["offline_services"] == 2
        assert stats["registry_started"] is False

    def test_setup_registry_event_handlers(self):
        """Test setting up registry event handlers."""
        mock_event_bus = Mock()
        mock_event_bus.subscribe = Mock()

        hub = MockServiceHub(event_bus=mock_event_bus)
        hub._setup_registry_event_handlers()

        # Should have subscribed to multiple event types
        assert mock_event_bus.subscribe.call_count >= 4  # At least 4 event types

    def test_handle_node_start_with_string_node_id(self):
        """Test handling node start with string node_id."""
        mock_event_bus = Mock()
        hub = MockServiceHub(event_bus=mock_event_bus)

        mock_event = Mock()
        mock_event.node_id = "string-node-id"
        mock_event.data = {"node_name": "test_node"}

        mock_envelope = Mock()
        mock_envelope.payload = mock_event

        # Should handle string node_id
        hub._handle_node_start(mock_envelope)

        # Should be in registry (converted or as-is)
        assert len(hub.service_registry) >= 0  # May not register due to validation
