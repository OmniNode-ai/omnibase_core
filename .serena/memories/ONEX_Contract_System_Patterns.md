# ONEX Contract System - Implementation Patterns and Best Practices

## Contract System Architecture

### Core Components
- **ContractLoader**: Automatic contract discovery and loading from YAML files
- **ContractService**: Runtime contract management and resolution
- **EnhancedContractValidator**: Comprehensive validation with business rule checking
- **ModelContract[Type]**: Type-specific contract models with validation schemas

### Contract Types and Specifications

#### ModelContractEffect
```yaml
# Effect Node Contract Example
node_type: effect
name: "database_effect"
description: "Database interaction effect node"
capabilities:
  - database_read
  - database_write
  - connection_management
subcontracts:
  caching:
    enabled: true
    ttl: 3600
  routing:
    protocol: "tcp"
    port: 5432
```

#### ModelContractCompute  
```yaml
# Compute Node Contract Example
node_type: compute
name: "data_processor"
description: "Data transformation compute node"
capabilities:
  - data_transformation
  - validation
  - aggregation
subcontracts:
  aggregation:
    strategy: "sum"
    group_by: ["category"]
```

#### ModelContractReducer
```yaml
# Reducer Node Contract Example  
node_type: reducer
name: "state_manager"
description: "Application state reducer"
capabilities:
  - state_transitions
  - event_reduction
subcontracts:
  fsm:
    initial_state: "idle"
    transitions:
      - from: "idle"
        to: "processing"
        event: "start"
  state_management:
    persistence: true
    backup_interval: 300
```

#### ModelContractOrchestrator
```yaml
# Orchestrator Node Contract Example
node_type: orchestrator
name: "workflow_coordinator"
description: "Workflow orchestration node"
capabilities:
  - workflow_execution
  - node_coordination
  - process_supervision
subcontracts:
  routing:
    load_balancing: "round_robin"
    health_check: true
  event_type:
    events:
      - workflow_started
      - workflow_completed
      - workflow_failed
```

### Subcontract System

#### Available Subcontract Types
1. **Aggregation**: `ModelSubcontractAggregation`
   - Data aggregation strategies and grouping rules
   - Statistical operations and windowing functions
   - Real-time and batch aggregation patterns

2. **Caching**: `ModelSubcontractCaching`  
   - Cache strategy configuration (LRU, LFU, TTL)
   - Invalidation policies and refresh patterns
   - Distributed caching coordination

3. **EventType**: `ModelSubcontractEventType`
   - Event schema definitions and validation
   - Event routing and subscription patterns
   - Event sourcing configuration

4. **FSM**: `ModelSubcontractFSM`
   - State machine definitions and transitions
   - Guard conditions and action specifications
   - State persistence and recovery

5. **Routing**: `ModelSubcontractRouting`
   - Message routing strategies and load balancing
   - Health checking and failover patterns
   - Protocol specifications and connection management

6. **StateManagement**: `ModelSubcontractStateManagement`
   - State lifecycle management and persistence
   - Backup and recovery strategies
   - Consistency guarantees and conflict resolution

### Contract-Driven Development Workflow

#### 1. Contract Design Phase
```python
# Define contract requirements
contract_spec = {
    "node_type": "compute",
    "capabilities": ["data_validation", "transformation"],
    "subcontracts": {
        "caching": {"enabled": True, "strategy": "lru"},
        "aggregation": {"window_size": 100, "strategy": "average"}
    }
}
```

#### 2. Contract Creation and Validation
```python
from omnibase_core.core.contracts import ContractLoader, EnhancedContractValidator

# Load and validate contract
loader = ContractLoader()
validator = EnhancedContractValidator()

contract = loader.load_contract("path/to/contract.yaml")
validation_result = validator.validate(contract)

if not validation_result.is_valid:
    raise ContractValidationError(validation_result.errors)
```

#### 3. Service Implementation
```python
class DataProcessorService(NodeComputeService):
    def __init__(self, contract: ModelContractCompute):
        super().__init__(contract)
        self._setup_from_contract(contract)

    def _setup_from_contract(self, contract):
        # Configure service based on contract specifications
        if contract.subcontracts.caching:
            self.setup_caching(contract.subcontracts.caching)
        if contract.subcontracts.aggregation:
            self.setup_aggregation(contract.subcontracts.aggregation)
```

### Contract Validation Patterns

#### Validation Rules
- **Type Safety**: Ensure all contract fields match expected types
- **Capability Verification**: Validate declared capabilities against implementation
- **Subcontract Consistency**: Verify subcontract compatibility and dependencies
- **Resource Constraints**: Check resource limits and allocation requirements
- **Protocol Compliance**: Validate protocol adherence and interface contracts

#### Custom Validation Extensions
```python
class CustomContractValidator(EnhancedContractValidator):
    def validate_business_rules(self, contract):
        """Apply custom business rule validation"""
        errors = []

        # Example: Effect nodes must have database capability for data persistence
        if contract.node_type == "effect" and "database" not in contract.capabilities:
            if contract.subcontracts.state_management.persistence:
                errors.append("Effect node requires database capability for persistence")

        return ValidationResult(errors=errors)
```

### Integration Patterns

#### Container Registration
```python
from omnibase_core.core import ONEXContainer

container = ONEXContainer()

# Register service with contract
container.register_service(
    service_class=DataProcessorService,
    contract=contract,
    protocol=IComputeProtocol
)
```

#### Service Discovery and Resolution
```python
# Resolve service by protocol
compute_service = container.resolve(IComputeProtocol)

# Resolve service by contract name
specific_service = container.resolve_by_name("data_processor")
```

## Success Patterns

### Effective Contract Design
- **Clear Capability Declaration**: Explicitly list all node capabilities
- **Comprehensive Subcontracts**: Include all relevant subcontract specifications
- **Resource Planning**: Define resource requirements and constraints
- **Versioning Strategy**: Include version information for contract evolution
- **Documentation**: Provide clear descriptions and usage examples

### Contract Validation Best Practices
- **Early Validation**: Validate contracts during development phase
- **Automated Testing**: Include contract validation in CI/CD pipelines
- **Business Rule Integration**: Implement domain-specific validation rules
- **Error Reporting**: Provide detailed validation error messages
- **Schema Evolution**: Support backward-compatible contract changes

### Common Anti-Patterns to Avoid
- **Over-Specification**: Avoid overly rigid contract constraints
- **Under-Specification**: Ensure sufficient detail for implementation
- **Subcontract Conflicts**: Prevent conflicting subcontract configurations
- **Circular Dependencies**: Avoid circular contract dependencies
- **Missing Validation**: Always implement comprehensive validation

This contract system enables robust, type-safe, and flexible node development within the ONEX architecture.
