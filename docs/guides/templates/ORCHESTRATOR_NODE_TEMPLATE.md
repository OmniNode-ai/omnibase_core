> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > Templates > ORCHESTRATOR Node

# ORCHESTRATOR Node Template

## Overview

Template for building ONEX ORCHESTRATOR nodes. ORCHESTRATOR nodes coordinate **workflows** by routing events to handlers and managing multi-step execution. They are the **only** node type that publishes events to the message bus.

**Architectural invariants**:

- Nodes are thin shells -- only `__init__` calling `super().__init__(container)`
- Handlers own ALL business logic
- YAML contracts define behavior
- ORCHESTRATOR nodes emit `events[]` and `intents[]` via `ModelHandlerOutput.for_orchestrator(events=[], intents=[])`
- **ORCHESTRATOR nodes CANNOT return `result`** -- this is enforced at runtime and will raise `ModelOnexError`
- Only COMPUTE nodes return typed results

## When to Use

- Multi-handler workflows
- Event coordination
- Publishing events to the message bus (ONLY orchestrators can publish)
- Routing intents to effect nodes
- Parallel execution coordination

## Directory Structure

```
nodes/node_order_workflow_orchestrator/
    contract.yaml                  # ONEX contract (required)
    node.py                        # Thin node shell (required)
    handlers/
        handler_order_placed.py    # Business logic lives here
        handler_order_fulfilled.py
    models/
        __init__.py
        model_order_event.py
```

## Template Files

### 1. YAML Contract (`contract.yaml`)

The contract is the **single source of truth** for node behavior.

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_order_workflow_orchestrator"
node_type: "ORCHESTRATOR_GENERIC"
description: "Coordinates the order processing workflow."

input_model:
  name: "ModelOrchestratorInput"
  module: "omnibase_core.models.orchestrator.model_orchestrator_input"

output_model:
  name: "ModelOrchestratorOutput"
  module: "omnibase_core.models.orchestrator"

# Workflow definition with execution graph
workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: "order_processing_workflow"
      workflow_version: { major: 1, minor: 0, patch: 0 }
      description: "End-to-end order processing"

    execution_graph:
      nodes:
        - node_id: "receive_order"
          node_type: EFFECT_GENERIC
          description: "Receive order event"
          step_config:
            event_pattern: ["order-placed.*"]

        - node_id: "validate_order"
          node_type: COMPUTE_GENERIC
          depends_on: ["receive_order"]
          description: "Validate order data"

        - node_id: "compute_state"
          node_type: REDUCER_GENERIC
          depends_on: ["validate_order"]
          description: "FSM transition and intent computation"

        - node_id: "process_payment"
          node_type: EFFECT_GENERIC
          depends_on: ["compute_state"]
          description: "Process payment"
          step_config:
            intent_filter: "payment.*"

    coordination_rules:
      execution_mode: sequential
      failure_recovery_strategy: retry
      max_retries: 3
      timeout_ms: 30000

# Handler routing (event -> handler mapping)
handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - event_model:
        name: "ModelOrderPlacedEvent"
        module: "myapp.models.events"
      handler:
        name: "HandlerOrderPlaced"
        module: "myapp.nodes.node_order_workflow_orchestrator.handlers.handler_order_placed"
      output_events:
        - "ModelOrderValidated"

    - event_model:
        name: "ModelOrderFulfilledEvent"
        module: "myapp.models.events"
      handler:
        name: "HandlerOrderFulfilled"
        module: "myapp.nodes.node_order_workflow_orchestrator.handlers.handler_order_fulfilled"
      output_events:
        - "ModelOrderCompleted"

# Events published to message bus
published_events:
  - topic: "{env}.{namespace}.orders.evt.order-validated.v1"
    event_type: "OrderValidated"
  - topic: "{env}.{namespace}.orders.evt.order-completed.v1"
    event_type: "OrderCompleted"

# Intent routing to effect nodes
intent_consumption:
  intent_routing_table:
    "payment.process": "node_payment_effect"
    "fulfillment.start": "node_fulfillment_effect"
```

### 2. Node Implementation (`node.py`)

The node is a **thin coordination shell**. No business logic here. No `process()` override. No private methods. No state tracking.

```python
"""Order workflow orchestrator for coordinating order processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrderWorkflowOrchestrator(NodeOrchestrator):
    """Declarative orchestrator for order processing workflow.

    All behavior is defined in contract.yaml -- no custom logic here.
    Handler routing is driven entirely by the contract.

    Workflow:
        1. Receive order event
        2. Validate order data (via compute handler)
        3. Call reducer to compute intents
        4. Execute payment intent via effect node
        5. Publish completion event

    CRITICAL: Orchestrators CANNOT return result.
    They emit events[] and intents[] only.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize with container dependency injection."""
        super().__init__(container)


__all__ = ["NodeOrderWorkflowOrchestrator"]
```

### 3. Handler Implementation (`handlers/handler_order_placed.py`)

All business logic lives in the handler. The handler emits events and intents -- never a typed result.

```python
"""Handler for order-placed events in the order workflow orchestrator."""

from __future__ import annotations

from typing import Any

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


class HandlerOrderPlaced:
    """Handler for processing order-placed events.

    This handler validates the order and emits:
    - Events describing what happened (order validated)
    - Intents requesting side effects (payment processing)

    It NEVER returns a typed result -- that is only for COMPUTE handlers.
    """

    async def handle(
        self,
        event: dict[str, Any],
    ) -> ModelHandlerOutput:
        """Process an order-placed event.

        Args:
            event: The order-placed event payload.

        Returns:
            ModelHandlerOutput with events and intents. No result.
        """
        order_id = event.get("order_id")
        customer_id = event.get("customer_id")
        items = event.get("items", [])

        # Validate order data
        if not order_id or not items:
            return ModelHandlerOutput.for_orchestrator(
                input_envelope_id=input_envelope_id,  # from handler args
                correlation_id=correlation_id,         # from handler args
                events=[
                    {
                        "event_type": "order.validation_failed",
                        "order_id": order_id,
                        "reason": "Missing order_id or items",
                    }
                ],
                intents=[],
            )

        total = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)

        # Emit events (what happened) and intents (what should happen next)
        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,  # from handler args
            correlation_id=correlation_id,         # from handler args
            events=[
                {
                    "event_type": "order.validated",
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "total": total,
                }
            ],
            intents=[
                {
                    "intent_type": "payment.process",
                    "target_pattern": f"payment://orders/{order_id}",
                    "payload": {
                        "order_id": order_id,
                        "amount": total,
                        "customer_id": customer_id,
                    },
                }
            ],
        )
```

### 4. Another Handler (`handlers/handler_order_fulfilled.py`)

```python
"""Handler for order-fulfilled events in the order workflow orchestrator."""

from __future__ import annotations

from typing import Any

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


class HandlerOrderFulfilled:
    """Handler for processing order-fulfilled events.

    Emits a completion event. No result field -- orchestrators
    coordinate via events and intents only.
    """

    async def handle(
        self,
        event: dict[str, Any],
    ) -> ModelHandlerOutput:
        """Process an order-fulfilled event.

        Args:
            event: The order-fulfilled event payload.

        Returns:
            ModelHandlerOutput with completion events. No result.
        """
        order_id = event.get("order_id")

        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,  # from handler args
            correlation_id=correlation_id,         # from handler args
            events=[
                {
                    "event_type": "order.completed",
                    "order_id": order_id,
                }
            ],
            intents=[],  # No further side effects needed
        )
```

## Output Constraints

ORCHESTRATOR nodes coordinate workflows via events and intents. They **CANNOT** return a typed result.

| Field | ORCHESTRATOR |
|-------|--------------|
| `events[]` | Allowed |
| `intents[]` | Allowed |
| `result` | **Forbidden** (raises `ModelOnexError`) |
| `projections[]` | Forbidden |

```python
# CORRECT -- orchestrator emits events and intents
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=input_envelope_id,  # from handler args
    correlation_id=correlation_id,         # from handler args
    events=[{"event_type": "order.validated", "order_id": "o123"}],
    intents=[{"intent_type": "payment.process", "payload": {...}}],
)

# WRONG -- orchestrator CANNOT return result (raises ModelOnexError)
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=input_envelope_id,
    correlation_id=correlation_id,
    result={"status": "done"},  # ModelOnexError!
)
# Raises: ModelOnexError: ORCHESTRATOR cannot set result - use events[] and intents[] only.

# WRONG -- orchestrator CANNOT emit projections (raises ModelOnexError)
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=input_envelope_id,
    correlation_id=correlation_id,
    projections=[some_projection],  # ModelOnexError!
)
```

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: Business logic in the node

```python
# WRONG -- ~15 methods of business logic in the node
class NodeMyOrchestrator(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self._step_executor = StepExecutor()      # NO
        self._recovery_handler = RecoveryHandler() # NO
        self._active_workflows = {}                # NO

    async def process(self, input_data):          # NO -- don't override
        await self._validate_workflow_input(...)   # NO
        order = self._resolve_execution_order(...) # NO
        ...

# CORRECT -- thin shell, all logic in handlers
class NodeMyOrchestrator(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

### Anti-Pattern 2: Returning a typed result

```python
# WRONG -- _create_timeout_output returns a typed result object
def _create_timeout_output(self, input_data):
    return ModelOrchestratorOutput(
        execution_status="failed",     # This is a typed result!
        execution_time_ms=...,
    )

# CORRECT -- emit a failure event instead
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=input_envelope_id,  # from handler args
    correlation_id=correlation_id,         # from handler args
    events=[{
        "event_type": "workflow.timeout",
        "workflow_id": str(workflow_id),
    }],
    intents=[],
)
```

### Anti-Pattern 3: Direct handler instantiation

```python
# WRONG -- never instantiate handlers directly
self._step_executor = StepExecutor()

# CORRECT -- handlers are resolved via the container/registry
# based on the contract's handler_routing configuration.
```

## Key Principles

1. **Node is a thin shell**: Only `__init__` calling `super().__init__(container)`. No `process()` override. No private methods. No state.
2. **Handler owns logic**: All workflow coordination logic lives in handler classes.
3. **NO result field**: Orchestrators emit events (what happened) and intents (what should happen next). Only COMPUTE nodes return results.
4. **Contract drives behavior**: Workflow definitions, handler routing, event publishing, and intent routing are all in YAML.
5. **Only orchestrators publish events**: To the message bus. Other node types return events to the orchestrator.
6. **PEP 604 types**: Use `X | None` not `Optional[X]`, `list[str]` not `List[str]`.
7. **Pydantic v2**: Use `model_config = ConfigDict(...)` not `class Config:`. Use `pattern=` not `regex=`.
8. **`ModelONEXContainer`**: Always use `ModelONEXContainer` for DI, never `ModelContainer`.
9. **No backwards compatibility**: This repo has no external consumers.

## Testing

```python
"""Tests for the order workflow orchestrator handlers."""

import pytest

from myapp.nodes.node_order_workflow_orchestrator.handlers.handler_order_placed import (
    HandlerOrderPlaced,
)


@pytest.mark.unit
class TestHandlerOrderPlaced:
    """Test the handler directly -- not the node."""

    async def test_valid_order_emits_events_and_intents(self) -> None:
        handler = HandlerOrderPlaced()
        result = await handler.handle({
            "order_id": "o1",
            "customer_id": "c1",
            "items": [{"price": 10.0, "quantity": 2}],
        })

        # Orchestrator output has events and intents, never result
        assert result.result is None
        assert len(result.events) == 1
        assert result.events[0]["event_type"] == "order.validated"
        assert len(result.intents) == 1
        assert result.intents[0]["intent_type"] == "payment.process"

    async def test_missing_items_emits_failure_event(self) -> None:
        handler = HandlerOrderPlaced()
        result = await handler.handle({"order_id": "o1"})

        assert result.result is None
        assert result.events[0]["event_type"] == "order.validation_failed"
        assert result.intents == []
```

## Related Documentation

| Topic | Document |
|-------|----------|
| Node archetypes reference | [Node Archetypes](../../reference/node-archetypes.md) |
| Handler contract guide | [Handler Contract Guide](../../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Four-node architecture | [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Execution shapes | [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) |
| Container types | [Container Types](../../architecture/CONTAINER_TYPES.md) |
| Coding standards | [CLAUDE.md](../../../CLAUDE.md) |
