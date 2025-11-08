"""
Test Request-Response Introspection Event Models

Comprehensive tests for REQUEST_REAL_TIME_INTROSPECTION and REAL_TIME_INTROSPECTION_RESPONSE events
and the MixinRequestResponseIntrospection functionality.
"""

from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
from omnibase_core.mixins.mixin_request_response_introspection import (
    MixinRequestResponseIntrospection,
)
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
)
from omnibase_core.models.discovery.model_discovery_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.models.discovery.model_request_introspection_event import (
    ModelRequestIntrospectionEvent,
)
from omnibase_core.models.discovery.model_resource_usage import ModelResourceUsage
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestRequestIntrospectionEvent:
    """Test REQUEST_REAL_TIME_INTROSPECTION event model."""

    def test_basic_request_creation(self):
        """Test creating a basic introspection request."""
        node_id = uuid4()
        requester_id = uuid4()
        request = ModelRequestIntrospectionEvent(
            node_id=node_id,
            requester_id=requester_id,
        )

        assert request.node_id == node_id
        assert request.requester_id == requester_id
        assert request.timeout_ms == 5000  # Default
        assert request.filters is None
        assert isinstance(request.correlation_id, UUID)
        assert not request.include_resource_usage
        assert not request.include_performance_metrics

    def test_factory_methods(self):
        """Test factory methods for creating requests."""

        # Test discovery request
        requester_id = uuid4()
        discovery_req = ModelRequestIntrospectionEvent.create_discovery_request(
            requester_id=requester_id,
            timeout_ms=3000,
            include_resource_usage=True,
        )

        assert discovery_req.requester_id == requester_id
        assert discovery_req.timeout_ms == 3000
        assert discovery_req.include_resource_usage
        assert isinstance(discovery_req.node_id, UUID)

        # Test MCP discovery request
        mcp_req = ModelRequestIntrospectionEvent.create_mcp_discovery_request()

        assert isinstance(mcp_req.requester_id, UUID)
        assert mcp_req.filters.protocols == ["mcp"]
        assert mcp_req.filters.status == ["ready", "busy"]
        assert mcp_req.include_resource_usage
        assert mcp_req.timeout_ms == 3000

        # Test health check request
        health_req = ModelRequestIntrospectionEvent.create_health_check_request()

        assert isinstance(health_req.requester_id, UUID)
        assert health_req.include_resource_usage
        assert health_req.include_performance_metrics
        assert health_req.timeout_ms == 2000

    def test_filters(self):
        """Test introspection filters."""
        filters = ModelIntrospectionFilters(
            node_type=["service"],
            capabilities=["validation", "generation"],
            protocols=["mcp", "graphql"],
            tags=["production"],
            status=["ready"],
            node_names=["node_generator"],
        )

        node_id = uuid4()
        requester_id = uuid4()
        request = ModelRequestIntrospectionEvent(
            node_id=node_id,
            requester_id=requester_id,
            filters=filters,
        )

        assert request.filters.node_type == ["service"]
        assert request.filters.capabilities == ["validation", "generation"]
        assert request.filters.protocols == ["mcp", "graphql"]
        assert request.filters.tags == ["production"]
        assert request.filters.status == ["ready"]
        assert request.filters.node_names == ["node_generator"]


class TestIntrospectionResponseEvent:
    """Test REAL_TIME_INTROSPECTION_RESPONSE event model."""

    def test_basic_response_creation(self):
        """Test creating a basic introspection response."""
        correlation_id = uuid4()
        capabilities = ModelNodeCapabilities(
            actions=["health_check", "validate"],
            protocols=["event_bus", "mcp"],
            metadata={"author": "test"},
        )

        node_id = uuid4()
        response = ModelIntrospectionResponseEvent(
            correlation_id=correlation_id,
            node_id=node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            current_status=EnumNodeCurrentStatus.READY,
            capabilities=capabilities,
            response_time_ms=25.5,
        )

        assert response.correlation_id == correlation_id
        assert response.node_id == node_id
        assert response.node_name == "test_node"
        assert response.version.major == 1
        assert response.current_status == EnumNodeCurrentStatus.READY
        assert response.capabilities.actions == ["health_check", "validate"]
        assert response.response_time_ms == 25.5

    def test_factory_methods(self):
        """Test factory methods for creating responses."""
        correlation_id = uuid4()
        capabilities = ModelNodeCapabilities(
            actions=["health_check"],
            protocols=["event_bus"],
            metadata={},
        )

        # Test basic response creation
        node_id = uuid4()
        response = ModelIntrospectionResponseEvent.create_response(
            correlation_id=correlation_id,
            node_id=node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            current_status=EnumNodeCurrentStatus.READY,
            capabilities=capabilities,
            response_time_ms=15.0,
        )

        assert response.correlation_id == correlation_id
        assert response.current_status == EnumNodeCurrentStatus.READY
        assert response.response_time_ms == 15.0

        # Test ready response creation
        ready_response = ModelIntrospectionResponseEvent.create_ready_response(
            correlation_id=correlation_id,
            node_id=node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            capabilities=capabilities,
            response_time_ms=10.0,
        )

        assert ready_response.current_status == EnumNodeCurrentStatus.READY
        assert ready_response.response_time_ms == 10.0

        # Test error response creation
        error_response = ModelIntrospectionResponseEvent.create_error_response(
            correlation_id=correlation_id,
            node_id=node_id,
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            error_message="Test error",
            response_time_ms=5.0,
        )

        assert error_response.current_status == EnumNodeCurrentStatus.ERROR
        assert error_response.additional_info.error_message == "Test error"
        assert error_response.capabilities.metadata["error"] == "Test error"

    def test_detailed_response_models(self):
        """Test detailed response models (resource usage, performance metrics, tools)."""

        # Test resource usage
        resource_usage = ModelResourceUsage(
            cpu_percent=45.5,
            memory_mb=256.7,
            memory_percent=12.3,
            disk_usage_percent=78.9,
            open_files=125,
            active_connections=8,
        )

        assert resource_usage.cpu_percent == 45.5
        assert resource_usage.memory_mb == 256.7
        assert resource_usage.open_files == 125

        # Test performance metrics
        performance_metrics = ModelPerformanceMetrics(
            uptime_seconds=3600.5,
            requests_per_minute=150.0,
            average_response_time_ms=25.3,
            error_rate_percent=0.5,
            queue_depth=3,
        )

        assert performance_metrics.uptime_seconds == 3600.5
        assert performance_metrics.requests_per_minute == 150.0
        assert performance_metrics.error_rate_percent == 0.5

        # Test tool availability
        tool_availability = ModelCurrentToolAvailability(
            tool_name="tool_validation",
            status=EnumNodeCurrentStatus.READY,
            last_execution="2025-01-01T12:00:00Z",
            execution_count=42,
            average_execution_time_ms=15.7,
        )

        assert tool_availability.tool_name == "tool_validation"
        assert tool_availability.status == EnumNodeCurrentStatus.READY
        assert tool_availability.execution_count == 42


class TestMixinRequestResponseIntrospection:
    """Test the MixinRequestResponseIntrospection functionality."""

    def create_test_node(self):
        """Create a test node with the mixin."""

        class TestNode(MixinRequestResponseIntrospection):
            def __init__(self):
                self.node_id = uuid4()
                self.node_name = "test_node"
                self.version = ModelSemVer(major=1, minor=0, patch=0)
                self.tags = ["test", "mcp"]
                self._event_bus = Mock()
                self._event_bus.is_connected.return_value = (
                    True  # Return bool, not Mock
                )
                self._logger = Mock()
                super().__init__()

        return TestNode()

    def test_setup_and_teardown(self):
        """Test setting up and tearing down request-response introspection."""
        node = self.create_test_node()

        # Test setup
        node._setup_request_response_introspection()

        # Verify event bus subscription was called
        node._event_bus.subscribe.assert_called_once()
        call_args = node._event_bus.subscribe.call_args
        assert call_args[0][0] == node._handle_introspection_request

        # Test teardown
        node._teardown_request_response_introspection()

        node._event_bus.unsubscribe.assert_called_once_with(
            node._handle_introspection_request,
        )

    def test_filter_matching(self):
        """Test filter matching logic."""
        node = self.create_test_node()
        node.get_supported_actions = Mock(return_value=["health_check", "validate"])
        node.get_supported_protocols = Mock(return_value=["event_bus", "mcp"])

        # Test no filters (should match)
        assert node._matches_introspection_filters(None) is True

        # Test matching filters
        matching_filters = ModelIntrospectionFilters(protocols=["mcp"], tags=["test"])
        assert node._matches_introspection_filters(matching_filters) is True

        # Test non-matching node_names filter
        non_matching_filters = ModelIntrospectionFilters(node_names=["other_node"])
        assert node._matches_introspection_filters(non_matching_filters) is False

        # Test non-matching capabilities filter
        capabilities_filter = ModelIntrospectionFilters(
            capabilities=["nonexistent_capability"],
        )
        assert node._matches_introspection_filters(capabilities_filter) is False

    def test_current_status_detection(self):
        """Test current node status detection."""
        node = self.create_test_node()

        # Test default ready status
        assert node._get_current_node_status() == EnumNodeCurrentStatus.READY

        # Test stopping status
        node._is_shutting_down = True
        assert node._get_current_node_status() == EnumNodeCurrentStatus.STOPPING

        # Test starting status
        node._is_shutting_down = False
        node._is_starting = True
        assert node._get_current_node_status() == EnumNodeCurrentStatus.STARTING

        # Test degraded status (disconnected event bus)
        node._is_starting = False
        node._event_bus.is_connected = Mock(return_value=False)
        assert node._get_current_node_status() == EnumNodeCurrentStatus.DEGRADED

    def test_handle_introspection_request(self):
        """Test handling introspection requests."""
        node = self.create_test_node()
        node.get_supported_actions = Mock(return_value=["health_check"])
        node.get_supported_protocols = Mock(return_value=["event_bus"])
        node.get_metadata = Mock(return_value={"author": "test"})

        # Create test request
        correlation_id = uuid4()
        node_id = uuid4()
        requester_id = uuid4()
        request = ModelRequestIntrospectionEvent(
            node_id=node_id,
            requester_id=requester_id,
            correlation_id=correlation_id,
            include_resource_usage=False,
            include_performance_metrics=False,
        )

        # Handle the request
        node._handle_introspection_request(request)

        # Verify response was published
        node._event_bus.publish.assert_called_once()
        published_envelope = node._event_bus.publish.call_args[0][0]

        # Extract event from envelope
        published_event = published_envelope.payload

        assert isinstance(published_event, ModelIntrospectionResponseEvent)
        assert published_event.correlation_id == correlation_id
        assert isinstance(published_event.node_id, UUID)
        assert published_event.current_status == EnumNodeCurrentStatus.READY
        assert published_event.capabilities.actions == ["health_check"]
        assert published_event.response_time_ms > 0

    def test_handle_filtered_request(self):
        """Test handling requests that don't match filters."""
        node = self.create_test_node()

        # Create request with non-matching filters
        correlation_id = uuid4()
        node_id = uuid4()
        requester_id = uuid4()
        filters = ModelIntrospectionFilters(
            node_names=["other_node"],  # Won't match our test_node
        )
        request = ModelRequestIntrospectionEvent(
            node_id=node_id,
            requester_id=requester_id,
            correlation_id=correlation_id,
            filters=filters,
        )

        # Handle the request
        node._handle_introspection_request(request)

        # Verify no response was published (filtered out)
        node._event_bus.publish.assert_not_called()

    def test_error_handling(self):
        """Test error handling in introspection request processing."""
        node = self.create_test_node()

        # Mock an error in capabilities gathering
        node._get_current_capabilities = Mock(side_effect=Exception("Test error"))

        correlation_id = uuid4()
        node_id = uuid4()
        requester_id = uuid4()
        request = ModelRequestIntrospectionEvent(
            node_id=node_id,
            requester_id=requester_id,
            correlation_id=correlation_id,
        )

        # Handle the request (should result in error response)
        node._handle_introspection_request(request)

        # Verify error response was published
        node._event_bus.publish.assert_called_once()
        published_envelope = node._event_bus.publish.call_args[0][0]

        # Extract event from envelope
        published_event = published_envelope.payload

        assert isinstance(published_event, ModelIntrospectionResponseEvent)
        assert published_event.correlation_id == correlation_id
        assert published_event.current_status == EnumNodeCurrentStatus.ERROR
        assert "Test error" in published_event.additional_info.error_message


if __name__ == "__main__":
    pytest.main([__file__])
