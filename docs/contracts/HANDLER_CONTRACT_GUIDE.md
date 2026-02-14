> **Navigation**: [Home](../INDEX.md) > Contracts > Handler Contract Guide

# Handler Contract Guide

**Version**: 1.0.0
**Last Updated**: 2025-12-31
**Status**: Comprehensive Reference

> **New in v0.4.1**: ModelHandlerContract provides the complete authoring surface for ONEX handlers with capability-based dependencies and embedded behavior descriptors.

> **Migration Note (OMN-1436)**: As of v0.4.2, contracts use `contract_version: ModelSemVer` (structured object) instead of the deprecated `version: str` field. The string-based `version` field has been removed. All contracts must now use the structured version format with explicit `major`, `minor`, and `patch` fields.

## Table of Contents

1. [Overview](#overview)
2. [ModelHandlerOutput Constraints](#modelhandleroutput-constraints)
3. [Handler ID Convention](#handler-id-convention)
   - [Prefix Naming Rules](#prefix-naming-rules)
   - [Valid and Invalid Examples](#valid-and-invalid-examples)
4. [Contract Structure](#contract-structure)
5. [Creating Handler Contracts](#creating-handler-contracts)
6. [Capability Dependencies](#capability-dependencies)
7. [Execution Constraints](#execution-constraints)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

`ModelHandlerContract` is the declarative specification that defines:

- **What the handler does**: Embedded behavior descriptor (purity, idempotency, etc.)
- **What capabilities it needs**: Vendor-agnostic capability dependencies
- **What it provides**: Output capabilities for downstream handlers
- **How it fits in execution order**: Ordering constraints
- **What it accepts and returns**: Input/output model references

```python
from omnibase_core.models.contracts import ModelHandlerContract
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.models.runtime import ModelHandlerBehaviorDescriptor

contract = ModelHandlerContract(
    handler_id="compute.json.transformer",
    name="JSON Transformer",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    descriptor=ModelHandlerBehaviorDescriptor(
        node_archetype="compute",
        purity="pure",
        idempotent=True,
    ),
    input_model="myapp.models.JsonInput",
    output_model="myapp.models.JsonOutput",
)
```

---

## ModelHandlerOutput Constraints

Handlers return `ModelHandlerOutput`, which enforces strict field constraints based on node kind. Attempting to populate a forbidden field raises a `ModelOnexError` at construction time.

| Field | COMPUTE | EFFECT | REDUCER | ORCHESTRATOR |
|-------|---------|--------|---------|--------------|
| `result` | **Required** | Forbidden | Forbidden | Forbidden |
| `events[]` | Forbidden | **Allowed** | Forbidden | **Allowed** |
| `intents[]` | Forbidden | Forbidden | Forbidden | **Allowed** |
| `projections[]` | Forbidden | Forbidden | **Allowed** | Forbidden |

**Enforcement**: `ModelHandlerOutput` Pydantic validator at construction time + CI `node-purity-check` job.

**Example** -- returning the correct output for a COMPUTE handler:

```python
# COMPUTE handler must return result, nothing else
return ModelHandlerOutput.for_compute(
    input_envelope_id=envelope.metadata.envelope_id,
    correlation_id=envelope.metadata.correlation_id,
    handler_id="compute.transform",
    result={"transformed": data},
)

# EFFECT handler may return events
return ModelHandlerOutput.for_effect(
    input_envelope_id=envelope.metadata.envelope_id,
    correlation_id=envelope.metadata.correlation_id,
    handler_id="effect.notify",
    events=[event],
)

# REDUCER handler may return projections
return ModelHandlerOutput.for_reducer(
    input_envelope_id=envelope.metadata.envelope_id,
    correlation_id=envelope.metadata.correlation_id,
    handler_id="reducer.state",
    projections=[projection],
)

# ORCHESTRATOR handler may return events and intents
return ModelHandlerOutput.for_orchestrator(
    input_envelope_id=envelope.metadata.envelope_id,
    correlation_id=envelope.metadata.correlation_id,
    handler_id="orchestrator.workflow",
    events=[event],
    intents=[intent],
)
```

---

## Handler ID Convention

The `handler_id` field uses dot-notation with at least 2 segments. The first segment (prefix) can indicate node archetype constraints, enabling self-documenting IDs that reflect handler architecture at a glance.

### Prefix Naming Rules

| Prefix | Constraint | Description |
|--------|------------|-------------|
| `node.*` | None (generic) | Generic node prefix, works with any `node_archetype` |
| `handler.*` | None (generic) | Generic handler prefix, works with any `node_archetype` |
| `compute.*` | Must match `"compute"` | ID indicates a compute handler |
| `effect.*` | Must match `"effect"` | ID indicates an effect handler |
| `reducer.*` | Must match `"reducer"` | ID indicates a reducer handler |
| `orchestrator.*` | Must match `"orchestrator"` | ID indicates an orchestrator handler |
| `*.*` (other) | None (generic) | Custom prefixes have no constraints |

**Why This Convention?**

1. **Self-Documenting**: `effect.email.sender` immediately communicates handler type
2. **Validation**: Prevents accidental mismatches between ID and actual kind
3. **Discovery**: Enables filtering handlers by prefix in registries
4. **Consistency**: Teams can enforce naming standards

### Valid and Invalid Examples

#### Valid Combinations

```python
# Generic prefixes - any node_archetype allowed
ModelHandlerContract(
    handler_id="node.user.processor",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="compute"),
    ...
)  # OK - "node" is generic

ModelHandlerContract(
    handler_id="handler.email.sender",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect"),
    ...
)  # OK - "handler" is generic

# Kind-specific prefixes - must match node_archetype
ModelHandlerContract(
    handler_id="compute.json.transformer",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="compute"),
    ...
)  # OK - "compute" matches node_archetype="compute"

ModelHandlerContract(
    handler_id="effect.db.writer",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect"),
    ...
)  # OK - "effect" matches node_archetype="effect"

ModelHandlerContract(
    handler_id="reducer.order.state",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="reducer"),
    ...
)  # OK - "reducer" matches node_archetype="reducer"

ModelHandlerContract(
    handler_id="orchestrator.workflow.manager",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="orchestrator"),
    ...
)  # OK - "orchestrator" matches node_archetype="orchestrator"

# Custom prefixes - no constraints
ModelHandlerContract(
    handler_id="myapp.custom.handler",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect"),
    ...
)  # OK - "myapp" is not a reserved prefix
```

#### Invalid Combinations

```python
# ERROR: prefix implies wrong node_archetype
ModelHandlerContract(
    handler_id="compute.json.transformer",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect"),
    ...
)
# Raises: ModelOnexError
# Message: "Handler ID prefix 'compute' implies node_archetype='compute'
#          but descriptor has node_archetype='effect'"

ModelHandlerContract(
    handler_id="reducer.state.machine",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="orchestrator"),
    ...
)
# Raises: ModelOnexError
# Message: "Handler ID prefix 'reducer' implies node_archetype='reducer'
#          but descriptor has node_archetype='orchestrator'"
```

### Choosing the Right Prefix

Use this decision tree:

```text
Do you want the handler_id to indicate the node archetype?
    |
    +-- YES --> Use kind-specific prefix (compute.*, effect.*, etc.)
    |
    +-- NO  --> Do you want a standard generic prefix?
                    |
                    +-- YES --> Use "node.*" or "handler.*"
                    |
                    +-- NO  --> Use your own custom prefix (myapp.*, domain.*, etc.)
```

**Recommendations**:

- Use **kind-specific prefixes** for libraries and reusable handlers
- Use **generic prefixes** when node archetype might change during development
- Use **custom prefixes** for application-specific handlers with domain naming

---

## Contract Structure

### Identity Fields

```python
handler_id: str              # Unique identifier with dot-notation (required)
name: str                    # Human-readable display name (required)
contract_version: ModelSemVer  # Structured semantic version (required)
description: str             # Optional detailed description
```

The `contract_version` field uses `ModelSemVer`, a structured object with explicit version components:

```python
from omnibase_core.models.primitives import ModelSemVer

contract_version=ModelSemVer(major=1, minor=0, patch=0)
```

Or in YAML format:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
```

### Behavior Configuration

```python
descriptor: ModelHandlerBehaviorDescriptor  # Runtime behavior (required)
```

The descriptor defines:
- `node_archetype`: compute, effect, reducer, orchestrator
- `purity`: pure, side_effecting
- `idempotent`: Whether safe to retry
- `timeout_ms`: Handler timeout
- `retry_policy`: Retry configuration
- `circuit_breaker`: Fault tolerance
- `concurrency_policy`: parallel_ok, serialized, singleflight
- `isolation_policy`: none, process, container, vm
- `observability_level`: minimal, standard, verbose

### I/O Models

```python
input_model: str   # Fully qualified input model reference (required)
output_model: str  # Fully qualified output model reference (required)
```

### Capability Dependencies

```python
capability_inputs: list[ModelCapabilityDependency]  # Required capabilities
capability_outputs: list[str]                        # Provided capabilities
```

### Execution and Lifecycle

```python
execution_constraints: ModelExecutionConstraints | None  # Ordering
supports_lifecycle: bool      # Implements init/shutdown hooks
supports_health_check: bool   # Implements health checking
supports_provisioning: bool   # Can be provisioned dynamically
```

### Metadata

```python
tags: list[str]           # Categorization tags
metadata: dict[str, Any]  # Extensibility metadata
```

---

## Creating Handler Contracts

### Minimal Contract

```python
from omnibase_core.models.contracts import ModelHandlerContract
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.models.runtime import ModelHandlerBehaviorDescriptor

contract = ModelHandlerContract(
    handler_id="node.my.handler",
    name="My Handler",
    contract_version=ModelSemVer(major=1, minor=0, patch=0),
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="compute"),
    input_model="myapp.models.Input",
    output_model="myapp.models.Output",
)
```

### Full Contract Example

```python
from omnibase_core.models.contracts import (
    ModelHandlerContract,
    ModelCapabilityDependency,
    ModelExecutionConstraints,
    ModelRequirementSet,
)
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.models.runtime import (
    ModelHandlerBehaviorDescriptor,
    ModelDescriptorRetryPolicy,
    ModelDescriptorCircuitBreaker,
)

contract = ModelHandlerContract(
    # Identity
    handler_id="effect.email.sender",
    name="Email Sender Effect",
    contract_version=ModelSemVer(major=2, minor=0, patch=0),
    description="Sends emails via SMTP with retry and circuit breaker protection",

    # Behavior
    descriptor=ModelHandlerBehaviorDescriptor(
        node_archetype="effect",
        purity="side_effecting",
        idempotent=True,  # Can safely retry
        timeout_ms=30000,
        concurrency_policy="parallel_ok",
        observability_level="standard",
        retry_policy=ModelDescriptorRetryPolicy(
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=1000,
        ),
        circuit_breaker=ModelDescriptorCircuitBreaker(
            enabled=True,
            failure_threshold=5,
            timeout_ms=60000,
        ),
    ),

    # Capability Dependencies
    capability_inputs=[
        ModelCapabilityDependency(
            alias="smtp",
            capability="email.smtp",
            requirements=ModelRequirementSet(
                must={"supports_tls": True},
                prefer={"max_batch_size": 100},
            ),
            strict=True,
        ),
    ],
    capability_outputs=["notification.email"],

    # I/O Models
    input_model="myapp.models.EmailRequest",
    output_model="myapp.models.EmailResult",

    # Execution
    execution_constraints=ModelExecutionConstraints(
        requires_before=["capability:auth"],
        requires_after=["capability:logging"],
    ),

    # Lifecycle
    supports_lifecycle=True,
    supports_health_check=True,

    # Metadata
    tags=["email", "notification", "effect"],
    metadata={"team": "platform", "priority": "high"},
)
```

---

## Capability Dependencies

Capability dependencies declare what the handler needs without specifying vendors:

```python
capability_inputs=[
    ModelCapabilityDependency(
        alias="db",                    # Local binding name
        capability="database.relational",  # Capability identifier
        requirements=ModelRequirementSet(
            must={"supports_transactions": True},
            prefer={"max_latency_ms": 20},
            forbid={"deprecated": True},
        ),
        selection_policy="auto_if_unique",  # Provider selection
        strict=True,                   # Fatal if not found
        version_range=">=1.0.0 <2.0.0",  # Optional version constraint
    ),
]
```

**Selection Policies**:
- `auto_if_unique`: Auto-select if exactly one match, else require explicit
- `best_score`: Select highest-scoring match based on requirements
- `require_explicit`: Always require explicit provider configuration

---

## Execution Constraints

Declare ordering requirements without absolute positions:

```python
execution_constraints=ModelExecutionConstraints(
    # This handler must run AFTER these dependencies
    requires_before=["capability:auth", "handler:config_loader"],

    # This handler must run BEFORE these dependents
    requires_after=["capability:logging", "tag:audit"],

    # Optimization hints
    can_run_parallel=True,

    # Special flags
    must_run=False,              # Force execution even if skippable
    nondeterministic_effect=False,  # Influences replay policy
)
```

**Reference Formats**:
- `capability:X` - Reference by capability
- `handler:Y` - Reference by handler ID
- `tag:Z` - Reference by tag

---

## Best Practices

### 1. Use Kind-Specific Prefixes for Clarity

```python
# GOOD: Self-documenting
handler_id="compute.json.parser"
handler_id="effect.db.writer"

# ACCEPTABLE: Generic but less clear
handler_id="node.json.parser"
```

### 2. Match Prefix to Node Archetype

```python
# CORRECT: Prefix matches archetype
ModelHandlerContract(
    handler_id="compute.transform",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="compute"),
)

# ERROR: Prefix doesn't match
ModelHandlerContract(
    handler_id="compute.transform",
    descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect"),
)  # Raises ValidationError
```

### 3. Use Generic Prefixes When Evolving

```python
# During development, use generic prefix
handler_id="handler.experimental.feature"

# After stabilization, use kind-specific
handler_id="compute.feature.processor"
```

### 4. Document Custom Prefixes

If using custom prefixes, document them in your project:

```python
# myapp.* - Application-specific handlers
# platform.* - Shared platform handlers
# infra.* - Infrastructure handlers
```

---

## Troubleshooting

### Error: Handler ID prefix implies wrong node_archetype

**Cause**: Using a kind-specific prefix (compute, effect, reducer, orchestrator) with a mismatched `node_archetype` in the descriptor.

**Solution**: Either:
1. Change the prefix to match the node_archetype
2. Change the node_archetype to match the prefix
3. Use a generic prefix (node, handler, or custom)

```python
# Option 1: Change prefix
handler_id="effect.email.sender"  # Changed from compute.*
descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect")

# Option 2: Change node_archetype
handler_id="compute.email.sender"
descriptor=ModelHandlerBehaviorDescriptor(node_archetype="compute")  # Changed

# Option 3: Use generic prefix
handler_id="handler.email.sender"  # No constraint
descriptor=ModelHandlerBehaviorDescriptor(node_archetype="effect")
```

### Error: handler_id must have at least 2 segments

**Cause**: handler_id doesn't use dot-notation properly.

**Solution**: Ensure at least 2 segments separated by dots:

```python
# WRONG
handler_id="myhandler"

# CORRECT
handler_id="node.myhandler"
handler_id="myapp.myhandler"
```

### Error: handler_id segment must start with letter or underscore

**Cause**: A segment starts with a number or invalid character.

**Solution**: Start segments with letters or underscores:

```python
# WRONG
handler_id="123.handler"
handler_id="node.123handler"

# CORRECT
handler_id="v123.handler"
handler_id="node._123handler"
handler_id="node.handler_123"
```

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Contract Profile Guide](../guides/CONTRACT_PROFILE_GUIDE.md)
- [Node Building Guide](../guides/node-building/README.md)
- [OMN-1117: Handler Contract Model & YAML Schema](https://linear.app/omninode/issue/OMN-1117)

---

## API Reference

### ModelHandlerContract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `handler_id` | `str` | Yes | Unique identifier with prefix convention |
| `name` | `str` | Yes | Human-readable name |
| `contract_version` | `ModelSemVer` | Yes | Structured semantic version with `major`, `minor`, `patch` |
| `description` | `str` | No | Detailed description |
| `descriptor` | `ModelHandlerBehaviorDescriptor` | Yes | Runtime behavior |
| `capability_inputs` | `list[ModelCapabilityDependency]` | No | Required capabilities |
| `capability_outputs` | `list[str]` | No | Provided capabilities |
| `input_model` | `str` | Yes | Input model reference |
| `output_model` | `str` | Yes | Output model reference |
| `execution_constraints` | `ModelExecutionConstraints` | No | Ordering constraints |
| `supports_lifecycle` | `bool` | No | Lifecycle hooks support |
| `supports_health_check` | `bool` | No | Health check support |
| `supports_provisioning` | `bool` | No | Dynamic provisioning |
| `tags` | `list[str]` | No | Categorization tags |
| `metadata` | `dict[str, Any]` | No | Extension metadata |

### Import Paths

```python
from omnibase_core.models.contracts import (
    ModelHandlerContract,
    ModelCapabilityDependency,
    ModelExecutionConstraints,
    ModelRequirementSet,
)

from omnibase_core.models.primitives import ModelSemVer

from omnibase_core.models.runtime import (
    ModelHandlerBehaviorDescriptor,
    ModelDescriptorRetryPolicy,
    ModelDescriptorCircuitBreaker,
)
```

---

**Last Updated**: 2025-12-31
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
