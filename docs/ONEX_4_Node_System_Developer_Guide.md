# ONEX 4-Node System Developer Guide

## Overview

The ONEX framework implements a sophisticated 4-node architectural pattern where each node type has distinct responsibilities and capabilities. This guide provides comprehensive documentation for developers working with the ONEX 4-Node System.

## Architecture Foundation

### The 4-Node Pattern

Based on research of both the current omnibase-core implementation and the reference architecture in omnibase_3, the ONEX system organizes functionality into four distinct node types:

1. **Effect Nodes** - Handle external system interactions
2. **Compute Nodes** - Process data transformations and business logic  
3. **Reducer Nodes** - Manage state transitions and finite state machines
4. **Orchestrator Nodes** - Coordinate workflows and manage node interactions

### Design Philosophy

- **Contract-Driven Development**: Every node requires a validated YAML contract
- **Service Discovery & Dependency Injection**: Protocol-based service resolution via ONEXContainer
- **Mixin-Based Composition**: Flexible capability enhancement through mixins
- **Event-Driven Communication**: Asynchronous messaging between components

## Node Types and Responsibilities

### Effect Nodes

**Purpose**: Handle all external system interactions including APIs, databases, file systems, and third-party services.

- **Base Class**: `NodeEffect` (inherits from `NodeCoreBase`)
- **Service Class**: `NodeEffectService`
- **Contract**: `ModelContractEffect`
- **Key Characteristics**:
  - External system integration
  - I/O operations and network calls
  - Resource management and connection pooling
  - Error handling and retry logic

**Examples**:
- `ConsulAdapterEffect` - Consul service registry integration
- `FileSystemEffect` - File operations and management
- `APIClientEffect` - External API interactions

### Compute Nodes

**Purpose**: Process data transformations, calculations, and business logic without external dependencies.

- **Base Class**: `NodeCompute` (inherits from `NodeCoreBase`)
- **Service Class**: `NodeComputeService`  
- **Contract**: `ModelContractCompute`
- **Key Characteristics**:
  - Pure data processing functions
  - Mathematical computations
  - Data validation and transformation
  - Business rule application

**Examples**:
- `MessageAggregatorCompute` - Message aggregation and processing
- `DataProcessorCompute` - Data transformation pipelines
- `CalculationCompute` - Mathematical computations

### Reducer Nodes

**Purpose**: Manage state transitions, finite state machines, and stateful operations.

- **Base Class**: `NodeReducer` (inherits from `NodeCoreBase`)
- **Service Class**: `NodeReducerService`
- **Contract**: `ModelContractReducer`  
- **Key Characteristics**:
  - State management and persistence
  - Finite state machine operations
  - Event sourcing patterns
  - Transaction management

**Examples**:
- `InfrastructureReducer` - Infrastructure state management
- `WorkflowReducer` - Workflow state transitions
- `StateReducer` - Generic state management

### Orchestrator Nodes

**Purpose**: Coordinate complex workflows, manage node interactions, and implement business processes.

- **Base Class**: `NodeOrchestrator` (inherits from `NodeCoreBase`)
- **Service Class**: `NodeOrchestratorService`
- **Contract**: `ModelContractOrchestrator`
- **Key Characteristics**:
  - Workflow coordination
  - Multi-node orchestration
  - Process management
  - Decision routing

**Examples**:
- `InfrastructureOrchestrator` - Infrastructure workflow coordination
- `WorkflowOrchestrator` - Business process management
- `ProcessOrchestrator` - Multi-step process coordination

## Base Class Hierarchy

### Foundation Classes

```
NodeCoreBase (Core foundation)
├── Logging integration (ProtocolLogger)
├── Health monitoring (MixinHealthCheck)
├── Lifecycle management
└── Error handling (OnexError)

ModelNodeBase (Enhanced foundation)
├── Inherits from NodeCoreBase
├── Contract loading and validation
├── Configuration management
└── Service integration

NodeBaseSimplified (Lightweight option)
├── Minimal base for simple use cases
├── Basic lifecycle management
└── Essential logging
```

### Specialized Node Bases

Each specialized base inherits from `ModelNodeBase` and adds type-specific capabilities:

- **NodeEffect**: External interaction patterns, connection management
- **NodeCompute**: Data processing patterns, transformation utilities
- **NodeReducer**: State management patterns, FSM utilities
- **NodeOrchestrator**: Coordination patterns, workflow utilities

## Contract System

### Contract Architecture

Every ONEX node requires a validated YAML contract that defines its interface, behavior, and requirements.

#### Contract Types

- **ModelContractBase**: Foundation contract with common fields (name, version, description)
- **ModelContractEffect**: Effect-specific contract with external system definitions
- **ModelContractCompute**: Compute-specific contract with processing logic definitions
- **ModelContractReducer**: Reducer-specific contract with state transition definitions  
- **ModelContractOrchestrator**: Orchestrator-specific contract with workflow definitions

#### Contract Loading System

- **ContractLoader**: Loads and validates YAML contracts with $ref resolution
- **ContractService**: Manages contract caching and validation lifecycle
- **EnhancedContractValidator**: Advanced validation with type checking and constraint validation

### Subcontracts

The system supports modular subcontracts for common patterns:

- **ModelAggregationSubcontract**: Data aggregation patterns and strategies
- **ModelCachingSubcontract**: Caching strategy definitions and configurations
- **ModelEventTypeSubcontract**: Event handling patterns and subscriptions
- **ModelFsmSubcontract**: Finite state machine definitions and transitions
- **ModelRoutingSubcontract**: Message routing patterns and rules
- **ModelStateManagementSubcontract**: State persistence patterns and storage

## Service Layer Architecture

### Service Classes

Each node type has a corresponding service class for lifecycle management:

- **NodeEffectService**: Manages Effect node lifecycle and execution
- **NodeComputeService**: Manages Compute node lifecycle and execution
- **NodeReducerService**: Manages Reducer node lifecycle and execution
- **NodeOrchestratorService**: Manages Orchestrator node lifecycle and execution

### Service Discovery

- **ONEXContainer**: Dependency injection container with protocol-based service resolution
- **ServiceDiscoveryManager**: Consul-based service discovery with fallback patterns
- **Protocol-Based Resolution**: Services resolved via protocol interfaces, not concrete types

### Lifecycle Management

```
Service Startup Flow:
1. Container initialization
2. Service registration
3. Contract loading and validation
4. Node instantiation
5. Health monitoring activation

Service Execution:
1. Request processing
2. Event handling
3. Health checks
4. Performance monitoring

Graceful Shutdown:
1. Signal handling
2. Service cleanup
3. Resource disposal
4. Container cleanup
```

## Mixin System

### Core Mixins

The mixin system provides modular capabilities that can be composed into nodes:

#### Essential Mixins
- **MixinNodeService**: Service integration and lifecycle management
- **MixinHealthCheck**: Health monitoring and status reporting
- **MixinNodeSetup**: Node initialization and configuration
- **MixinEventDrivenNode**: Event-based processing and handling
- **MixinIntrospection**: Runtime introspection and debugging capabilities

#### Specialized Mixins
- **MixinAutoConnect**: Automatic service connection patterns
- **MixinCanonicalSerialization**: Standardized serialization/deserialization
- **MixinContractMetadata**: Contract-based metadata extraction
- **MixinFailFast**: Early failure detection and handling
- **MixinWorkflowSupport**: Workflow integration capabilities

### Composition Patterns

Common mixin composition patterns for different node types:

```python
# Service-oriented node
class MyServiceNode(NodeEffect, MixinNodeService, MixinHealthCheck):
    pass

# Contract-driven node  
class MyContractNode(NodeCompute, MixinContractMetadata, MixinIntrospection):
    pass

# Event-driven node
class MyEventNode(NodeReducer, MixinEventDrivenNode, MixinEventHandler):
    pass
```

## Development Patterns

### Node Development Workflow

1. **Define Contract**: Create YAML contract with inputs, outputs, and behavior specifications
2. **Choose Base Class**: Inherit from appropriate node base (Effect/Compute/Reducer/Orchestrator)
3. **Compose Mixins**: Add required mixins based on node capabilities needed
4. **Implement Logic**: Add core processing logic in `process()` or `execute()` methods
5. **Add Service Class**: Create service class for lifecycle management if needed

### Service Integration

#### Dependency Injection
```python
# Protocol-based service resolution
container = ONEXContainer()
logger = container.get_service("ProtocolLogger")
event_bus = container.get_service("ProtocolEventBus")
```

#### Event Handling
```python
# Event-driven processing
class MyEventNode(NodeEffect, MixinEventDrivenNode):
    async def handle_event(self, event):
        # Process incoming event
        result = await self.process_event(event)
        # Emit result event
        await self.emit_event("result", result)
```

### Testing Patterns

#### Unit Testing
```python
# Mock containers and services for isolated testing
def test_node_processing():
    mock_container = MockONEXContainer()
    mock_container.register_service("ProtocolLogger", MockLogger())

    node = MyNode(container=mock_container)
    result = node.process(test_data)

    assert result == expected_result
```

#### Integration Testing
```python
# Full container setup with real dependencies
def test_node_integration():
    container = ONEXContainer()
    container.load_services_from_config("test_config.yaml")

    node = MyNode(container=container)
    result = await node.execute(test_data)

    assert_integration_success(result)
```

#### Contract Testing
```python
# Validate contract compliance
def test_contract_compliance():
    contract = ContractLoader.load("my_node_contract.yaml")
    validator = EnhancedContractValidator(contract)

    node = MyNode()
    assert validator.validate_node(node)
```

## Best Practices

### Design Principles

1. **Single Responsibility**: Each node should have one clear, well-defined purpose
2. **Contract-Driven**: Every node must have a validated YAML contract defining its interface
3. **Protocol-Based**: Use protocols for service dependencies, not concrete types
4. **Mixin Composition**: Compose capabilities via mixins rather than deep inheritance
5. **Event-Driven**: Prefer event-based communication between nodes for loose coupling

### Performance Considerations

1. **Container Caching**: Service resolution is cached for performance - avoid repeated lookups
2. **Contract Validation**: Validation happens at startup, not runtime - design for fast execution
3. **Mixin Efficiency**: Mixins add capabilities without runtime overhead - use liberally
4. **Async Patterns**: Event bus provides async communication - design for concurrent processing

### Error Handling

1. **Consistent Errors**: Use OnexError for consistent error chaining and context preservation
2. **Health Monitoring**: Implement health checks via MixinHealthCheck for service monitoring
3. **Graceful Degradation**: Provide fallback behavior when dependencies are unavailable
4. **Correlation Tracking**: Log errors with correlation IDs for distributed tracing

### Security Considerations

1. **Input Validation**: Validate all inputs against contracts before processing
2. **Service Authentication**: Use secure service-to-service authentication patterns
3. **Logging Security**: Avoid logging sensitive data - use redaction mixins
4. **Container Security**: Limit service access through container configuration

## Examples

### Basic Effect Node

```python
class ApiClientEffect(NodeEffect, MixinNodeService, MixinHealthCheck):
    """Effect node for external API integration."""

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.http_client = container.get_service("ProtocolHttpClient")
        self.logger = container.get_service("ProtocolLogger")

    async def execute(self, input_data: dict) -> dict:
        """Execute API call with input data."""
        try:
            # Validate input against contract
            validated_input = self.validate_input(input_data)

            # Make external API call
            response = await self.http_client.post(
                url=validated_input["api_endpoint"],
                data=validated_input["payload"]
            )

            # Process and return response
            return self.process_response(response)

        except Exception as e:
            self.logger.emit(LogLevel.ERROR, f"API call failed: {e}", self.correlation_id)
            raise OnexError("API_CALL_FAILED", f"External API call failed: {e}") from e
```

### Compute Node with Contract

```python
class DataProcessorCompute(NodeCompute, MixinContractMetadata, MixinIntrospection):
    """Compute node for data transformation processing."""

    def process(self, data: dict) -> dict:
        """Process data transformation according to contract."""
        # Contract-based input validation
        validated_data = self.validate_input(data)

        # Extract processing parameters from contract
        transform_config = self.get_contract_metadata("transform_config")

        # Apply transformation logic
        transformed_data = self.apply_transformations(
            validated_data,
            transform_config
        )

        # Validate output against contract
        return self.validate_output(transformed_data)

    def apply_transformations(self, data: dict, config: dict) -> dict:
        """Apply configured data transformations."""
        # Implementation of transformation logic
        pass
```

### Event-Driven Reducer

```python
class StateReducer(NodeReducer, MixinEventDrivenNode, MixinFailFast):
    """Reducer node for state management with event handling."""

    def __init__(self, container: ONEXContainer):
        super().__init__(container)
        self.state_store = container.get_service("ProtocolStateStore")
        self.register_event_handlers()

    def register_event_handlers(self):
        """Register event handlers for state transitions."""
        self.register_handler("state_change", self.handle_state_change)
        self.register_handler("state_query", self.handle_state_query)

    async def handle_state_change(self, event: dict) -> dict:
        """Handle state change events."""
        current_state = await self.state_store.get_state(event["entity_id"])
        new_state = self.calculate_new_state(current_state, event["transition"])

        # Validate state transition
        if not self.validate_transition(current_state, new_state):
            raise OnexError("INVALID_TRANSITION", "State transition not allowed")

        # Store new state
        await self.state_store.set_state(event["entity_id"], new_state)

        # Emit state changed event
        await self.emit_event("state_changed", {
            "entity_id": event["entity_id"],
            "old_state": current_state,
            "new_state": new_state
        })

        return {"success": True, "new_state": new_state}
```

## Advanced Topics

### Custom Mixin Development

```python
class MixinCustomCapability:
    """Custom mixin for specialized node capabilities."""

    def initialize_custom_capability(self):
        """Initialize custom capability resources."""
        self._custom_resource = self.container.get_service("ProtocolCustomResource")

    def custom_operation(self, data: dict) -> dict:
        """Perform custom operation with capability."""
        return self._custom_resource.process(data)
```

### Contract Extension Patterns

```yaml
# base_contract.yaml
name: "BaseContract"
version: "1.0.0"
description: "Base contract for node operations"
inputs:
  common_field:
    type: string
    required: true

# extended_contract.yaml  
$ref: "./base_contract.yaml"
name: "ExtendedContract"
inputs:
  additional_field:
    type: integer
    required: false
```

### Service Factory Patterns

```python
class NodeServiceFactory:
    """Factory for creating node services with proper configuration."""

    def create_effect_service(self, node_class: Type[NodeEffect], config: dict) -> NodeEffectService:
        """Create properly configured Effect service."""
        container = self.create_container(config)
        node = node_class(container)
        return NodeEffectService(node, container)
```

This comprehensive guide provides the foundation for developing with the ONEX 4-Node System. For specific implementation details, refer to the source code and example implementations in the omnibase-core and omnibase_3 repositories.
