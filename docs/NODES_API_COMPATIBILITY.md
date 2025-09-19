# Nodes API Compatibility Guide

## Overview

This document outlines the API compatibility between the legacy nodes implementation and the new ONEX four-node architecture, providing clear guidance for maintaining backward compatibility where necessary and migrating to new patterns.

## API Compatibility Matrix

### Core Node Classes

| Legacy Class | New Class | Compatibility | Migration Required |
|--------------|-----------|---------------|-------------------|
| `NodeCanaryCompute` | `NodeComputeService` | ❌ Breaking | Full migration |
| `NodeCanaryEffect` | `NodeEffectService` | ❌ Breaking | Full migration |
| `NodeCanaryReducer` | `NodeReducerService` | ❌ Breaking | Full migration |
| `NodeCanaryOrchestrator` | `NodeOrchestratorService` | ❌ Breaking | Full migration |
| `NodeReducerPatternEngine` | `NodeReducerService` | ❌ Breaking | Architectural change |

### Model Classes

| Legacy Model | New Model | Compatibility | Notes |
|--------------|-----------|---------------|-------|
| `ModelCanaryComputeInput` | `ModelComputeInput` | 🟡 Partial | Field mapping required |
| `ModelCanaryComputeOutput` | `ModelComputeOutput` | 🟡 Partial | Field mapping required |
| `ModelCanaryEffectInput` | `ModelEffectInput` | 🟡 Partial | Field mapping required |
| `ModelCanaryEffectOutput` | `ModelEffectOutput` | 🟡 Partial | Field mapping required |
| `ModelNodeInformation` | `ModelNodeInformation` | ✅ Compatible | New location only |
| `ModelNodeType` | `ModelNodeType` | ✅ Compatible | New location only |

### Utility Classes

| Legacy Utility | New Pattern | Compatibility | Replacement |
|----------------|-------------|---------------|-------------|
| `CircuitBreaker` | `@standard_error_handling` | ❌ Breaking | Decorator pattern |
| `ErrorHandler` | `OnexError` | ❌ Breaking | Exception class |
| `MetricsCollector` | Container services | ❌ Breaking | Protocol-based |
| `MemoryMonitor` | Container services | ❌ Breaking | Protocol-based |

## Method Signature Changes

### COMPUTE Nodes

**Legacy Signature:**
```python
class NodeCanaryCompute(NodeComputeService):
    async def compute(
        self,
        compute_input: ModelComputeInput,
    ) -> ModelComputeOutput:
        # Legacy implementation with complex setup
```

**New Signature:**
```python
class MyComputeNode(NodeComputeService):
    async def compute(
        self,
        input_data: ModelComputeInput
    ) -> ModelComputeOutput:
        # Simplified implementation
```

**Compatibility Adapter:**
```python
class ComputeCompatibilityAdapter:
    """Adapter for legacy compute node interfaces."""

    def __init__(self, new_node: NodeComputeService):
        self.new_node = new_node

    async def compute(
        self,
        compute_input: ModelComputeInput,  # Legacy parameter name
    ) -> ModelComputeOutput:
        # Map to new interface
        return await self.new_node.compute(compute_input)
```

### EFFECT Nodes

**Legacy Signature:**
```python
class NodeCanaryEffect(NodeEffectService):
    async def process(
        self,
        effect_input: ModelEffectInput,
    ) -> ModelEffectOutput:
        # Legacy complex processing
```

**New Signature:**
```python
class MyEffectNode(NodeEffectService):
    async def process(
        self,
        input_data: ModelEffectInput
    ) -> ModelEffectOutput:
        # Simplified processing
```

### REDUCER Nodes

**Legacy Signature:**
```python
class NodeCanaryReducer(NodeReducerService):
    async def reduce(
        self,
        reducer_input: ModelReducerInput,
    ) -> ModelReducerOutput:
        # Legacy state management
```

**New Signature:**
```python
class MyReducerNode(NodeReducerService):
    async def reduce(
        self,
        input_data: ModelReducerInput
    ) -> ModelReducerOutput:
        # Simplified state management
```

### ORCHESTRATOR Nodes

**Legacy Signature:**
```python
class NodeCanaryOrchestrator(NodeOrchestratorService):
    async def orchestrate(
        self,
        orchestrator_input: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        # Legacy orchestration
```

**New Signature:**
```python
class MyOrchestratorNode(NodeOrchestratorService):
    async def orchestrate(
        self,
        input_data: ModelOrchestratorInput
    ) -> ModelOrchestratorOutput:
        # Simplified orchestration
```

## Data Model Compatibility

### Input Models

**Legacy Input Structure:**
```python
class ModelCanaryComputeInput(BaseModel):
    operation_type: str
    data_payload: dict[str, Any]
    parameters: dict[str, Any]
    correlation_id: str | None
```

**New Input Structure:**
```python
class ModelComputeInput(BaseModel):
    data: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
```

**Compatibility Mapping:**
```python
def map_legacy_to_new_input(legacy_input: ModelCanaryComputeInput) -> ModelComputeInput:
    """Map legacy input format to new format."""
    return ModelComputeInput(
        data={
            "operation_type": legacy_input.operation_type,
            "payload": legacy_input.data_payload,
            "parameters": legacy_input.parameters
        },
        correlation_id=legacy_input.correlation_id
    )
```

### Output Models

**Legacy Output Structure:**
```python
class ModelCanaryComputeOutput(BaseModel):
    computation_result: dict[str, Any]
    success: bool
    error_message: str | None
    execution_time_ms: int | None
    correlation_id: str | None
```

**New Output Structure:**
```python
class ModelComputeOutput(BaseModel):
    data: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_message: str | None = None
```

**Compatibility Mapping:**
```python
def map_new_to_legacy_output(new_output: ModelComputeOutput) -> ModelCanaryComputeOutput:
    """Map new output format to legacy format."""
    return ModelCanaryComputeOutput(
        computation_result=new_output.data,
        success=new_output.success,
        error_message=new_output.error_message,
        execution_time_ms=new_output.metadata.get("execution_time_ms"),
        correlation_id=new_output.metadata.get("correlation_id")
    )
```

## Configuration Compatibility

### Legacy Configuration

```python
# Legacy configuration patterns
circuit_breaker_config = ModelCircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout_seconds=30,
    timeout_seconds=10
)

error_handler_config = {
    "max_retries": 3,
    "retry_delay_ms": 1000,
    "enable_correlation_tracking": True
}

metrics_config = {
    "enable_performance_tracking": True,
    "enable_error_tracking": True,
    "metrics_endpoint": "http://localhost:9090/metrics"
}
```

### New Configuration

```python
# New protocol-based configuration
from omnibase_core.core.onex_container import ONEXContainer

container = ONEXContainer()

# Configuration through container services
config_service = container.get_service("ProtocolConfiguration")
metrics_service = container.get_service("ProtocolMetrics")
logger_service = container.get_service("ProtocolLogger")
```

### Configuration Migration Adapter

```python
class ConfigurationAdapter:
    """Adapter for legacy configuration patterns."""

    def __init__(self, container: ONEXContainer):
        self.container = container

    def get_circuit_breaker_config(self) -> dict:
        """Get circuit breaker configuration in legacy format."""
        config_service = self.container.get_service("ProtocolConfiguration")
        return {
            "failure_threshold": config_service.get("circuit_breaker.failure_threshold", 3),
            "recovery_timeout_seconds": config_service.get("circuit_breaker.recovery_timeout", 30),
            "timeout_seconds": config_service.get("circuit_breaker.timeout", 10)
        }

    def get_error_handler_config(self) -> dict:
        """Get error handler configuration in legacy format."""
        config_service = self.container.get_service("ProtocolConfiguration")
        return {
            "max_retries": config_service.get("error_handler.max_retries", 3),
            "retry_delay_ms": config_service.get("error_handler.retry_delay", 1000),
            "enable_correlation_tracking": config_service.get("error_handler.correlation_tracking", True)
        }
```

## Error Handling Compatibility

### Legacy Error Handling

```python
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler

try:
    result = await self.process_data(input_data)
except Exception as e:
    error_info = self.error_handler.handle_error(
        error=e,
        context={
            "operation_type": input_data.operation_type,
            "correlation_id": input_data.correlation_id
        },
        correlation_id=input_data.correlation_id,
        operation_name="compute_operation"
    )

    return ModelCanaryComputeOutput(
        computation_result={},
        success=False,
        error_message=error_info["message"],
        correlation_id=input_data.correlation_id
    )
```

### New Error Handling

```python
from omnibase_core.decorators.error_handling import standard_error_handling
from omnibase_core.exceptions.base_onex_error import OnexError

@standard_error_handling
async def compute(self, input_data: ModelComputeInput) -> ModelComputeOutput:
    if error_condition:
        raise OnexError(
            message="Computation failed",
            error_code=CoreErrorCode.COMPUTATION_FAILED,
            context={
                "operation_type": input_data.data.get("operation_type"),
                "correlation_id": input_data.correlation_id
            }
        )
```

### Error Handling Adapter

```python
class ErrorHandlingAdapter:
    """Adapter for legacy error handling patterns."""

    def __init__(self, logger):
        self.logger = logger

    def handle_error(
        self,
        error: Exception,
        context: dict,
        correlation_id: str,
        operation_name: str
    ) -> dict:
        """Handle error using legacy pattern."""

        # Convert to new OnexError if not already
        if not isinstance(error, OnexError):
            onex_error = OnexError(
                message=str(error),
                error_code=CoreErrorCode.GENERAL_ERROR,
                context=context
            )
        else:
            onex_error = error

        # Log error
        self.logger.error(
            f"Operation {operation_name} failed",
            extra={
                "correlation_id": correlation_id,
                "error_code": onex_error.error_code,
                "context": context
            }
        )

        # Return legacy format
        return {
            "message": onex_error.message,
            "error_id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat()
        }
```

## Health Check Compatibility

### Legacy Health Checks

```python
async def get_health_status(self) -> ModelHealthStatus:
    """Legacy health status pattern."""
    status = EnumHealthStatus.HEALTHY
    details = {
        "node_type": "canary_compute",
        "operation_count": self.operation_count,
        "success_count": self.success_count,
        "error_count": self.error_count,
        "success_rate": self.success_count / max(1, self.operation_count)
    }

    # Complex health determination logic
    min_ops = int(self.config_utils.get_performance_config("min_operations_for_health", 10))
    error_threshold = float(self.config_utils.get_performance_config("error_rate_threshold", 0.1))

    if (
        self.operation_count > min_ops
        and (self.error_count / self.operation_count) > error_threshold
    ):
        status = EnumHealthStatus.DEGRADED

    return ModelHealthStatus(
        status=status,
        timestamp=datetime.now(),
        details=details
    )
```

### New Health Checks

```python
async def get_health_status(self) -> ModelHealthStatus:
    """Simplified health status pattern."""
    return ModelHealthStatus(
        status=EnumHealthStatus.HEALTHY,
        timestamp=datetime.now(),
        details={
            "node_type": "compute",
            "operations_processed": self.operation_count,
            "error_rate": self.get_error_rate()
        }
    )
```

## Metrics Compatibility

### Legacy Metrics

```python
def get_metrics(self) -> dict[str, Any]:
    """Legacy metrics collection."""
    return {
        "operation_count": self.operation_count,
        "success_count": self.success_count,
        "error_count": self.error_count,
        "success_rate": self.success_count / max(1, self.operation_count),
        "node_type": "canary_compute"
    }
```

### New Metrics

```python
def get_metrics(self) -> dict[str, Any]:
    """Simplified metrics collection."""
    return {
        "operations_total": self.operation_count,
        "operations_successful": self.success_count,
        "operations_failed": self.error_count,
        "node_type": "compute"
    }
```

### Metrics Adapter

```python
class MetricsAdapter:
    """Adapter for legacy metrics format."""

    def __init__(self, node):
        self.node = node

    def get_legacy_metrics(self) -> dict:
        """Get metrics in legacy format."""
        new_metrics = self.node.get_metrics()

        return {
            "operation_count": new_metrics.get("operations_total", 0),
            "success_count": new_metrics.get("operations_successful", 0),
            "error_count": new_metrics.get("operations_failed", 0),
            "success_rate": (
                new_metrics.get("operations_successful", 0) /
                max(1, new_metrics.get("operations_total", 1))
            ),
            "node_type": f"canary_{new_metrics.get('node_type', 'unknown')}"
        }
```

## Container Registry Compatibility

### Legacy Registry Pattern

```python
from omnibase_core.nodes.canary.container import CanaryContainer

container = CanaryContainer()
container.register_specialized_service("compute", NodeCanaryCompute)
container.register_specialized_service("effect", NodeCanaryEffect)

# Service lookup
compute_service = container.get_specialized_service("compute")
```

### New Container Pattern

```python
from omnibase_core.core.onex_container import ONEXContainer

container = ONEXContainer()
container.register_service("ProtocolComputeService", MyComputeNode)
container.register_service("ProtocolEffectService", MyEffectNode)

# Service lookup
compute_service = container.get_service("ProtocolComputeService")
```

### Registry Adapter

```python
class RegistryAdapter:
    """Adapter for legacy registry patterns."""

    def __init__(self, onex_container: ONEXContainer):
        self.container = onex_container
        self._service_mappings = {
            "compute": "ProtocolComputeService",
            "effect": "ProtocolEffectService",
            "reducer": "ProtocolReducerService",
            "orchestrator": "ProtocolOrchestratorService"
        }

    def get_specialized_service(self, service_type: str):
        """Get service using legacy pattern."""
        protocol_name = self._service_mappings.get(service_type)
        if not protocol_name:
            raise ValueError(f"Unknown service type: {service_type}")

        return self.container.get_service(protocol_name)

    def register_specialized_service(self, service_type: str, service_class):
        """Register service using legacy pattern."""
        protocol_name = self._service_mappings.get(service_type)
        if not protocol_name:
            raise ValueError(f"Unknown service type: {service_type}")

        self.container.register_service(protocol_name, service_class)
```

## Migration Timeline and Compatibility Strategy

### Phase 1: Compatibility Layer (Weeks 1-2)
- Implement adapter classes for all legacy interfaces
- Create mapping functions for data models
- Set up compatibility registry patterns
- Validate adapter functionality

### Phase 2: Gradual Migration (Weeks 3-6)
- Migrate high-priority nodes to new architecture
- Update tests to use new patterns
- Maintain compatibility adapters for legacy consumers
- Document migration progress

### Phase 3: Deprecation (Weeks 7-8)
- Mark legacy interfaces as deprecated
- Update all documentation to reference new patterns
- Create migration warnings for legacy usage
- Plan removal timeline

### Phase 4: Cleanup (Weeks 9-10)
- Remove compatibility adapters
- Delete legacy code and tests
- Update all dependencies
- Final validation and documentation

## Testing Compatibility

### Compatibility Test Suite

```python
class TestNodeCompatibility:
    """Test suite for API compatibility."""

    def test_legacy_compute_interface(self):
        """Test legacy compute interface compatibility."""
        # Legacy input
        legacy_input = ModelCanaryComputeInput(
            operation_type="data_processing",
            data_payload={"values": [1, 2, 3]},
            parameters={"operation": "sum"}
        )

        # Convert to new format
        new_input = map_legacy_to_new_input(legacy_input)
        assert new_input.data["operation_type"] == "data_processing"

    def test_output_mapping(self):
        """Test output format mapping."""
        # New output
        new_output = ModelComputeOutput(
            data={"result": 6},
            metadata={"execution_time_ms": 150}
        )

        # Convert to legacy format
        legacy_output = map_new_to_legacy_output(new_output)
        assert legacy_output.computation_result == {"result": 6}
        assert legacy_output.execution_time_ms == 150

    def test_adapter_functionality(self):
        """Test adapter classes."""
        container = create_test_container()
        adapter = RegistryAdapter(container)

        # Legacy registration
        adapter.register_specialized_service("compute", MyComputeNode)

        # Legacy lookup
        service = adapter.get_specialized_service("compute")
        assert isinstance(service, MyComputeNode)
```

## Breaking Changes Summary

| Component | Breaking Change | Impact | Mitigation |
|-----------|----------------|---------|------------|
| Base Classes | New inheritance hierarchy | High | Compatibility adapters |
| Method Signatures | Parameter name changes | Medium | Method overloading |
| Configuration | Protocol-based config | High | Configuration adapters |
| Error Handling | New exception patterns | Medium | Error handling adapters |
| Container Registry | Protocol-based services | High | Registry adapters |
| Data Models | Field structure changes | Medium | Data mapping functions |

## Support and Resources

### Compatibility Tools
- **Adapter Generator**: Automated adapter class generation
- **Migration Validator**: Validation tools for migration completeness
- **Compatibility Tester**: Automated compatibility test suite

### Documentation
- [Migration Guide](NODES_DOMAIN_MIGRATION_GUIDE.md)
- [Architecture Guide](NODES_DOMAIN_ARCHITECTURE.md)
- [Implementation Examples](../examples/)

### Support Contacts
- **Architecture Team**: For design questions and compatibility issues
- **Migration Team**: For migration planning and execution support
- **Testing Team**: For compatibility validation and testing strategies

---

**Compatibility Guide Version**: 1.0
**Generated**: 2025-09-19
**Author**: Documentation Specialist
**Status**: Complete