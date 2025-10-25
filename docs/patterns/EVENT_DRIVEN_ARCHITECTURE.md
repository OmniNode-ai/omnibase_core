# Event-Driven Architecture - omnibase_core

**Status**: ✅ Available

## Overview

Event-driven architecture patterns for ONEX services using ModelEventEnvelope and Intent emission.

## Core Concepts

### Event Envelope Pattern

All events use `ModelEventEnvelope` for consistent communication:

```python
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope

envelope = ModelEventEnvelope(
    event_type="DATA_PROCESSED",
    payload={"result": data},
    metadata={"source": "node_compute", "timestamp": datetime.now()},
    correlation_id=UUID("...")
)
```

### Intent Emission Pattern (REDUCER)

REDUCER nodes emit Intents instead of performing side effects:

```python
def reduce_state(
    state: ModelState,
    action: ModelAction
) -> Tuple[ModelState, List[ModelIntent]]:
    """Pure FSM - emit Intents for side effects."""

    new_state = state.model_copy(deep=True)
    new_state.value += action.payload['delta']

    # Emit Intent for side effect
    intents = [
        ModelIntent(
            intent_type="NOTIFY",
            payload={"change": action.payload['delta']}
        )
    ]

    return new_state, intents
```

## Event Flow Patterns

### Pattern 1: Request-Response

```
┌─────────┐     event      ┌─────────┐     event      ┌─────────┐
│ Client  │ ──────────────> │  Node   │ ──────────────> │ Client  │
└─────────┘                 └─────────┘                 └─────────┘
```

### Pattern 2: Publish-Subscribe

```
┌─────────┐                 ┌─────────────┐
│Publisher│ ───────────────>│  Event Bus  │
└─────────┘                 └──────┬──────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    v              v              v
             ┌──────────┐   ┌──────────┐   ┌──────────┐
             │Subscriber│   │Subscriber│   │Subscriber│
             └──────────┘   └──────────┘   └──────────┘
```

### Pattern 3: Intent → Action Flow (Pure FSM)

```
┌─────────┐   Action   ┌─────────┐  Intents  ┌────────┐
│Orchestr │ ─────────> │ Reducer │ ────────> │ Effect │
└─────────┘            └─────────┘           └────────┘
                            │
                            v
                     New State (Pure)
```

## Implementation Patterns

### Event Publishing

```python
class MyNode(NodeComputeService):
    async def process(self, data: dict) -> dict:
        # Process data
        result = await self.compute(data)

        # Publish event
        event = ModelEventEnvelope(
            event_type="COMPUTATION_COMPLETE",
            payload={"result": result},
            correlation_id=self.correlation_id
        )

        event_bus = self.container.get_service("ProtocolEventBus")
        await event_bus.publish(event)

        return result
```

### Event Subscription

```python
class MyNode(NodeEffectService):
    async def initialize(self):
        event_bus = self.container.get_service("ProtocolEventBus")

        # Subscribe to events
        await event_bus.subscribe(
            event_type="COMPUTATION_COMPLETE",
            handler=self.handle_computation_complete
        )

    async def handle_computation_complete(
        self,
        envelope: ModelEventEnvelope
    ):
        """Handle computation complete event."""
        result = envelope.payload["result"]
        await self.save_result(result)
```

### Intent Execution

```python
class MyEffectNode(NodeEffectService):
    async def execute_intent(self, intent: ModelIntent):
        """Execute Intent from REDUCER."""

        match intent.intent_type:
            case "NOTIFY":
                await self.send_notification(intent.payload)
            case "PERSIST":
                await self.save_data(intent.payload)
            case "EXTERNAL_API":
                await self.call_api(intent.payload)
```

## Benefits

1. **Loose Coupling**: Components don't know about each other
2. **Scalability**: Easy to add new event handlers
3. **Testability**: Events can be mocked
4. **Pure Functions**: REDUCER remains pure (no side effects)
5. **Traceability**: Correlation IDs track event chains

## Best Practices

### 1. Use Correlation IDs

```python
envelope = ModelEventEnvelope(
    event_type="DATA_PROCESSED",
    payload=data,
    correlation_id=incoming_request.correlation_id  # Propagate
)
```

### 2. Type-Safe Event Types

```python
class EnumEventType(str, Enum):
    DATA_PROCESSED = "data_processed"
    ERROR_OCCURRED = "error_occurred"
    STATE_CHANGED = "state_changed"

# Use enum instead of string
envelope = ModelEventEnvelope(
    event_type=EnumEventType.DATA_PROCESSED,
    payload=data
)
```

### 3. Structured Event Payloads

```python
# ❌ Bad: Unstructured payload
payload = {"data": "something", "other": 123}

# ✅ Good: Pydantic model
class DataProcessedPayload(BaseModel):
    result: str
    metrics: dict

payload = DataProcessedPayload(result="success", metrics={...})
```

## Testing Event-Driven Code

```python
@pytest.mark.asyncio
async def test_event_publishing():
    # Arrange
    mock_event_bus = MockEventBus()
    container = create_test_container()
    container.register_service("ProtocolEventBus", mock_event_bus)

    node = MyNode(container)

    # Act
    await node.process({"value": 42})

    # Assert
    assert len(mock_event_bus.published_events) == 1
    assert mock_event_bus.published_events[0].event_type == "COMPUTATION_COMPLETE"
```

## Next Steps

- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
- [ORCHESTRATOR Node Tutorial](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)
- [Model Action Architecture](../architecture/MODEL_ACTION_ARCHITECTURE.md)

---

**Related Documentation**:
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Testing Guide](../guides/TESTING_GUIDE.md)
