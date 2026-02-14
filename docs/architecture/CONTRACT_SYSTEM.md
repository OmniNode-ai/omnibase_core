> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Contract System
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Contract System

**Status**: Current
**Last Updated**: 2026-02-14

---

## Table of Contents

1. [Overview](#overview)
2. [Contract-Driven Architecture](#contract-driven-architecture)
3. [YAML Contract Format](#yaml-contract-format)
4. [Contract Models](#contract-models)
5. [Contract Versioning](#contract-versioning)
6. [Contract Loading and Validation](#contract-loading-and-validation)
7. [Contract-to-Handler Resolution](#contract-to-handler-resolution)
8. [Handler Contracts](#handler-contracts)
9. [Subcontracts](#subcontracts)
10. [Output Constraints by Node Kind](#output-constraints-by-node-kind)
11. [Protocol Dependencies in Contracts](#protocol-dependencies-in-contracts)

---

## Overview

The ONEX contract system is **YAML-driven and declarative**. Contracts are the source of truth for node behavior -- they define what a node does, what it depends on, what it accepts and returns, and how it connects to handlers.

Key principles:

- **Contracts define behavior, not code.** Business logic lives in handlers; contracts declare the shape of that logic.
- **YAML is the authoring surface.** Contracts are authored as `.onex.yaml` files and loaded into Pydantic models at runtime.
- **Handlers own all business logic.** Nodes are thin coordination shells; contracts bind handlers to nodes.
- **Validation is layered.** Pydantic validates contract structure at load time; node-specific validators enforce domain rules.

---

## Contract-Driven Architecture

The contract system sits at the center of the 4-node architecture:

```
                  .onex.yaml
                      |
                      v
             ModelContractBase (Pydantic)
             /        |         \        \
    Compute    Effect    Reducer    Orchestrator
   contract   contract  contract    contract
             |
             v
        Handler Resolution
             |
             v
        Handler Execution
```

Every node loads its contract from a YAML file. The contract determines:

1. **Identity**: Name, version, description, node type
2. **I/O shape**: Input and output model references (fully qualified class paths)
3. **Performance**: SLA requirements, timeout limits
4. **Dependencies**: Other nodes, protocols, and services this node requires
5. **Validation**: Rules and constraints for contract compliance
6. **Behavior**: Handler routing, event subscriptions, execution profile

---

## YAML Contract Format

Contracts are stored as `.onex.yaml` files. The YAML structure maps directly to `ModelContractBase` and its specialized subclasses.

### Minimal Contract

```yaml
name: node_price_calculator
contract_version:
  major: 1
  minor: 0
  patch: 0
description: Computes product prices with discount factors
node_type: compute

input_model: myapp.models.PriceInput
output_model: myapp.models.PriceOutput

algorithm:
  algorithm_type: weighted_factor_algorithm
  factors:
    base_price:
      weight: 1.0

performance:
  single_operation_max_ms: 100
```

### Full Contract with All Sections

```yaml
name: node_order_orchestrator
contract_version:
  major: 2
  minor: 1
  patch: 0
node_version:
  major: 1
  minor: 3
  patch: 0
description: Orchestrates order processing workflow
node_type: orchestrator

input_model: myapp.models.OrderRequest
output_model: myapp.models.OrderResult

# Performance SLA
performance:
  single_operation_max_ms: 5000

# Lifecycle configuration
lifecycle:
  health_check_enabled: true
  graceful_shutdown_timeout_ms: 30000

# Dependencies
dependencies:
  - name: inventory_service
    dependency_type: service
    required: true
  - name: payment_processor
    dependency_type: service
    required: true

# Protocol dependencies for DI
protocol_dependencies:
  - name: ProtocolEventBus
    protocol: "omnibase_core.protocols.event_bus:ProtocolEventBus"
    required: true
  - name: ProtocolLogger
    protocol: "omnibase_core.protocols.logging:ProtocolMinimalLogger"
    required: true

# Execution profile
execution:
  phases:
    - validate_order
    - check_inventory
    - process_payment
    - confirm_order
  ordering_policy: sequential

# Handler behavior
behavior:
  node_archetype: orchestrator
  purity: side_effecting
  idempotent: false
  concurrency_policy: serialized

# Handler routing (dispatches to different handlers by payload type)
handler_routing:
  version:
    major: 1
    minor: 0
    patch: 0
  routing_strategy: payload_type_match
  handlers:
    - routing_key: ModelEventOrderCreated
      handler_key: handle_order_created
      priority: 0
  default_handler: handle_unknown

# Event subscriptions
yaml_consumed_events:
  - "orders.events.created.v1"
  - "orders.events.cancelled.v1"

yaml_published_events:
  - topic: "orders.events.confirmed.v1"
    event_type: ModelEventOrderConfirmed

# Tags and metadata
tags:
  - order-processing
  - workflow

validation_rules:
  max_input_size_bytes: 1048576
```

---

## Contract Models

### ModelContractBase

The abstract base class for all contract models. Defined in `src/omnibase_core/models/contracts/model_contract_base.py`.

```python
class ModelContractBase(BaseModel, ABC):
    """Abstract base for 4-node architecture contract models."""

    name: str
    contract_version: ModelSemVer
    node_version: ModelSemVer | None = None
    description: str
    node_type: EnumNodeType

    input_model: str   # Fully qualified class path
    output_model: str  # Fully qualified class path

    performance: ModelPerformanceRequirements
    lifecycle: ModelLifecycleConfig
    dependencies: list[ModelDependency]
    protocol_interfaces: list[str]
    protocol_dependencies: list[ModelProtocolDependency]
    validation_rules: ModelValidationRules

    # Optional fields
    author: str | None = None
    documentation_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    execution: ModelExecutionProfile | None = None
    behavior: ModelHandlerBehavior | None = None
    handler_routing: ModelHandlerRoutingSubcontract | None = None
    yaml_consumed_events: list[ModelConsumedEventEntry] = Field(default_factory=list)
    yaml_published_events: list[ModelPublishedEventEntry] = Field(default_factory=list)

    @abstractmethod
    def validate_node_specific_config(self) -> None:
        """Each specialized contract validates its own domain rules."""
```

### Specialized Contract Models

Each node kind has its own contract model that extends `ModelContractBase`:

| Node Kind | Contract Model | Key Fields |
|-----------|---------------|------------|
| **COMPUTE** | `ModelContractCompute` | `algorithm`, `parallel_processing`, `input_validation`, `output_transformation`, `caching` |
| **EFFECT** | `ModelContractEffect` | Effect-specific I/O, transaction config, retry policies |
| **REDUCER** | `ModelContractReducer` | State management, aggregation configuration |
| **ORCHESTRATOR** | `ModelContractOrchestrator` | `action_emission`, `workflow_coordination`, `conditional_branching`, `event_registry`, `published_events`, `consumed_events` |

#### ModelContractCompute

```python
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

# Loaded from YAML or created programmatically
contract = ModelContractCompute(
    name="price_calculator",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Calculates weighted product prices",
    node_type=EnumNodeType.COMPUTE_GENERIC,
    input_model="myapp.models.PriceInput",
    output_model="myapp.models.PriceOutput",
    algorithm=ModelAlgorithmConfig(
        algorithm_type="weighted_factor_algorithm",
        factors={"base_price": ModelAlgorithmFactorConfig(weight=1.0)},
    ),
    performance=ModelPerformanceRequirements(single_operation_max_ms=100),
)
```

#### ModelContractOrchestrator

```python
from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

contract = ModelContractOrchestrator(
    name="workflow_coordinator",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Coordinates multi-step workflows",
    node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    input_model="myapp.models.WorkflowInput",
    output_model="myapp.models.WorkflowOutput",
    action_emission=ModelActionEmissionConfig(emission_strategy="sequential"),
    workflow_coordination=ModelWorkflowConfig(
        execution_mode="sequential",
        checkpoint_enabled=True,
        checkpoint_interval_ms=5000,
    ),
    performance=ModelPerformanceRequirements(single_operation_max_ms=30000),
)
```

### Import Paths

```python
# Base contract
from omnibase_core.models.contracts.model_contract_base import ModelContractBase

# Specialized contracts
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_orchestrator import ModelContractOrchestrator

# Version model
from omnibase_core.models.primitives.model_semver import ModelSemVer
```

---

## Contract Versioning

All contracts use `ModelSemVer` for structured semantic versioning (SemVer 2.0.0).

### ModelSemVer

```python
from omnibase_core.models.primitives.model_semver import ModelSemVer

version = ModelSemVer(major=2, minor=1, patch=0)
```

In YAML:

```yaml
contract_version:
  major: 2
  minor: 1
  patch: 0
```

Key rules:

- The `contract_version` field is **required** on all contracts.
- The optional `node_version` field tracks the implementation version separately.
- The deprecated string-based `version` field has been removed (see OMN-1436).
- Pre-release and build metadata are supported per SemVer 2.0.0.

### Version Comparison

`ModelSemVer` supports comparison operators for compatibility checking:

```python
v1 = ModelSemVer(major=1, minor=0, patch=0)
v2 = ModelSemVer(major=2, minor=0, patch=0)

assert v1 < v2
assert v2 > v1
```

---

## Contract Loading and Validation

### Loading from YAML

Contracts are loaded from YAML files and validated through Pydantic:

```python
import yaml
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

# Load and parse
with open("node_calculator.onex.yaml") as f:
    raw_data = yaml.safe_load(f)

# Validate through Pydantic
contract = ModelContractCompute.model_validate(raw_data)
```

The `from_yaml` class method provides a convenience wrapper:

```python
yaml_content = Path("node_calculator.onex.yaml").read_text()
contract = ModelContractCompute.from_yaml(yaml_content)
```

### Validation Layers

Contract validation happens in multiple stages:

1. **Pydantic structural validation**: Field types, required fields, constraints (automatic at `model_validate` time).
2. **Field validators**: Custom `@field_validator` methods on each contract model handle format conversion (e.g., converting dicts to `ModelAlgorithmConfig`).
3. **Post-init validation** (`model_post_init`): Calls `_validate_node_type_compliance()`, `_validate_protocol_dependencies()`, `_validate_dependency_graph()`.
4. **Node-specific validation** (`validate_node_specific_config`): Each specialized contract implements domain-specific checks. For example, `ModelContractCompute` validates algorithm factors, parallel processing workers, and performance requirements.
5. **Subcontract constraint validation**: Uses `ModelSubcontractConstraintValidator` to verify subcontract field combinations are valid for the node kind.

### Validation Errors

Validation errors use `ModelOnexError` with specific error codes:

```python
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Structural errors
EnumCoreErrorCode.VALIDATION_ERROR

# Orchestrator-specific three-level hierarchy
EnumCoreErrorCode.ORCHESTRATOR_STRUCT_MISSING_FIELD
EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_FIELD_TYPE
EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_DUPLICATE_STEP_ID
EnumCoreErrorCode.ORCHESTRATOR_EXEC_STEP_TIMEOUT
```

---

## Contract-to-Handler Resolution

The contract-to-handler pipeline connects YAML contracts to executable handler functions:

```
.onex.yaml  -->  ModelContractBase  -->  NodeCoreBase.__init__
                                              |
                                   resolve_handler()
                                              |
                                   HandlerCallable / LazyLoader
                                              |
                                   handler.execute(input, ctx)
```

### Resolution in NodeCoreBase

When a node initializes, `NodeCoreBase.__init__` receives a `ModelONEXContainer` and loads its contract. The handler is resolved using `resolve_handler()` from `omnibase_core.resolution.resolver_handler`:

```python
from omnibase_core.resolution.resolver_handler import resolve_handler, HandlerCallable

# resolve_handler returns a callable or LazyLoader bound to the contract
handler: HandlerCallable = resolve_handler(contract_data, container)
```

### Handler Routing

For nodes that dispatch to multiple handlers based on payload type, the `handler_routing` field in the contract defines routing rules:

```yaml
handler_routing:
  version:
    major: 1
    minor: 0
    patch: 0
  routing_strategy: payload_type_match
  handlers:
    - routing_key: ModelEventOrderCreated
      handler_key: handle_order_created
      priority: 0
    - routing_key: ModelEventOrderCancelled
      handler_key: handle_order_cancelled
      priority: 1
  default_handler: handle_unknown
```

### Protocol Dependency Resolution

Contracts can declare protocol dependencies that are resolved from the DI container at node initialization:

```yaml
protocol_dependencies:
  - name: ProtocolEventBus
    protocol: "omnibase_core.protocols.event_bus:ProtocolEventBus"
    required: true
  - name: ProtocolLogger
    protocol: "omnibase_core.protocols.logging:ProtocolMinimalLogger"
    required: false
```

The framework uses `resolve_protocol_dependencies()` to inject these into the node's `self.protocols` namespace:

```python
from omnibase_core.resolution.resolver_protocol_dependency import resolve_protocol_dependencies

# Resolves all protocol dependencies from the contract
# and binds them to the node's protocols namespace
resolve_protocol_dependencies(node, contract, container)

# Access resolved protocols
event_bus = node.protocols.ProtocolEventBus
logger = node.protocols.ProtocolLogger
```

Duplicate bind names are rejected at validation time by `validate_no_duplicate_protocol_bindings`.

---

## Handler Contracts

`ModelHandlerContract` is the handler-level contract that defines handler capabilities independently of nodes. While `ModelContractBase` defines node-level contracts, `ModelHandlerContract` defines the handler's own specification.

See [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) for full details.

### Key Fields

```python
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior

contract = ModelHandlerContract(
    handler_id="compute.json.transformer",
    name="JSON Transformer",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    descriptor=ModelHandlerBehavior(
        node_archetype="compute",
        purity="pure",
        idempotent=True,
    ),
    input_model="myapp.models.JsonInput",
    output_model="myapp.models.JsonOutput",
)
```

### Handler ID Convention

The `handler_id` uses dot-notation with at least 2 segments. Kind-specific prefixes (`compute.*`, `effect.*`, `reducer.*`, `orchestrator.*`) are validated against the `node_archetype` in the behavior descriptor. Generic prefixes (`node.*`, `handler.*`) and custom prefixes have no constraints.

### Capability Dependencies

Handler contracts declare vendor-agnostic capability requirements:

```python
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)

capability_inputs=[
    ModelCapabilityDependency(
        alias="db",
        capability="database.relational",
        requirements=ModelRequirementSet(
            must={"supports_transactions": True},
        ),
        strict=True,
    ),
]
```

---

## Subcontracts

Complex contracts use subcontract composition for specialized behaviors. Subcontracts are Pydantic models that live in `src/omnibase_core/models/contracts/subcontracts/`.

### Subcontract Types

| Subcontract | Purpose | Used By |
|-------------|---------|---------|
| `ModelCachingSubcontract` | Cache strategies and TTL | COMPUTE |
| `ModelEventTypeSubcontract` | Event type definitions | COMPUTE, ORCHESTRATOR |
| `ModelRoutingSubcontract` | Message routing rules | ORCHESTRATOR |
| `ModelStateManagementSubcontract` | State persistence and transitions | REDUCER |
| `ModelAggregationSubcontract` | Data aggregation configuration | REDUCER |
| `ModelEffectSubcontract` | Effect-specific I/O patterns | EFFECT |
| `ModelComputeSubcontract` | Compute pipeline steps | COMPUTE |
| `ModelHandlerRoutingSubcontract` | Handler dispatch routing | All node types |
| `ModelProtocolDependency` | Contract-driven DI declarations | All node types |

### Subcontract Constraint Validation

`ModelSubcontractConstraintValidator` enforces that subcontract fields are valid for the contract's node kind:

```python
from omnibase_core.models.utils.model_subcontract_constraint_validator import (
    ModelSubcontractConstraintValidator,
)

# Called automatically in validate_node_specific_config()
ModelSubcontractConstraintValidator.validate_node_subcontract_constraints(
    "compute",
    contract.model_dump(),
    original_contract_data,
)
```

---

## Output Constraints by Node Kind

Contracts enforce strict output constraints based on node kind. These are validated at the `ModelHandlerOutput` level:

| Node Kind | Allowed Fields | Forbidden Fields |
|-----------|---------------|-----------------|
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |

These constraints are not optional. Returning `result` from an ORCHESTRATOR handler raises `ValueError` at construction time.

---

## Protocol Dependencies in Contracts

The `protocol_dependencies` field on `ModelContractBase` enables contract-driven dependency injection. Each entry is a `ModelProtocolDependency` that specifies:

- `name`: Protocol identifier (e.g., `"ProtocolEventBus"`)
- `protocol`: Fully qualified protocol path (e.g., `"omnibase_core.protocols.event_bus:ProtocolEventBus"`)
- `required`: Whether the dependency is mandatory
- `bind_name` (optional): Custom name for the `self.protocols` namespace binding

```python
from omnibase_core.models.contracts.subcontracts.model_protocol_dependency import (
    ModelProtocolDependency,
)

dep = ModelProtocolDependency(
    name="ProtocolEventBus",
    protocol="omnibase_core.protocols.event_bus:ProtocolEventBus",
    required=True,
)
```

At node initialization, the framework resolves each declared protocol from the `ModelONEXContainer` and binds it to `self.protocols.<bind_name>`. This keeps handler code decoupled from concrete service implementations.

---

## Related Documentation

- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) -- Full ModelHandlerContract reference
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) -- Node kind definitions
- [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md) -- Valid data flow patterns
- [Container Types](CONTAINER_TYPES.md) -- ModelContainer[T] vs ModelONEXContainer
- [Dependency Injection](DEPENDENCY_INJECTION.md) -- Protocol-based service resolution
- [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md) -- Subcontract design details
- [Type System](TYPE_SYSTEM.md) -- Type conventions (PEP 604)
- [Node Building Guide](../guides/node-building/README.md) -- How to build nodes with contracts
