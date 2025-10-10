"""
Comprehensive Test Suite for Unified Discovery System

Tests the complete hybrid discovery system including:
- Discovery coordinator request-response patterns
- Unified discovery API combining catalog and real-time discovery
- Integration with registry coordination hub
"""

import time
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from omnibase_core.constants.event_types import (
    NODE_INTROSPECTION_EVENT,
    REAL_TIME_INTROSPECTION_RESPONSE,
)
from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
from omnibase_core.models.discovery.model_current_tool_availability import (
    ModelCurrentToolAvailability,
)
from omnibase_core.models.discovery.model_introspection_filters import (
    ModelIntrospectionFilters,
)
from omnibase_core.models.discovery.model_introspection_response_event import (
    ModelIntrospectionResponseEvent,
)
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
    ModelNodeIntrospectionEvent,
)
from omnibase_core.models.discovery.model_request_introspection_event import (
    ModelRequestIntrospectionEvent,
)

# TODO: Re-enable these imports when the tools are implemented
# from omnibase_core.nodes.node_registry.v1_0_0.tools.tool_discovery_coordinator import (
#     ToolDiscoveryCoordinator,
# )
# from omnibase_core.nodes.node_registry.v1_0_0.tools.tool_unified_discovery import (
#     ToolUnifiedDiscovery,
# )
from omnibase_core.primitives.model_semver import ModelSemVer

# Marker for skipping tests that require unimplemented tools
pytest.skip(
    "Tools not yet implemented: ToolDiscoveryCoordinator, ToolUnifiedDiscovery",
    allow_module_level=True,
)


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    event_bus = Mock()
    event_bus.subscribe = Mock()
    event_bus.unsubscribe = Mock()
    event_bus.publish = Mock()
    return event_bus


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock()
    logger.emit_log_event_sync = Mock()
    return logger


@pytest.fixture
def sample_introspection_filters():
    """Create sample introspection filters for testing."""
    return ModelIntrospectionFilters(
        node_names=["node_test"],
        capabilities=["test_capability"],
        protocols=["test_protocol"],
        tags=["test_tag"],
        status=EnumNodeCurrentStatus.READY,
    )


@pytest.fixture
def sample_node_introspection_event():
    """Create a sample node introspection event for testing."""
    capabilities = ModelNodeCapabilities(
        actions=["test_action"],
        protocols=["test_protocol"],
        metadata={"description": "Test node"},
    )

    return ModelNodeIntrospectionEvent(
        node_id="test_node_001",
        node_name="node_test",
        version=ModelSemVer(major=1, minor=0, patch=0),
        capabilities=capabilities,
        tags=["test_tag"],
        health_endpoint="/health",
    )


@pytest.fixture
def sample_introspection_response_event():
    """Create a sample introspection response event for testing."""
    return ModelIntrospectionResponseEvent(
        node_id="test_node_001",
        correlation_id=uuid4(),
        node_name="node_test",
        version=ModelSemVer(major=1, minor=0, patch=0),
        current_status=EnumNodeCurrentStatus.READY,
        capabilities=ModelCurrentToolAvailability(
            available_tools=["test_tool"],
            tool_status={},
            total_tools=1,
        ),
    )


class TestToolDiscoveryCoordinator:
    """Test suite for ToolDiscoveryCoordinator."""

    def test_initialization(self, mock_event_bus, mock_logger):
        """Test discovery coordinator initialization."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        assert coordinator.event_bus == mock_event_bus
        assert coordinator.logger == mock_logger
        assert len(coordinator.active_requests) == 0
        mock_event_bus.subscribe.assert_called_once()
        mock_logger.emit_log_event_sync.assert_called()

    def test_discover_nodes_basic(
        self,
        mock_event_bus,
        mock_logger,
        sample_introspection_filters,
    ):
        """Test basic node discovery request."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        correlation_id = coordinator.discover_nodes(
            requester_id="test_requester",
            filters=sample_introspection_filters,
            timeout_ms=5000,
        )

        # Verify correlation ID is UUID
        assert isinstance(correlation_id, UUID)

        # Verify request is tracked
        assert correlation_id in coordinator.active_requests
        request_info = coordinator.active_requests[correlation_id]
        assert request_info.requester_id == "test_requester"
        assert request_info.filters == sample_introspection_filters
        assert request_info.timeout_ms == 5000
        assert not request_info.completed

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ModelRequestIntrospectionEvent)
        assert published_event.correlation_id == correlation_id
        assert published_event.requester_id == "test_requester"

    def test_discover_nodes_with_callback(self, mock_event_bus, mock_logger):
        """Test node discovery with callback."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)
        callback = Mock()

        correlation_id = coordinator.discover_nodes(
            requester_id="test_requester",
            callback=callback,
        )

        request_info = coordinator.active_requests[correlation_id]
        assert request_info.callback == callback

    def test_response_handling(
        self,
        mock_event_bus,
        mock_logger,
        sample_introspection_response_event,
    ):
        """Test handling of introspection response events."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        # Start a discovery request
        correlation_id = coordinator.discover_nodes(requester_id="test_requester")

        # Simulate response event
        sample_introspection_response_event.correlation_id = correlation_id
        sample_introspection_response_event.event_type = (
            REAL_TIME_INTROSPECTION_RESPONSE
        )

        # Handle the response
        coordinator._handle_introspection_response(sample_introspection_response_event)

        # Verify response was collected
        request_info = coordinator.active_requests[correlation_id]
        assert len(request_info.responses) == 1
        assert request_info.responses[0] == sample_introspection_response_event

    def test_discovery_timeout(self, mock_event_bus, mock_logger):
        """Test discovery request timeout handling."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        correlation_id = coordinator.discover_nodes(
            requester_id="test_requester",
            timeout_ms=100,  # Very short timeout
        )

        # Wait for timeout
        time.sleep(0.2)

        # Check if request is completed due to timeout
        request_info = coordinator.active_requests.get(correlation_id)
        if request_info:
            assert request_info.completed

    def test_cancel_discovery(self, mock_event_bus, mock_logger):
        """Test cancelling an active discovery request."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        correlation_id = coordinator.discover_nodes(requester_id="test_requester")

        # Cancel the request
        result = coordinator.cancel_discovery(correlation_id)

        assert result is True
        assert correlation_id not in coordinator.active_requests

    def test_get_active_discoveries(self, mock_event_bus, mock_logger):
        """Test getting active discovery statistics."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        # Start multiple discoveries
        coordinator.discover_nodes(requester_id="requester1")
        coordinator.discover_nodes(requester_id="requester2")

        stats = coordinator.get_active_discoveries()

        assert stats["active_requests"] == 2
        assert stats["total_requests"] == 2
        assert len(stats["active_correlation_ids"]) == 2


class TestToolUnifiedDiscovery:
    """Test suite for ToolUnifiedDiscovery."""

    @pytest.fixture
    def mock_discovery_coordinator(self):
        """Create a mock discovery coordinator."""
        coordinator = Mock()
        coordinator.discover_nodes = Mock(return_value=uuid4())
        coordinator.get_discovery_responses = Mock(return_value=[])
        coordinator.is_discovery_complete = Mock(return_value=True)
        coordinator.cancel_discovery = Mock(return_value=True)
        coordinator.get_active_discoveries = Mock(return_value={"active_requests": 0})
        coordinator.shutdown = Mock()
        return coordinator

    def test_initialization(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
    ):
        """Test unified discovery initialization."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        assert unified_discovery.event_bus == mock_event_bus
        assert unified_discovery.logger == mock_logger
        assert unified_discovery.discovery_coordinator == mock_discovery_coordinator
        assert len(unified_discovery.catalog) == 0
        mock_event_bus.subscribe.assert_called_once()

    def test_catalog_management(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
    ):
        """Test catalog management with NODE_INTROSPECTION_EVENT."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Simulate introspection event
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        # Verify catalog was updated
        expected_key = f"{sample_node_introspection_event.node_name}:{sample_node_introspection_event.node_id}"
        assert expected_key in unified_discovery.catalog
        assert (
            unified_discovery.catalog[expected_key] == sample_node_introspection_event
        )

    def test_get_available_nodes_no_filters(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
    ):
        """Test getting available nodes without filters."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Add node to catalog
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        # Get available nodes
        nodes = unified_discovery.get_available_nodes()

        assert len(nodes) == 1
        assert nodes[0] == sample_node_introspection_event
        assert unified_discovery.statistics["catalog_hits"] == 1

    def test_get_available_nodes_with_filters(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
        sample_introspection_filters,
    ):
        """Test getting available nodes with filters."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Add node to catalog
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        # Get available nodes with matching filters
        nodes = unified_discovery.get_available_nodes(
            filters=sample_introspection_filters,
        )

        assert len(nodes) == 1
        assert unified_discovery.statistics["filter_queries"] == 1

        # Test with non-matching filters
        non_matching_filters = ModelIntrospectionFilters(
            node_names=["non_existent_node"],
        )
        nodes = unified_discovery.get_available_nodes(filters=non_matching_filters)

        assert len(nodes) == 0

    def test_discover_real_time(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_introspection_filters,
    ):
        """Test real-time discovery initiation."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        expected_correlation_id = uuid4()
        mock_discovery_coordinator.discover_nodes.return_value = expected_correlation_id

        correlation_id = unified_discovery.discover_real_time(
            requester_id="test_requester",
            filters=sample_introspection_filters,
            timeout_ms=5000,
        )

        assert correlation_id == expected_correlation_id
        assert unified_discovery.statistics["real_time_requests"] == 1
        mock_discovery_coordinator.discover_nodes.assert_called_once_with(
            requester_id="test_requester",
            filters=sample_introspection_filters,
            timeout_ms=5000,
            include_resource_usage=False,
            include_performance_metrics=False,
        )

    def test_get_cached_and_discover(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
    ):
        """Test hybrid approach with cached results and real-time discovery."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Add node to catalog
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        expected_correlation_id = uuid4()
        mock_discovery_coordinator.discover_nodes.return_value = expected_correlation_id

        cached_nodes, correlation_id = unified_discovery.get_cached_and_discover(
            requester_id="test_requester",
        )

        # Verify cached results
        assert len(cached_nodes) == 1
        assert cached_nodes[0] == sample_node_introspection_event

        # Verify real-time discovery initiated
        assert correlation_id == expected_correlation_id
        assert unified_discovery.statistics["hybrid_requests"] == 1
        mock_discovery_coordinator.discover_nodes.assert_called_once()

    def test_catalog_ttl_cleanup(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
    ):
        """Test catalog TTL cleanup functionality."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Set short TTL for testing
        unified_discovery.catalog_ttl_seconds = 0.1

        # Add node to catalog
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        # Verify node is in catalog
        assert len(unified_discovery.catalog) == 1

        # Wait for TTL expiration
        time.sleep(0.2)

        # Get available nodes (should trigger cleanup)
        nodes = unified_discovery.get_available_nodes(include_offline=False)

        # Verify expired node was cleaned up
        assert len(nodes) == 0
        assert len(unified_discovery.catalog) == 0

    def test_clear_catalog_cache(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
        sample_node_introspection_event,
    ):
        """Test manual catalog cache clearing."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Add node to catalog
        sample_node_introspection_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(sample_node_introspection_event)

        assert len(unified_discovery.catalog) == 1

        # Clear cache
        unified_discovery.clear_catalog_cache()

        assert len(unified_discovery.catalog) == 0
        assert unified_discovery.statistics["cache_clears"] == 1

    def test_get_discovery_statistics(
        self,
        mock_event_bus,
        mock_logger,
        mock_discovery_coordinator,
    ):
        """Test getting discovery system statistics."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        # Perform some operations to update statistics
        unified_discovery.get_available_nodes()
        unified_discovery.discover_real_time("requester1")
        unified_discovery.clear_catalog_cache()

        stats = unified_discovery.get_discovery_statistics()

        assert "catalog_hits" in stats
        assert "real_time_requests" in stats
        assert "cache_clears" in stats
        assert "catalog_size" in stats
        assert "active_requests" in stats
        assert "ttl_seconds" in stats

        assert stats["catalog_hits"] == 1
        assert stats["real_time_requests"] == 1
        assert stats["cache_clears"] == 1

    def test_shutdown(self, mock_event_bus, mock_logger, mock_discovery_coordinator):
        """Test unified discovery shutdown."""
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=mock_discovery_coordinator,
        )

        unified_discovery.shutdown()

        mock_discovery_coordinator.shutdown.assert_called_once()
        mock_event_bus.unsubscribe.assert_called_once()
        assert len(unified_discovery.catalog) == 0


class TestIntegrationScenarios:
    """Integration tests for the complete unified discovery system."""

    def test_end_to_end_discovery_flow(self, mock_event_bus, mock_logger):
        """Test complete end-to-end discovery flow."""
        # Create coordinator and unified discovery
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=coordinator,
        )

        # 1. Add node to catalog via introspection event
        node_event = ModelNodeIntrospectionEvent(
            node_id="test_node_001",
            node_name="node_test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            capabilities=ModelNodeCapabilities(
                actions=["test_action"],
                protocols=["test_protocol"],
                metadata={},
            ),
            tags=["test_tag"],
            health_endpoint="/health",
        )
        node_event.event_type = NODE_INTROSPECTION_EVENT
        unified_discovery._handle_node_introspection(node_event)

        # 2. Get cached results
        cached_nodes = unified_discovery.get_available_nodes()
        assert len(cached_nodes) == 1
        assert cached_nodes[0].node_name == "node_test"

        # 3. Initiate real-time discovery
        correlation_id = unified_discovery.discover_real_time(
            requester_id="integration_test",
            timeout_ms=5000,
        )
        assert isinstance(correlation_id, UUID)

        # 4. Simulate response
        response_event = ModelIntrospectionResponseEvent(
            node_id="test_node_002",
            correlation_id=correlation_id,
            node_name="node_test_2",
            version=ModelSemVer(major=1, minor=0, patch=0),
            current_status=EnumNodeCurrentStatus.READY,
            capabilities=ModelCurrentToolAvailability(
                available_tools=["test_tool"],
                tool_status={},
                total_tools=1,
            ),
        )
        response_event.event_type = REAL_TIME_INTROSPECTION_RESPONSE
        coordinator._handle_introspection_response(response_event)

        # 5. Get real-time results
        responses = unified_discovery.get_discovery_results(correlation_id)
        assert responses is not None
        assert len(responses) == 1
        assert responses[0].node_name == "node_test_2"

        # 6. Test hybrid approach
        cached_nodes, new_correlation_id = unified_discovery.get_cached_and_discover(
            requester_id="hybrid_test",
        )
        assert len(cached_nodes) == 1  # From catalog
        assert isinstance(new_correlation_id, UUID)
        assert new_correlation_id != correlation_id

    def test_filtering_across_catalog_and_realtime(self, mock_event_bus, mock_logger):
        """Test filtering works consistently across catalog and real-time discovery."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=coordinator,
        )

        # Add nodes with different capabilities to catalog
        for i, capability in enumerate(["capability_a", "capability_b"]):
            node_event = ModelNodeIntrospectionEvent(
                node_id=f"test_node_{i:03d}",
                node_name=f"node_test_{capability}",
                version=ModelSemVer(major=1, minor=0, patch=0),
                capabilities=ModelNodeCapabilities(
                    actions=[capability],
                    protocols=["test_protocol"],
                    metadata={},
                ),
                tags=[f"tag_{capability}"],
                health_endpoint="/health",
            )
            node_event.event_type = NODE_INTROSPECTION_EVENT
            unified_discovery._handle_node_introspection(node_event)

        # Test filtering by capability
        filters = ModelIntrospectionFilters(capabilities=["capability_a"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)

        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].node_name == "node_test_capability_a"

        # Test filtering by tag
        filters = ModelIntrospectionFilters(tags=["tag_capability_b"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)

        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].node_name == "node_test_capability_b"

        # Test filtering with no matches
        filters = ModelIntrospectionFilters(capabilities=["non_existent_capability"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)

        assert len(filtered_nodes) == 0


class TestUnifiedDiscoverySystem:
    """Comprehensive test suite for the unified discovery system."""

    def test_complete_discovery_flow(self, mock_event_bus, mock_logger):
        """Test the complete unified discovery flow."""
        # Create discovery coordinator and unified discovery
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=coordinator,
        )

        # Test auto-publish catalog functionality
        node_event = ModelNodeIntrospectionEvent(
            node_id="test_node_001",
            node_name="node_test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            capabilities=ModelNodeCapabilities(
                actions=["test_action"],
                protocols=["test_protocol"],
                metadata={},
            ),
            tags=["test_tag"],
            health_endpoint="/health",
        )
        node_event.event_type = NODE_INTROSPECTION_EVENT

        # Simulate node introspection event
        unified_discovery._handle_node_introspection(node_event)

        # Test catalog query
        available_nodes = unified_discovery.get_available_nodes()
        assert len(available_nodes) == 1
        assert available_nodes[0].node_name == "node_test"

        # Test real-time discovery
        correlation_id = unified_discovery.discover_real_time(
            requester_id="test_requester",
            timeout_ms=5000,
        )
        assert isinstance(correlation_id, UUID)

        # Test hybrid discovery
        cached_nodes, discovery_id = unified_discovery.get_cached_and_discover(
            requester_id="hybrid_test",
        )
        assert len(cached_nodes) == 1
        assert isinstance(discovery_id, UUID)

        # Test statistics
        stats = unified_discovery.get_discovery_statistics()
        assert stats["catalog_hits"] >= 2  # From get_available_nodes calls
        assert stats["real_time_requests"] >= 1
        assert stats["hybrid_requests"] >= 1

        # Test cleanup
        unified_discovery.shutdown()
        mock_event_bus.unsubscribe.assert_called()

    def test_filtering_functionality(self, mock_event_bus, mock_logger):
        """Test filtering across catalog and real-time discovery."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)
        unified_discovery = ToolUnifiedDiscovery(
            event_bus=mock_event_bus,
            logger=mock_logger,
            discovery_coordinator=coordinator,
        )

        # Add multiple nodes with different capabilities
        for i, capability in enumerate(["auth", "logging", "storage"]):
            node_event = ModelNodeIntrospectionEvent(
                node_id=f"node_{i:03d}",
                node_name=f"node_{capability}",
                version=ModelSemVer(major=1, minor=0, patch=0),
                capabilities=ModelNodeCapabilities(
                    actions=[f"{capability}_action"],
                    protocols=[f"{capability}_protocol"],
                    metadata={},
                ),
                tags=[f"{capability}_tag"],
                health_endpoint="/health",
            )
            node_event.event_type = NODE_INTROSPECTION_EVENT
            unified_discovery._handle_node_introspection(node_event)

        # Test filtering by capability
        filters = ModelIntrospectionFilters(capabilities=["auth_action"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)
        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].node_name == "node_auth"

        # Test filtering by tag
        filters = ModelIntrospectionFilters(tags=["logging_tag"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)
        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].node_name == "node_logging"

        # Test no matches
        filters = ModelIntrospectionFilters(capabilities=["nonexistent"])
        filtered_nodes = unified_discovery.get_available_nodes(filters=filters)
        assert len(filtered_nodes) == 0

    def test_coordinator_response_handling(self, mock_event_bus, mock_logger):
        """Test discovery coordinator response collection."""
        coordinator = ToolDiscoveryCoordinator(mock_event_bus, mock_logger)

        # Start discovery request
        correlation_id = coordinator.discover_nodes(
            requester_id="test_requester",
            timeout_ms=5000,
        )

        # Verify request tracking
        assert correlation_id in coordinator.active_requests
        assert not coordinator.is_discovery_complete(correlation_id)

        # Create proper capabilities
        capabilities = ModelNodeCapabilities(
            actions=["action1", "action2"],
            protocols=["protocol1"],
            metadata={},
        )

        # Create tool availability objects
        tools = [
            ModelCurrentToolAvailability(
                tool_name="tool1",
                status=EnumNodeCurrentStatus.READY,
            ),
            ModelCurrentToolAvailability(
                tool_name="tool2",
                status=EnumNodeCurrentStatus.READY,
            ),
        ]

        # Simulate response
        response_event = ModelIntrospectionResponseEvent(
            node_id="responding_node",
            correlation_id=correlation_id,
            node_name="node_responder",
            version=ModelSemVer(major=1, minor=0, patch=0),
            current_status=EnumNodeCurrentStatus.READY,
            capabilities=capabilities,
            tools=tools,
            response_time_ms=50.0,
        )
        response_event.event_type = REAL_TIME_INTROSPECTION_RESPONSE

        # Handle response
        coordinator._handle_introspection_response(response_event)

        # Verify response collection
        responses = coordinator.get_discovery_responses(correlation_id)
        assert responses is not None
        assert len(responses) == 1
        assert responses[0].node_name == "node_responder"
        assert len(responses[0].tools) == 2

        # Test cancellation
        new_correlation_id = coordinator.discover_nodes(requester_id="test_cancel")
        assert coordinator.cancel_discovery(new_correlation_id) is True
        assert new_correlation_id not in coordinator.active_requests


if __name__ == "__main__":
    # Run basic smoke tests
    mock_bus = Mock()
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    mock_bus.publish = Mock()

    mock_log = Mock()
    mock_log.emit_log_event_sync = Mock()

    test_instance = TestUnifiedDiscoverySystem()
    test_instance.test_complete_discovery_flow(mock_bus, mock_log)
    test_instance.test_filtering_functionality(mock_bus, mock_log)
    test_instance.test_coordinator_response_handling(mock_bus, mock_log)
