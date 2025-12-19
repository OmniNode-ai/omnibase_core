# Envelope Flow Architecture

> **Version**: 0.4.0
> **Last Updated**: 2025-12-19
> **Status**: Production

## Overview

The ONEX event system uses two complementary envelope models for message tracing, correlation, and delivery guarantees. This document explains how these envelopes flow through the 4-node architecture (EFFECT -> COMPUTE -> REDUCER -> ORCHESTRATOR) and when to use each type.

### Quick Reference

| Envelope Type | Purpose | Use Case |
|---------------|---------|----------|
| `ModelEnvelope` | Lightweight tracing context | Kafka headers, correlation tracking, causation chains |
| `ModelEventEnvelope[T]` | Full event wrapper | Complete event delivery with QoS, security, routing |

## The Two Envelope Models

### ModelEnvelope (Tracing Envelope)

**Location**: `omnibase_core.models.common.model_envelope`

`ModelEnvelope` is a minimal, immutable tracing envelope that provides correlation and causation tracking for distributed workflows. It is designed to be lightweight enough to include in Kafka message headers or pass through high-throughput pipelines.

**Key Fields**:

| Field | Type | Purpose |
|-------|------|---------|
| `message_id` | `UUID` | Unique identifier for this specific message |
| `correlation_id` | `UUID` | Groups all messages in a logical workflow/transaction |
| `causation_id` | `UUID \| None` | References the immediate parent message (None for root) |
| `emitted_at` | `datetime` | Timestamp when message was created (UTC, timezone-aware) |
| `entity_id` | `str` | Partition key and identity anchor (max 512 chars) |

**Characteristics**:
- Immutable (`frozen=True`) and thread-safe after creation
- Minimal memory footprint (~200 bytes per instance)
- O(1) validation complexity
- Supports causation chain validation

### ModelEventEnvelope[T] (Event Wrapper)

**Location**: `omnibase_core.models.events.model_event_envelope`

`ModelEventEnvelope[T]` is a generic, full-featured event wrapper that wraps any payload type `T` with comprehensive metadata for distributed event-driven systems. It includes QoS features, security context, routing information, and distributed tracing.

**Key Fields**:

| Field | Type | Purpose |
|-------|------|---------|
| `payload` | `T` | The wrapped event data (generic type) |
| `envelope_id` | `UUID` | Unique identifier for this envelope |
| `envelope_timestamp` | `datetime` | When envelope was created (UTC) |
| `correlation_id` | `UUID \| None` | Correlation ID for request tracing |
| `source_tool` | `str \| None` | Identifier of the originating tool/service |
| `target_tool` | `str \| None` | Identifier of the intended recipient |
| `metadata` | `ModelEnvelopeMetadata` | Typed metadata (tracing, headers, tags) |
| `security_context` | `ModelSecurityContext \| None` | Security and authorization context |
| `priority` | `int` | Request priority (1-10, default 5) |
| `timeout_seconds` | `int \| None` | Optional timeout in seconds |
| `retry_count` | `int` | Number of retry attempts (0 = first attempt) |
| `request_id` | `UUID \| None` | Request identifier for tracing |
| `trace_id` | `UUID \| None` | OpenTelemetry-compatible trace ID |
| `span_id` | `UUID \| None` | OpenTelemetry-compatible span ID |
| `onex_version` | `ModelSemVer` | ONEX standard version compliance |
| `envelope_version` | `ModelSemVer` | Envelope schema version |

**Characteristics**:
- Generic payload support via `ModelEventEnvelope[T]`
- Lazy evaluation support via `MixinLazyEvaluation` (~60% memory savings)
- Immutable builder pattern via `with_*` methods
- QoS features (priority, timeout, retry)
- Full distributed tracing support

## Architecture Diagram

### Relationship Between Envelope Types

```
+-----------------------------------------------------------------------------------+
|                           ONEX Envelope Architecture                               |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  +------------------------+         +------------------------------------------+  |
|  |    ModelEnvelope       |         |       ModelEventEnvelope[T]              |  |
|  |   (Tracing Context)    |         |         (Event Wrapper)                  |  |
|  +------------------------+         +------------------------------------------+  |
|  |                        |         |                                          |  |
|  | - message_id           |         | - envelope_id                            |  |
|  | - correlation_id  <--------+-----+-- correlation_id (same concept)          |  |
|  | - causation_id         |   |     | - payload: T (generic event data)        |  |
|  | - emitted_at           |   |     | - envelope_timestamp                     |  |
|  | - entity_id            |   |     | - source_tool / target_tool              |  |
|  |                        |   |     | - metadata: ModelEnvelopeMetadata        |  |
|  +------------------------+   |     |   +-- trace_id                           |  |
|                               |     |   +-- span_id                            |  |
|         PURPOSE:              |     |   +-- request_id                         |  |
|  * Lightweight tracing        |     |   +-- headers, tags                      |  |
|  * Kafka header propagation   |     | - security_context: ModelSecurityContext |  |
|  * Causation chain tracking   |     | - priority, timeout_seconds, retry_count |  |
|  * Partition key routing      |     | - trace_id, span_id (distributed tracing)|  |
|                               |     | - onex_version, envelope_version         |  |
|                               |     +------------------------------------------+  |
|                               |                                                   |
|                               |              PURPOSE:                             |
|                               |     * Full event delivery semantics               |
|                               |     * QoS guarantees (priority, timeout, retry)   |
|                               |     * Security context propagation                |
|                               |     * Routing (source -> target)                  |
|                               |     * Distributed tracing integration             |
|                               |                                                   |
+-----------------------------------------------------------------------------------+
```

### Envelope Flow Through 4-Node Architecture

```
+-----------------------------------------------------------------------------------+
|                    Event Flow Through ONEX 4-Node Architecture                     |
+-----------------------------------------------------------------------------------+

  External               EFFECT                COMPUTE               REDUCER
  Event                  (I/O)                (Process)             (Aggregate)
    |                      |                     |                      |
    v                      v                     v                      v
+--------+          +------------+         +------------+         +------------+
| Kafka  |          |            |         |            |         |            |
| Topic  |--------->| NodeEffect |-------->|NodeCompute |-------->|NodeReducer |
|        |          |            |         |            |         |            |
+--------+          +------------+         +------------+         +------------+
    |                     |                      |                      |
    |                     |                      |                      |
    | ModelEnvelope       | ModelEventEnvelope   | ModelEventEnvelope   |
    | (Kafka Headers)     | wraps payload        | wraps result         |
    |                     |                      |                      |
    | - correlation_id    | - correlation_id     | - correlation_id     |
    | - causation_id      |   (preserved)        |   (preserved)        |
    | - entity_id         | - payload: T         | - intents[]          |
    |                     | - trace_id/span_id   | - new_state          |
    v                     v                      v                      v

+-----------------------------------------------------------------------------------+
|                              ORCHESTRATOR                                          |
|                            (Coordinate)                                            |
+-----------------------------------------------------------------------------------+
|                                                                                    |
|  +----------------+     +----------------+     +----------------+                  |
|  | Receive Event  |     | Validate Lease |     | Issue Actions  |                 |
|  | Envelope       |---->| & Epoch        |---->| with Envelope  |                 |
|  |                |     |                |     | Context        |                 |
|  +----------------+     +----------------+     +----------------+                  |
|         |                      |                      |                           |
|         v                      v                      v                           |
|   Extract payload      Check ownership       Preserve:                            |
|   & trace context      via lease_id          - correlation_id                     |
|                        & epoch               - trace_id/span_id                   |
|                                              - causation chain                    |
|                                                                                    |
+-----------------------------------------------------------------------------------+
```

### Causation Chain Propagation

```
+-----------------------------------------------------------------------------------+
|                         Causation Chain Through Pipeline                           |
+-----------------------------------------------------------------------------------+

  ROOT EVENT                 CHILD 1                   CHILD 2                CHILD 3
  (User Request)             (Effect Result)           (Compute Result)       (Reducer)
       |                          |                         |                     |
       v                          v                         v                     v
  +-----------+              +-----------+              +-----------+        +-----------+
  | message_id|              | message_id|              | message_id|        | message_id|
  |   UUID-A  |              |   UUID-B  |              |   UUID-C  |        |   UUID-D  |
  +-----------+              +-----------+              +-----------+        +-----------+
  |correlation|              |correlation|              |correlation|        |correlation|
  |   UUID-X  |------------->|   UUID-X  |------------->|   UUID-X  |------->|   UUID-X  |
  +-----------+   (same)     +-----------+   (same)     +-----------+ (same) +-----------+
  |causation  |              |causation  |              |causation  |        |causation  |
  |   None    |              |   UUID-A  |------------->|   UUID-B  |------->|   UUID-C  |
  +-----------+   (root)     +-----------+  (parent)    +-----------+(parent)+-----------+
  | entity_id |              | entity_id |              | entity_id |        | entity_id |
  |"node-001" |              |"node-001" |              |"node-001" |        |"node-001" |
  +-----------+              +-----------+              +-----------+        +-----------+

  Legend:
  * correlation_id: Same UUID-X throughout entire workflow (horizontal grouping)
  * causation_id: Links to immediate parent (vertical chain)
  * entity_id: Partition key (often inherited, can change for cross-entity workflows)

+-----------------------------------------------------------------------------------+
```

## Flow Through 4-Node Architecture

### Stage 1: EFFECT Node (External I/O)

The EFFECT node receives events from external sources (Kafka, APIs, databases) and wraps them in `ModelEventEnvelope` for internal processing.

```python
from uuid import uuid4
from omnibase_core.models.common.model_envelope import ModelEnvelope
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

class NodeExternalApiEffect(NodeEffect):
    """EFFECT node that receives external events."""

    async def execute_effect(self, input_data: dict) -> ModelEventEnvelope:
        # Extract tracing from Kafka headers (ModelEnvelope fields)
        kafka_headers = input_data.get("kafka_headers", {})
        correlation_id = UUID(kafka_headers.get("correlation_id"))
        causation_id = UUID(kafka_headers.get("causation_id")) if kafka_headers.get("causation_id") else None
        entity_id = kafka_headers.get("entity_id", "unknown")

        # Create tracing envelope for this message
        trace_envelope = ModelEnvelope(
            correlation_id=correlation_id,
            causation_id=causation_id,
            entity_id=entity_id,
        )

        # Wrap payload in full event envelope
        payload = input_data.get("payload")
        event_envelope = ModelEventEnvelope(
            payload=payload,
            correlation_id=correlation_id,
            source_tool=self.node_id,
            trace_id=uuid4(),
            span_id=uuid4(),
        )

        return event_envelope
```

### Stage 2: COMPUTE Node (Processing)

The COMPUTE node receives `ModelEventEnvelope`, extracts the payload for processing, and produces a new envelope with preserved tracing context.

```python
class NodeDataProcessingCompute(NodeCompute):
    """COMPUTE node that processes event payloads."""

    async def execute_compute(
        self,
        envelope: ModelEventEnvelope[InputData]
    ) -> ModelEventEnvelope[ProcessedData]:
        # Extract payload for processing
        input_data = envelope.extract_payload()

        # Process data (pure computation, no side effects)
        processed_result = await self._transform_data(input_data)

        # Create child envelope preserving trace context
        result_envelope = ModelEventEnvelope(
            payload=processed_result,
            correlation_id=envelope.correlation_id,  # Preserve correlation
            source_tool=str(self.node_id),
            target_tool=envelope.source_tool,  # Return to sender pattern
            trace_id=envelope.trace_id,        # Preserve trace
            span_id=uuid4(),                   # New span for this operation
        ).with_metadata(envelope.metadata)     # Preserve metadata

        return result_envelope
```

### Stage 3: REDUCER Node (Aggregation)

The REDUCER node uses `ModelEnvelope` for causation tracking when emitting intents, while receiving `ModelEventEnvelope` for full context.

```python
class NodeMetricsReducer(NodeReducer):
    """REDUCER node with FSM-driven state transitions."""

    async def execute_reduction(
        self,
        envelope: ModelEventEnvelope[MetricsData]
    ) -> tuple[NewState, list[ModelIntent]]:
        # Extract payload
        metrics = envelope.extract_payload()

        # Create tracing envelope for causation chain
        trace_envelope = ModelEnvelope(
            correlation_id=envelope.correlation_id,
            causation_id=envelope.envelope_id,  # Link to parent
            entity_id=f"metrics-{envelope.source_tool}",
        )

        # Pure FSM transition
        new_state, intents = self._fsm_transition(
            current_state=self.state,
            event=metrics,
            trace=trace_envelope,
        )

        # Each intent carries the trace envelope fields
        for intent in intents:
            intent.correlation_id = trace_envelope.correlation_id
            intent.causation_id = trace_envelope.message_id

        return new_state, intents
```

### Stage 4: ORCHESTRATOR Node (Coordination)

The ORCHESTRATOR coordinates workflows using `ModelEventEnvelope` for full event context and `ModelEnvelope` for lightweight action tracking.

```python
class NodePipelineOrchestrator(NodeOrchestrator):
    """ORCHESTRATOR node with lease-based action emission."""

    async def execute_orchestration(
        self,
        envelope: ModelEventEnvelope[WorkflowRequest]
    ) -> ModelEventEnvelope[WorkflowResult]:
        # Acquire lease for workflow
        lease = await self._acquire_lease(envelope.correlation_id)

        # Create action with trace envelope fields
        action = ModelAction(
            action_id=uuid4(),
            lease_id=lease.lease_id,
            epoch=lease.epoch,
            correlation_id=envelope.correlation_id,
            # ... other fields
        )

        # Execute workflow steps with trace propagation
        result = await self._execute_workflow(
            action=action,
            trace_id=envelope.trace_id,
            span_id=envelope.span_id,
        )

        # Return result with preserved correlation
        return ModelEventEnvelope(
            payload=result,
            correlation_id=envelope.correlation_id,
            trace_id=envelope.trace_id,
            span_id=uuid4(),  # New span for orchestration
        )
```

## Use Cases and Examples

### Use Case 1: ModelEnvelope for Kafka Headers

When publishing events to Kafka, use `ModelEnvelope` fields as message headers for lightweight tracing across services.

```python
from uuid import uuid4
from omnibase_core.models.common.model_envelope import ModelEnvelope

# Create root envelope for new workflow
root = ModelEnvelope.create_root(
    correlation_id=uuid4(),
    entity_id="order-12345",
)

# Serialize to Kafka headers
kafka_headers = {
    "message_id": str(root.message_id),
    "correlation_id": str(root.correlation_id),
    "causation_id": str(root.causation_id) if root.causation_id else "",
    "entity_id": root.entity_id,
    "emitted_at": root.emitted_at.isoformat(),
}

# Produce message with headers
await kafka_producer.send(
    topic="order-events",
    key=root.entity_id.encode(),
    value=payload_bytes,
    headers=[(k, v.encode()) for k, v in kafka_headers.items()],
)
```

### Use Case 2: ModelEventEnvelope for Full Event Delivery

When processing events internally with QoS requirements, use `ModelEventEnvelope`.

```python
from uuid import uuid4
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

# Create event envelope with full features
envelope = ModelEventEnvelope(
    payload=OrderPlacedEvent(order_id="12345", items=[...]),
    correlation_id=uuid4(),
    source_tool="order-service",
    target_tool="inventory-service",
    priority=8,  # High priority
    timeout_seconds=30,
    retry_count=0,
)

# Add distributed tracing
envelope = envelope.with_tracing(
    trace_id=uuid4(),
    span_id=uuid4(),
    request_id=uuid4(),
)

# Add security context
envelope = envelope.with_security_context(
    ModelSecurityContext(
        user_id=current_user.id,
        roles=["order_writer"],
    )
)

# Check QoS properties
if envelope.is_high_priority():
    await fast_queue.publish(envelope)
else:
    await standard_queue.publish(envelope)
```

### Use Case 3: Creating Causation Chains

Use `ModelEnvelope.create_child()` to build causation chains for workflow tracking.

```python
from uuid import uuid4
from omnibase_core.models.common.model_envelope import (
    ModelEnvelope,
    validate_causation_chain,
)

# Create root envelope
root = ModelEnvelope.create_root(
    correlation_id=uuid4(),
    entity_id="workflow-abc",
)
print(f"Root is_root: {root.is_root()}")  # True

# Create child from effect node
effect_envelope = root.create_child()
print(f"Effect causation_id == root.message_id: {effect_envelope.causation_id == root.message_id}")  # True

# Create grandchild from compute node
compute_envelope = effect_envelope.create_child()
print(f"Same workflow: {compute_envelope.has_same_workflow(root)}")  # True

# Validate the chain
chain = [root, effect_envelope, compute_envelope]
is_valid = validate_causation_chain(chain)
print(f"Chain valid: {is_valid}")  # True

# Check direct causation
print(f"Compute caused by Effect: {compute_envelope.is_caused_by(effect_envelope)}")  # True
print(f"Compute caused by Root: {compute_envelope.is_caused_by(root)}")  # False
```

### Use Case 4: Accessing Trace Context from ModelEventEnvelope

Extract and use distributed tracing context from event envelopes.

```python
# Incoming envelope from upstream service
envelope: ModelEventEnvelope[OrderData] = await receive_event()

# Check for trace context
if envelope.has_trace_context():
    trace_ctx = envelope.get_trace_context()
    print(f"Trace ID: {trace_ctx['trace_id']}")
    print(f"Span ID: {trace_ctx['span_id']}")

    # Propagate to OpenTelemetry
    tracer.start_span(
        name="process_order",
        parent=trace_ctx,
    )

# Access metadata
tool_version = envelope.get_metadata_value("tool_version", default="unknown")
environment = envelope.get_metadata_value("environment", default="dev")

# Check expiration
if envelope.is_expired():
    logger.warning(f"Event {envelope.envelope_id} expired after {envelope.get_elapsed_time()}s")
    return

# Check if this is a retry
if envelope.is_retry():
    logger.info(f"Processing retry #{envelope.retry_count}")
```

### Use Case 5: Immutable Builder Pattern

Use `with_*` methods to create modified envelopes without mutating the original.

```python
from uuid import uuid4

# Original envelope
original = ModelEventEnvelope(
    payload={"data": "original"},
    correlation_id=uuid4(),
)

# Create variations without mutating original
high_priority = original.with_priority(10)
with_routing = original.set_routing(
    source_tool="service-a",
    target_tool="service-b",
)
on_retry = original.increment_retry_count()

# All are different instances
assert original.priority == 5
assert high_priority.priority == 10
assert original.retry_count == 0
assert on_retry.retry_count == 1
```

## When to Use Each Envelope Type

### Use ModelEnvelope When:

1. **Kafka Header Propagation**: Need lightweight tracing fields for message headers
2. **Causation Chain Tracking**: Building parent-child relationships between messages
3. **Partition Key Routing**: Using `entity_id` for consistent hashing
4. **High-Throughput Pipelines**: Memory efficiency is critical
5. **Cross-Service Tracing**: Minimal context needed for correlation

### Use ModelEventEnvelope[T] When:

1. **Full Event Delivery**: Need QoS guarantees (priority, timeout, retry)
2. **Security Context**: Must propagate authentication/authorization
3. **Distributed Tracing**: OpenTelemetry integration with trace_id/span_id
4. **Routing Logic**: Need source/target tool identification
5. **Rich Metadata**: Headers, tags, and custom metadata required
6. **Internal Processing**: Events flowing between ONEX nodes

### Combined Usage Pattern

A common pattern is to use both envelope types together:

```python
# External: ModelEnvelope in Kafka headers
kafka_headers = {
    "correlation_id": str(envelope.correlation_id),
    "causation_id": str(envelope.causation_id),
    "entity_id": envelope.entity_id,
}

# Internal: ModelEventEnvelope for processing
event_envelope = ModelEventEnvelope(
    payload=event_data,
    correlation_id=envelope.correlation_id,  # From ModelEnvelope
    trace_id=extract_from_headers(kafka_headers),
    priority=determine_priority(event_data),
    security_context=current_security_context(),
)
```

## Best Practices

### 1. Always Preserve Correlation ID

The `correlation_id` must flow through the entire workflow unchanged.

```python
# When creating child envelopes or messages
child = ModelEventEnvelope(
    payload=result,
    correlation_id=parent.correlation_id,  # Always preserve!
)
```

### 2. Build Causation Chains

Use `create_child()` to maintain proper causation relationships.

```python
# Correct: Creates proper causation link
child = parent_envelope.create_child()

# Also correct: Manual linkage
child = ModelEnvelope(
    correlation_id=parent.correlation_id,
    causation_id=parent.message_id,  # Point to parent
    entity_id=parent.entity_id,
)
```

### 3. Use Appropriate Envelope for Context

```python
# Lightweight (Kafka headers, logging)
trace = ModelEnvelope(correlation_id=cid, entity_id=eid)

# Full-featured (event processing)
event = ModelEventEnvelope(
    payload=data,
    correlation_id=cid,
    priority=8,
    timeout_seconds=30,
)
```

### 4. Validate Chains Before Processing

```python
from omnibase_core.models.common.model_envelope import validate_causation_chain

# Before processing a batch
if not validate_causation_chain(envelope_batch):
    raise ValidationError("Invalid causation chain detected")
```

### 5. Extract Payload Explicitly

```python
# Preferred: Explicit extraction
payload = envelope.extract_payload()
process(payload)

# Also works: Direct access
process(envelope.payload)
```

## Related Documentation

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) - Core architectural patterns
- [Model Intent Architecture](MODEL_INTENT_ARCHITECTURE.md) - Intent emission from Reducers
- [Model Action Architecture](MODEL_ACTION_ARCHITECTURE.md) - Action emission from Orchestrators
- [Contract System](CONTRACT_SYSTEM.md) - Contract-based communication

---

**Document Version**: 0.4.0
**Last Updated**: 2025-12-19
**Primary Maintainer**: ONEX Framework Team
