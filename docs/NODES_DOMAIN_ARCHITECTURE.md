# Nodes Domain Architecture

## Overview

The ONEX nodes domain implements a four-node architecture pattern that provides a standardized approach to service implementation. Each node type has specific responsibilities and follows consistent patterns for initialization, processing, and error handling.

## Four-Node Architecture Pattern

### Core Principles

1. **Single Responsibility**: Each node type has a specific, well-defined purpose
2. **Protocol-Driven**: Services are resolved by protocol interfaces, not implementations
3. **Zero Boilerplate**: Base classes eliminate repetitive initialization code
4. **Type Safety**: Full type checking with Pydantic models and protocol constraints
5. **Event-Driven**: Inter-node communication through structured events

### Node Type Hierarchy

```
ONEX Four-Node Architecture
├── EFFECT (External Interactions)
│   ├── Purpose: Handle external system interactions
│   ├── Examples: API calls, database operations, file I/O
│   └── Base Class: NodeEffectService
├── COMPUTE (Data Processing)
│   ├── Purpose: Pure computation without side effects
│   ├── Examples: Data transformation, calculations, algorithms
│   └── Base Class: NodeComputeService
├── REDUCER (State Aggregation)
│   ├── Purpose: Aggregate state and manage consistency
│   ├── Examples: State machines, data consolidation, workflows
│   └── Base Class: NodeReducerService
└── ORCHESTRATOR (Workflow Coordination)
    ├── Purpose: Coordinate workflows and manage services
    ├── Examples: Service orchestration, workflow management
    └── Base Class: NodeOrchestratorService
```

## Node Type Specifications

### EFFECT Nodes

**Purpose**: Handle all external system interactions and side effects

**Characteristics**:
- Manage external API calls
- Handle database operations
- Process file system operations
- Manage network communications
- Handle authentication and authorization

**Interface Contract**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeEffectService

class MyEffectNode(NodeEffectService):
    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """
        Process external interaction request.

        Args:
            input_data: External interaction parameters

        Returns:
            ModelEffectOutput: Result of external interaction
        """
        # External interaction logic
        return ModelEffectOutput(data=result)
```

**Common Patterns**:
```python
class DatabaseEffectNode(NodeEffectService):
    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        # Database connection from container
        db_service = self.container.get_service("ProtocolDatabase")

        # External database operation
        result = await db_service.execute_query(input_data.query)

        return ModelEffectOutput(
            data={"records": result.records, "count": result.count},
            metadata={"execution_time_ms": result.execution_time}
        )
```

### COMPUTE Nodes

**Purpose**: Perform pure computation and data processing without side effects

**Characteristics**:
- Stateless operations
- Deterministic results
- No external dependencies
- Pure data transformation
- Mathematical computations

**Interface Contract**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeComputeService

class MyComputeNode(NodeComputeService):
    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        """
        Perform computation on input data.

        Args:
            input_data: Data to be processed

        Returns:
            ModelComputeOutput: Computation results
        """
        # Pure computation logic
        return ModelComputeOutput(data=result)
```

**Common Patterns**:
```python
class DataTransformationComputeNode(NodeComputeService):
    async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        # Pure data transformation
        raw_data = input_data.data

        # Business logic computation
        transformed_data = {
            "processed_records": len(raw_data.get("records", [])),
            "average_value": sum(raw_data.get("values", [])) / len(raw_data.get("values", [1])),
            "transformation_type": "statistical_summary"
        }

        return ModelComputeOutput(
            data=transformed_data,
            metadata={"computation_type": "statistical_analysis"}
        )
```

### REDUCER Nodes

**Purpose**: Aggregate state and manage data consistency across operations

**Characteristics**:
- State management
- Data aggregation
- Workflow coordination
- Consistency enforcement
- Event processing

**Interface Contract**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeReducerService

class MyReducerNode(NodeReducerService):
    async def reduce(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        """
        Aggregate and reduce input data to consistent state.

        Args:
            input_data: Data to be reduced/aggregated

        Returns:
            ModelReducerOutput: Aggregated state
        """
        # State aggregation logic
        return ModelReducerOutput(data=result)
```

**Common Patterns**:
```python
class WorkflowReducerNode(NodeReducerService):
    async def reduce(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        # Get current workflow state
        workflow_state = input_data.data.get("workflow_state", {})
        new_event = input_data.data.get("event", {})

        # Apply state reduction logic
        updated_state = self._apply_workflow_transition(workflow_state, new_event)

        # Store aggregated state
        state_service = self.container.get_service("ProtocolStateManager")
        await state_service.update_state(updated_state)

        return ModelReducerOutput(
            data={"updated_state": updated_state},
            metadata={"state_version": updated_state.get("version", 1)}
        )
```

### ORCHESTRATOR Nodes

**Purpose**: Coordinate complex workflows and manage inter-service communication

**Characteristics**:
- Service coordination
- Workflow management
- Resource allocation
- Error recovery
- Load balancing

**Interface Contract**:
```python
from omnibase_core.core.infrastructure_service_bases import NodeOrchestratorService

class MyOrchestratorNode(NodeOrchestratorService):
    async def orchestrate(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
        """
        Orchestrate workflow execution across multiple services.

        Args:
            input_data: Orchestration parameters and workflow definition

        Returns:
            ModelOrchestratorOutput: Orchestration results
        """
        # Workflow orchestration logic
        return ModelOrchestratorOutput(data=result)
```

**Common Patterns**:
```python
class DataPipelineOrchestratorNode(NodeOrchestratorService):
    async def orchestrate(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
        workflow_definition = input_data.data.get("workflow", {})

        # Coordinate multiple services
        results = []
        for step in workflow_definition.get("steps", []):
            if step["type"] == "effect":
                service = self.container.get_service("ProtocolEffectService")
                result = await service.process(step["input"])
            elif step["type"] == "compute":
                service = self.container.get_service("ProtocolComputeService")
                result = await service.compute(step["input"])

            results.append(result)

        return ModelOrchestratorOutput(
            data={"workflow_results": results},
            metadata={"steps_executed": len(results)}
        )
```

## Node Implementation Guidelines

### 1. Base Class Usage

**Always extend the appropriate base class**:
```python
from omnibase_core.core.infrastructure_service_bases import (
    NodeEffectService,      # For external interactions
    NodeComputeService,     # For data processing
    NodeReducerService,     # For state aggregation
    NodeOrchestratorService # For workflow coordination
)

class MyNode(NodeComputeService):  # Choose appropriate base
    def __init__(self, container: ONEXContainer):
        super().__init__(container)  # MANDATORY - handles boilerplate
        # Only business-specific initialization here
```

### 2. Protocol-Based Dependency Resolution

**Use protocol names for service resolution**:
```python
def __init__(self, container: ONEXContainer):
    super().__init__(container)

    # Protocol-based service resolution
    self.logger = container.get_service("ProtocolLogger")
    self.event_bus = container.get_service("ProtocolEventBus")
    self.metrics = container.get_service("ProtocolMetrics")
```

### 3. Error Handling Patterns

**Use structured error handling**:
```python
from omnibase_core.decorators.error_handling import standard_error_handling
from omnibase_core.exceptions.base_onex_error import OnexError

@standard_error_handling
async def my_operation(self):
    if error_condition:
        raise OnexError(
            message="Operation failed",
            error_code=CoreErrorCode.OPERATION_FAILED,
            context={"node_type": "compute", "operation": "data_processing"}
        )
```

### 4. Event-Driven Communication

**Use structured events for inter-node communication**:
```python
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope

async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    # Process input
    result = await self._perform_external_operation(input_data)

    # Emit event for other nodes
    event = ModelEventEnvelope(
        event_type="external_operation_completed",
        payload={"result": result, "node_id": self.node_id},
        correlation_id=input_data.correlation_id
    )

    event_bus = self.container.get_service("ProtocolEventBus")
    await event_bus.publish(event)

    return ModelEffectOutput(data=result)
```

## Data Flow Patterns

### 1. Linear Processing Flow

```
Request → EFFECT → COMPUTE → REDUCER → Response
```

Example: External data retrieval, processing, and state storage

### 2. Orchestrated Workflow

```
Request → ORCHESTRATOR → [EFFECT, COMPUTE, REDUCER] → ORCHESTRATOR → Response
```

Example: Complex multi-step workflows requiring coordination

### 3. Event-Driven Processing

```
Event → REDUCER → [EFFECT, COMPUTE] → REDUCER → Event
```

Example: State machine processing with side effects

### 4. Pipeline Processing

```
Request → EFFECT → COMPUTE → COMPUTE → REDUCER → Response
```

Example: Data transformation pipelines

## Node Registration and Discovery

### Container-Based Registration

```python
from omnibase_core.core.onex_container import ONEXContainer

# Register nodes with container
container = ONEXContainer()
container.register_service("ProtocolMyEffectNode", MyEffectNode)
container.register_service("ProtocolMyComputeNode", MyComputeNode)

# Service discovery
effect_node = container.get_service("ProtocolMyEffectNode")
```

### Dynamic Node Discovery

```python
from omnibase_core.models.nodes import ModelNodeInformation

# Node metadata for discovery
node_info = ModelNodeInformation(
    node_id="data-processor-compute",
    node_type=EnumNodeType.COMPUTE,
    capabilities=[
        ModelNodeCapability(name="data_transformation", version="1.0.0"),
        ModelNodeCapability(name="statistical_analysis", version="1.2.0")
    ],
    endpoint="http://localhost:8080/compute",
    health_check_endpoint="http://localhost:8080/health"
)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock

from omnibase_core.core.infrastructure_service_bases import NodeComputeService

class TestMyComputeNode:
    def test_compute_operation(self):
        # Mock container
        container = Mock()
        container.get_service.return_value = Mock()

        # Test node
        node = MyComputeNode(container)

        # Test computation
        input_data = ModelComputeInput(data={"values": [1, 2, 3, 4, 5]})
        result = await node.compute(input_data)

        assert result.data["average"] == 3.0
```

### Integration Testing

```python
class TestNodeIntegration:
    @pytest.mark.asyncio
    async def test_effect_to_compute_flow(self):
        # Setup real container with services
        container = create_test_container()

        effect_node = MyEffectNode(container)
        compute_node = MyComputeNode(container)

        # Test data flow
        effect_result = await effect_node.process(effect_input)
        compute_input = ModelComputeInput(data=effect_result.data)
        compute_result = await compute_node.compute(compute_input)

        assert compute_result.success is True
```

## Performance Considerations

### Node Performance Metrics

- **Initialization Time**: <100ms for typical nodes
- **Processing Latency**: <50ms for simple operations
- **Memory Usage**: <50MB baseline per node
- **Throughput**: >1000 requests/second for lightweight operations

### Optimization Patterns

**Async Processing**:
```python
async def process_batch(self, inputs: list[ModelEffectInput]) -> list[ModelEffectOutput]:
    # Concurrent processing
    tasks = [self.process(input_data) for input_data in inputs]
    results = await asyncio.gather(*tasks)
    return results
```

**Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_computation(self, input_hash: str) -> dict:
    # Expensive computation with caching
    return self._perform_computation(input_hash)
```

**Resource Pooling**:
```python
async def __aenter__(self):
    self.connection_pool = await self._create_connection_pool()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.connection_pool.close()
```

## Security Considerations

### Input Validation

```python
from pydantic import BaseModel, Field, validator

class SecureInput(BaseModel):
    data: dict = Field(..., description="Input data")

    @validator('data')
    def validate_data_structure(cls, v):
        # Validate input structure
        if not isinstance(v, dict):
            raise ValueError("Data must be a dictionary")
        return v
```

### Authorization

```python
async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    # Authorization check
    auth_service = self.container.get_service("ProtocolAuthorization")
    if not await auth_service.check_permission(input_data.user_id, "effect:process"):
        raise OnexError(
            message="Insufficient permissions",
            error_code=CoreErrorCode.AUTHORIZATION_FAILED
        )
```

### Audit Logging

```python
from omnibase_core.core.core_structured_logging import emit_log_event_sync

async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    # Audit log entry
    emit_log_event_sync(
        level=LogLevel.INFO,
        message="Effect processing started",
        metadata={
            "node_type": "effect",
            "user_id": input_data.user_id,
            "operation": "external_api_call",
            "correlation_id": input_data.correlation_id
        }
    )
```

## Monitoring and Observability

### Health Checks

```python
from omnibase_core.models.core.model_health_status import ModelHealthStatus

async def get_health_status(self) -> ModelHealthStatus:
    """Node health status."""
    return ModelHealthStatus(
        status=EnumHealthStatus.HEALTHY,
        timestamp=datetime.now(),
        details={
            "node_type": "compute",
            "operations_processed": self.operation_count,
            "average_processing_time_ms": self.avg_processing_time,
            "error_rate": self.error_count / max(1, self.operation_count)
        }
    )
```

### Metrics Collection

```python
def get_metrics(self) -> dict:
    """Node performance metrics."""
    return {
        "operations_total": self.operation_count,
        "operations_successful": self.success_count,
        "operations_failed": self.error_count,
        "average_processing_time_ms": self.avg_processing_time,
        "memory_usage_mb": self._get_memory_usage(),
        "cpu_usage_percent": self._get_cpu_usage()
    }
```

## Best Practices

1. **Single Responsibility**: Each node should have one clear purpose
2. **Stateless Design**: Nodes should be stateless when possible
3. **Protocol Compliance**: Always use protocol-based service resolution
4. **Error Handling**: Use structured error handling with OnexError
5. **Event-Driven**: Communicate through events, not direct calls
6. **Type Safety**: Use comprehensive type hints and Pydantic validation
7. **Testing**: Write comprehensive unit and integration tests
8. **Documentation**: Document all public interfaces and business logic
9. **Performance**: Monitor and optimize for throughput and latency
10. **Security**: Validate inputs and implement proper authorization

---

**Architecture Version**: 1.0
**Generated**: 2025-09-19
**Author**: Documentation Specialist
**Status**: Complete