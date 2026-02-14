> **Navigation**: [Home](../INDEX.md) > [Patterns](./README.md) > Event-Driven Architecture

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Event-Driven Architecture -- omnibase_core

**Status**: Complete

> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions of Event, Intent, and other ONEX concepts.

## Overview

This document describes the event-driven architecture patterns used in ONEX. All inter-node communication flows through `ModelEventEnvelope`, published and consumed via `ProtocolEventBus`. Events follow a unidirectional flow through the four-node architecture: EFFECT produces raw events from external I/O, COMPUTE transforms data purely, REDUCER aggregates state and emits intents, and ORCHESTRATOR coordinates workflows by publishing events and routing intents.

## Table of Contents

1. [Event Envelope Structure](#event-envelope-structure)
2. [Event Bus Protocol](#event-bus-protocol)
3. [Event Flow Patterns](#event-flow-patterns)
4. [Event-to-Reducer Flow](#event-to-reducer-flow)
5. [Event-to-Orchestrator Flow](#event-to-orchestrator-flow)
6. [Intent Emission and Routing](#intent-emission-and-routing)
7. [Error Handling](#error-handling)
8. [Idempotency](#idempotency)
9. [Event Ordering](#event-ordering)
10. [Backpressure](#backpressure)
11. [Testing Event-Driven Code](#testing-event-driven-code)

---

## Event Envelope Structure

All events are wrapped in `ModelEventEnvelope[T]`, a generic Pydantic model that provides standardized metadata, correlation tracking, distributed tracing, and QoS features.

**Import path**: `omnibase_core.models.events.model_event_envelope.ModelEventEnvelope`

### Envelope Fields

```python
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from uuid import uuid4

envelope = ModelEventEnvelope(
    # Payload -- the actual event data (generic type T)
    payload={"order_id": "ORD-001", "total": 99.99},

    # Routing
    event_type="orders.order-placed.v1",
    payload_type="ModelOrderPlacedEvent",
    payload_schema_version=ModelSemVer(major=1, minor=0, patch=0),

    # Correlation and tracing
    correlation_id=uuid4(),
    request_id=uuid4(),
    trace_id=uuid4(),
    span_id=uuid4(),

    # Source and target
    source_tool="node_order_intake_effect",
    target_tool="node_order_workflow_orchestrator",

    # QoS
    priority=5,
    timeout_seconds=30,
    retry_count=0,

    # Metadata
    metadata=ModelEnvelopeMetadata(
        tool_version="1.0.0",
        environment="production",
    ),
)
```

### Key Design Decisions

- **Generic payload**: `ModelEventEnvelope[T]` accepts any Pydantic model or dict as payload.
- **Immutable after creation**: The envelope itself is a Pydantic model; treat it as immutable.
- **Lazy evaluation**: Includes `MixinLazyEvaluation` for 60% memory savings on serialization.
- **Correlation propagation**: `correlation_id` must be copied from the input envelope, never generated fresh mid-chain.

---

## Event Bus Protocol

The event bus is defined as a set of Protocol interfaces following the Interface Segregation Principle (ISP). Components depend only on the minimal interface they need.

### Protocol Hierarchy

| Protocol | Purpose | Methods |
|----------|---------|---------|
| `ProtocolEventBusPublisher` | Publish events | `publish()`, `publish_envelope()`, `broadcast_to_environment()`, `send_to_group()` |
| `ProtocolEventBusSubscriber` | Consume events | `subscribe()`, `start_consuming()` |
| `ProtocolEventBusLifecycle` | Start/stop bus | `start()`, `stop()`, `is_running()` |
| `ProtocolEventBus` | Full interface | Combines all three above |

**Import paths**:

```python
# Full interface (when you need everything)
from omnibase_core.protocols.event_bus import ProtocolEventBus

# Minimal interfaces (preferred -- follow ISP)
from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
from omnibase_core.protocols.event_bus import ProtocolEventBusSubscriber
from omnibase_core.protocols.event_bus import ProtocolEventBusLifecycle
```

### Publishing

```python
from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher


class HandlerOrderValidated:
    """Handler that publishes a validated-order event."""

    def __init__(self, publisher: ProtocolEventBusPublisher) -> None:
        self._publisher = publisher

    async def publish_validated(
        self, envelope: ModelEventEnvelope[object], topic: str
    ) -> None:
        await self._publisher.publish_envelope(envelope, topic)
```

### Subscribing

```python
from omnibase_core.protocols.event_bus import ProtocolEventBusSubscriber
from omnibase_core.protocols.event_bus.protocol_event_message import ProtocolEventMessage
from omnibase_core.protocols.event_bus.protocol_node_identity import ProtocolNodeIdentity


async def setup_subscription(
    subscriber: ProtocolEventBusSubscriber,
    identity: ProtocolNodeIdentity,
) -> None:
    async def on_message(msg: ProtocolEventMessage) -> None:
        # Process the incoming message
        pass

    unsubscribe = await subscriber.subscribe(
        topic="dev.orders.order-placed.v1",
        node_identity=identity,
        on_message=on_message,
    )

    # Later, to stop:
    # await unsubscribe()
```

### Resolving from Container

The event bus is resolved from `ModelONEXContainer` via protocol-based DI:

```python
# In a handler or service
event_bus = container.get_service(ProtocolEventBus)
publisher = container.get_service(ProtocolEventBusPublisher)
```

---

## Event Flow Patterns

### Unidirectional Flow

Events flow left to right through the four node types. Backwards dependencies are forbidden.

```text
EFFECT          COMPUTE          REDUCER          ORCHESTRATOR
(External I/O)  (Transform)      (State/FSM)      (Coordinate)
    |               |                |                 |
    |--raw data---->|                |                 |
    |               |--processed---->|                 |
    |               |                |--state+intents->|
    |               |                |                 |--events-->
    |<-----------intents routed back to effects--------|
```

### Canonical Execution Shapes

| Shape | Flow | Description |
|-------|------|-------------|
| EVENT_TO_REDUCER | Event -> Reducer -> (State, Intents) | Domain event triggers state transition |
| EVENT_TO_ORCHESTRATOR | Event -> Orchestrator -> (Events, Intents) | Event triggers workflow |
| INTENT_TO_EFFECT | Intent -> Effect -> Events | Side effect execution |
| COMMAND_TO_ORCHESTRATOR | Command -> Orchestrator -> (Events, Intents) | External command triggers workflow |
| COMMAND_TO_EFFECT | Command -> Effect -> Events | Direct I/O command |

---

## Event-to-Reducer Flow

Reducers are pure functions: `delta(state, event) -> (new_state, intents[])`. They receive domain events, compute new state, and emit intents for side effects.

### Flow Diagram

```text
                    +------------------+
                    |  ModelEventEnvelope  |
                    |  (domain event)   |
                    +--------+---------+
                             |
                             v
                    +--------+---------+
                    |    REDUCER        |
                    |  (pure function)  |
                    |                   |
                    |  state + event    |
                    |     --> new_state |
                    |     --> intents[] |
                    +--------+---------+
                             |
                    +--------+---------+
                    |                   |
                    v                   v
           +-------+------+   +--------+--------+
           |  New State   |   |  ModelIntent[]   |
           |  (immutable) |   |  (side effects)  |
           +--------------+   +---------+--------+
                                        |
                                        v
                              +---------+--------+
                              |  ORCHESTRATOR    |
                              |  routes intents  |
                              |  to EFFECT nodes |
                              +------------------+
```

### Implementation

```python
from omnibase_core.models.reducer.model_intent import ModelIntent


class HandlerOrderReducer:
    """Pure reduction handler."""

    def reduce(
        self,
        state: ModelOrderState,
        event: ModelEventEnvelope[object],
    ) -> tuple[ModelOrderState, tuple[ModelIntent, ...]]:
        trigger = str(event.event_type).split(".")[-1]
        event_id = event.envelope_id

        if state.is_duplicate_event(event_id):
            return state, ()  # Idempotent -- no change

        if trigger == "order_placed":
            new_state = state.with_order_placed(
                order_id=event.payload["order_id"],  # type: ignore[index]
                event_id=event_id,
            )
            intents = (
                ModelIntent(
                    intent_type="payment.process",
                    target="payment_service",
                    payload={"order_id": event.payload["order_id"]},  # type: ignore[index]
                    priority=1,
                ),
            )
            return new_state, intents

        return state, ()
```

---

## Event-to-Orchestrator Flow

Orchestrators receive events via handler routing (declared in contract YAML), coordinate workflows, and emit events and intents. They never return typed results.

### Flow Diagram

```text
                    +------------------+
                    |  ModelEventEnvelope  |
                    |  (trigger event)  |
                    +--------+---------+
                             |
                             v
                    +--------+---------+
                    |  ORCHESTRATOR    |
                    |  handler routing |
                    |  (contract.yaml) |
                    +--------+---------+
                             |
                    +--------+---------+
                    |                   |
                    v                   v
           +-------+------+   +--------+--------+
           |  Events[]    |   |  Intents[]      |
           |  (published  |   |  (routed to     |
           |  to bus)     |   |  effect nodes)  |
           +--------------+   +-----------------+
```

### Implementation

```python
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.reducer.model_intent import ModelIntent


class HandlerOrderWorkflow:
    """Orchestrator handler: emits events and intents, never results."""

    async def handle(
        self,
        event: ModelEventEnvelope[object],
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        # Emit a downstream event
        validated_event = ModelEventEnvelope(
            event_type="orders.order-validated.v1",
            payload=event.payload,
            correlation_id=correlation_id,
        )

        # Emit an intent for side effect execution
        payment_intent = ModelIntent(
            intent_type="payment.process",
            target="node_payment_effect",
            payload={"order_id": event.payload.get("order_id")},  # type: ignore[union-attr]
            priority=1,
        )

        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="orchestrator.order.workflow",
            events=(validated_event,),
            intents=(payment_intent,),
        )
```

---

## Intent Emission and Routing

Intents bridge reducers and effects. A reducer describes what side effects should happen (intents). The orchestrator routes those intents to the appropriate effect nodes for execution.

### Intent Model

**Import path**: `omnibase_core.models.reducer.model_intent.ModelIntent`

```python
from omnibase_core.models.reducer.model_intent import ModelIntent

intent = ModelIntent(
    intent_type="payment.process",        # Routing key
    target="node_payment_gateway_effect", # Target effect node
    payload={"order_id": "ORD-001"},      # Data for the effect
    priority=1,                           # 1 = highest priority
)
```

### Intent Routing Table (Contract YAML)

The orchestrator's contract declares how intents map to effect nodes:

```yaml
intent_consumption:
  intent_routing_table:
    "payment.process": "node_payment_gateway_effect"
    "fulfillment.start": "node_fulfillment_effect"
    "notification.send": "node_notification_effect"
```

### Execution by Effect Nodes

Effect nodes receive intents and execute the actual I/O:

```python
class HandlerIntentExecutor:
    """Effect handler that executes intents."""

    async def execute(
        self,
        intent: ModelIntent,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        if intent.intent_type == "payment.process":
            result = await self._payment_client.charge(intent.payload)

            event = ModelEventEnvelope(
                event_type="payment.charged",
                payload={"charge_id": result.id},
                correlation_id=correlation_id,
            )

            return ModelHandlerOutput.for_effect(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="effect.payment.executor",
                events=(event,),
            )
```

---

## Error Handling

### Dead Letter Queue (DLQ)

Events that fail processing after all retries are routed to a dead letter topic. DLQ events retain the original envelope with added error metadata for later inspection and reprocessing.

```text
+------------------+     retry 1..N     +------------------+
|  Original Event  | -----------------> |  Handler         |
+------------------+                    +--------+---------+
                                                 |
                                          failure after N retries
                                                 |
                                                 v
                                        +--------+---------+
                                        |  DLQ Topic       |
                                        |  (dead letter)   |
                                        +------------------+
```

**DLQ envelope structure**:

```python
dlq_envelope = ModelEventEnvelope(
    event_type="dlq.processing-failed",
    payload={
        "original_event": original_envelope.model_dump(),
        "error": str(exception),
        "error_type": type(exception).__name__,
        "retry_count": retry_count,
        "failed_handler": handler_id,
        "failed_at": datetime.now(UTC).isoformat(),
    },
    correlation_id=original_envelope.correlation_id,
)
```

### Retry with Exponential Backoff

Retry policies are declared in the contract YAML and applied by the runtime. Handlers do not implement retry logic themselves.

```yaml
# contract.yaml
error_handling:
  retry_policy:
    max_retries: 3
    exponential_base: 2
    initial_delay_ms: 1000
    max_delay_ms: 30000
    jitter: true
    retry_on:
      - "ConnectionError"
      - "TimeoutError"
```

**Retry schedule** (with exponential_base=2, initial_delay=1000ms):

| Attempt | Delay | Cumulative |
|---------|-------|------------|
| 1 | 1000ms | 1000ms |
| 2 | 2000ms | 3000ms |
| 3 | 4000ms | 7000ms |
| DLQ | -- | -- |

### Circuit Breaker

Circuit breakers prevent cascading failures when downstream services are unhealthy. Configured per-node in the contract.

```yaml
error_handling:
  circuit_breaker:
    enabled: true
    failure_threshold: 5        # Open after 5 consecutive failures
    reset_timeout_seconds: 60   # Try again after 60s
    half_open_max_calls: 1      # Allow 1 test call in half-open state
```

**State machine**:

```text
     CLOSED ----failure_threshold----> OPEN
        ^                                |
        |                          reset_timeout
        |                                |
        +---success--- HALF_OPEN <-------+
        |                  |
        +---failure--------+
```

When the circuit is OPEN, the handler returns a fallback or error immediately without attempting the operation. After `reset_timeout_seconds`, one test call is allowed (HALF_OPEN). If it succeeds, the circuit closes. If it fails, the circuit reopens.

### Error Propagation Rules

These rules are enforced by the error handling decorator:

| Exception Type | Behavior |
|---------------|----------|
| `SystemExit`, `KeyboardInterrupt`, `asyncio.CancelledError` | Always propagate (cancellation signals) |
| `ModelOnexError` | Re-raised as-is (preserves error code and context) |
| Other exceptions | Wrapped in `ModelOnexError` with context |

---

## Idempotency

Idempotency ensures that processing the same event multiple times produces the same result. This is critical for retry safety and at-least-once delivery guarantees.

### Event ID Tracking

The most common strategy: track processed `envelope_id` values in the state model.

```python
class ModelOrderState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: str = "idle"
    last_processed_event_id: UUID | None = None

    def is_duplicate_event(self, event_id: UUID) -> bool:
        """Idempotency check: was this event already processed?"""
        return self.last_processed_event_id == event_id
```

Usage in the reducer handler:

```python
def reduce(
    self,
    state: ModelOrderState,
    event: ModelEventEnvelope[object],
) -> tuple[ModelOrderState, tuple[ModelIntent, ...]]:
    if state.is_duplicate_event(event.envelope_id):
        return state, ()  # No-op on duplicate

    # Process normally...
```

### Idempotency for Effects

Effect nodes use idempotency keys in external calls:

```python
class HandlerPaymentEffect:
    async def charge(self, intent: ModelIntent) -> None:
        # Use the intent's correlation data as idempotency key
        await self._client.charge(
            amount=intent.payload["amount"],
            idempotency_key=f"{intent.payload['order_id']}-{intent.intent_type}",
        )
```

### Contract Declaration

```yaml
idempotency:
  enabled: true
  strategy: "event_id_tracking"
  description: "Track processed event IDs to prevent duplicate processing"
```

---

## Event Ordering

### Within a Partition

Events with the same partition key are guaranteed to be processed in order. Use meaningful keys:

```python
# Order events keyed by order_id -- all events for one order are ordered
await publisher.publish(
    topic="dev.orders.events.v1",
    key=f"order-{order_id}".encode(),
    value=envelope_bytes,
)
```

### Across Partitions

No ordering guarantee. Design handlers to be order-independent across different entities.

### Causal Ordering

Use `correlation_id` and `request_id` to reconstruct causal chains:

```python
# Event A triggers Event B
event_b = ModelEventEnvelope(
    event_type="orders.order-validated.v1",
    payload=validated_data,
    correlation_id=event_a.correlation_id,  # Same correlation chain
    request_id=event_a.request_id,          # Same request context
)
```

### Out-of-Order Handling

When events may arrive out of order, use guard conditions in the reducer:

```python
def reduce(self, state: ModelOrderState, trigger: str) -> ModelOrderState:
    # Guard: payment_confirmed only valid in "pending" state
    if trigger == "payment_confirmed" and state.status != "pending":
        return state  # Ignore out-of-order event

    # Process normally...
```

---

## Backpressure

### Consumer-Side Backpressure

Control processing rate at the consumer level:

**Bounded concurrency**: Limit the number of events processed concurrently.

```yaml
# contract.yaml
consumer_config:
  max_concurrent_handlers: 10
  max_poll_records: 100
  poll_interval_ms: 500
```

**Rate limiting**: Declare maximum throughput in the contract.

```yaml
consumer_config:
  rate_limit:
    max_events_per_second: 1000
    burst_size: 50
```

### Producer-Side Backpressure

When the event bus is slow:

1. **Buffering**: The producer buffers events locally until the bus accepts them.
2. **Timeout**: If the buffer is full, publish calls fail with a timeout error.
3. **Monitoring**: The event bus exposes metrics for buffer depth and publish latency.

```python
# QoS fields on the envelope control producer behavior
envelope = ModelEventEnvelope(
    payload=data,
    event_type="high-volume.events.v1",
    priority=3,           # Lower priority can be shed under load
    timeout_seconds=10,   # Fail fast if bus is unresponsive
)
```

### Load Shedding

Under extreme load, low-priority events can be dropped:

| Priority | Behavior Under Load |
|----------|-------------------|
| 8-10 | Always delivered (critical) |
| 5-7 | Queued with bounded buffer |
| 1-4 | May be shed under extreme backpressure |

---

## Testing Event-Driven Code

### Testing Event Publishing

```python
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_publishes_event() -> None:
    # Arrange -- mock the publisher
    mock_publisher = AsyncMock()

    handler = HandlerOrderValidated(publisher=mock_publisher)

    envelope = ModelEventEnvelope(
        event_type="orders.order-placed.v1",
        payload={"order_id": "ORD-001"},
        correlation_id=uuid4(),
    )

    # Act
    await handler.publish_validated(
        envelope=envelope,
        topic="dev.orders.order-validated.v1",
    )

    # Assert
    mock_publisher.publish_envelope.assert_called_once()
    published_envelope = mock_publisher.publish_envelope.call_args[0][0]
    assert published_envelope.correlation_id == envelope.correlation_id
```

### Testing Reducer Idempotency

```python
@pytest.mark.unit
def test_duplicate_event_is_idempotent() -> None:
    handler = HandlerOrderReducer()
    event_id = uuid4()

    state = ModelOrderState(
        status="pending",
        order_id="ORD-001",
        last_processed_event_id=event_id,
    )

    envelope = ModelEventEnvelope(
        event_type="orders.payment-confirmed.v1",
        payload={},
        envelope_id=event_id,  # Same ID as already processed
    )

    new_state, intents = handler.reduce(state, envelope)

    # No change -- idempotent
    assert new_state.status == "pending"
    assert intents == ()
```

### Testing Intent Emission

```python
@pytest.mark.unit
def test_reducer_emits_payment_intent() -> None:
    handler = HandlerOrderReducer()
    state = ModelOrderState(status="idle")

    envelope = ModelEventEnvelope(
        event_type="orders.order-placed.v1",
        payload={"order_id": "ORD-001"},
        correlation_id=uuid4(),
    )

    new_state, intents = handler.reduce(state, envelope)

    assert new_state.status == "pending"
    assert len(intents) == 1
    assert intents[0].intent_type == "payment.process"
    assert intents[0].target == "payment_service"
    assert intents[0].payload["order_id"] == "ORD-001"
```

### Testing Orchestrator Output Constraints

```python
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_node_kind import EnumNodeKind


@pytest.mark.unit
def test_orchestrator_cannot_return_result() -> None:
    """Verify ModelHandlerOutput rejects result for ORCHESTRATOR."""
    with pytest.raises(ModelOnexError, match="ORCHESTRATOR cannot set result"):
        ModelHandlerOutput(
            node_kind=EnumNodeKind.ORCHESTRATOR,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="orchestrator.test",
            result={"status": "done"},  # Forbidden for ORCHESTRATOR
        )
```

### Testing with Mock Event Bus

```python
class MockEventBus:
    """Test double for ProtocolEventBus."""

    def __init__(self) -> None:
        self.published: list[tuple[ModelEventEnvelope, str]] = []
        self.subscriptions: dict[str, list] = {}

    async def publish_envelope(
        self, envelope: ModelEventEnvelope, topic: str
    ) -> None:
        self.published.append((envelope, topic))

    async def subscribe(self, topic, identity, on_message, **kwargs):
        self.subscriptions.setdefault(topic, []).append(on_message)
        async def unsubscribe():
            self.subscriptions[topic].remove(on_message)
        return unsubscribe


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    return MockEventBus()
```

---

## Summary

| Concept | Implementation | Key Class |
|---------|---------------|-----------|
| Event wrapping | Generic envelope with metadata | `ModelEventEnvelope[T]` |
| Event publishing | ISP-compliant protocol | `ProtocolEventBusPublisher` |
| Event subscribing | ISP-compliant protocol | `ProtocolEventBusSubscriber` |
| Full bus interface | Composed protocol | `ProtocolEventBus` |
| Side effect description | Emitted by reducers | `ModelIntent` |
| Handler output | Enforced per node kind | `ModelHandlerOutput[T]` |
| Correlation tracking | Propagated through chains | `correlation_id` on envelope |
| Idempotency | Event ID tracking in state | `is_duplicate_event()` |
| Retry | Contract-declared, runtime-applied | `error_handling.retry_policy` |
| Circuit breaker | Contract-declared, runtime-applied | `error_handling.circuit_breaker` |
| DLQ | Failed events after max retries | DLQ topic with error metadata |

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Canonical Execution Shapes](../architecture/CANONICAL_EXECUTION_SHAPES.md)
- [Node Archetypes Reference](../reference/node-archetypes.md)
- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
- [ORCHESTRATOR Node Tutorial](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md)
- [Anti-Patterns](./ANTI_PATTERNS.md)
- [Model Intent Architecture](../architecture/MODEL_INTENT_ARCHITECTURE.md)

---

## Document Metadata

- **Version**: 2.0.0
- **Last Updated**: 2026-02-14
- **Maintainer**: ONEX Core Team
- **Status**: Complete
