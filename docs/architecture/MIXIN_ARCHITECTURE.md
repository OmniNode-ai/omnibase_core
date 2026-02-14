> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Mixin Architecture

# ONEX Mixin Architecture

**Status**: Active
**Last Updated**: 2026-02-14
**Related Documents**: [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md), [Mixin Development Guide](../guides/mixin-development/README.md)

## Overview

The ONEX framework implements a sophisticated mixin system (also called "subcontracts") that provides reusable cross-cutting concerns for nodes. Mixins enable composable functionality while maintaining architectural boundaries and separation of concerns across the four node types.

### Terminology: Mixin vs Subcontract

> **📘 Key Distinction:**
> **"Mixin"** and **"subcontract"** refer to the **same concept** in ONEX, viewed from different perspectives:
> - **Mixin** (Implementation View): Emphasizes the composable, reusable behavior that nodes can "mix in" to gain capabilities. Think: Python multiple inheritance, behavior composition.
> - **Subcontract** (Contract View): Emphasizes the formal contract/specification that defines the mixin's interface, configuration, and constraints. Think: API specification, formal agreement.
> **Usage Guidelines**:
> - Use **"mixin"** when discussing implementation, composition, and runtime behavior
> - Use **"subcontract"** when discussing contracts, validation, and formal specifications
> - File naming can use either: `mixin_health_check.yaml` or `health_check_subcontract.yaml`
> **In Practice**: Both terms are interchangeable. This document uses "mixin" primarily but references "subcontracts" in contract-related contexts.

### Core Principles

1. **Reusability**: Mixins encapsulate common functionality that can be shared across multiple nodes
2. **Composability**: Multiple mixins can be combined additively in a single node
3. **Type Safety**: Strong typing through Pydantic models ensures contract compliance
4. **Architectural Enforcement**: Node type constraints maintain separation of concerns
5. **Contract-Driven**: YAML contracts define capabilities, actions, and schema

## Three-Layer Architecture

The ONEX mixin system uses a three-layer architecture that separates concerns while maintaining type safety:

### Layer 1: YAML Contract Files (Planned)

> **Note**: YAML mixin contract files are a **planned feature**, not yet implemented.
> The directory `src/omnibase_core/nodes/canary/mixins/` does not currently exist.
> A metadata file exists at `src/omnibase_core/mixins/mixin_metadata.yaml` for reference,
> but individual YAML mixin contracts have not been created yet. Currently, the Pydantic
> subcontract models (Layer 2) serve as the primary contract definitions.

**Planned Location**: `src/omnibase_core/nodes/canary/mixins/` or `subcontracts/`
**Purpose**: Define mixin capabilities, actions, configuration, and schema
**Format**: Structured YAML following ONEX contract schema

**Planned Characteristics**:
- Human-readable contract definitions
- Version-controlled capabilities
- Declarative action specifications
- Configuration schema with defaults
- Dependency declarations

**Planned Structure**:
```
mixin_name: "mixin_health_check"
mixin_version: {major: 1, minor: 0, patch: 0}
description: "Health monitoring capabilities for ONEX nodes"
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

actions:
  - name: "check_health"
    description: "Execute health check"
    inputs: ["component_id"]
    outputs: ["health_status"]
    required: true
    timeout_ms: 5000

health_check_config:
  interval_seconds: 30
  timeout_ms: 5000
  retry_attempts: 3
```

### Layer 2: Pydantic Model Files

**Location**: `src/omnibase_core/models/contracts/subcontracts/`
**Purpose**: Provide runtime type safety and validation
**Format**: Python Pydantic models with strong typing

**Key Characteristics**:
- Runtime validation of contract data
- Type hints for IDE support
- Field constraints and validation rules
- JSON schema generation
- Serialization/deserialization

**Example Structure**:
```
from pydantic import BaseModel, Field

class ModelHealthCheckSubcontract(BaseModel):
    """Health check mixin Pydantic backing model."""

    subcontract_name: str = Field(default="mixin_health_check")
    subcontract_version: str = Field(default="1.0.0")
    applicable_node_types: list[str] = Field(default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"])

    interval_seconds: int = Field(default=30, ge=5, le=300)
    timeout_ms: int = Field(default=5000, ge=100, le=60000)
    retry_attempts: int = Field(default=3, ge=1, le=10)

    class Config:
        json_schema_extra = {
            "example": {
                "interval_seconds": 30,
                "timeout_ms": 5000,
                "retry_attempts": 3
            }
        }
```

### Layer 3: Integration Layer

**Location**: Node contract YAML files
**Purpose**: Connect mixins to specific node implementations
**Format**: Subcontract references in node contracts

**Key Characteristics**:
- Relative path references to mixin files
- Integration field mapping
- Configuration overrides
- Composition of multiple mixins

**Example Structure**:
```
# In node contract: canary_compute/v1_0_0/contract.yaml
node_name: "canary_compute"
node_type: "COMPUTE"

subcontracts:
  - path: "../../subcontracts/health_check_subcontract.yaml"
    integration_field: "health_check_configuration"
  - path: "../../subcontracts/performance_monitoring_subcontract.yaml"
    integration_field: "performance_monitoring_configuration"
```

## Node Type Constraints

ONEX enforces architectural constraints to maintain separation of concerns across node types. These constraints determine which mixins are applicable to each node type.

### Core Mixins (Universal)

Core mixins are applicable to **all node types** and provide foundational capabilities:

| Mixin | Purpose | Applicable To |
|-------|---------|---------------|
| `mixin_health_check` | Health monitoring and status reporting | All nodes |
| `mixin_introspection` | Node discovery and metadata | All nodes |
| `mixin_event_handling` | Event bus integration | All nodes |
| `mixin_service_resolution` | Service discovery | All nodes |
| `mixin_performance_monitoring` | Metrics collection | All nodes |
| `mixin_request_response` | Request/response patterns | All nodes |

### Node Type-Specific Mixins

Specialized mixins enforce architectural boundaries:

#### COMPUTE Nodes

**Constraint**: Core mixins only (stateless processing)

**Rationale**: COMPUTE nodes perform pure transformations without side effects or state management. Limiting mixins to core capabilities maintains this purity.

**Allowed Mixins**:
- Core mixins only
- No state management
- No external dependencies
- No workflow coordination

#### EFFECT Nodes

**Constraint**: Core mixins + external dependency management

**Allowed Additional Mixins**:
- `mixin_external_dependencies`: External system integration
- `mixin_circuit_breaker`: Fault tolerance for external calls
- `mixin_retry_policy`: Retry strategies for external operations

**Rationale**: EFFECT nodes interact with external systems, requiring dependency management and fault tolerance capabilities.

#### REDUCER Nodes

**Constraint**: Core mixins + state management

**Allowed Additional Mixins**:
- `mixin_state_management`: State persistence and recovery
- `mixin_aggregation`: Data aggregation operations
- `mixin_caching`: Caching strategies

**Rationale**: REDUCER nodes manage state and aggregate data, requiring specialized state management and aggregation capabilities.

#### ORCHESTRATOR Nodes

**Constraint**: Core mixins + workflow coordination

**Allowed Additional Mixins**:
- `mixin_workflow_coordination`: Workflow management
- `mixin_fsm`: Finite state machine processing
- `mixin_routing`: Request routing and load balancing
- `mixin_dependency_management`: Inter-node dependency tracking

**Rationale**: ORCHESTRATOR nodes coordinate complex workflows, requiring workflow management and coordination capabilities.

## File Organization

### Directory Structure

```
src/omnibase_core/
├── mixins/                                    # Python mixin implementations
│   ├── mixin_caching.py
│   ├── mixin_compute_execution.py
│   ├── mixin_effect_execution.py
│   ├── mixin_event_bus.py
│   ├── mixin_event_handler.py
│   ├── mixin_fsm_execution.py
│   ├── mixin_handler_routing.py
│   ├── mixin_health_check.py
│   ├── mixin_introspection.py
│   ├── mixin_metadata.yaml               # Mixin metadata reference
│   ├── mixin_metrics.py
│   ├── mixin_node_lifecycle.py
│   ├── mixin_node_service.py
│   ├── mixin_workflow_execution.py
│   └── ...                                # (~40 mixin files total)
│
├── models/contracts/subcontracts/             # Pydantic subcontract models
│   ├── __init__.py
│   ├── model_health_check_subcontract.py
│   ├── model_metrics_subcontract.py
│   ├── model_fsm_subcontract.py
│   ├── model_caching_subcontract.py
│   ├── model_event_handling_subcontract.py
│   ├── model_introspection_subcontract.py
│   ├── model_discovery_subcontract.py
│   ├── model_workflow_coordination_subcontract.py
│   └── ...                                # (~100+ subcontract model files)
│
└── nodes/canary/
    └── [node_name]/v1_0_0/
        └── contract.yaml                  # Node contract with mixin references
```

> **Note**: YAML mixin contract files (e.g., `mixin_health_check.yaml`) in a
> `nodes/canary/mixins/` directory are a planned feature. Currently, the Pydantic
> subcontract models in `models/contracts/subcontracts/` serve as the contract
> definitions, and the Python mixins in `mixins/` provide the runtime behavior.

### Naming Conventions

**Mixin YAML Files**:
- Pattern: `mixin_[capability_name].yaml`
- Examples: `mixin_health_check.yaml`, `mixin_event_handling.yaml`

**Alternative Subcontract Files**:
- Pattern: `[capability_name]_subcontract.yaml`
- Examples: `health_check_subcontract.yaml`, `event_handling_subcontract.yaml`

**Pydantic Model Files**:
- Pattern: `model_[capability_name]_subcontract.py`
- Examples: `model_health_check_subcontract.py`, `model_event_handling_subcontract.py`

**Pydantic Model Classes**:
- Pattern: `Model[CapabilityName]Subcontract`
- Examples: `ModelHealthCheckSubcontract`, `ModelEventHandlingSubcontract`

## Contract Validation & Processing

### Validation Flow

The `EnhancedContractValidator` handles mixin validation and integration:

1. **Load Main Contract**: Parse node contract YAML
2. **Parse Contract Content**: Convert to `ModelContractContent`
3. **Resolve Subcontract References**: Load referenced mixin files
4. **Validate Architectural Constraints**: Enforce node type constraints
5. **Merge Mixin Capabilities**: Combine mixin capabilities into final contract
6. **Generate Types**: Create runtime types from contracts

### Validation Rules

**Schema Validation**:
- YAML structure matches expected schema
- Required fields present with correct types
- Version information valid (semantic versioning)
- Action definitions complete with inputs/outputs

**Node Type Constraint Enforcement**:
- Mixin applicable to target node type
- No unauthorized mixins for node type
- Core mixins available to all nodes
- Specialized mixins restricted appropriately

**Mixin Compatibility Checking**:
- No conflicting mixin configurations
- Dependencies between mixins satisfied
- Integration fields unique across mixins
- No circular dependencies

### Contract Loading

**Contract Loading Process**:

```
# Pseudocode for contract loading flow
def load_node_contract(contract_path: Path) -> ModelContractContent:
    # 1. Load main contract
    contract_yaml = load_yaml(contract_path)

    # 2. Parse contract content
    contract = ModelContractContent.model_validate(contract_yaml)

    # 3. Resolve subcontract references
    for subcontract_ref in contract.subcontracts:
        subcontract_path = resolve_relative_path(contract_path, subcontract_ref.path)
        subcontract_yaml = load_yaml(subcontract_path)

        # 4. Validate architectural constraints
        validate_node_type_constraints(
            node_type=contract.node_type,
            mixin=subcontract_yaml
        )

        # 5. Merge mixin capabilities
        contract = merge_mixin_into_contract(contract, subcontract_yaml, subcontract_ref.integration_field)

    # 6. Validate final contract
    validate_complete_contract(contract)

    return contract
```

## Integration with Contract System

### Subcontract References

Nodes consume mixins through the `subcontracts` section of their contract:

```
# Node contract
subcontracts:
  - path: "../../subcontracts/health_check_subcontract.yaml"
    integration_field: "health_check_configuration"
```

**Path Resolution**:
- Relative paths from node contract location
- Supports `../` for directory traversal
- Resolved at contract loading time

**Integration Fields**:
- Unique field name for mixin configuration
- Maps mixin config to node contract field
- Enables configuration overrides

### Mixin Composition

Multiple mixins compose additively:

```
subcontracts:
  - path: "../../subcontracts/health_check_subcontract.yaml"
    integration_field: "health_check_configuration"
  - path: "../../subcontracts/performance_monitoring_subcontract.yaml"
    integration_field: "performance_monitoring_configuration"
  - path: "../../subcontracts/event_handling_subcontract.yaml"
    integration_field: "event_handling_configuration"
```

**Composition Rules**:
- Each mixin contributes independent capabilities
- No mixin overrides another's capabilities
- Configuration fields must be unique
- Dependencies between mixins explicitly declared

### Runtime Integration

**Node Implementation**:

Nodes are thin coordination shells. Business logic lives in handlers:

```
from omnibase_core.core.node_compute import NodeCompute

class MyComputeNode(NodeCompute):
    """Thin node shell -- delegates to handler for business logic."""

    async def execute_compute(self, input_data, **kwargs):
        # Node delegates to handler; mixin configuration is
        # accessed through the contract by the handler.
        handler = self.container.get_service("MyComputeHandler")
        return await handler.handle(input_data, contract=self.contract)
```

## Architectural Principles

### Separation of Concerns

**Principle**: Each mixin addresses a single cross-cutting concern.

**Benefits**:
- Clear responsibility boundaries
- Easier testing and validation
- Simpler composition
- Reduced coupling

**Implementation**:
- One capability per mixin
- No overlapping functionality between mixins
- Explicit dependencies where needed

### Contract-Driven Development

**Principle**: Contracts define all mixin behavior before implementation.

**Benefits**:
- Clear API specifications
- Type-safe implementations
- Validation at contract load time
- Documentation from contracts

**Implementation**:
- YAML contracts as source of truth
- Pydantic models generated from contracts
- Validation at multiple levels

### Type Safety

**Principle**: Strong typing throughout the mixin system.

**Benefits**:
- Compile-time error detection
- IDE support and autocomplete
- Runtime validation
- Clear API contracts

**Implementation**:
- Pydantic models for all mixins
- Type hints throughout
- Runtime validation
- Schema generation

### Architectural Enforcement

**Principle**: Node type constraints enforced at contract validation time.

**Benefits**:
- Maintains architectural boundaries
- Prevents anti-patterns
- Clear node type responsibilities
- Consistent system design

**Implementation**:
- Node type constraints in mixin contracts
- Validation during contract loading
- Clear error messages for violations
- Documentation of constraints

## Performance Considerations

### Contract Loading Performance

**Optimization Strategies**:
- Cache parsed contracts
- Lazy load mixin definitions
- Validate once at startup
- Reuse validation results

### Runtime Performance

**Optimization Strategies**:
- Minimize runtime validation
- Cache mixin configurations
- Use compiled Pydantic models
- Avoid redundant capability checks

### Memory Usage

**Optimization Strategies**:
- Share mixin definitions across nodes
- Use flyweight pattern for common configs
- Lazy initialize mixin capabilities
- Release unused mixin resources

## Future Enhancements

### Planned Improvements

1. **Dynamic Mixin Loading**: Load mixins at runtime based on conditions
2. **Mixin Versioning**: Support multiple versions of same mixin
3. **Mixin Dependencies**: Explicit dependency graph between mixins
4. **Mixin Plugins**: Plugin system for third-party mixins
5. **Mixin Metrics**: Automatic metrics collection for mixin usage

### Research Areas

1. **Aspect-Oriented Programming**: Investigate AOP patterns for mixins
2. **Code Generation**: Auto-generate boilerplate from contracts
3. **Static Analysis**: Compile-time validation of mixin usage
4. **Performance Profiling**: Per-mixin performance tracking

## Related Documentation

- **[Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md)**: Detailed subcontract implementation patterns
- **[Mixin Development Guide](../guides/mixin-development/README.md)**: Step-by-step guide to creating mixins
- **[ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)**: Core ONEX architecture patterns
- **[Node Building Guide](../guides/node-building/README.md)**: Building nodes with mixins

---

## Service Wrappers and Mixin Mapping

Standard service wrappers pre-compose node types with the correct mixins and ordering. Prefer these for most implementations:

- ModelServiceEffect = `MixinNodeService` + `NodeEffect` + `MixinHealthCheck` + `MixinEventBus` + `MixinMetrics`
- ModelServiceCompute = `MixinNodeService` + `NodeCompute` + `MixinHealthCheck` + `MixinCaching` + `MixinMetrics`
- ModelServiceReducer = `MixinNodeService` + `NodeReducer` + `MixinHealthCheck` + `MixinCaching` + `MixinMetrics`
- ModelServiceOrchestrator = `MixinNodeService` + `NodeOrchestrator` + `MixinHealthCheck` + `MixinEventBus` + `MixinMetrics`

MRO principle for wrappers: `ModelService* → MixinNodeService → Node<Type> → (other mixins) → NodeCoreBase → ABC`.

Use wrappers unless you need a specialized composition; if so, inherit directly from `Node<Type>` and add mixins, keeping node type first and mixins ordered by dependency.

> See also: `src/omnibase_core/models/nodes/node_services/README.md` for end-to-end examples and migration guidance.

---

**Next Steps**:
- Read the [Mixin Development Guide](../guides/mixin-development/README.md) to learn how to create mixins
- See the [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md) for implementation patterns
- Review existing mixins in `src/omnibase_core/mixins/`
