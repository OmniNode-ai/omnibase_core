> **Navigation**: [Home](../index.md) > Contracts > Operation Bindings DSL

# Operation Bindings DSL

**Version**: 1.0.0
**Last Updated**: 2025-01-25
**Status**: Comprehensive Reference

> **New in v0.4.2**: ModelOperationBindings provides declarative handler wiring without code adapters, enabling contract-driven operation binding.

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [Expression Syntax](#expression-syntax)
   - [Expression Format](#expression-format)
   - [Allowed Roots](#allowed-roots)
   - [Pipe Functions](#pipe-functions)
4. [Validation Rules](#validation-rules)
5. [Schema Reference](#schema-reference)
   - [ModelOperationBindings](#modeloperationbindings)
   - [ModelOperationMapping](#modeloperationmapping)
   - [ModelEnvelopeTemplate](#modelenvelopetemplate)
   - [ModelResponseMapping](#modelresponsemapping)
6. [Examples](#examples)
   - [Filesystem Write Operation](#filesystem-write-operation)
   - [Database Query Result Mapping](#database-query-result-mapping)
   - [Event Publish Payload Mapping](#event-publish-payload-mapping)
7. [Non-Goals](#non-goals)
8. [Future Extensions](#future-extensions)
9. [Related Documentation](#related-documentation)

---

## Overview

The Operation Bindings DSL enables **declarative handler wiring** directly in YAML contracts, eliminating the need for code adapters. Instead of writing Python code to transform requests into handler envelopes and map results back to responses, you define the mappings declaratively.

**Problem Solved**: Previously, each operation required a custom adapter class to:
1. Extract fields from incoming requests
2. Construct handler envelopes
3. Map handler results to response fields

**Solution**: With operation bindings, these mappings are declared in the contract YAML using simple `${...}` expressions.

```yaml
operation_bindings:
  version:
    major: 1
    minor: 0
    patch: 0
  handler: "omnibase_infra.handlers.handler_filesystem.HandlerFileSystem"
  config:
    base_path: "${contract.config.base_path}"
  mappings:
    store:
      envelope:
        operation: "write_file"
        path: "${binding.config.base_path}/snapshots/${request.snapshot_id}.json"
        content: "${request.snapshot | to_json}"
      response:
        status: "${result.status}"
        bytes_written: "${result.bytes_written}"
```

**Related Tickets**:
- [OMN-1410](https://linear.app/omninode/issue/OMN-1410): Schema implementation (completed)
- [OMN-1517](https://linear.app/omninode/issue/OMN-1517): Documentation (this document)
- [OMN-1518](https://linear.app/omninode/issue/OMN-1518): Routing integration
- [OMN-1519](https://linear.app/omninode/issue/OMN-1519): Runtime loader

---

## Design Philosophy

The Operation Bindings DSL follows a **"dumb DSL"** design philosophy:

1. **Wiring, not logic**: The DSL handles data routing between request, config, and result objects. Business logic belongs in handlers.

2. **Explicit over implicit**: All mappings are visible in the contract. No hidden transformations or magic.

3. **Security by constraint**: The DSL intentionally limits what can be expressed to prevent injection attacks and maintain auditability.

4. **Validation at load time**: All expressions are validated when the contract is loaded, not at runtime. Invalid expressions fail fast.

5. **Composable with other subcontracts**: Operation bindings work alongside FSM, routing, and other subcontracts.

---

## Expression Syntax

### Expression Format

Expressions use the `${...}` syntax with an optional pipe function:

```
${root.path}
${root.path | function}
```

**Components**:
- **root**: One of the allowed roots (`binding.config`, `contract.config`, `request`, `result`)
- **path**: Dot-separated path to the desired value (e.g., `snapshot.snapshot_id`)
- **function** (optional): A transformation function separated by `|`

**Examples**:
```yaml
# Simple path access
path: "${request.file_path}"

# Nested path access
id: "${request.snapshot.snapshot_id}"

# Path with pipe function
content: "${request.data | to_json}"

# Config reference
base_dir: "${binding.config.base_path}"
```

### Allowed Roots

| Root | Context | Description |
|------|---------|-------------|
| `binding.config` | Envelope/Response | Local configuration defined in this binding's `config` field |
| `contract.config` | Envelope/Response | Parent contract's configuration (shared across all bindings) |
| `request` | Envelope/Response | Incoming request data being processed |
| `result` | Response only | Handler execution result (only available in response mappings) |

**Root Selection Guide**:

```yaml
operation_bindings:
  config:
    # binding.config values are defined here
    base_path: "/data/snapshots"
    max_size: 1048576

  mappings:
    store:
      envelope:
        # Use binding.config for binding-specific settings
        path: "${binding.config.base_path}/${request.id}.json"

        # Use contract.config for shared settings
        region: "${contract.config.default_region}"

        # Use request for incoming data
        content: "${request.payload}"

      response:
        # Use result for handler output
        status: "${result.status}"

        # Can still use request in response
        request_id: "${request.id}"
```

### Pipe Functions

Only two pipe functions are allowed. Chaining is **not permitted**.

| Function | Description | Example |
|----------|-------------|---------|
| `to_json` | Serialize value to JSON string | `${request.data \| to_json}` |
| `from_json` | Parse JSON string to object | `${result.payload \| from_json}` |

**Valid**:
```yaml
content: "${request.snapshot | to_json}"
data: "${result.json_string | from_json}"
```

**Invalid** (chaining):
```yaml
# ERROR: Chained pipes not allowed
data: "${request.raw | from_json | to_json}"
```

---

## Validation Rules

The DSL enforces strict validation rules at contract load time.

### Syntax Constraints

| Rule | Description | Error |
|------|-------------|-------|
| **No empty expressions** | `${}` is not allowed | "Empty expression not allowed" |
| **Dot-path only** | Use `a.b.c` not `a["b"]["c"]` | "Bracket notation not allowed" |
| **No ternary operators** | `?` and `:` are forbidden | "Ternary operators not allowed" |
| **No chained pipes** | Maximum one `\|` per expression | "Chained pipes not allowed" |
| **Valid root required** | Must start with allowed root | "Invalid expression root" |
| **Valid function only** | Only `to_json`, `from_json` | "Invalid pipe function" |

### Security Constraints

| Rule | Description | Rationale |
|------|-------------|-----------|
| **No double underscores** | `__` anywhere in path is rejected | Prevents `__class__`, `__import__`, etc. |
| **Denied builtins** | `eval`, `exec`, `getattr`, etc. blocked | Prevents code injection |
| **Maximum depth** | 20 levels of nesting | Prevents DoS via deep recursion |

**Denied Builtins** (partial list):
- Code execution: `eval`, `exec`, `compile`, `__import__`
- Introspection: `globals`, `locals`, `vars`, `dir`, `getattr`, `setattr`
- Special attributes: `__class__`, `__bases__`, `__mro__`, `__dict__`, `__code__`

### Context-Specific Roots

Certain roots are only valid in specific contexts:

| Root | Config Section | Envelope Template | Response Mapping |
|------|----------------|-------------------|------------------|
| `binding.config` | Yes | Yes | Yes |
| `contract.config` | Yes | Yes | Yes |
| `request` | No | Yes | Yes |
| `result` | No | No | Yes |

**Config expressions** can only reference `binding.config` or `contract.config`:
```yaml
config:
  # Valid
  base_path: "${contract.config.data_dir}"

  # Invalid - request not available in config
  # user_id: "${request.user_id}"  # ERROR
```

---

## Schema Reference

### ModelOperationBindings

Top-level subcontract for operation bindings.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | `ModelSemVer` | Yes | Subcontract version (must be provided in YAML) |
| `handler` | `str` | Yes | Python dotted import path to handler class |
| `config` | `dict[str, Any]` | No | Local configuration for this binding |
| `mappings` | `dict[str, ModelOperationMapping]` | Yes | Operation name to mapping definitions |
| `description` | `str` | No | Human-readable description |

**Handler Path Validation**:
- Must contain at least one dot (e.g., `module.ClassName`)
- Each segment must be a valid Python identifier
- No double underscores allowed (security)

**Source**: `src/omnibase_core/models/contracts/subcontracts/model_operation_bindings.py`

### ModelOperationMapping

Combines envelope template and response mapping for a single operation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `envelope` | `ModelEnvelopeTemplate` | Yes | Template for constructing handler envelope |
| `response` | `ModelResponseMapping` | No | Optional mapping of result to response fields |
| `description` | `str` | No | Human-readable description of this mapping |

**Note**: The operation name (e.g., "store", "retrieve") is the dictionary key, not a field on this model.

**Source**: `src/omnibase_core/models/contracts/subcontracts/model_operation_mapping.py`

### ModelEnvelopeTemplate

Defines how to construct handler envelopes from request data.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operation` | `str` | Yes | Operation name for the handler (e.g., "write_file") |
| `fields` | `dict[str, Any]` | No | Additional envelope fields with template values |

**Source**: `src/omnibase_core/models/contracts/subcontracts/model_envelope_template.py`

### ModelResponseMapping

Maps handler results to response fields.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fields` | `dict[str, Any]` | No | Response field mappings with template values |

**Source**: `src/omnibase_core/models/contracts/subcontracts/model_response_mapping.py`

---

## Examples

### Filesystem Write Operation

Store session snapshots to the filesystem.

```yaml
operation_bindings:
  version:
    major: 1
    minor: 0
    patch: 0

  handler: "omnibase_infra.handlers.handler_filesystem.HandlerFileSystem"

  description: "Filesystem operations for session snapshot persistence"

  config:
    base_path: "${contract.config.snapshot_storage_path}"
    allowed_paths:
      - "${contract.config.snapshot_storage_path}"

  mappings:
    store_snapshot:
      description: "Persist session snapshot to JSON file"
      envelope:
        operation: "write_file"
        path: "${binding.config.base_path}/sessions/${request.session_id}/${request.snapshot.snapshot_id}.json"
        content: "${request.snapshot | to_json}"
        mode: "w"
        encoding: "utf-8"
        create_parents: true
      response:
        status: "${result.status}"
        snapshot_id: "${request.snapshot.snapshot_id}"
        bytes_written: "${result.bytes_written}"
        file_path: "${result.path}"

    retrieve_snapshot:
      description: "Load session snapshot from JSON file"
      envelope:
        operation: "read_file"
        path: "${binding.config.base_path}/sessions/${request.session_id}/${request.snapshot_id}.json"
        encoding: "utf-8"
      response:
        snapshot: "${result.content | from_json}"
        status: "${result.status}"
        error_message: "${result.error_message}"
```

### Database Query Result Mapping

Map database query results to response models.

```yaml
operation_bindings:
  version:
    major: 1
    minor: 0
    patch: 0

  handler: "omnibase_infra.handlers.handler_database.HandlerDatabase"

  config:
    connection_pool: "${contract.config.database.pool_name}"
    default_timeout_ms: 5000

  mappings:
    get_user_profile:
      description: "Fetch user profile by ID"
      envelope:
        operation: "query"
        sql: "SELECT id, name, email, created_at FROM users WHERE id = :user_id"
        params:
          user_id: "${request.user_id}"
        timeout_ms: "${binding.config.default_timeout_ms}"
      response:
        user:
          id: "${result.rows.0.id}"
          name: "${result.rows.0.name}"
          email: "${result.rows.0.email}"
          created_at: "${result.rows.0.created_at}"
        found: "${result.row_count}"
        query_time_ms: "${result.execution_time_ms}"

    list_user_sessions:
      description: "List active sessions for a user"
      envelope:
        operation: "query"
        sql: "SELECT session_id, created_at, last_active FROM sessions WHERE user_id = :user_id AND active = true"
        params:
          user_id: "${request.user_id}"
      response:
        sessions: "${result.rows}"
        count: "${result.row_count}"
```

### Event Publish Payload Mapping

Construct event payloads for publishing.

```yaml
operation_bindings:
  version:
    major: 1
    minor: 0
    patch: 0

  handler: "omnibase_infra.handlers.handler_event_bus.HandlerEventBus"

  config:
    topic_prefix: "${contract.config.kafka.topic_prefix}"
    default_partition_key: "event_id"

  mappings:
    publish_session_event:
      description: "Publish session lifecycle event to Kafka"
      envelope:
        operation: "publish"
        topic: "${binding.config.topic_prefix}.session.lifecycle"
        partition_key: "${request.session_id}"
        payload:
          event_type: "${request.event_type}"
          session_id: "${request.session_id}"
          user_id: "${request.user_id}"
          timestamp: "${request.timestamp}"
          data: "${request.event_data | to_json}"
        headers:
          correlation_id: "${request.correlation_id}"
          source: "session-service"
      response:
        published: "${result.success}"
        partition: "${result.partition}"
        offset: "${result.offset}"
        error: "${result.error_message}"
```

---

## Non-Goals

The Operation Bindings DSL is intentionally limited. The following are **explicitly out of scope**:

### No Conditionals

Conditional logic belongs in handlers, not in wiring.

```yaml
# NOT SUPPORTED - use handler logic instead
status: "${result.success ? 'ok' : 'error'}"
```

### No Loops

Iteration over collections must happen in handlers.

```yaml
# NOT SUPPORTED - handler should return formatted data
items: "${for item in result.items: item.name}"
```

### No Array Indexing

Bracket notation is forbidden for security reasons.

```yaml
# NOT SUPPORTED - use dot-path only
first_item: "${result.items[0].name}"

# WORKAROUND: Handler returns pre-indexed values
first_item: "${result.first_item.name}"
```

### No Arbitrary Functions

Only `to_json` and `from_json` are allowed.

```yaml
# NOT SUPPORTED
length: "${result.items | len}"
upper: "${result.name | upper}"
```

### Complex Transformations

Data reshaping, filtering, and aggregation belong in handlers.

```yaml
# NOT SUPPORTED - complex transformations
summary:
  total: "${sum(result.items.price)}"
  filtered: "${filter(result.items, active=true)}"

# CORRECT - handler returns pre-computed values
summary:
  total: "${result.computed_total}"
  filtered_count: "${result.active_item_count}"
```

---

## Future Extensions

The following extensions are **known likely needs** but are **not currently implemented**. They may be added in future versions based on real-world usage patterns.

### Array Indexing Syntax

Access specific array elements by index.

```yaml
# Potential future syntax
first_item: "${result.items.0.name}"
last_error: "${result.errors.-1.message}"
```

**Status**: Under consideration. Requires careful security review for bounds checking.

### Default Value Function

Provide fallback values for missing fields.

```yaml
# Potential future syntax
name: "${result.name | default('Unknown')}"
count: "${result.items.length | default(0)}"
```

**Status**: Under consideration. Would need escaping rules for the default value.

### Ternary/Conditionals

Simple conditional expressions if use cases justify the complexity.

```yaml
# Potential future syntax (if ever added)
status: "${result.success | if_else('ok', 'error')}"
```

**Status**: Low priority. Current philosophy pushes conditionals to handlers.

---

## Related Documentation

- [Handler Contract Guide](HANDLER_CONTRACT_GUIDE.md) - Handler contract structure and behavior descriptors
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node types and data flow
- [Node Building Guide](../guides/node-building/README.md) - Building ONEX nodes

---

## API Reference

### Import Paths

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelOperationBindings,
    ModelOperationMapping,
    ModelEnvelopeTemplate,
    ModelResponseMapping,
)

from omnibase_core.models.primitives import ModelSemVer
```

### Programmatic Usage

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelOperationBindings,
    ModelOperationMapping,
    ModelEnvelopeTemplate,
    ModelResponseMapping,
)
from omnibase_core.models.primitives import ModelSemVer

# Create bindings programmatically
bindings = ModelOperationBindings(
    version=ModelSemVer(major=1, minor=0, patch=0),
    handler="mymodule.handlers.MyHandler",
    config={"base_path": "${contract.config.data_dir}"},
    mappings={
        "process": ModelOperationMapping(
            envelope=ModelEnvelopeTemplate(
                operation="do_work",
                fields={
                    "input": "${request.data}",
                    "config": "${binding.config.base_path}",
                },
            ),
            response=ModelResponseMapping(
                fields={
                    "result": "${result.output}",
                    "status": "${result.status}",
                }
            ),
        )
    },
)

# Get all operation names
operations = bindings.get_all_operation_names()
# {'process'}

# Get mapping for specific operation
mapping = bindings.get_mapping("process")
```

---

**Last Updated**: 2025-01-25
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
