"""
Basic tests for discovery event models to validate schema definitions.
"""

from uuid import uuid4

from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.discovery import (
    ModelNodeHealthEvent,
    ModelNodeIntrospectionEvent,
    ModelNodeShutdownEvent,
    ModelToolDiscoveryRequest,
    ModelToolDiscoveryResponse,
)
from omnibase_core.models.discovery.model_node_health_event import ModelHealthMetrics
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.models.discovery.model_tool_discovery_request import (
    ModelDiscoveryFilters,
)
from omnibase_core.models.discovery.model_tool_discovery_response import (
    ModelDiscoveredTool,
)


class TestNodeIntrospectionEvent:
    """Test NODE_INTROSPECTION_EVENT model"""

    def test_create_basic_introspection_event(self):
        """Test creating a basic introspection event"""
        capabilities = ModelNodeCapabilities(
            actions=["health_check", "validate_contract"],
            protocols=["mcp", "event_bus"],
            metadata={"author": "test", "trust_score": 0.9},
        )

        event = ModelNodeIntrospectionEvent(
            node_id="test_node_123",
            node_name="test_node",
            version=ModelSemVer(major=1, minor=0, patch=0),
            capabilities=capabilities,
            tags=["test", "generator"],
        )

        assert event.node_id == "test_node_123"
        assert event.node_name == "test_node"
        assert event.version.major == 1
        assert len(event.capabilities.actions) == 2
        assert "mcp" in event.capabilities.protocols
        assert len(event.tags) == 2
        assert event.event_type.value == "NODE_INTROSPECTION_EVENT"

    def test_factory_method_create_from_node_info(self):
        """Test factory method for creating introspection events"""
        event = ModelNodeIntrospectionEvent.create_from_node_info(
            node_id="generator_456",
            node_name="node_generator",
            version=ModelSemVer.parse("1.2.3"),
            actions=["generate_complete_node", "health_check"],
            protocols=["mcp", "graphql"],
            metadata={"author": "ONEX"},
            tags=["generator", "validated"],
        )

        assert event.node_name == "node_generator"
        assert event.version.minor == 2
        assert "generate_complete_node" in event.capabilities.actions
        assert event.capabilities.metadata["author"] == "ONEX"


class TestToolDiscoveryRequest:
    """Test TOOL_DISCOVERY_REQUEST model"""

    def test_create_basic_discovery_request(self):
        """Test creating a basic discovery request"""
        filters = ModelDiscoveryFilters(
            tags=["generator"],
            protocols=["mcp"],
            min_trust_score=0.8,
        )

        request = ModelToolDiscoveryRequest(
            node_id="mcp_server",
            requester_id="mcp_service",
            filters=filters,
            max_results=10,
            correlation_id=uuid4(),
        )

        assert request.requester_id == "mcp_service"
        assert request.filters.tags == ["generator"]
        assert request.filters.min_trust_score == 0.8
        assert request.max_results == 10
        assert request.event_type.value == "TOOL_DISCOVERY_REQUEST"

    def test_factory_method_create_mcp_request(self):
        """Test MCP-specific factory method"""
        request = ModelToolDiscoveryRequest.create_mcp_request(correlation_id=uuid4())

        assert request.requester_id == "mcp_server"
        assert "mcp" in request.filters.protocols
        assert "event_bus" in request.filters.protocols
        assert request.filters.health_status == "healthy"


class TestToolDiscoveryResponse:
    """Test TOOL_DISCOVERY_RESPONSE model"""

    def test_create_basic_discovery_response(self):
        """Test creating a basic discovery response"""
        tool = ModelDiscoveredTool(
            node_id="gen_123",
            node_name="node_generator",
            version=ModelSemVer.parse("1.0.0"),
            actions=["health_check", "generate_complete_node"],
            protocols=["mcp", "event_bus"],
            tags=["generator"],
            health_status="healthy",
        )

        response = ModelToolDiscoveryResponse(
            node_id="registry_456",
            requester_id="mcp_server",
            tools=[tool],
            total_count=1,
            filtered_count=1,
            correlation_id=uuid4(),
        )

        assert response.requester_id == "mcp_server"
        assert len(response.tools) == 1
        assert response.tools[0].node_name == "node_generator"
        assert response.total_count == 1
        assert response.event_type.value == "TOOL_DISCOVERY_RESPONSE"

    def test_factory_method_create_success_response(self):
        """Test success response factory method"""
        tools = [
            ModelDiscoveredTool(
                node_id="test_123",
                node_name="test_node",
                version=ModelSemVer.parse("1.0.0"),
                actions=["test_action"],
                protocols=["mcp"],
            ),
        ]

        response = ModelToolDiscoveryResponse.create_success_response(
            node_id="registry",
            requester_id="client",
            tools=tools,
            request_correlation_id=str(uuid4()),
            response_time_ms=45.5,
        )

        assert response.tools == tools
        assert response.response_time_ms == 45.5
        assert response.request_correlation_id is not None
        assert not response.timeout_occurred


class TestNodeHealthEvent:
    """Test NODE_HEALTH_EVENT model"""

    def test_create_basic_health_event(self):
        """Test creating a basic health event"""
        metrics = ModelHealthMetrics(
            status="healthy",
            cpu_usage_percent=25.5,
            memory_usage_percent=60.0,
            uptime_seconds=3600,
        )

        event = ModelNodeHealthEvent(
            node_id="test_node_789",
            node_name="test_node",
            health_metrics=metrics,
        )

        assert event.node_name == "test_node"
        assert event.health_metrics.status == "healthy"
        assert event.health_metrics.cpu_usage_percent == 25.5
        assert event.is_healthy()
        assert not event.needs_attention()
        assert event.event_type.value == "NODE_HEALTH_EVENT"

    def test_factory_method_create_warning_report(self):
        """Test warning report factory method"""
        event = ModelNodeHealthEvent.create_warning_report(
            node_id="warn_node",
            node_name="warning_node",
            warning_reason="High CPU usage",
            cpu_usage=85.0,
            memory_usage=90.0,
        )

        assert event.health_metrics.status == "warning"
        assert event.health_metrics.cpu_usage_percent == 85.0
        assert event.health_metrics.custom_metrics["warning_reason"] == "High CPU usage"
        assert not event.is_healthy()
        assert event.needs_attention()


class TestNodeShutdownEvent:
    """Test NODE_SHUTDOWN_EVENT model"""

    def test_create_basic_shutdown_event(self):
        """Test creating a basic shutdown event"""
        event = ModelNodeShutdownEvent(
            node_id="shutdown_node_999",
            node_name="shutting_down_node",
            shutdown_reason="graceful",
            uptime_seconds=7200,
            requests_processed=1000,
        )

        assert event.node_name == "shutting_down_node"
        assert event.shutdown_reason == "graceful"
        assert event.uptime_seconds == 7200
        assert event.is_graceful()
        assert not event.has_cleanup_errors()
        assert event.event_type.value == "NODE_SHUTDOWN_EVENT"

    def test_factory_method_create_error_shutdown(self):
        """Test error shutdown factory method"""
        event = ModelNodeShutdownEvent.create_error_shutdown(
            node_id="error_node",
            node_name="failed_node",
            error_message="Out of memory",
            uptime_seconds=1800,
        )

        assert event.shutdown_reason == "error"
        assert event.final_status == "error"
        assert "Out of memory" in event.cleanup_errors
        assert not event.is_graceful()
        assert event.has_cleanup_errors()


def test_all_events_have_correlation_id_support():
    """Test that all events support correlation_id for request/response matching"""
    correlation_id = uuid4()

    # Test each event type can accept correlation_id
    introspection = ModelNodeIntrospectionEvent.create_from_node_info(
        node_id="test",
        node_name="test",
        version=ModelSemVer.parse("1.0.0"),
        actions=["test"],
        correlation_id=correlation_id,
    )

    request = ModelToolDiscoveryRequest.create_simple_request(
        node_id="test",
        requester_id="test",
        correlation_id=correlation_id,
    )

    response = ModelToolDiscoveryResponse.create_success_response(
        node_id="test",
        requester_id="test",
        tools=[],
        request_correlation_id=str(correlation_id),
    )

    health = ModelNodeHealthEvent.create_healthy_report(
        node_id="test",
        node_name="test",
        correlation_id=correlation_id,
    )

    shutdown = ModelNodeShutdownEvent.create_graceful_shutdown(
        node_id="test",
        node_name="test",
        correlation_id=correlation_id,
    )

    # All should have the same correlation_id
    assert introspection.correlation_id == correlation_id
    assert request.correlation_id == correlation_id
    assert (
        response.correlation_id == correlation_id
    )  # Now converted properly from string
    assert health.correlation_id == correlation_id
    assert shutdown.correlation_id == correlation_id


if __name__ == "__main__":
    # Run basic validation tests

    test_node_introspection = TestNodeIntrospectionEvent()
    test_node_introspection.test_create_basic_introspection_event()
    test_node_introspection.test_factory_method_create_from_node_info()

    test_discovery_request = TestToolDiscoveryRequest()
    test_discovery_request.test_create_basic_discovery_request()
    test_discovery_request.test_factory_method_create_mcp_request()

    test_discovery_response = TestToolDiscoveryResponse()
    test_discovery_response.test_create_basic_discovery_response()
    test_discovery_response.test_factory_method_create_success_response()

    test_health_event = TestNodeHealthEvent()
    test_health_event.test_create_basic_health_event()
    test_health_event.test_factory_method_create_warning_report()

    test_shutdown_event = TestNodeShutdownEvent()
    test_shutdown_event.test_create_basic_shutdown_event()
    test_shutdown_event.test_factory_method_create_error_shutdown()

    test_all_events_have_correlation_id_support()
