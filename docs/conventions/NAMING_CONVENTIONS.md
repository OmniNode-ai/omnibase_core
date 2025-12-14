# ONEX Naming Conventions

This document defines naming conventions for ONEX components including topics, handlers, profiles, subscriptions, and fingerprints.

---

## Table of Contents

1. [Topic Naming](#topic-naming)
2. [Handler Conventions](#handler-conventions)
3. [Profile Tags](#profile-tags)
4. [Subscription Formats](#subscription-formats)
5. [Fingerprint Format](#fingerprint-format)
6. [Model Naming](#model-naming)

---

## Topic Naming

### Required Prefix: `onex.*`

All ONEX event bus topics **MUST** use the `onex.` prefix to:
- Ensure namespace isolation from other systems
- Enable topic filtering and routing
- Support multi-tenant deployments
- Provide clear ownership and discoverability

### Topic Format

Topics and event types follow a hierarchical naming structure:

- **Topic name**: The full dot-separated path used for event bus routing (e.g., `onex.node.compute.completed`). This is what you subscribe to or publish on.
- **Event type suffix**: The final segment that describes what happened (e.g., `completed`, `failed`, `started`). This is part of the topic name, not a separate identifier.

```text
onex.<domain>.<entity>.<event-type-suffix>
```

**Components:**
- `onex.` - Required prefix (lowercase)
- `<domain>` - Business domain (e.g., `node`, `workflow`, `discovery`)
- `<entity>` - Specific entity type (e.g., `compute`, `effect`, `reducer`)
- `<event-type-suffix>` - Event action suffix (e.g., `created`, `completed`, `failed`)

### Examples

```python
# Node lifecycle events
"onex.node.compute.started"
"onex.node.compute.completed"
"onex.node.effect.failed"

# Workflow events
"onex.workflow.execution.started"
"onex.workflow.step.completed"
"onex.workflow.execution.failed"

# Discovery events
"onex.discovery.request"
"onex.discovery.response"
"onex.introspection.request"
"onex.introspection.response"

# System events (use reserved topic prefixes from table below)
"onex.discovery.node.request"
"onex.introspection.node.request"
"onex.health.node.check"
"onex.metrics.node.collected"
"onex.dlq.compute.failed"
```

### Reserved Topics

These topics are reserved for ONEX core functionality:

| Topic | Purpose |
|-------|---------|
| `onex.discovery.*` | Node discovery protocol |
| `onex.introspection.*` | Node introspection protocol |
| `onex.health.*` | Health check protocol |
| `onex.metrics.*` | Metrics collection |
| `onex.dlq.*` | Dead letter queues |

### Topic Configuration

```python
from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)

config = ModelEventBusConfig(
    bootstrap_servers=["localhost:9092"],
    topics=[
        "onex.node.compute.events",  # Correct: uses onex. prefix
        "onex.workflow.execution.events",
    ],
    # ... other configuration
)
```

---

## Handler Conventions

### Handler Type Classification

Handlers are classified by `EnumHandlerType` for routing purposes:

| Handler Type | Purpose | Example |
|-------------|---------|---------|
| `HTTP` | HTTP/REST API calls | API gateway, webhooks |
| `DATABASE` | Database operations | PostgreSQL, MongoDB queries |
| `KAFKA` | Message queue operations | Event publishing/consuming |
| `FILESYSTEM` | File system operations | File read/write, temp files |
| `GRPC` | gRPC service calls | Microservice communication |
| `WEBSOCKET` | WebSocket connections | Real-time streaming |
| `CUSTOM` | Custom implementations | Specialized handlers |

### When Handlers are Required vs Optional

**Required Handlers:**
- Node contracts that specify `io_configs` **MUST** have registered handlers for each I/O type
- Runtime will fail on initialization if required handlers are missing
- Example: A contract specifying `HTTP` I/O requires an HTTP handler

**Optional Handlers:**
- Handlers can be registered dynamically at runtime
- Handlers can be replaced (same `handler_type` overwrites previous)
- Use `replace=False` for strict registration that raises on duplicates

### Handler Registration Example

```python
"""Example handler implementation demonstrating ONEX conventions.

Copy-paste safe: All imports and types are included.
"""

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols.runtime import ProtocolHandler
from omnibase_core.types.typed_dict_handler_metadata import TypedDictHandlerMetadata


class MyHttpHandler(ProtocolHandler):
    """Custom HTTP handler implementation.

    This handler processes HTTP-related events through the ONEX event bus.
    Implements the ProtocolHandler interface for runtime integration.
    """

    @property
    def handler_type(self) -> EnumHandlerType:
        """Return the handler type classification."""
        return EnumHandlerType.HTTP

    async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """Execute the handler logic.

        Args:
            envelope: The incoming event envelope to process.

        Returns:
            The processed event envelope with results.
        """
        # Implement your handler logic here
        # Example: Process HTTP request data from envelope.payload
        return envelope

    def describe(self) -> TypedDictHandlerMetadata:
        """Provide handler metadata for discovery and routing.

        Returns:
            Handler metadata dictionary with name, version, and capabilities.
        """
        return {
            "name": "my_http_handler",
            "version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Custom HTTP handler for API integration",
            "capabilities": ["GET", "POST", "PUT", "DELETE"],
        }
```

### Handler Version Format

Handler versions **MUST** use semantic versioning (SemVer):

```python
from omnibase_core.models.primitives.model_semver import ModelSemVer

version = ModelSemVer(major=1, minor=0, patch=0)  # 1.0.0
```

**Version Compatibility:**
- Major version change: Breaking API changes
- Minor version change: Backward-compatible features
- Patch version change: Bug fixes only

---

## Profile Tags

### Tag Formats

Profile tags support two formats:

#### 1. Hierarchical Format (Recommended for Metadata)

Use `category:value` format for structured metadata that supports filtering:

```text
<category>:<value>
```

#### 2. Simple String Format (For Categorization)

Use simple strings without colons for basic categorization tags:

```text
<tag-name>
```

### Standard Hierarchical Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| `env` | Environment classification | `env:production`, `env:staging`, `env:development` |
| `region` | Geographic region | `region:us-east-1`, `region:eu-west-1` |
| `tier` | Service tier | `tier:critical`, `tier:standard`, `tier:background` |
| `team` | Owning team | `team:platform`, `team:data`, `team:ml` |
| `capability` | Feature capabilities | `capability:async`, `capability:batch` |

### Common Simple Tags

Simple tags are useful for categorization without structured filtering:

| Tag | Purpose |
|-----|---------|
| `runtime` | Runtime-related functionality |
| `effect` | Effect node functionality |
| `contracts` | Contract-related functionality |
| `validation` | Validation functionality |
| `discovery` | Discovery-related functionality |

### Tag Usage in Python

```python
from omnibase_core.models.container.model_service_metadata import (
    ModelServiceMetadata,
)

metadata = ModelServiceMetadata(
    service_id=uuid4(),
    service_name="compute_processor",
    service_interface="ProtocolCompute",
    service_implementation="ComputeProcessor",
    version=ModelSemVer(major=1, minor=0, patch=0),
    tags=[
        # Hierarchical tags for filtering
        "env:production",
        "tier:critical",
        "team:platform",
        "capability:async",
    ],
)
```

### Tag Usage in YAML Contracts

Both formats are valid in YAML `profile_tags` arrays:

```yaml
# Example with hierarchical tags
profile_tags:
  - "env:production"
  - "tier:critical"
  - "team:platform"

# Example with simple categorization tags
profile_tags:
  - "runtime"
  - "effect"
  - "contracts"

# Mixed usage (valid but hierarchical preferred for consistency)
profile_tags:
  - "env:production"
  - "runtime"
```

### Tag Best Practices

1. **Lowercase**: Use lowercase for consistency
2. **Hierarchical for Filtering**: Use `category:value` format when you need to filter by category
3. **Simple for Categorization**: Use simple strings for basic categorization without filtering needs
4. **Consistent Within Project**: Choose one format per use case and apply consistently
5. **Documented**: Document custom tags in your project

---

## Subscription Formats

### Event Subscription Patterns

Subscriptions use pattern matching for flexible event filtering:

```python
subscribed_events: list[str] = [
    "NODE_INTROSPECTION_REQUEST",  # Exact match
    "NODE_DISCOVERY_REQUEST",      # Exact match
    "WORKFLOW_*",                  # Wildcard: all WORKFLOW events
]
```

### Pattern Types

| Pattern | Description | Example |
|---------|-------------|---------|
| Exact | Matches exact event type | `NODE_INTROSPECTION_REQUEST` |
| Wildcard suffix | Matches prefix with any suffix | `WORKFLOW_*` |
| Wildcard prefix | Matches suffix with any prefix | `*_COMPLETED` |

### Filter Configuration

```python
from omnibase_core.models.contracts.subcontracts.model_event_handling_subcontract import (
    ModelEventHandlingSubcontract,
)

event_handling = ModelEventHandlingSubcontract(
    version=ModelSemVer(major=1, minor=0, patch=0),
    enabled=True,
    subscribed_events=[
        "NODE_INTROSPECTION_REQUEST",
        "NODE_DISCOVERY_REQUEST",
    ],
    event_filters={
        "node_id": "compute-*",   # fnmatch pattern
        "node_name": "processor*",
    },
    enable_node_id_filtering=True,
    enable_node_name_filtering=True,
)
```

### Dead Letter Queue Configuration

Failed events can be routed to a dead letter queue:

```python
event_handling = ModelEventHandlingSubcontract(
    # ... other config ...
    dead_letter_channel="onex.dlq.compute.failed",  # Must be alphanumeric with ._-
    dead_letter_max_events=1000,
    dead_letter_overflow_strategy="drop_oldest",  # or "drop_newest", "block"
)
```

---

## Fingerprint Format

### Format Specification

```text
<semver>:<sha256-first-N-hex-chars>
```

**Components:**
- `semver`: Semantic version **without 'v' prefix** (e.g., `1.0.0`, `0.3.6-beta.1`)
- `:`: Separator (single colon)
- `hash`: First N hex characters of SHA256 (default: 12)

**Important:** The semver component must NOT include a 'v' prefix. Use `1.0.0`, not `v1.0.0`.

### Examples

```text
1.0.0:8fa1e2b4c9d1
0.3.6:abcdef123456
2.1.3-beta.1:deadbeef0000
```

### Hash Length Configuration

Default hash length is **12 characters (48 bits)**.

**Collision Analysis:**
- 12 chars = 48 bits = ~281 trillion possibilities
- With 10,000 contracts: ~0.00002% collision probability
- Sufficient for typical contract registries

**Configure longer hash for higher security:**

```python
from omnibase_core.models.contracts.model_contract_normalization_config import (
    ModelContractNormalizationConfig,
)

config = ModelContractNormalizationConfig(
    hash_length=16,  # 64 bits for higher security
)
```

### Fingerprint Computation

```python
from omnibase_core.contracts.hash_registry import compute_contract_fingerprint

# Compute fingerprint for a contract model
fingerprint = compute_contract_fingerprint(contract_model)
print(fingerprint)  # "1.0.0:8fa1e2b4c9d1"
```

---

## Model Naming

### Model Class Naming

All Pydantic model classes **MUST** use the `Model` prefix:

```python
# Correct
class ModelComputeInput(BaseModel): ...
class ModelEffectOutput(BaseModel): ...
class ModelContractFingerprint(BaseModel): ...

# Incorrect
class ComputeInput(BaseModel): ...
class EffectOutput(BaseModel): ...
```

### Contract Naming

Contract names should follow PascalCase or snake_case:

```yaml
# PascalCase (recommended for node contracts)
name: NodeDataTransformerCompute

# snake_case (acceptable)
name: node_data_transformer_compute
```

### File Naming

Model files follow `model_<name>.py` convention:

```text
models/
  core/
    model_onex_envelope.py
    model_event_channels.py
  contracts/
    model_contract_compute.py
    model_contract_fingerprint.py
```

---

## Related Documentation

- **Pydantic Best Practices**: `docs/conventions/PYDANTIC_BEST_PRACTICES.md`
- **Version Semantics**: `docs/conventions/VERSION_SEMANTICS.md`
- **Error Handling**: `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`
- **Contract System**: `docs/architecture/CONTRACT_SYSTEM.md`
- **Event-Driven Architecture**: `docs/patterns/EVENT_DRIVEN_ARCHITECTURE.md`

---

**Last Updated**: 2025-12-14
**Project**: omnibase_core v0.3.6
