> **Navigation**: [Home](../INDEX.md) > Reference > Contracts

> **Note**: For authoritative coding rules, see [CLAUDE.md](../../CLAUDE.md).

# Contract.yaml Reference

This reference documents the complete structure of ONEX contract files as defined by omnibase_core.

## Overview

ONEX contracts are YAML files that declare node behavior declaratively. omnibase_core provides the foundational enums, models, and validation infrastructure that all contracts must adhere to.

| File | Purpose | Location |
|------|---------|----------|
| `contract.yaml` | Node contract | `nodes/<node_name>/contract.yaml` |
| `handler_contract.yaml` | Handler contract | `contracts/handlers/<handler>/handler_contract.yaml` |

**Key Principle**: Contracts define WHAT a node does. Python code defines HOW (but should be minimal).

**Relationship to omnibase_core**: This package provides the enums (`EnumNodeKind`, `EnumNodeType`) and base models that contracts reference. Actual contract files typically reside in implementation packages like `omnibase_infra`.

---

## Minimal Contract Example

Every node contract requires these fields:

```yaml
# Required fields
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_example"
node_type: "COMPUTE_GENERIC"  # See Node Types below
description: "What this node does."

input_model:
  name: "ModelExampleInput"
  module: "mypackage.nodes.node_example.models"

output_model:
  name: "ModelExampleOutput"
  module: "mypackage.nodes.node_example.models"
```

---

## Node Types

### EnumNodeKind (Architectural Role)

`EnumNodeKind` defines the high-level architectural classification for ONEX nodes. Use these values in the `node_type` field with a `_GENERIC` suffix:

| Contract Value | EnumNodeKind | Purpose |
|----------------|--------------|---------|
| `EFFECT_GENERIC` | `EFFECT` | External I/O operations (API calls, database, files) |
| `COMPUTE_GENERIC` | `COMPUTE` | Pure data transformations and calculations |
| `REDUCER_GENERIC` | `REDUCER` | State aggregation and FSM-driven state machines |
| `ORCHESTRATOR_GENERIC` | `ORCHESTRATOR` | Workflow coordination and multi-step execution |
| `RUNTIME_HOST_GENERIC` | `RUNTIME_HOST` | Infrastructure nodes (rarely used in contracts) |

**Import Path**:
```python
from omnibase_core.enums.enum_node_kind import EnumNodeKind
```

### EnumNodeType (Implementation Type)

`EnumNodeType` provides more specific implementation types that map to `EnumNodeKind`:

| EnumNodeType | Maps to EnumNodeKind | Description |
|--------------|---------------------|-------------|
| `COMPUTE_GENERIC` | `COMPUTE` | Generic compute node |
| `TRANSFORMER` | `COMPUTE` | Data transformation |
| `AGGREGATOR` | `COMPUTE` | Data aggregation |
| `FUNCTION` | `COMPUTE` | Pure function node |
| `MODEL` | `COMPUTE` | ML model inference |
| `EFFECT_GENERIC` | `EFFECT` | Generic effect node |
| `TOOL` | `EFFECT` | Tool invocation |
| `AGENT` | `EFFECT` | Agent interaction |
| `REDUCER_GENERIC` | `REDUCER` | Generic reducer node |
| `ORCHESTRATOR_GENERIC` | `ORCHESTRATOR` | Generic orchestrator |
| `GATEWAY` | `ORCHESTRATOR` | API gateway/routing |
| `VALIDATOR` | `ORCHESTRATOR` | Validation workflow |
| `WORKFLOW` | `ORCHESTRATOR` | Multi-step workflow |

**Import Path**:
```python
from omnibase_core.enums.enum_node_type import EnumNodeType
```

**Usage in Contracts**: Use `_GENERIC` suffixes for node_type values in YAML contracts.

---

## Common Fields (All Types)

These fields apply to all node types:

### Version Information

```yaml
contract_version:
  major: 1       # Breaking changes
  minor: 0       # New features (backward compatible)
  patch: 0       # Bug fixes

node_version: "1.0.0"  # Implementation version (semver string)
```

### Basic Identity

```yaml
name: "node_example"            # Unique identifier (snake_case)
node_type: "COMPUTE_GENERIC"    # One of the four archetypes + _GENERIC suffix
description: "Human-readable description of what this node does."
```

### Input/Output Models

```yaml
input_model:
  name: "ModelExampleInput"
  module: "mypackage.nodes.node_example.models"
  description: "Optional description of input model."

output_model:
  name: "ModelExampleOutput"
  module: "mypackage.nodes.node_example.models"
  description: "Optional description of output model."
```

**Type Safety**: All I/O types must be proper Pydantic models. `Any` types are not allowed in contracts.

### Capabilities Section

Capabilities declare what a node can do, enabling discovery and routing.

```yaml
capabilities:
  - name: "registration.storage"
    description: "Store and query registration records"
  - name: "registration.storage.query"
  - name: "registration.storage.upsert"
  - name: "registration.storage.delete"
```

#### Capability Naming Convention

**Use capability-oriented names** (what it does), **not technology names** (how it does it).

| Aspect | Good Examples | Bad Examples |
|--------|--------------|--------------|
| **Domain-scoped** | `registration.storage` | `postgres` |
| **Action-oriented** | `service.discovery.register` | `consul` |
| **Hierarchical** | `node.lifecycle.introspection` | `introspect` |
| **Descriptive** | `workflow.coordination.parallel` | `parallel_exec` |

**Good Capability Names**:

```yaml
# Pattern: {domain}.{subdomain}.{action}
capabilities:
  # Service discovery capabilities
  - name: "service.discovery.register"
    description: "Register a service for discovery"
  - name: "service.discovery.lookup"
    description: "Find services by criteria"

  # Data persistence capabilities
  - name: "registration.storage.upsert"
    description: "Insert or update registration records"
  - name: "registration.storage.query"
    description: "Query registration records"
```

**Bad Capability Names (Avoid)**:

```yaml
# WRONG: Technology-specific names
capabilities:
  - name: "postgres"           # Technology, not capability
  - name: "consul"             # Implementation detail
  - name: "kafka.publish"      # Exposes transport

# WRONG: Non-hierarchical names
capabilities:
  - name: "store"              # Too generic
  - name: "query"              # Ambiguous
  - name: "process"            # Meaningless without domain

# WRONG: Non-descriptive names
capabilities:
  - name: "doStuff"            # Meaningless
  - name: "handler1"           # Numbered handlers = poor design
  - name: "run"                # Too generic
```

### Dependencies

```yaml
dependencies:
  protocols:
    - name: "ProtocolEventBus"
      module: "omnibase_core.protocols"
      required: true
    - name: "ProtocolLogger"
      module: "omnibase_core.protocols"
      required: false

  nodes:
    - name: "node_registry_effect"
      required: true

  services:
    - name: "postgresql"
      version: ">=15.0"
      required: true
```

### Error Handling

```yaml
error_handling:
  retry_policy:
    max_retries: 3
    exponential_base: 2
    max_delay_seconds: 60
    retry_on:
      - "ConnectionError"
      - "TimeoutError"
    do_not_retry_on:
      - "AuthenticationError"

  circuit_breaker:
    enabled: true
    failure_threshold: 5
    reset_timeout_seconds: 60
```

### Metadata

```yaml
metadata:
  author: "ONEX Team"
  created_at: "2025-01-15"
  updated_at: "2026-01-18"
  tags:
    - "infrastructure"
    - "compute"
  license: "MIT"
```

---

## EFFECT-Specific Fields

EFFECT nodes handle external I/O operations.

### IO Operations

```yaml
io_operations:
  - operation: "store_record"
    description: "Persist a record to storage"
    input_fields:
      - record: "ModelRecord"
      - correlation_id: "UUID | None"
    output_fields:
      - result: "ModelUpsertResult"
    idempotent: true
    timeout_ms: 5000

  - operation: "query_record"
    description: "Query record by ID"
    input_fields:
      - record_id: "str"
    output_fields:
      - record: "ModelRecord | None"
    idempotent: true
    read_only: true
```

### Handler Routing (Effect)

```yaml
handler_routing:
  routing_strategy: "handler_type_match"
  default_handler: "postgresql"
  execution_mode: "parallel"          # parallel | sequential
  partial_failure_handling: true

  handlers:
    - handler_type: "postgresql"
      handler:
        name: "HandlerStoragePostgres"
        module: "mypackage.handlers.storage"
      backend: "postgres"

    - handler_type: "mock"
      handler:
        name: "HandlerStorageMock"
        module: "mypackage.handlers.storage"
      backend: "mock"
```

---

## COMPUTE-Specific Fields

COMPUTE nodes perform pure data transformations.

### Validation Rules

```yaml
validation_rules:
  - rule_id: "VAL-001"
    name: "Input Schema Validation"
    severity: "ERROR"
    description: "Validate input against schema"
    detection_strategy:
      type: "pydantic_validation"
```

### Transformation Rules

```yaml
transformations:
  - name: "normalize_data"
    input_type: "dict"
    output_type: "ModelNormalized"
    description: "Normalize raw input data"

  - name: "aggregate_results"
    input_type: "list[ModelResult]"
    output_type: "ModelAggregatedResult"
    description: "Aggregate multiple results"
```

---

## REDUCER-Specific Fields

REDUCER nodes manage state with FSM-driven state machines.

### State Machine

```yaml
state_machine:
  state_machine_name: "example_fsm"
  initial_state: "idle"

  states:
    - state_name: "idle"
      description: "Waiting for events"
      entry_actions: []
      exit_actions: []

    - state_name: "processing"
      description: "Processing request"
      entry_actions:
        - "emit_started_event"
      timeout_seconds: 30

    - state_name: "complete"
      description: "Successfully completed"
      terminal: false

    - state_name: "failed"
      description: "Failed state"
      terminal: false

  transitions:
    - from_state: "idle"
      to_state: "processing"
      trigger: "request_received"
      conditions:
        - expression: "input is_valid"
          required: true
      actions:
        - action_name: "validate_input"
          action_type: "validation"

    - from_state: "processing"
      to_state: "complete"
      trigger: "processing_done"

    - from_state: "*"           # Wildcard: any state
      to_state: "failed"
      trigger: "error_received"
```

### Intent Emission

```yaml
intent_emission:
  enabled: true
  intents:
    - intent_type: "storage.upsert"
      target_pattern: "postgres://records/{record_id}"
      payload_model: "ModelUpsertPayload"
      payload_module: "mypackage.models"
```

### Idempotency

```yaml
idempotency:
  enabled: true
  strategy: "event_id_tracking"
  description: "Track processed event_ids to prevent duplicates"
  storage: "in_state"           # in_state | external
```

---

## ORCHESTRATOR-Specific Fields

ORCHESTRATOR nodes coordinate workflows. **Important**: ORCHESTRATOR nodes cannot return typed results - they can only emit events and intents. See [CLAUDE.md](../../CLAUDE.md) for details.

### Workflow Coordination

```yaml
workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: "example_workflow"
      workflow_version:
        major: 1
        minor: 0
        patch: 0
      description: "Multi-step workflow example"

    execution_graph:
      nodes:
        - node_id: "receive_event"
          node_type: EFFECT_GENERIC
          description: "Receive incoming event"

        - node_id: "process_data"
          node_type: COMPUTE_GENERIC
          depends_on: ["receive_event"]
          description: "Process the data"

        - node_id: "update_state"
          node_type: REDUCER_GENERIC
          depends_on: ["process_data"]
          description: "Update state machine"

    coordination_rules:
      execution_mode: parallel
      parallel_execution_allowed: true
      max_parallel_branches: 2
      failure_recovery_strategy: retry
      max_retries: 3
      timeout_ms: 30000
```

### Handler Routing (Orchestrator)

```yaml
handler_routing:
  routing_strategy: "payload_type_match"

  handlers:
    - event_model:
        name: "ModelInputEvent"
        module: "mypackage.models"
      handler:
        name: "HandlerInputReceived"
        module: "mypackage.handlers"
      output_events:
        - "ModelOutputEvent"
```

### Consumed Events

```yaml
consumed_events:
  - topic: "{env}.{namespace}.onex.evt.input.v1"
    event_type: "InputEvent"
    description: "Input event to process"
    consumer_group: "example-orchestrator"
```

### Published Events

```yaml
published_events:
  - topic: "{env}.{namespace}.onex.evt.output.v1"
    event_type: "OutputEvent"
    description: "Output event after processing"
```

---

## Validation Errors

Contracts are validated at load time. Common errors:

| Error | Cause | Fix |
|-------|-------|-----|
| Missing required field | `name`, `node_type`, or I/O models missing | Add required fields |
| Invalid node_type | Not one of the four archetypes | Use `*_GENERIC` suffix |
| Module not found | `module` path doesn't resolve | Check import path |
| Invalid transition | FSM transition references unknown state | Define all states first |
| Ambiguous contracts | Both `contract.yaml` and `handler_contract.yaml` exist | Use only one per directory |
| Any type detected | Contract uses `Any` type | Use `object` or specific types |

---

## Best Practices

1. **Use capabilities, not technologies**: Name by what it does, not what it uses (see Capability Naming Convention above)
2. **Keep contracts focused**: One node = one responsibility
3. **Define error handling**: Always include retry and circuit breaker config for EFFECT nodes
4. **Version intentionally**: Bump major for breaking changes
5. **Document thoroughly**: Use description fields liberally
6. **Validate module paths**: Ensure all `module` paths resolve to actual Python modules
7. **Use Pydantic models**: All I/O types must be proper Pydantic models

---

## Common Mistakes

Avoid these frequently encountered contract issues:

### 1. Technology-Leaking Capability Names

```yaml
# WRONG - Technology-specific capability names
capabilities:
  - name: "postgres"
  - name: "consul.register"
  - name: "kafka.publish"

# CORRECT - Capability-oriented names
capabilities:
  - name: "data.storage.write"
  - name: "service.discovery.register"
  - name: "event.publish"
```

**Why this matters**: Technology-agnostic names allow backend swaps without contract changes.

### 2. Missing Version Field

```yaml
# WRONG - Missing contract_version
name: "node_example"
node_type: "COMPUTE_GENERIC"

# CORRECT - Include version
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_example"
node_type: "COMPUTE_GENERIC"
```

### 3. Wrong Node Type for Intended Behavior

```yaml
# WRONG - Using COMPUTE for I/O operations
node_type: "COMPUTE_GENERIC"
io_operations:
  - operation: "write_to_database"  # I/O belongs in EFFECT!

# CORRECT - Use EFFECT for I/O
node_type: "EFFECT_GENERIC"
io_operations:
  - operation: "write_to_database"
```

**Node Type Selection Guide**:
- Has external I/O (database, API, files)? Use `EFFECT_GENERIC`
- Pure data transformation? Use `COMPUTE_GENERIC`
- Manages state with FSM? Use `REDUCER_GENERIC`
- Coordinates multi-step workflow? Use `ORCHESTRATOR_GENERIC`

### 4. Circular Dependencies

```yaml
# WRONG - Node A depends on Node B, Node B depends on Node A
# node_a/contract.yaml
dependencies:
  nodes:
    - name: "node_b"
      required: true

# node_b/contract.yaml
dependencies:
  nodes:
    - name: "node_a"    # Circular!
      required: true

# CORRECT - Use capability-based dependencies or refactor
dependencies:
  protocols:
    - name: "ProtocolSharedCapability"
      module: "mypackage.protocols"
```

### 5. Missing Module Paths

```yaml
# WRONG - Module path missing
input_model:
  name: "ModelExampleInput"

# CORRECT - Full module path included
input_model:
  name: "ModelExampleInput"
  module: "mypackage.nodes.node_example.models"
```

### 6. Incorrect Node Type Suffix

```yaml
# WRONG - Missing _GENERIC suffix
node_type: "EFFECT"

# CORRECT - Use _GENERIC suffix in contracts
node_type: "EFFECT_GENERIC"
```

### 7. Using Any Types

```yaml
# WRONG - Any type not allowed
input_model:
  name: "dict[str, Any]"  # Violates type safety

# CORRECT - Use object or specific Pydantic model
input_model:
  name: "ModelSpecificInput"
  module: "mypackage.models"
```

### 8. Ambiguous Contract Files

```
# WRONG - Both files in same directory
nodes/my_node/
  contract.yaml
  handler_contract.yaml  # Causes AMBIGUOUS_CONTRACT_CONFIGURATION error

# CORRECT - One contract per directory
nodes/my_node/
  contract.yaml          # Single source of truth
```

---

## Related Documentation

| Topic | Document |
|-------|----------|
| Coding standards | [CLAUDE.md](../../CLAUDE.md) (authoritative source) |
| Handler contracts | [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Node architecture | [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Node kind enum | [EnumNodeKind Migration Guide](../guides/ENUM_NODE_KIND_MIGRATION.md) |
| Node building | [Node Building Guide](../guides/node-building/README.md) |
| Node templates | [COMPUTE Template](../guides/templates/COMPUTE_NODE_TEMPLATE.md) / [EFFECT Template](../guides/templates/EFFECT_NODE_TEMPLATE.md) / [REDUCER Template](../guides/templates/REDUCER_NODE_TEMPLATE.md) / [ORCHESTRATOR Template](../guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md) |

---

**Last Updated**: 2026-01-18
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
