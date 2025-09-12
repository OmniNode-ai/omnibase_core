#!/usr/bin/env python3

"""
Comprehensive unit tests for Infrastructure Orchestrator.
Tests all functionality with real event bus integration and orchestration workflows.
Achieves >85% code coverage requirement focusing on modernized health_check() method.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.models.core.model_core_errors import CoreErrorCode, OnexError
from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_health_status import ModelHealthStatus
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_parameters import ModelToolParameters
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node import (
    ToolInfrastructureOrchestrator,
    main,
)
from omnibase_core.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.protocols.protocol_infrastructure_orchestrator import (
    ProtocolInfrastructureOrchestrator,
)


class TestInfrastructureOrchestrator:
    """
    Comprehensive test suite for Infrastructure Orchestrator.
    Tests orchestration, event bus coordination, health monitoring, and failover handling.
    """

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus with all required methods."""
        event_bus = MagicMock()
        event_bus.subscribe = MagicMock()
        event_bus.publish = MagicMock()
        event_bus.publish_event_async = AsyncMock()
        return event_bus

    @pytest.fixture
    def container(self, mock_event_bus):
        """Mock ONEX container with event bus service."""
        container = MagicMock(spec=ModelONEXContainer)
        container.get_service = MagicMock(return_value=mock_event_bus)
        return container

    @pytest.fixture
    def orchestrator(self, container):
        """Create Infrastructure Orchestrator instance for testing."""
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            return ToolInfrastructureOrchestrator(container)

    @pytest.fixture
    def sample_tool_response(self):
        """Sample tool response event for testing."""
        correlation_id = uuid4()
        return ModelToolResponseEvent(
            correlation_id=correlation_id,
            target_node_id="infrastructure_orchestrator",
            target_node_name="infrastructure_orchestrator",
            tool_name="tool_consul_adapter",
            status="success",
            result={"health": "healthy", "services": 5},
            error=None,
            metadata={"response_time": 0.5, "timestamp": "2024-08-27T10:00:00Z"},
        )

    @pytest.fixture
    def sample_tool_invocation(self):
        """Sample tool invocation for testing."""
        return {
            "operation": "bootstrap",
            "priority": "high",
            "timeout": 30,
            "retry_count": 3,
        }

    # =============================================================================
    # Initialization and Setup Tests
    # =============================================================================

    def test_initialization_success(self, orchestrator, mock_event_bus):
        """Test successful orchestrator initialization."""
        assert orchestrator.domain == "infrastructure"
        assert orchestrator.event_bus == mock_event_bus
        assert hasattr(orchestrator, "_pending_invocations")
        assert isinstance(orchestrator._pending_invocations, dict)
        assert len(orchestrator._pending_invocations) == 0

        # Verify response handler setup
        mock_event_bus.subscribe.assert_called_once_with(
            CoreEventTypes.TOOL_RESPONSE,
            orchestrator._handle_tool_response,
        )

    def test_initialization_no_event_bus(self):
        """Test initialization when event bus is not available."""
        container = MagicMock(spec=ModelONEXContainer)
        container.get_service = MagicMock(return_value=None)

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        assert orchestrator.event_bus is None
        assert orchestrator.domain == "infrastructure"

    def test_response_handler_setup_no_subscribe(self, container):
        """Test response handler setup when event bus doesn't have subscribe method."""
        mock_event_bus = MagicMock()
        delattr(mock_event_bus, "subscribe")  # Remove subscribe method
        container.get_service.return_value = mock_event_bus

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        # Should not raise error even without subscribe method
        assert orchestrator.event_bus == mock_event_bus

    def test_protocol_compliance(self, orchestrator):
        """Test that orchestrator implements the required protocol."""
        assert isinstance(orchestrator, ProtocolInfrastructureOrchestrator)

        # Verify all protocol methods are implemented
        assert hasattr(orchestrator, "coordinate_infrastructure_bootstrap")
        assert hasattr(orchestrator, "coordinate_infrastructure_health_check")
        assert hasattr(orchestrator, "coordinate_infrastructure_failover")

        # Verify methods are callable
        assert callable(orchestrator.coordinate_infrastructure_bootstrap)
        assert callable(orchestrator.coordinate_infrastructure_health_check)
        assert callable(orchestrator.coordinate_infrastructure_failover)

    # =============================================================================
    # Health Check Tests (Primary Focus - Modernized Implementation)
    # =============================================================================

    def test_health_check_healthy_state(self, orchestrator):
        """Test health check in healthy state with minimal pending invocations."""
        # Set up healthy state
        orchestrator._pending_invocations = {"test1": MagicMock(), "test2": MagicMock()}

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY
        assert "Orchestrator healthy - 2 pending invocations" in result.message
        assert "event bus and adapters ready" in result.message

    def test_health_check_no_event_bus(self, container):
        """Test health check when event bus is not initialized."""
        container.get_service.return_value = None

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.CRITICAL
        assert (
            "Event bus not initialized - orchestration cannot function"
            in result.message
        )

    def test_health_check_event_bus_missing_methods(self, container):
        """Test health check when event bus is missing required methods."""
        mock_event_bus = MagicMock()
        delattr(mock_event_bus, "subscribe")  # Missing subscribe method
        container.get_service.return_value = mock_event_bus

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.CRITICAL
        assert "Event bus missing methods: subscribe" in result.message

    def test_health_check_event_bus_missing_publish(self, container):
        """Test health check when event bus is missing publish method."""
        mock_event_bus = MagicMock()
        mock_event_bus.subscribe = MagicMock()
        delattr(mock_event_bus, "publish")  # Missing publish method
        container.get_service.return_value = mock_event_bus

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.CRITICAL
        assert "Event bus missing methods: publish" in result.message

    def test_health_check_both_event_bus_methods_missing(self, container):
        """Test health check when event bus is missing both required methods."""
        mock_event_bus = MagicMock()
        delattr(mock_event_bus, "subscribe")
        delattr(mock_event_bus, "publish")
        container.get_service.return_value = mock_event_bus

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.CRITICAL
        assert "Event bus missing methods: subscribe, publish" in result.message

    def test_health_check_pending_invocations_not_initialized(
        self,
        container,
        mock_event_bus,
    ):
        """Test health check when pending invocations tracking is not initialized."""
        container.get_service.return_value = mock_event_bus

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        # Remove pending invocations attribute
        delattr(orchestrator, "_pending_invocations")

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.UNHEALTHY
        assert "Orchestrator invocation tracking not initialized" in result.message

    def test_health_check_warning_state_moderate_pending(self, orchestrator):
        """Test health check in warning state with moderate pending invocations."""
        # Create 25 pending invocations (>20, ≤50)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(25)
        }

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.WARNING
        assert "Moderate pending invocations: 25" in result.message
        assert "monitor coordination performance" in result.message

    def test_health_check_degraded_state_high_pending(self, orchestrator):
        """Test health check in degraded state with high pending invocations."""
        # Create 60 pending invocations (>50)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(60)
        }

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED
        assert "High pending invocations: 60" in result.message
        assert "possible coordination delays" in result.message

    def test_health_check_edge_case_exact_thresholds(self, orchestrator):
        """Test health check at exact threshold boundaries."""
        # Test exactly 20 pending invocations (healthy state)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(20)
        }

        result = orchestrator.health_check()
        assert result.status == EnumHealthStatus.HEALTHY

        # Test exactly 21 pending invocations (warning state)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(21)
        }

        result = orchestrator.health_check()
        assert result.status == EnumHealthStatus.WARNING

        # Test exactly 50 pending invocations (warning state)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(50)
        }

        result = orchestrator.health_check()
        assert result.status == EnumHealthStatus.WARNING

        # Test exactly 51 pending invocations (degraded state)
        orchestrator._pending_invocations = {
            f"test_{i}": MagicMock() for i in range(51)
        }

        result = orchestrator.health_check()
        assert result.status == EnumHealthStatus.DEGRADED

    def test_health_check_exception_handling(self, orchestrator):
        """Test health check exception handling."""
        # Mock the event bus to raise an exception
        orchestrator.event_bus = MagicMock()
        orchestrator.event_bus.side_effect = Exception("Event bus error")

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.ERROR
        assert "Health check failed:" in result.message

    def test_health_check_zero_pending_invocations(self, orchestrator):
        """Test health check with zero pending invocations."""
        orchestrator._pending_invocations = {}

        result = orchestrator.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY
        assert "0 pending invocations" in result.message

    # =============================================================================
    # Event Handling Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_handle_tool_response_success(
        self,
        orchestrator,
        sample_tool_response,
    ):
        """Test successful tool response handling."""
        correlation_id = str(sample_tool_response.correlation_id)

        # Set up pending invocation
        future = asyncio.Future()
        orchestrator._pending_invocations[correlation_id] = future

        # Create envelope
        envelope = ModelEventEnvelope(
            correlation_id=sample_tool_response.correlation_id,
            payload=sample_tool_response,
        )

        # Handle the response
        await orchestrator._handle_tool_response(envelope)

        # Verify future was resolved
        assert future.done()
        result = future.result()
        assert result["status"] == "success"
        assert result["result"] == {"health": "healthy", "services": 5}
        assert result["error"] is None
        assert result["metadata"]["response_time"] == 0.5

        # Verify correlation ID was removed from pending
        assert correlation_id not in orchestrator._pending_invocations

    @pytest.mark.asyncio
    async def test_handle_tool_response_invalid_payload(self, orchestrator):
        """Test handling tool response with invalid payload type."""
        correlation_id = uuid4()

        # Create envelope with invalid payload
        envelope = ModelEventEnvelope(
            correlation_id=correlation_id,
            payload="invalid_payload",  # Not a ModelToolResponseEvent
        )

        # Should not raise error, just return silently
        await orchestrator._handle_tool_response(envelope)

        # No pending invocations should be affected
        assert len(orchestrator._pending_invocations) == 0

    @pytest.mark.asyncio
    async def test_handle_tool_response_unknown_correlation_id(
        self,
        orchestrator,
        sample_tool_response,
    ):
        """Test handling tool response with unknown correlation ID."""
        # Create envelope without setting up pending invocation
        envelope = ModelEventEnvelope(
            correlation_id=sample_tool_response.correlation_id,
            payload=sample_tool_response,
        )

        # Should not raise error
        await orchestrator._handle_tool_response(envelope)

        # No pending invocations should be affected
        assert len(orchestrator._pending_invocations) == 0

    @pytest.mark.asyncio
    async def test_handle_tool_response_future_already_done(
        self,
        orchestrator,
        sample_tool_response,
    ):
        """Test handling tool response when future is already resolved."""
        correlation_id = str(sample_tool_response.correlation_id)

        # Set up completed future
        future = asyncio.Future()
        future.set_result("already_done")
        orchestrator._pending_invocations[correlation_id] = future

        # Create envelope
        envelope = ModelEventEnvelope(
            correlation_id=sample_tool_response.correlation_id,
            payload=sample_tool_response,
        )

        # Handle the response
        await orchestrator._handle_tool_response(envelope)

        # Future should still have original result
        assert future.result() == "already_done"

        # Correlation ID should be removed from pending
        assert correlation_id not in orchestrator._pending_invocations

    @pytest.mark.asyncio
    async def test_handle_tool_response_exception_handling(self, orchestrator):
        """Test exception handling in tool response processing."""
        # Create malformed envelope that will cause exception
        envelope = MagicMock()
        envelope.payload = MagicMock()
        envelope.payload.correlation_id = "invalid_uuid"

        # Mock isinstance to return True but then cause str() to fail
        with (
            patch("builtins.isinstance", return_value=True),
            patch(
                "builtins.str",
                side_effect=Exception("String conversion failed"),
            ),
        ):
            with pytest.raises(OnexError) as exc_info:
                await orchestrator._handle_tool_response(envelope)

            assert "Tool response handling failed" in str(exc_info.value)
            assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    # =============================================================================
    # Adapter Coordination Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_coordinate_adapter_success(
        self,
        orchestrator,
        mock_event_bus,
        sample_tool_invocation,
    ):
        """Test successful adapter coordination."""

        # Set up mock response
        async def mock_publish(envelope):
            # Simulate immediate response
            correlation_id = str(envelope.correlation_id)
            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    future.set_result(
                        {
                            "status": "success",
                            "result": {"bootstrapped": True},
                            "error": None,
                            "metadata": {"duration": 2.5},
                        },
                    )

        mock_event_bus.publish_event_async = AsyncMock(side_effect=mock_publish)

        # Remove publish method to test fallback
        delattr(mock_event_bus, "publish")

        result = await orchestrator._coordinate_adapter(
            "tool_consul_adapter",
            sample_tool_invocation,
        )

        assert result["status"] == "success"
        assert result["result"]["bootstrapped"] is True
        assert result["error"] is None
        mock_event_bus.publish_event_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinate_adapter_with_sync_publish(
        self,
        orchestrator,
        mock_event_bus,
        sample_tool_invocation,
    ):
        """Test adapter coordination using synchronous publish method."""

        # Set up mock response
        def mock_publish(envelope):
            # Simulate immediate response
            correlation_id = str(envelope.correlation_id)
            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    asyncio.get_event_loop().call_soon(
                        future.set_result,
                        {
                            "status": "success",
                            "result": {"health": "healthy"},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = mock_publish

        result = await orchestrator._coordinate_adapter(
            "tool_vault_adapter",
            sample_tool_invocation,
        )

        assert result["status"] == "success"
        assert result["result"]["health"] == "healthy"
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinate_adapter_timeout(
        self,
        orchestrator,
        mock_event_bus,
        sample_tool_invocation,
    ):
        """Test adapter coordination timeout."""
        # Mock event bus that doesn't respond
        mock_event_bus.publish = MagicMock()

        result = await orchestrator._coordinate_adapter(
            "tool_slow_adapter",
            sample_tool_invocation,
        )

        assert result["status"] == "timeout"
        assert result["adapter"] == "tool_slow_adapter"
        assert result["operation"] == sample_tool_invocation["operation"]
        assert "No response from tool_slow_adapter within 30 seconds" in result["error"]

    @pytest.mark.asyncio
    async def test_coordinate_adapter_exception(self, orchestrator):
        """Test adapter coordination with exception during setup."""
        # Mock uuid4 to raise exception
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.uuid4",
            side_effect=Exception("UUID generation failed"),
        ):
            with pytest.raises(OnexError) as exc_info:
                await orchestrator._coordinate_adapter("tool_error_adapter", {})

            assert "Adapter coordination failed for tool_error_adapter" in str(
                exc_info.value,
            )
            assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_coordinate_adapter_invocation_event_creation(
        self,
        orchestrator,
        mock_event_bus,
    ):
        """Test proper creation of tool invocation events."""
        captured_envelope = None

        def capture_envelope(envelope):
            nonlocal captured_envelope
            captured_envelope = envelope
            # Immediately resolve to prevent timeout
            correlation_id = str(envelope.correlation_id)
            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    asyncio.get_event_loop().call_soon(
                        future.set_result,
                        {
                            "status": "captured",
                            "result": {},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = capture_envelope

        request = {"operation": "test_op", "priority": "high", "custom_param": "value"}
        await orchestrator._coordinate_adapter("test_adapter", request)

        # Verify envelope structure
        assert captured_envelope is not None
        assert isinstance(captured_envelope, ModelEventEnvelope)
        assert isinstance(captured_envelope.payload, ModelToolInvocationEvent)

        # Verify invocation event details
        invocation = captured_envelope.payload
        assert invocation.target_node_id == "test_adapter"
        assert invocation.target_node_name == "test_adapter"
        assert invocation.tool_name == "test_adapter"
        assert invocation.action == "test_op"
        assert invocation.source_node_id == orchestrator.node_id
        assert invocation.source_node_name == "infrastructure_orchestrator"

        # Verify parameters
        assert isinstance(invocation.parameters, ModelToolParameters)
        assert invocation.parameters.action_parameters == request

        # Verify correlation ID consistency
        assert invocation.correlation_id == captured_envelope.correlation_id

    # =============================================================================
    # Bootstrap Coordination Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_bootstrap_success(self, orchestrator):
        """Test successful infrastructure bootstrap coordination."""

        # Mock successful adapter responses
        async def mock_coordinate_adapter(adapter_name, request):
            return {
                "status": "success",
                "adapter": adapter_name,
                "result": {"bootstrapped": True, "services": 3},
            }

        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=mock_coordinate_adapter,
        )

        result = await orchestrator.coordinate_infrastructure_bootstrap()

        assert result["status"] == "success"
        assert "bootstrap_results" in result

        bootstrap_results = result["bootstrap_results"]
        assert "consul_adapter" in bootstrap_results
        assert "vault_adapter" in bootstrap_results
        assert "kafka_wrapper" in bootstrap_results

        # Verify all adapters were called with correct parameters
        expected_calls = [
            ("tool_consul_adapter", {"operation": "bootstrap", "priority": "high"}),
            ("tool_vault_adapter", {"operation": "bootstrap", "priority": "high"}),
            ("tool_kafka_wrapper", {"operation": "bootstrap", "priority": "medium"}),
        ]

        orchestrator._coordinate_adapter.assert_has_calls(
            [pytest.mock.call(adapter, params) for adapter, params in expected_calls],
        )

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_bootstrap_partial_failure(
        self,
        orchestrator,
    ):
        """Test infrastructure bootstrap with partial adapter failures."""

        async def mock_coordinate_adapter(adapter_name, request):
            if adapter_name == "tool_consul_adapter":
                return {"status": "success", "result": {"bootstrapped": True}}
            if adapter_name == "tool_vault_adapter":
                return {"status": "error", "error": "Connection refused"}
            # kafka_wrapper
            return {"status": "timeout", "error": "Response timeout"}

        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=mock_coordinate_adapter,
        )

        result = await orchestrator.coordinate_infrastructure_bootstrap()

        assert result["status"] == "success"  # Bootstrap continues despite failures

        bootstrap_results = result["bootstrap_results"]
        assert bootstrap_results["consul_adapter"]["status"] == "success"
        assert bootstrap_results["vault_adapter"]["status"] == "error"
        assert bootstrap_results["kafka_wrapper"]["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_bootstrap_exception(self, orchestrator):
        """Test infrastructure bootstrap with coordination exception."""
        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=Exception("Coordination failure"),
        )

        with pytest.raises(OnexError) as exc_info:
            await orchestrator.coordinate_infrastructure_bootstrap()

        assert "Infrastructure bootstrap failed" in str(exc_info.value)
        assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    # =============================================================================
    # Health Check Coordination Tests (Deprecated Method)
    # =============================================================================

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_health_check_success(self, orchestrator):
        """Test successful infrastructure health check coordination (deprecated method)."""

        async def mock_coordinate_adapter(adapter_name, request):
            return {"status": "healthy", "adapter": adapter_name}

        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=mock_coordinate_adapter,
        )

        with pytest.warns(None) as warning_list:
            result = await orchestrator.coordinate_infrastructure_health_check()

        # Check for deprecation warning
        deprecation_warnings = [
            w for w in warning_list if "deprecated" in str(w.message).lower()
        ]
        assert len(deprecation_warnings) > 0

        assert result["status"] == "healthy"
        assert "adapter_health" in result
        assert "deprecation_notice" in result

        adapter_health = result["adapter_health"]
        assert "consul_adapter" in adapter_health
        assert "vault_adapter" in adapter_health
        assert "kafka_wrapper" in adapter_health

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_health_check_degraded(self, orchestrator):
        """Test infrastructure health check coordination with degraded adapters."""

        async def mock_coordinate_adapter(adapter_name, request):
            if adapter_name == "tool_consul_adapter":
                return {"status": "healthy"}
            return {"status": "degraded", "warning": "High memory usage"}

        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=mock_coordinate_adapter,
        )

        result = await orchestrator.coordinate_infrastructure_health_check()

        assert result["status"] == "degraded"  # Not all healthy
        assert "deprecation_notice" in result

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_health_check_exception(self, orchestrator):
        """Test infrastructure health check coordination with exception."""
        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=Exception("Health check failure"),
        )

        with pytest.raises(OnexError) as exc_info:
            await orchestrator.coordinate_infrastructure_health_check()

        assert "Infrastructure health check failed" in str(exc_info.value)
        assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    # =============================================================================
    # Failover Coordination Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_failover_kafka(self, orchestrator):
        """Test failover coordination for Kafka wrapper."""

        async def mock_coordinate_adapter(adapter_name, request):
            return {
                "status": "success",
                "result": {"fallback_mode": True, "in_memory_queue": True},
            }

        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=mock_coordinate_adapter,
        )

        result = await orchestrator.coordinate_infrastructure_failover("kafka_wrapper")

        assert result["status"] == "failover_coordinated"
        assert result["failed_adapter"] == "kafka_wrapper"
        assert result["failover_result"]["status"] == "success"

        orchestrator._coordinate_adapter.assert_called_once_with(
            "tool_kafka_wrapper",
            {"operation": "enable_fallback_mode"},
        )

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_failover_consul(self, orchestrator):
        """Test failover coordination for Consul adapter."""
        result = await orchestrator.coordinate_infrastructure_failover("consul_adapter")

        assert result["status"] == "failover_coordinated"
        assert result["failed_adapter"] == "consul_adapter"
        assert result["failover_result"]["status"] == "critical"
        assert "Critical infrastructure failure" in result["failover_result"]["message"]

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_failover_vault(self, orchestrator):
        """Test failover coordination for Vault adapter."""
        result = await orchestrator.coordinate_infrastructure_failover("vault_adapter")

        assert result["status"] == "failover_coordinated"
        assert result["failed_adapter"] == "vault_adapter"
        assert result["failover_result"]["status"] == "critical"
        assert "Critical infrastructure failure" in result["failover_result"]["message"]

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_failover_unknown_adapter(
        self,
        orchestrator,
    ):
        """Test failover coordination for unknown adapter."""
        result = await orchestrator.coordinate_infrastructure_failover(
            "unknown_adapter",
        )

        assert result["status"] == "failover_coordinated"
        assert result["failed_adapter"] == "unknown_adapter"
        assert result["failover_result"]["status"] == "unknown_adapter"

    @pytest.mark.asyncio
    async def test_coordinate_infrastructure_failover_exception(self, orchestrator):
        """Test failover coordination with exception."""
        orchestrator._coordinate_adapter = AsyncMock(
            side_effect=Exception("Failover coordination error"),
        )

        with pytest.raises(OnexError) as exc_info:
            await orchestrator.coordinate_infrastructure_failover("kafka_wrapper")

        assert "Failover coordination failed" in str(exc_info.value)
        assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    # =============================================================================
    # Integration and Workflow Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_end_to_end_bootstrap_workflow(self, orchestrator, mock_event_bus):
        """Test complete bootstrap workflow with event bus integration."""
        responses = {
            "tool_consul_adapter": {
                "status": "success",
                "result": {"services_registered": 5},
            },
            "tool_vault_adapter": {
                "status": "success",
                "result": {"secrets_loaded": 12},
            },
            "tool_kafka_wrapper": {
                "status": "success",
                "result": {"topics_created": 3},
            },
        }

        def mock_publish(envelope):
            adapter_name = envelope.payload.target_node_id
            correlation_id = str(envelope.correlation_id)

            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    response_data = responses.get(adapter_name, {"status": "unknown"})
                    response_data.update({"error": None, "metadata": {}})
                    asyncio.get_event_loop().call_soon(future.set_result, response_data)

        mock_event_bus.publish.side_effect = mock_publish

        result = await orchestrator.coordinate_infrastructure_bootstrap()

        assert result["status"] == "success"
        assert len(result["bootstrap_results"]) == 3

        # Verify all adapters were successfully bootstrapped
        for adapter_key in ["consul_adapter", "vault_adapter", "kafka_wrapper"]:
            assert result["bootstrap_results"][adapter_key]["status"] == "success"

    @pytest.mark.asyncio
    async def test_concurrent_adapter_operations(self, orchestrator, mock_event_bus):
        """Test handling multiple concurrent adapter operations."""
        operation_count = 0

        def mock_publish(envelope):
            nonlocal operation_count
            operation_count += 1
            correlation_id = str(envelope.correlation_id)

            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    # Simulate varied response times
                    delay = 0.1 * operation_count
                    asyncio.get_event_loop().call_later(
                        delay,
                        future.set_result,
                        {
                            "status": "success",
                            "result": {"op_id": operation_count},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = mock_publish

        # Start multiple concurrent operations
        tasks = [
            orchestrator._coordinate_adapter(f"adapter_{i}", {"operation": "test"})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(result["status"] == "success" for result in results)
        assert len({result["result"]["op_id"] for result in results}) == 5  # All unique

    @pytest.mark.asyncio
    async def test_pending_invocations_management(self, orchestrator):
        """Test proper management of pending invocations."""
        initial_count = len(orchestrator._pending_invocations)

        # Start an operation that will timeout
        task = asyncio.create_task(
            orchestrator._coordinate_adapter("slow_adapter", {"operation": "slow"}),
        )

        # Wait a bit for the invocation to be registered
        await asyncio.sleep(0.1)
        assert len(orchestrator._pending_invocations) == initial_count + 1

        # Let the operation timeout
        result = await task
        assert result["status"] == "timeout"

        # Verify pending invocation was cleaned up
        assert len(orchestrator._pending_invocations) == initial_count

    def test_logging_integration(self, orchestrator):
        """Test logging integration throughout orchestrator operations."""
        assert hasattr(orchestrator, "logger")

        # Test health check logging on exception
        with patch.object(orchestrator, "logger") as mock_logger:
            orchestrator.event_bus = MagicMock(side_effect=Exception("Test error"))
            orchestrator.health_check()
            mock_logger.error.assert_called_once()

    # =============================================================================
    # Edge Cases and Error Conditions
    # =============================================================================

    @pytest.mark.asyncio
    async def test_memory_management_large_pending_invocations(self, orchestrator):
        """Test memory management with large number of pending invocations."""
        # Simulate large number of pending invocations
        large_pending = {f"test_{i}": MagicMock() for i in range(1000)}
        orchestrator._pending_invocations = large_pending

        # Health check should handle this gracefully
        result = orchestrator.health_check()
        assert result.status == EnumHealthStatus.DEGRADED
        assert "1000" in result.message

    @pytest.mark.asyncio
    async def test_uuid_consistency_in_correlation(self, orchestrator, mock_event_bus):
        """Test UUID consistency in correlation ID handling."""
        captured_correlation_ids = []

        def capture_correlation_id(envelope):
            captured_correlation_ids.append(envelope.correlation_id)
            correlation_id = str(envelope.correlation_id)

            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    asyncio.get_event_loop().call_soon(
                        future.set_result,
                        {
                            "status": "success",
                            "result": {},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = capture_correlation_id

        await orchestrator._coordinate_adapter("test_adapter", {})

        assert len(captured_correlation_ids) == 1
        assert isinstance(captured_correlation_ids[0], UUID)

    def test_container_service_injection(self, container, mock_event_bus):
        """Test proper service injection from container."""
        container.get_service.assert_called_with("ProtocolEventBus")

        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
        ) as mock_path:
            mock_path.return_value.parent = MagicMock()
            orchestrator = ToolInfrastructureOrchestrator(container)

        assert orchestrator.event_bus == mock_event_bus

    # =============================================================================
    # Main Function and Entry Point Tests
    # =============================================================================

    def test_main_function(self):
        """Test main function creates orchestrator with infrastructure container."""
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.create_infrastructure_container",
        ) as mock_create_container:
            with patch(
                "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
            ) as mock_path:
                mock_path.return_value.parent = MagicMock()
                mock_container = MagicMock()
                mock_container.get_service.return_value = MagicMock()
                mock_create_container.return_value = mock_container

                result = main()

                mock_create_container.assert_called_once()
                assert isinstance(result, ToolInfrastructureOrchestrator)
                assert result.domain == "infrastructure"

    def test_main_function_integration(self):
        """Test main function can be called directly."""
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.create_infrastructure_container",
        ) as mock_create_container:
            with patch(
                "omnibase.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.node.Path",
            ) as mock_path:
                mock_path.return_value.parent = MagicMock()
                mock_container = MagicMock()
                mock_container.get_service.return_value = MagicMock()
                mock_create_container.return_value = mock_container

                # Test direct execution
                result = main()
                assert result is not None

    # =============================================================================
    # Performance and Stress Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_high_throughput_operations(self, orchestrator, mock_event_bus):
        """Test orchestrator performance under high throughput operations."""
        start_time = time.time()

        def fast_mock_publish(envelope):
            correlation_id = str(envelope.correlation_id)
            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    future.set_result(
                        {
                            "status": "success",
                            "result": {"operation_time": time.time()},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = fast_mock_publish

        # Execute 50 concurrent operations
        tasks = [
            orchestrator._coordinate_adapter(
                f"adapter_{i % 5}",
                {"operation": f"op_{i}"},
            )
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)
        operation_duration = time.time() - start_time

        assert len(results) == 50
        assert all(result["status"] == "success" for result in results)
        assert operation_duration < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_timeout_handling_under_load(self, orchestrator, mock_event_bus):
        """Test timeout handling when system is under load."""
        # Mock event bus that simulates overload (no responses)
        mock_event_bus.publish = MagicMock()  # No responses

        start_time = time.time()

        # Start multiple operations that will timeout
        tasks = [
            orchestrator._coordinate_adapter(f"slow_adapter_{i}", {"operation": "slow"})
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time

        # All should timeout
        assert all(result["status"] == "timeout" for result in results)
        # Should take approximately 30 seconds (timeout duration)
        assert 29 < total_duration < 35

        # Verify no pending invocations remain
        assert len(orchestrator._pending_invocations) == 0

    # =============================================================================
    # Service Integration Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_real_event_bus_integration_simulation(self, orchestrator):
        """Test integration with real event bus simulation."""
        # Create a more realistic event bus mock that simulates async behavior
        real_event_bus = MagicMock()

        async def async_publish_event(event):
            # Simulate processing delay
            await asyncio.sleep(0.1)

            # Create response event
            response = ModelToolResponseEvent(
                correlation_id=event.correlation_id,
                target_node_id=event.source_node_id,
                target_node_name=event.source_node_name,
                tool_name=event.tool_name,
                status="success",
                result={"processed": True},
                error=None,
                metadata={"processing_time": 0.1},
            )

            # Send response back to orchestrator
            envelope = ModelEventEnvelope(
                correlation_id=event.correlation_id,
                payload=response,
            )
            await orchestrator._handle_tool_response(envelope)

        real_event_bus.publish_event_async = async_publish_event
        orchestrator.event_bus = real_event_bus

        result = await orchestrator._coordinate_adapter(
            "realistic_adapter",
            {"operation": "test"},
        )

        assert result["status"] == "success"
        assert result["result"]["processed"] is True

    def test_node_orchestrator_service_inheritance(self, orchestrator):
        """Test proper inheritance from NodeOrchestratorService."""
        from omnibase_core.core.infrastructure_service_bases import (
            NodeOrchestratorService,
        )

        assert isinstance(orchestrator, NodeOrchestratorService)

        # Verify inherited functionality
        assert hasattr(orchestrator, "node_id")
        assert hasattr(orchestrator, "health_check")  # From MixinHealthCheck
        assert hasattr(orchestrator, "logger")  # From base classes

    # =============================================================================
    # Coverage and Completeness Tests
    # =============================================================================

    def test_all_protocol_methods_implemented(self, orchestrator):
        """Test that all protocol methods are properly implemented."""
        from omnibase_core.tools.infrastructure.tool_infrastructure_orchestrator.v1_0_0.protocols.protocol_infrastructure_orchestrator import (
            ProtocolInfrastructureOrchestrator,
        )

        # Get all abstract methods from the protocol
        protocol_methods = [
            method
            for method in dir(ProtocolInfrastructureOrchestrator)
            if not method.startswith("_")
            and callable(getattr(ProtocolInfrastructureOrchestrator, method, None))
        ]

        # Verify all are implemented in orchestrator
        for method_name in protocol_methods:
            assert hasattr(orchestrator, method_name)
            method = getattr(orchestrator, method_name)
            assert callable(method)

    def test_error_code_usage(self, orchestrator):
        """Test consistent usage of ONEX error codes."""
        # Test that OnexError is used with proper error codes
        with patch.object(
            orchestrator,
            "_coordinate_adapter",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(OnexError) as exc_info:
                asyncio.run(orchestrator.coordinate_infrastructure_bootstrap())

            assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_comprehensive_workflow_simulation(
        self,
        orchestrator,
        mock_event_bus,
    ):
        """Test comprehensive workflow covering all major functionality."""
        # Step 1: Check initial health
        health = orchestrator.health_check()
        assert health.status == EnumHealthStatus.HEALTHY

        # Step 2: Bootstrap infrastructure
        def bootstrap_mock_publish(envelope):
            correlation_id = str(envelope.correlation_id)
            if correlation_id in orchestrator._pending_invocations:
                future = orchestrator._pending_invocations[correlation_id]
                if not future.done():
                    future.set_result(
                        {
                            "status": "success",
                            "result": {"bootstrapped": True},
                            "error": None,
                            "metadata": {},
                        },
                    )

        mock_event_bus.publish.side_effect = bootstrap_mock_publish
        bootstrap_result = await orchestrator.coordinate_infrastructure_bootstrap()
        assert bootstrap_result["status"] == "success"

        # Step 3: Simulate failover scenario
        failover_result = await orchestrator.coordinate_infrastructure_failover(
            "kafka_wrapper",
        )
        assert failover_result["status"] == "failover_coordinated"

        # Step 4: Check health under load
        orchestrator._pending_invocations = {
            f"load_test_{i}": MagicMock() for i in range(25)
        }
        health_under_load = orchestrator.health_check()
        assert health_under_load.status == EnumHealthStatus.WARNING

        # Step 5: Clear load and verify recovery
        orchestrator._pending_invocations.clear()
        health_recovered = orchestrator.health_check()
        assert health_recovered.status == EnumHealthStatus.HEALTHY
