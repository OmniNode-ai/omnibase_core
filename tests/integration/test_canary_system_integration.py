"""
Integration tests for the complete canary system.

Tests the full end-to-end canary architecture including:
- Container setup and dependency injection
- Event-driven communication between nodes
- Health checks and metrics collection
- Effect operations with proper error handling
- Inter-node coordination and messaging

This test can be run repeatedly and provides comprehensive coverage
of the canary system functionality.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import pytest

from omnibase_core.core.node_effect import EffectType, ModelEffectInput
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.nodes.canary.canary_effect.v1_0_0.node import NodeCanaryEffect
from omnibase_core.nodes.canary.container import create_infrastructure_container


class TestCanarySystemIntegration:
    """Comprehensive integration tests for the canary system."""

    @pytest.fixture
    def container(self):
        """Create a fresh container for each test."""
        return create_infrastructure_container()

    @pytest.fixture
    def effect_node(self, container):
        """Create a canary effect node for testing."""
        return NodeCanaryEffect(container)

    def test_container_creation(self, container):
        """Test that the infrastructure container is created successfully."""
        assert container is not None

        # Verify essential services are registered
        assert hasattr(container, "_service_registry")
        registry = container._service_registry

        essential_services = [
            "event_bus",
            "ProtocolEventBus",
            "event_bus_service",
            "schema_loader",
            "ProtocolSchemaLoader",
        ]

        for service_name in essential_services:
            assert (
                service_name in registry
            ), f"Missing essential service: {service_name}"
            # Note: Services might be None if external systems unavailable,
            # but they should be registered

    def test_effect_node_initialization(self, effect_node):
        """Test that canary effect node initializes properly."""
        assert effect_node is not None
        assert hasattr(effect_node, "node_id")
        assert hasattr(effect_node, "config")
        assert effect_node.operation_count == 0
        assert effect_node.success_count == 0
        assert effect_node.error_count == 0

    @pytest.mark.asyncio
    async def test_health_check_operation(self, effect_node):
        """Test health check functionality."""
        health_status = await effect_node.get_health_status()

        assert health_status is not None
        assert health_status.status in [
            EnumHealthStatus.HEALTHY,
            EnumHealthStatus.DEGRADED,
        ]
        assert health_status.timestamp is not None
        assert hasattr(health_status, "details")
        assert health_status.details.service_name == "canary_effect"
        assert health_status.details.error_count is not None

    def test_metrics_collection(self, effect_node):
        """Test metrics collection and reporting."""
        metrics = effect_node.get_metrics()

        assert isinstance(metrics, dict)
        required_metrics = [
            "operation_count",
            "success_count",
            "error_count",
            "success_rate",
            "node_type",
        ]

        for metric in required_metrics:
            assert metric in metrics, f"Missing required metric: {metric}"

        assert metrics["node_type"] == "canary_effect"
        assert metrics["success_rate"] >= 0.0
        assert metrics["success_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_effect_operation_health_check(self, effect_node):
        """Test performing a health check effect operation."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "health_check",
                "parameters": {},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        assert hasattr(result, "result")
        assert "operation_result" in result.result
        assert hasattr(result, "metadata")
        assert result.metadata["node_type"] == "canary_effect"

        # Verify metrics were updated
        assert effect_node.operation_count > 0

    @pytest.mark.asyncio
    async def test_effect_operation_external_api_call(self, effect_node):
        """Test performing an external API call effect operation."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "external_api_call",
                "parameters": {"test_param": "test_value"},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        result_data = result.result

        # Verify the simulation worked
        assert "operation_result" in result_data
        operation_result = result_data["operation_result"]
        assert operation_result["api_response"] == "simulated_response"
        assert operation_result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_effect_operation_file_system(self, effect_node):
        """Test performing a file system effect operation."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.FILE_OPERATION,
            operation_data={
                "operation_type": "file_system_operation",
                "parameters": {"operation": "read"},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(
            effect_input, EffectType.FILE_OPERATION
        )

        assert result is not None
        result_data = result.result

        assert "operation_result" in result_data
        operation_result = result_data["operation_result"]
        assert operation_result["operation"] == "read"
        assert operation_result["result"] == "file_content_simulated"

    @pytest.mark.asyncio
    async def test_effect_operation_error_handling(self, effect_node):
        """Test error handling for invalid operations."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "invalid_operation_type",
                "parameters": {},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        result_data = result.result

        # Should have error information
        assert result_data["success"] is False
        assert "error_message" in result_data
        assert result.metadata.get("error") is True

        # Verify error metrics were updated
        assert effect_node.error_count > 0

    @pytest.mark.asyncio
    async def test_multiple_operations_metrics(self, effect_node):
        """Test that metrics are properly tracked across multiple operations."""
        initial_count = effect_node.operation_count

        # Perform multiple successful operations
        for i in range(3):
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": "health_check",
                    "parameters": {},
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        # Perform one error operation
        error_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "invalid_operation",
                "parameters": {},
                "correlation_id": str(uuid.uuid4()),
            },
        )
        await effect_node.perform_effect(error_input, EffectType.API_CALL)

        # Verify metrics
        assert effect_node.operation_count == initial_count + 4
        assert effect_node.success_count >= 3
        assert effect_node.error_count >= 1

        success_rate = effect_node.success_count / effect_node.operation_count
        assert 0.0 <= success_rate <= 1.0

    def test_node_configuration_loading(self, effect_node):
        """Test that node configuration is loaded properly."""
        assert hasattr(effect_node, "config")
        config = effect_node.config

        # Verify config has expected structure
        assert hasattr(config, "performance")
        assert hasattr(config.performance, "min_operations_for_health")
        assert hasattr(config.performance, "error_rate_threshold")

    @pytest.mark.asyncio
    async def test_health_status_degradation(self, effect_node):
        """Test that health status degrades with high error rates."""
        # Force enough operations to trigger health evaluation
        min_ops = effect_node.config.performance.min_operations_for_health + 1

        # Perform mostly error operations
        for i in range(min_ops):
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": "invalid_operation",
                    "parameters": {},
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        health_status = await effect_node.get_health_status()

        # With high error rate, should be degraded
        error_rate = effect_node.error_count / effect_node.operation_count
        threshold = effect_node.config.performance.error_rate_threshold

        if error_rate > threshold:
            assert health_status.status == EnumHealthStatus.DEGRADED

    def test_event_bus_integration(self, container):
        """Test that event bus integration works properly."""
        # Verify event bus services are available
        event_bus = container.get_service("ProtocolEventBus")
        event_bus_service = container.get_service("event_bus_service")

        # These might be None if external systems unavailable, but should be registered
        assert "ProtocolEventBus" in container._service_registry
        assert "event_bus_service" in container._service_registry

    @pytest.mark.asyncio
    async def test_end_to_end_canary_workflow(self, effect_node):
        """Test a complete end-to-end canary workflow."""
        # Step 1: Initial health check
        initial_health = await effect_node.get_health_status()
        assert initial_health.status in [
            EnumHealthStatus.HEALTHY,
            EnumHealthStatus.DEGRADED,
        ]

        # Step 2: Perform various effect operations
        operations = [
            "health_check",
            "external_api_call",
            "file_system_operation",
            "database_operation",
            "message_queue_operation",
        ]

        results = []
        for operation in operations:
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": operation,
                    "parameters": {"test": f"param_for_{operation}"},
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)
            results.append(result)

        # Step 3: Verify all operations completed
        assert len(results) == len(operations)
        for result in results:
            assert result is not None
            assert hasattr(result, "result")
            assert "operation_result" in result.result

        # Step 4: Final health and metrics check
        final_health = await effect_node.get_health_status()
        final_metrics = effect_node.get_metrics()

        assert final_health is not None
        assert final_metrics["operation_count"] >= len(operations)
        assert final_metrics["success_count"] > 0


if __name__ == "__main__":
    """Run integration tests directly."""
    pytest.main([__file__, "-v", "--tb=short"])
