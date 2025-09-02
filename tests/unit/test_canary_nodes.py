#!/usr/bin/env python3
"""
Unit Tests for Canary Nodes

Fast, isolated unit tests for all canary node types without external dependencies.
These tests validate core functionality and business logic.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from omnibase_core.core.node_effect import EffectType, ModelEffectInput
from omnibase_core.core.node_reducer import ModelReducerInput, ReductionType
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.nodes.canary.canary_effect.v1_0_0.node import NodeCanaryEffect
from omnibase_core.nodes.canary.canary_reducer.v1_0_0.node import NodeCanaryReducer
from omnibase_core.nodes.canary.canary_compute.v1_0_0.node import NodeCanaryCompute
from omnibase_core.nodes.canary.canary_orchestrator.v1_0_0.node import NodeCanaryOrchestrator
from omnibase_core.nodes.canary.canary_gateway.v1_0_0.node import NodeCanaryGateway


class TestCanaryEffect:
    """Unit tests for Canary Effect Node."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        container._service_registry = {}
        return container

    @pytest.fixture
    def effect_node(self, mock_container):
        """Create effect node with mocked dependencies."""
        return NodeCanaryEffect(mock_container)

    @pytest.mark.asyncio
    async def test_health_check_operation(self, effect_node):
        """Test health check effect operation."""
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
        assert "operation_result" in result.result
        assert result.metadata["node_type"] == "canary_effect"
        assert effect_node.operation_count == 1
        assert effect_node.success_count == 1

    @pytest.mark.asyncio
    async def test_external_api_call_operation(self, effect_node):
        """Test external API call simulation."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "external_api_call",
                "parameters": {"endpoint": "test"},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        assert result.result["operation_result"]["api_response"] == "simulated_response"
        assert result.result["operation_result"]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_file_system_operation(self, effect_node):
        """Test file system operation simulation."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.FILE_OPERATION,
            operation_data={
                "operation_type": "file_system_operation",
                "parameters": {"operation": "read"},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.FILE_OPERATION)

        assert result is not None
        assert result.result["operation_result"]["result"] == "file_content_simulated"

    @pytest.mark.asyncio
    async def test_error_handling(self, effect_node):
        """Test error handling for invalid operations."""
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "invalid_operation",
                "parameters": {},
                "correlation_id": str(uuid.uuid4()),
            },
        )

        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        assert result.result["success"] is False
        assert "error_message" in result.result
        assert effect_node.error_count > 0

    @pytest.mark.asyncio
    async def test_health_status(self, effect_node):
        """Test health status reporting."""
        # Perform some operations first
        for _ in range(3):
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": "health_check",
                    "parameters": {},
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        health_status = await effect_node.get_health_status()

        assert health_status.status in [EnumHealthStatus.HEALTHY, EnumHealthStatus.DEGRADED]
        assert health_status.details["node_type"] == "canary_effect"
        assert health_status.details["operation_count"] >= 3

    def test_metrics_collection(self, effect_node):
        """Test metrics collection."""
        metrics = effect_node.get_metrics()

        assert isinstance(metrics, dict)
        assert "operation_count" in metrics
        assert "success_count" in metrics
        assert "error_count" in metrics
        assert "success_rate" in metrics
        assert metrics["node_type"] == "canary_effect"
        assert 0.0 <= metrics["success_rate"] <= 1.0


class TestCanaryCompute:
    """Unit tests for Canary Compute Node."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        return container

    @pytest.fixture
    def compute_node(self, mock_container):
        """Create compute node with mocked dependencies."""
        return NodeCanaryCompute(mock_container)

    @pytest.mark.asyncio
    async def test_data_validation(self, compute_node):
        """Test data validation computation."""
        from omnibase_core.core.node_compute import ModelComputeInput

        compute_input = ModelComputeInput(
            data={
                "operation_type": "data_validation",
                "data_payload": {"name": "test", "age": 25},
                "parameters": {
                    "rules": [
                        {"field": "name", "type": "string", "required": True},
                        {"field": "age", "type": "number", "required": True}
                    ]
                }
            }
        )

        result = await compute_node.compute(compute_input)

        assert result is not None
        assert result.data["computation_result"]["valid"] is True
        assert result.data["success"] is True

    @pytest.mark.asyncio
    async def test_business_logic_customer_scoring(self, compute_node):
        """Test customer scoring business logic."""
        from omnibase_core.core.node_compute import ModelComputeInput

        compute_input = ModelComputeInput(
            data={
                "operation_type": "business_logic",
                "data_payload": {
                    "purchase_history": 150,
                    "loyalty_years": 3,
                    "support_tickets": 1
                },
                "parameters": {"logic_type": "customer_scoring"}
            }
        )

        result = await compute_node.compute(compute_input)

        assert result is not None
        assert result.data["success"] is True
        computation_result = result.data["computation_result"]
        assert "customer_score" in computation_result
        assert "tier" in computation_result
        assert computation_result["tier"] in ["premium", "standard"]

    @pytest.mark.asyncio
    async def test_data_transformation(self, compute_node):
        """Test data transformation operations."""
        from omnibase_core.core.node_compute import ModelComputeInput

        compute_input = ModelComputeInput(
            data={
                "operation_type": "data_transformation",
                "data_payload": {"NAME": "  JOHN DOE  ", "Age": "30", "score": 85.5},
                "parameters": {"transformation": "normalize"}
            }
        )

        result = await compute_node.compute(compute_input)

        assert result is not None
        assert result.data["success"] is True
        transformed = result.data["computation_result"]["transformed_data"]
        assert transformed["NAME"] == "john doe"  # normalized string
        assert transformed["Age"] == 30.0  # normalized number

    @pytest.mark.asyncio
    async def test_mathematical_calculations(self, compute_node):
        """Test mathematical calculation operations."""
        from omnibase_core.core.node_compute import ModelComputeInput

        compute_input = ModelComputeInput(
            data={
                "operation_type": "calculation",
                "data_payload": {"value1": 10, "value2": 20, "value3": 30},
                "parameters": {"calculation": "sum"}
            }
        )

        result = await compute_node.compute(compute_input)

        assert result is not None
        assert result.data["success"] is True
        assert result.data["computation_result"]["result"] == 60
        assert result.data["computation_result"]["calculation"] == "sum"


class TestCanaryReducer:
    """Unit tests for Canary Reducer Node."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        return container

    @pytest.fixture
    def reducer_node(self, mock_container):
        """Create reducer node with mocked dependencies."""
        return NodeCanaryReducer(mock_container)

    @pytest.mark.asyncio
    async def test_health_aggregation(self, reducer_node):
        """Test health status aggregation."""
        health_data = [
            {"service_name": "service1", "status": "healthy"},
            {"service_name": "service2", "status": "healthy"},
            {"service_name": "service3", "status": "degraded"}
        ]

        reducer_input = ModelReducerInput(
            data=health_data,
            reduction_type=ReductionType.AGGREGATE
        )

        result = await reducer_node.reduce(reducer_input)

        assert result is not None
        assert result.data["success"] is True

    @pytest.mark.asyncio
    async def test_metric_aggregation(self, reducer_node):
        """Test metric data aggregation."""
        metric_data = [
            {"node": "node1", "cpu": 45.2, "memory": 78.1},
            {"node": "node2", "cpu": 52.8, "memory": 65.3},
            {"node": "node3", "cpu": 38.9, "memory": 82.7}
        ]

        reducer_input = ModelReducerInput(
            data=metric_data,
            reduction_type=ReductionType.AGGREGATE
        )

        result = await reducer_node.reduce(reducer_input)

        assert result is not None
        assert result.data["success"] is True


class TestCanaryOrchestrator:
    """Unit tests for Canary Orchestrator Node."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        return container

    @pytest.fixture
    def orchestrator_node(self, mock_container):
        """Create orchestrator node with mocked dependencies."""
        return NodeCanaryOrchestrator(mock_container)

    @pytest.mark.asyncio
    async def test_workflow_coordination(self, orchestrator_node):
        """Test workflow coordination capabilities."""
        from omnibase_core.core.node_orchestrator import ModelOrchestratorInput

        orchestrator_input = ModelOrchestratorInput(
            workflow_definition={
                "steps": [
                    {"name": "step1", "type": "effect", "operation": "health_check"},
                    {"name": "step2", "type": "compute", "operation": "data_validation"}
                ]
            }
        )

        result = await orchestrator_node.orchestrate(orchestrator_input)

        assert result is not None
        assert result.data["success"] is True
        assert "workflow_result" in result.data


class TestCanaryGateway:
    """Unit tests for Canary Gateway Node."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        return container

    @pytest.fixture
    def gateway_node(self, mock_container):
        """Create gateway node with mocked dependencies."""
        return NodeCanaryGateway(mock_container)

    @pytest.mark.asyncio
    async def test_message_routing(self, gateway_node):
        """Test message routing capabilities."""
        from omnibase_core.core.node_gateway import ModelGatewayInput

        gateway_input = ModelGatewayInput(
            message={
                "type": "health_check_request",
                "target": "canary_nodes",
                "payload": {"service": "canary_effect"}
            }
        )

        result = await gateway_node.route(gateway_input)

        assert result is not None
        assert result.data["success"] is True

    def test_caching_functionality(self, gateway_node):
        """Test caching functionality."""
        test_key = "test_cache_key"
        test_value = {"data": "test_value"}

        # Test cache set
        gateway_node._cache[test_key] = test_value

        # Test cache get
        cached_value = gateway_node._cache.get(test_key)
        assert cached_value == test_value


class TestCanaryNodeIntegration:
    """Integration tests between canary nodes."""

    @pytest.fixture
    def mock_container(self):
        """Mock container for testing."""
        container = Mock()
        container._service_registry = {}
        return container

    @pytest.mark.asyncio
    async def test_effect_to_reducer_integration(self, mock_container):
        """Test integration between effect and reducer nodes."""
        effect_node = NodeCanaryEffect(mock_container)
        reducer_node = NodeCanaryReducer(mock_container)

        # Generate some effect results
        effect_results = []
        for i in range(3):
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": "health_check",
                    "parameters": {},
                    "correlation_id": str(uuid.uuid4()),
                },
            )
            result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)
            effect_results.append(result.result)

        # Aggregate results with reducer
        reducer_input = ModelReducerInput(
            data=effect_results,
            reduction_type=ReductionType.AGGREGATE
        )

        final_result = await reducer_node.reduce(reducer_input)

        assert final_result is not None
        assert final_result.data["success"] is True
        assert len(effect_results) == 3

    @pytest.mark.asyncio
    async def test_compute_to_reducer_integration(self, mock_container):
        """Test integration between compute and reducer nodes."""
        compute_node = NodeCanaryCompute(mock_container)
        reducer_node = NodeCanaryReducer(mock_container)

        # Generate computation results
        from omnibase_core.core.node_compute import ModelComputeInput

        compute_results = []
        for i in range(2):
            compute_input = ModelComputeInput(
                data={
                    "operation_type": "calculation",
                    "data_payload": {"value1": i * 10, "value2": (i + 1) * 10},
                    "parameters": {"calculation": "sum"}
                }
            )
            result = await compute_node.compute(compute_input)
            compute_results.append(result.data["computation_result"])

        # Aggregate computation results
        reducer_input = ModelReducerInput(
            data=compute_results,
            reduction_type=ReductionType.AGGREGATE
        )

        final_result = await reducer_node.reduce(reducer_input)

        assert final_result is not None
        assert final_result.data["success"] is True


if __name__ == "__main__":
    """Run unit tests directly."""
    pytest.main([__file__, "-v"])