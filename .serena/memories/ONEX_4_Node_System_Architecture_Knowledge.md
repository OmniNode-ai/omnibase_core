# ONEX 4-Node System Architecture - Comprehensive Knowledge Base

## Core 4-Node Architecture Pattern

### Node Type Definitions
**Effect Nodes**: Handle external system interactions
- Purpose: APIs, databases, file systems, third-party integrations
- Base Class: NodeEffect → NodeEffectService
- Contract Type: ModelContractEffect
- Key Capabilities: I/O operations, external resource management, connection handling

**Compute Nodes**: Process data transformations and business logic
- Purpose: Data processing, calculations, transformations, algorithm execution  
- Base Class: NodeCompute → NodeComputeService
- Contract Type: ModelContractCompute
- Key Capabilities: Pure functions, data manipulation, business rule processing

**Reducer Nodes**: Manage state transitions and finite state machines
- Purpose: State management, FSM coordination, data aggregation
- Base Class: NodeReducer → NodeReducerService  
- Contract Type: ModelContractReducer
- Key Capabilities: State transitions, event reduction, state validation

**Orchestrator Nodes**: Coordinate workflows and manage node interactions
- Purpose: Workflow coordination, node communication, process management
- Base Class: NodeOrchestrator → NodeOrchestratorService
- Contract Type: ModelContractOrchestrator
- Key Capabilities: Workflow execution, node coordination, process supervision

## Implementation Architecture

### Base Class Hierarchy
```
NodeCoreBase
├── ModelNodeBase
    ├── NodeEffect → NodeEffectService
    ├── NodeCompute → NodeComputeService  
    ├── NodeReducer → NodeReducerService
    └── NodeOrchestrator → NodeOrchestratorService
```

### Key Implementation Files
- Node Bases: `src/omnibase_core/core/node_*.py`
- Service Classes: `src/omnibase_core/core/node_*_service.py`
- Container: `src/omnibase_core/core/onex_container.py` (ONEXContainer)
- Contracts: `src/omnibase_core/core/contracts/`
- Mixins: `src/omnibase_core/mixin/` and `src/omnibase_core/core/mixins/`

## Contract System

### Contract Architecture
- **Base Contract**: ModelContract with validation framework
- **Type-Specific**: ModelContractEffect, ModelContractCompute, ModelContractReducer, ModelContractOrchestrator
- **YAML-Based**: Human-readable contract definitions
- **Validation**: EnhancedContractValidator with comprehensive rule checking
- **Loading**: ContractLoader with automatic discovery and instantiation

### Subcontract Types
- **Aggregation**: Data aggregation patterns and rules
- **Caching**: Cache strategy configuration and policies  
- **EventType**: Event definition and handling specifications
- **FSM**: Finite State Machine definitions and transitions
- **Routing**: Message routing and delivery patterns
- **StateManagement**: State lifecycle and persistence rules

### Contract-Driven Development Pattern
1. Define YAML contract specifying node capabilities
2. Validate contract against type-specific schema
3. Generate service class with contract-defined interfaces
4. Implement business logic within contract constraints
5. Register with container using contract metadata

## Service Layer Architecture

### Service Discovery
- **ServiceDiscoveryManager**: Central service registry and resolution
- **Protocol-Based Resolution**: Services resolved via protocol interfaces
- **Consul Integration**: Distributed service discovery support
- **ONEXContainer**: Dependency injection container with lifecycle management

### Service Lifecycle
1. **Registration**: Services register with container using contracts
2. **Discovery**: Container resolves dependencies via protocol matching
3. **Initialization**: Services initialized with validated configurations
4. **Runtime**: Services communicate via event bus and direct calls
5. **Shutdown**: Graceful shutdown with resource cleanup

## Mixin System

### Core Mixins (20+ Available)
- **MixinNodeService**: Base service functionality
- **MixinHealthCheck**: Health monitoring and status reporting
- **MixinLogging**: Structured logging with context awareness
- **MixinEventBus**: Event publishing and subscription
- **MixinMetrics**: Performance monitoring and metrics collection
- **MixinCaching**: Caching layer with invalidation strategies
- **MixinRateLimiting**: Request rate limiting and throttling
- **MixinRetry**: Automatic retry with backoff strategies

### Composition Pattern
```python
class CustomNodeService(NodeComputeService, MixinHealthCheck, MixinMetrics):
    """Service with health monitoring and metrics collection"""
    pass
```

## Development Patterns

### Event-Driven Communication
- **Async Messaging**: Non-blocking event bus communication
- **Event Types**: Strongly typed events with validation
- **Pub/Sub Pattern**: Loose coupling via event subscription
- **Event Sourcing**: State reconstruction from event history

### Protocol-Based Design
- **Interface Definition**: Python protocols define service contracts
- **Type Safety**: Static type checking with protocol conformance
- **Runtime Resolution**: Dynamic service resolution via protocols
- **Dependency Injection**: Constructor injection with protocol matching

## Implementation Examples

### Reference Locations
- **Current Implementation**: `/Volumes/PRO-G40/Code/omnibase_core`
- **Reference Architecture**: `/Volumes/PRO-G40/Code/omnibase_3/tools/infrastructure`  
- **Example Implementations**: `src/omnibase_core/examples/tool_infrastructure_*/`
- **Developer Guide**: `/Volumes/PRO-G40/Code/omnibase_core/docs/ONEX_4_Node_System_Developer_Guide.md`

### Usage Patterns
```python
# Effect Node - External API Integration
class APIEffectNode(NodeEffectService):
    async def execute_effect(self, request):
        return await self.external_api.call(request.data)

# Compute Node - Data Processing  
class DataComputeNode(NodeComputeService):
    async def compute(self, input_data):
        return self.transform_data(input_data)

# Reducer Node - State Management
class StateReducerNode(NodeReducerService):
    async def reduce(self, state, event):
        return self.apply_state_transition(state, event)

# Orchestrator Node - Workflow Coordination
class WorkflowOrchestratorNode(NodeOrchestratorService):
    async def orchestrate(self, workflow_spec):
        return await self.execute_workflow(workflow_spec)
```

## Key Success Patterns

### Architecture Benefits
- **Separation of Concerns**: Clear responsibility boundaries between node types
- **Scalability**: Independent scaling of different node types based on load
- **Maintainability**: Modular design with well-defined interfaces
- **Testability**: Each node type can be tested in isolation
- **Flexibility**: Mixin composition allows custom capability combinations

### Implementation Quality Indicators
- **Contract Coverage**: All nodes have validated YAML contracts
- **Service Registration**: Proper registration with ONEXContainer
- **Mixin Utilization**: Appropriate mixin selection for required capabilities
- **Event Bus Integration**: Proper async communication patterns
- **Protocol Conformance**: Services implement required protocol interfaces

## Best Practices

### Development Workflow
1. **Design Phase**: Define node responsibilities and interaction patterns
2. **Contract Creation**: Write YAML contracts with comprehensive specifications
3. **Service Implementation**: Implement service classes with mixin composition
4. **Integration Testing**: Test node interactions via event bus
5. **Performance Validation**: Verify scalability and resource utilization

### Common Pitfalls to Avoid
- **Cross-Cutting Concerns**: Don't mix node type responsibilities
- **Direct Coupling**: Use event bus instead of direct service calls
- **Contract Violations**: Ensure implementations match contract specifications
- **Resource Leaks**: Properly implement cleanup in service lifecycle
- **Missing Validation**: Always validate inputs and contract conformance

This knowledge represents a comprehensive understanding of the ONEX 4-Node System architecture, implementation patterns, and best practices for effective development and deployment.
