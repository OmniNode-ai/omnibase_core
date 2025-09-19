# Nodes Integration Examples

## Overview

This document provides comprehensive examples of integrating with the ONEX four-node architecture, demonstrating common patterns, best practices, and real-world use cases for each node type.

## Basic Integration Patterns

### Simple Linear Processing

**Use Case**: Data retrieval, processing, and storage

```python
from omnibase_core.core.infrastructure_service_bases import (
    NodeEffectService,
    NodeComputeService,
    NodeReducerService
)

# 1. EFFECT Node - Data Retrieval
class DataRetrievalEffectNode(NodeEffectService):
    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        # External data source interaction
        api_service = self.container.get_service("ProtocolExternalAPI")

        external_data = await api_service.fetch_data(
            endpoint=input_data.data["endpoint"],
            parameters=input_data.data.get("parameters", {})
        )

        return ModelEffectOutput(
            data={"raw_data": external_data},
            metadata={"source": "external_api", "timestamp": datetime.now().isoformat()}
        )

# 2. COMPUTE Node - Data Processing
class DataProcessingComputeNode(NodeComputeService):
    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        raw_data = input_data.data["raw_data"]

        # Data transformation and analysis
        processed_data = {
            "total_records": len(raw_data),
            "processed_at": datetime.now().isoformat(),
            "summary_statistics": self._calculate_statistics(raw_data),
            "cleaned_data": self._clean_data(raw_data)
        }

        return ModelComputeOutput(
            data=processed_data,
            metadata={"processing_time_ms": 150, "algorithm": "statistical_summary"}
        )

    def _calculate_statistics(self, data: list) -> dict:
        if not data:
            return {"count": 0, "average": 0, "total": 0}

        numeric_values = [item.get("value", 0) for item in data if isinstance(item.get("value"), (int, float))]

        return {
            "count": len(numeric_values),
            "total": sum(numeric_values),
            "average": sum(numeric_values) / len(numeric_values) if numeric_values else 0,
            "min": min(numeric_values) if numeric_values else 0,
            "max": max(numeric_values) if numeric_values else 0
        }

    def _clean_data(self, data: list) -> list:
        # Remove invalid entries and normalize
        cleaned = []
        for item in data:
            if isinstance(item, dict) and "value" in item:
                cleaned_item = {
                    "id": item.get("id", "unknown"),
                    "value": float(item["value"]) if isinstance(item["value"], (int, float)) else 0,
                    "timestamp": item.get("timestamp", datetime.now().isoformat())
                }
                cleaned.append(cleaned_item)
        return cleaned

# 3. REDUCER Node - State Aggregation
class DataAggregationReducerNode(NodeReducerService):
    async def reduce(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        processed_data = input_data.data

        # Get existing state
        state_service = self.container.get_service("ProtocolStateManager")
        current_state = await state_service.get_state("data_aggregation")

        # Update aggregated state
        updated_state = self._update_aggregate_state(current_state, processed_data)

        # Persist updated state
        await state_service.update_state("data_aggregation", updated_state)

        return ModelReducerOutput(
            data={"updated_state": updated_state},
            metadata={"state_version": updated_state["version"], "records_aggregated": len(processed_data.get("cleaned_data", []))}
        )

    def _update_aggregate_state(self, current_state: dict, new_data: dict) -> dict:
        if not current_state:
            current_state = {"version": 0, "total_records": 0, "total_value": 0, "last_update": None}

        cleaned_data = new_data.get("cleaned_data", [])
        new_total_value = sum(item["value"] for item in cleaned_data)

        return {
            "version": current_state["version"] + 1,
            "total_records": current_state["total_records"] + len(cleaned_data),
            "total_value": current_state["total_value"] + new_total_value,
            "last_update": datetime.now().isoformat(),
            "last_batch_summary": new_data.get("summary_statistics", {})
        }

# Integration Example
async def process_data_pipeline(external_endpoint: str) -> dict:
    """Complete data processing pipeline example."""
    container = create_container()

    # Initialize nodes
    effect_node = DataRetrievalEffectNode(container)
    compute_node = DataProcessingComputeNode(container)
    reducer_node = DataAggregationReducerNode(container)

    # Step 1: Retrieve data
    effect_input = ModelEffectInput(data={"endpoint": external_endpoint})
    effect_result = await effect_node.process(effect_input)

    # Step 2: Process data
    compute_input = ModelComputeInput(data=effect_result.data)
    compute_result = await compute_node.compute(compute_input)

    # Step 3: Aggregate state
    reducer_input = ModelReducerInput(data=compute_result.data)
    reducer_result = await reducer_node.reduce(reducer_input)

    return {
        "pipeline_completed": True,
        "final_state": reducer_result.data["updated_state"],
        "processing_metadata": {
            "effect_metadata": effect_result.metadata,
            "compute_metadata": compute_result.metadata,
            "reducer_metadata": reducer_result.metadata
        }
    }
```

### Orchestrated Workflow

**Use Case**: Complex multi-step workflow with error handling and rollback

```python
class WorkflowOrchestratorNode(NodeOrchestratorService):
    async def orchestrate(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
        workflow_definition = input_data.data["workflow"]

        execution_context = {
            "workflow_id": str(uuid.uuid4()),
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "rollback_actions": []
        }

        try:
            results = []

            for step in workflow_definition["steps"]:
                step_result = await self._execute_workflow_step(step, execution_context)
                results.append(step_result)
                execution_context["steps_completed"].append(step["id"])

                # Check for step failure
                if not step_result.get("success", True):
                    await self._handle_workflow_failure(execution_context)
                    break

            return ModelOrchestratorOutput(
                data={
                    "workflow_completed": True,
                    "execution_context": execution_context,
                    "step_results": results
                },
                metadata={"total_steps": len(workflow_definition["steps"]), "completed_steps": len(results)}
            )

        except Exception as e:
            await self._handle_workflow_failure(execution_context)
            raise OnexError(
                message=f"Workflow execution failed: {str(e)}",
                error_code=CoreErrorCode.WORKFLOW_EXECUTION_FAILED,
                context=execution_context
            )

    async def _execute_workflow_step(self, step: dict, context: dict) -> dict:
        """Execute individual workflow step."""
        step_type = step["type"]
        step_input = step["input"]

        if step_type == "effect":
            service = self.container.get_service("ProtocolEffectService")
            result = await service.process(ModelEffectInput(data=step_input))
            context["rollback_actions"].append({"type": "effect_rollback", "step_id": step["id"]})

        elif step_type == "compute":
            service = self.container.get_service("ProtocolComputeService")
            result = await service.compute(ModelComputeInput(data=step_input))

        elif step_type == "reducer":
            service = self.container.get_service("ProtocolReducerService")
            result = await service.reduce(ModelReducerInput(data=step_input))
            context["rollback_actions"].append({"type": "state_rollback", "step_id": step["id"]})

        else:
            raise ValueError(f"Unknown step type: {step_type}")

        return {
            "step_id": step["id"],
            "step_type": step_type,
            "success": True,
            "result": result.data,
            "metadata": getattr(result, 'metadata', {})
        }

    async def _handle_workflow_failure(self, context: dict):
        """Handle workflow failure with rollback actions."""
        rollback_service = self.container.get_service("ProtocolRollbackService")

        # Execute rollback actions in reverse order
        for rollback_action in reversed(context["rollback_actions"]):
            await rollback_service.execute_rollback(rollback_action)

        context["rollback_completed"] = True
        context["failed_at"] = datetime.now().isoformat()
```

## Event-Driven Integration

### Publisher-Subscriber Pattern

```python
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope

class EventPublisherEffectNode(NodeEffectService):
    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        # Process external interaction
        result = await self._perform_external_operation(input_data.data)

        # Publish event for downstream processing
        event = ModelEventEnvelope(
            event_type="external_data_received",
            payload={
                "data": result,
                "source_node": "event_publisher_effect",
                "timestamp": datetime.now().isoformat()
            },
            correlation_id=input_data.correlation_id,
            metadata={"node_id": self.node_id, "operation": "data_retrieval"}
        )

        event_bus = self.container.get_service("ProtocolEventBus")
        await event_bus.publish(event)

        return ModelEffectOutput(
            data=result,
            metadata={"event_published": True, "event_type": "external_data_received"}
        )

class EventSubscriberComputeNode(NodeComputeService):
    def __init__(self, container: ONEXContainer):
        super().__init__(container)

        # Subscribe to events
        event_bus = container.get_service("ProtocolEventBus")
        event_bus.subscribe("external_data_received", self._handle_external_data_event)

    async def _handle_external_data_event(self, event: ModelEventEnvelope):
        """Handle incoming event and trigger computation."""
        event_data = event.payload["data"]

        # Create compute input from event
        compute_input = ModelComputeInput(
            data=event_data,
            correlation_id=event.correlation_id
        )

        # Process computation
        result = await self.compute(compute_input)

        # Publish computation result
        result_event = ModelEventEnvelope(
            event_type="computation_completed",
            payload={
                "computation_result": result.data,
                "original_correlation_id": event.correlation_id
            },
            correlation_id=event.correlation_id
        )

        event_bus = self.container.get_service("ProtocolEventBus")
        await event_bus.publish(result_event)

    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        # Standard compute implementation
        processed_data = self._process_data(input_data.data)

        return ModelComputeOutput(
            data=processed_data,
            metadata={"processing_type": "event_driven"}
        )
```

## Microservices Integration

### Service Registry Pattern

```python
from omnibase_core.models.nodes import ModelNodeInformation, ModelNodeCapability

class ServiceRegistryIntegration:
    """Integration with external service registry."""

    def __init__(self, container: ONEXContainer):
        self.container = container
        self.service_registry = container.get_service("ProtocolServiceRegistry")

    async def register_node_service(self, node: NodeComputeService, endpoint: str):
        """Register node as a microservice."""
        node_info = ModelNodeInformation(
            node_id=f"compute-service-{uuid.uuid4().hex[:8]}",
            node_type=EnumNodeType.COMPUTE,
            capabilities=[
                ModelNodeCapability(name="data_processing", version="1.0.0"),
                ModelNodeCapability(name="statistical_analysis", version="1.2.0")
            ],
            endpoint=endpoint,
            health_check_endpoint=f"{endpoint}/health",
            metadata={
                "service_type": "compute",
                "deployment_environment": "production",
                "scaling_policy": "auto"
            }
        )

        await self.service_registry.register_service(node_info)
        return node_info.node_id

    async def discover_services(self, capability_name: str) -> list[ModelNodeInformation]:
        """Discover services by capability."""
        return await self.service_registry.find_services_by_capability(capability_name)

class DistributedComputeNode(NodeComputeService):
    """Compute node that can scale across multiple instances."""

    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        # Check if computation should be distributed
        if self._should_distribute(input_data):
            return await self._distributed_compute(input_data)
        else:
            return await self._local_compute(input_data)

    def _should_distribute(self, input_data: ModelComputeInput) -> bool:
        """Determine if computation should be distributed."""
        data_size = len(str(input_data.data))
        complexity = input_data.data.get("complexity", "low")

        return data_size > 10000 or complexity == "high"

    async def _distributed_compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        """Distribute computation across multiple nodes."""
        service_registry = self.container.get_service("ProtocolServiceRegistry")

        # Find available compute nodes
        compute_nodes = await service_registry.find_services_by_capability("data_processing")

        if not compute_nodes:
            # Fallback to local computation
            return await self._local_compute(input_data)

        # Partition data for distributed processing
        partitions = self._partition_data(input_data.data, len(compute_nodes))

        # Send partitions to different nodes
        tasks = []
        for i, partition in enumerate(partitions):
            node = compute_nodes[i % len(compute_nodes)]
            partition_input = ModelComputeInput(
                data=partition,
                correlation_id=f"{input_data.correlation_id}-partition-{i}"
            )
            task = self._remote_compute(node.endpoint, partition_input)
            tasks.append(task)

        # Gather results
        partition_results = await asyncio.gather(*tasks)

        # Aggregate distributed results
        aggregated_result = self._aggregate_results(partition_results)

        return ModelComputeOutput(
            data=aggregated_result,
            metadata={
                "computation_type": "distributed",
                "partitions": len(partitions),
                "nodes_used": len(compute_nodes)
            }
        )

    async def _local_compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        """Local computation implementation."""
        # Standard local processing
        result = self._process_data_locally(input_data.data)

        return ModelComputeOutput(
            data=result,
            metadata={"computation_type": "local"}
        )
```

## Database Integration

### Repository Pattern with EFFECT Nodes

```python
class DatabaseEffectNode(NodeEffectService):
    """Database operations through EFFECT node."""

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        operation = input_data.data["operation"]

        db_service = self.container.get_service("ProtocolDatabase")

        if operation == "create":
            result = await self._create_record(db_service, input_data.data)
        elif operation == "read":
            result = await self._read_records(db_service, input_data.data)
        elif operation == "update":
            result = await self._update_record(db_service, input_data.data)
        elif operation == "delete":
            result = await self._delete_record(db_service, input_data.data)
        else:
            raise ValueError(f"Unknown database operation: {operation}")

        return ModelEffectOutput(
            data=result,
            metadata={"operation": operation, "table": input_data.data.get("table")}
        )

    async def _create_record(self, db_service, data: dict) -> dict:
        """Create new database record."""
        table = data["table"]
        record_data = data["record"]

        result = await db_service.insert(table, record_data)

        return {
            "operation": "create",
            "record_id": result.inserted_id,
            "success": True
        }

    async def _read_records(self, db_service, data: dict) -> dict:
        """Read database records."""
        table = data["table"]
        filters = data.get("filters", {})
        limit = data.get("limit", 100)

        result = await db_service.select(table, filters, limit=limit)

        return {
            "operation": "read",
            "records": result.records,
            "count": len(result.records),
            "success": True
        }

class DataPersistenceReducerNode(NodeReducerService):
    """Reducer for managing data persistence state."""

    async def reduce(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        persistence_operation = input_data.data

        # Get database effect node
        db_effect = self.container.get_service("ProtocolDatabaseEffect")

        # Execute database operation
        db_input = ModelEffectInput(data=persistence_operation)
        db_result = await db_effect.process(db_input)

        # Update persistence state
        state_service = self.container.get_service("ProtocolStateManager")
        current_state = await state_service.get_state("data_persistence")

        updated_state = self._update_persistence_state(current_state, db_result.data)
        await state_service.update_state("data_persistence", updated_state)

        return ModelReducerOutput(
            data={
                "persistence_result": db_result.data,
                "updated_state": updated_state
            },
            metadata={"state_version": updated_state["version"]}
        )
```

## API Gateway Integration

### HTTP Service Wrapper

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class NodeHTTPWrapper:
    """HTTP wrapper for ONEX nodes."""

    def __init__(self, node, app: FastAPI):
        self.node = node
        self.app = app
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes for node operations."""

        if isinstance(self.node, NodeEffectService):
            @self.app.post("/effect/process")
            async def process_effect(request: dict):
                try:
                    input_data = ModelEffectInput(data=request)
                    result = await self.node.process(input_data)
                    return {"success": True, "data": result.data, "metadata": result.metadata}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

        elif isinstance(self.node, NodeComputeService):
            @self.app.post("/compute/process")
            async def process_compute(request: dict):
                try:
                    input_data = ModelComputeInput(data=request)
                    result = await self.node.compute(input_data)
                    return {"success": True, "data": result.data, "metadata": result.metadata}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health_check():
            try:
                health_status = await self.node.get_health_status()
                return {
                    "status": health_status.status.value,
                    "timestamp": health_status.timestamp.isoformat(),
                    "details": health_status.details
                }
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        @self.app.get("/metrics")
        async def get_metrics():
            try:
                metrics = self.node.get_metrics()
                return metrics
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

# Usage Example
def create_node_service(node_class, port: int):
    """Create HTTP service for a node."""
    app = FastAPI(title=f"{node_class.__name__} Service")
    container = create_container()
    node = node_class(container)

    wrapper = NodeHTTPWrapper(node, app)

    return app

# Deploy multiple node services
if __name__ == "__main__":
    import uvicorn

    # Deploy different node types on different ports
    effect_app = create_node_service(DataRetrievalEffectNode, 8001)
    compute_app = create_node_service(DataProcessingComputeNode, 8002)
    reducer_app = create_node_service(DataAggregationReducerNode, 8003)

    # Run services (in production, use proper process management)
    uvicorn.run(effect_app, host="0.0.0.0", port=8001)
```

## Testing Integration Examples

### Integration Test Suite

```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestNodeIntegration:
    """Comprehensive integration tests for node patterns."""

    @pytest.fixture
    def mock_container(self):
        """Create mock container for testing."""
        container = Mock()

        # Mock services
        container.get_service.side_effect = lambda name: {
            "ProtocolDatabase": AsyncMock(),
            "ProtocolEventBus": AsyncMock(),
            "ProtocolStateManager": AsyncMock(),
            "ProtocolLogger": Mock()
        }.get(name, Mock())

        return container

    @pytest.mark.asyncio
    async def test_linear_processing_pipeline(self, mock_container):
        """Test complete linear processing pipeline."""

        # Setup nodes
        effect_node = DataRetrievalEffectNode(mock_container)
        compute_node = DataProcessingComputeNode(mock_container)
        reducer_node = DataAggregationReducerNode(mock_container)

        # Mock external API response
        mock_api_data = [
            {"id": "1", "value": 100, "timestamp": "2025-01-01"},
            {"id": "2", "value": 200, "timestamp": "2025-01-02"}
        ]

        # Test pipeline execution
        effect_input = ModelEffectInput(data={"endpoint": "test-api"})

        # Mock effect result
        effect_node._perform_external_operation = AsyncMock(return_value=mock_api_data)
        effect_result = await effect_node.process(effect_input)

        # Test compute processing
        compute_input = ModelComputeInput(data=effect_result.data)
        compute_result = await compute_node.compute(compute_input)

        # Verify compute results
        assert compute_result.data["total_records"] == 2
        assert compute_result.data["summary_statistics"]["total"] == 300

        # Test reducer aggregation
        reducer_input = ModelReducerInput(data=compute_result.data)
        reducer_result = await reducer_node.reduce(reducer_input)

        # Verify reducer results
        assert "updated_state" in reducer_result.data
        assert reducer_result.data["updated_state"]["total_records"] == 2

    @pytest.mark.asyncio
    async def test_event_driven_processing(self, mock_container):
        """Test event-driven node communication."""

        publisher_node = EventPublisherEffectNode(mock_container)
        subscriber_node = EventSubscriberComputeNode(mock_container)

        # Mock event bus
        event_bus = mock_container.get_service("ProtocolEventBus")

        # Test event publishing
        effect_input = ModelEffectInput(data={"test": "data"})
        publisher_node._perform_external_operation = AsyncMock(return_value={"result": "success"})

        result = await publisher_node.process(effect_input)

        # Verify event was published
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.event_type == "external_data_received"
        assert published_event.payload["data"]["result"] == "success"

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_container):
        """Test error handling across node integration."""

        # Setup node with error condition
        compute_node = DataProcessingComputeNode(mock_container)

        # Test with invalid input that should trigger error
        invalid_input = ModelComputeInput(data={"invalid": "structure"})

        # Should handle error gracefully
        result = await compute_node.compute(invalid_input)

        # Verify error handling
        assert result.data is not None  # Should not crash

    @pytest.mark.asyncio
    async def test_workflow_orchestration(self, mock_container):
        """Test complex workflow orchestration."""

        orchestrator = WorkflowOrchestratorNode(mock_container)

        # Mock service dependencies
        mock_container.get_service.side_effect = lambda name: {
            "ProtocolEffectService": AsyncMock(process=AsyncMock(return_value=Mock(data={"effect": "result"}))),
            "ProtocolComputeService": AsyncMock(compute=AsyncMock(return_value=Mock(data={"compute": "result"}))),
            "ProtocolReducerService": AsyncMock(reduce=AsyncMock(return_value=Mock(data={"reducer": "result"}))),
            "ProtocolRollbackService": AsyncMock()
        }.get(name, Mock())

        # Define test workflow
        workflow_definition = {
            "steps": [
                {"id": "step1", "type": "effect", "input": {"data": "test"}},
                {"id": "step2", "type": "compute", "input": {"data": "test"}},
                {"id": "step3", "type": "reducer", "input": {"data": "test"}}
            ]
        }

        # Execute workflow
        orchestrator_input = ModelOrchestratorInput(data={"workflow": workflow_definition})
        result = await orchestrator.orchestrate(orchestrator_input)

        # Verify workflow execution
        assert result.data["workflow_completed"] is True
        assert len(result.data["step_results"]) == 3
        assert result.metadata["completed_steps"] == 3

class TestPerformanceIntegration:
    """Performance testing for node integration."""

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_container):
        """Test concurrent node processing."""
        import asyncio
        import time

        compute_node = DataProcessingComputeNode(mock_container)

        # Create multiple concurrent requests
        inputs = [
            ModelComputeInput(data={"values": list(range(i*10, (i+1)*10))})
            for i in range(10)
        ]

        # Measure concurrent processing time
        start_time = time.time()

        tasks = [compute_node.compute(input_data) for input_data in inputs]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify all requests completed
        assert len(results) == 10
        assert all(result.data for result in results)

        # Performance assertion (adjust based on requirements)
        assert processing_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, mock_container):
        """Test memory usage during integration."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Process large dataset
        compute_node = DataProcessingComputeNode(mock_container)

        large_input = ModelComputeInput(data={
            "values": list(range(10000)),
            "metadata": {f"key_{i}": f"value_{i}" for i in range(1000)}
        })

        result = await compute_node.compute(large_input)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory usage should be reasonable (adjust threshold as needed)
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
        assert result.data is not None
```

## Production Deployment Examples

### Docker Integration

```dockerfile
# Dockerfile for node service
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml for multi-node deployment
version: '3.8'
services:
  effect-service:
    build: .
    environment:
      - NODE_TYPE=effect
      - SERVICE_PORT=8001
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  compute-service:
    build: .
    environment:
      - NODE_TYPE=compute
      - SERVICE_PORT=8002
    ports:
      - "8002:8002"
    depends_on:
      - effect-service

  reducer-service:
    build: .
    environment:
      - NODE_TYPE=reducer
      - SERVICE_PORT=8003
    ports:
      - "8003:8003"
    depends_on:
      - compute-service

  orchestrator-service:
    build: .
    environment:
      - NODE_TYPE=orchestrator
      - SERVICE_PORT=8004
    ports:
      - "8004:8004"
    depends_on:
      - effect-service
      - compute-service
      - reducer-service

networks:
  default:
    name: onex-network
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compute-node-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compute-node
  template:
    metadata:
      labels:
        app: compute-node
    spec:
      containers:
      - name: compute-node
        image: onex/compute-node:latest
        ports:
        - containerPort: 8000
        env:
        - name: NODE_TYPE
          value: "compute"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: compute-node-service
spec:
  selector:
    app: compute-node
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring and Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

class MonitoredComputeNode(NodeComputeService):
    """Compute node with Prometheus metrics."""

    def __init__(self, container: ONEXContainer):
        super().__init__(container)

        # Prometheus metrics
        self.request_count = Counter('compute_requests_total', 'Total compute requests')
        self.request_duration = Histogram('compute_request_duration_seconds', 'Request duration')
        self.active_requests = Gauge('compute_active_requests', 'Active compute requests')
        self.error_count = Counter('compute_errors_total', 'Total compute errors')

        # Start metrics server
        start_http_server(8090)

    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        self.request_count.inc()
        self.active_requests.inc()

        with self.request_duration.time():
            try:
                result = await self._do_compute(input_data)
                return result
            except Exception as e:
                self.error_count.inc()
                raise
            finally:
                self.active_requests.dec()
```

### Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class TracedComputeNode(NodeComputeService):
    """Compute node with distributed tracing."""

    def __init__(self, container: ONEXContainer):
        super().__init__(container)

        # Setup tracing
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)

        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger",
            agent_port=6831,
        )

        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

        self.tracer = tracer

    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        with self.tracer.start_as_current_span("compute_operation") as span:
            span.set_attribute("node.type", "compute")
            span.set_attribute("correlation.id", input_data.correlation_id or "none")

            try:
                result = await self._do_compute(input_data)
                span.set_attribute("operation.success", True)
                return result
            except Exception as e:
                span.set_attribute("operation.success", False)
                span.set_attribute("error.message", str(e))
                raise
```

## Summary

These integration examples demonstrate:

1. **Linear Processing**: Simple data flow through multiple node types
2. **Event-Driven Architecture**: Asynchronous communication between nodes
3. **Microservices Integration**: Service registry and discovery patterns
4. **Database Integration**: Repository pattern with EFFECT nodes
5. **API Gateway Integration**: HTTP wrapper for node services
6. **Testing Strategies**: Comprehensive testing approaches
7. **Production Deployment**: Docker and Kubernetes configurations
8. **Monitoring**: Metrics collection and distributed tracing

Each example follows ONEX architecture principles:
- Protocol-driven dependency injection
- Structured error handling
- Event-driven communication
- Type safety with Pydantic models
- Zero boilerplate through base classes

---

**Integration Examples Version**: 1.0
**Generated**: 2025-09-19
**Author**: Documentation Specialist
**Status**: Complete