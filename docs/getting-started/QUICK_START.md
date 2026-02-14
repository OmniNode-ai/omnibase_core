> **Navigation**: [Home](../INDEX.md) > Getting Started > Quick Start

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Quick Start Guide

**Estimated Time**: 10 minutes

## The ONEX Pattern in 30 Seconds

Every ONEX node follows the same three-part pattern:

1. **YAML contract** -- declares what the node does, its I/O models, and its handler
2. **Handler** -- owns all business logic, returns `ModelHandlerOutput`
3. **Thin node shell** -- inherits from a base class, contains zero business logic

This guide shows all four node kinds using this pattern.

## Prerequisites

- [Installation completed](installation.md)
- Python 3.12+

## Output Constraints

Every handler returns `ModelHandlerOutput`, which enforces these constraints at runtime:

| Kind | Allowed | Forbidden |
|------|---------|-----------|
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |

Violations raise `ModelOnexError` at construction time. The builder methods (`for_compute`, `for_effect`, `for_reducer`, `for_orchestrator`) enforce these automatically.

---

## COMPUTE -- Pure Transformation

COMPUTE nodes perform deterministic transformations with no side effects. Same input always produces the same output.

**When to use**: Data validation, format conversion, calculations, parsing, business rule evaluation.

### contract.yaml

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_text_normalizer"
node_type: "COMPUTE_GENERIC"
description: "Normalizes text by trimming whitespace and lowercasing."

input_model:
  name: "ModelNormalizerInput"
  module: "myapp.nodes.node_text_normalizer.models.model_normalizer_input"

output_model:
  name: "ModelNormalizerOutput"
  module: "myapp.nodes.node_text_normalizer.models.model_normalizer_output"

capabilities:
  - name: "text.normalization"

handler:
  path: "myapp.nodes.node_text_normalizer.handlers.handler_normalizer:handle_normalize"
```

### Models

```python
# models/model_normalizer_input.py
"""Input model for text normalization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNormalizerInput(BaseModel):
    """Text normalization input."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    text: str = Field(description="Raw text to normalize")
```

```python
# models/model_normalizer_output.py
"""Output model for text normalization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNormalizerOutput(BaseModel):
    """Text normalization result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    normalized: str = Field(description="Normalized text")
    original_length: int = Field(description="Length of original text")
    normalized_length: int = Field(description="Length after normalization")
```

### Handler (business logic)

```python
# handlers/handler_normalizer.py
"""Handler for text normalization."""

from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

from myapp.nodes.node_text_normalizer.models.model_normalizer_input import (
    ModelNormalizerInput,
)
from myapp.nodes.node_text_normalizer.models.model_normalizer_output import (
    ModelNormalizerOutput,
)


def handle_normalize(
    input_data: ModelNormalizerInput,
    *,
    input_envelope_id: UUID,
    correlation_id: UUID,
) -> ModelHandlerOutput[ModelNormalizerOutput]:
    """Normalize text by trimming and lowercasing.

    Pure function -- no I/O, no state, deterministic.
    """
    normalized = input_data.text.strip().lower()

    result = ModelNormalizerOutput(
        normalized=normalized,
        original_length=len(input_data.text),
        normalized_length=len(normalized),
    )

    # COMPUTE MUST return result. Cannot emit events, intents, or projections.
    return ModelHandlerOutput.for_compute(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="compute.text.normalizer",
        result=result,
    )
```

### Node shell (thin -- no logic)

```python
# node.py
"""Text normalizer compute node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeTextNormalizer(NodeCompute):
    """Text normalizer - COMPUTE_GENERIC node.

    All logic in handler_normalizer:handle_normalize.
    Behavior defined by contract.yaml.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


__all__ = ["NodeTextNormalizer"]
```

---

## EFFECT -- External I/O

EFFECT nodes handle interactions with systems outside the ONEX runtime: databases, APIs, file systems, message queues.

**When to use**: Database operations, HTTP calls, file read/write, message publishing, service discovery.

### contract.yaml

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_user_storage_effect"
node_type: "EFFECT_GENERIC"
description: "Stores user records to the database."

input_model:
  name: "ModelStorageRequest"
  module: "myapp.nodes.node_user_storage_effect.models.model_storage_request"

output_model:
  name: "ModelStorageResult"
  module: "myapp.nodes.node_user_storage_effect.models.model_storage_result"

capabilities:
  - name: "user.storage"
    description: "Persist and query user records"

handler:
  path: "myapp.nodes.node_user_storage_effect.handlers.handler_storage:handle_store_user"

error_handling:
  retry_policy:
    max_retries: 3
    exponential_base: 2
    retry_on:
      - "ConnectionError"
      - "TimeoutError"
```

### Handler (business logic)

```python
# handlers/handler_storage.py
"""Handler for user storage effect."""

from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

from myapp.nodes.node_user_storage_effect.models.model_storage_request import (
    ModelStorageRequest,
)


async def handle_store_user(
    input_data: ModelStorageRequest,
    *,
    input_envelope_id: UUID,
    correlation_id: UUID,
) -> ModelHandlerOutput[None]:
    """Store a user record in the database.

    Side-effecting: performs actual database write.
    Publishes a user_stored event on success.
    """
    # Perform the database write (side effect)
    # db = await get_connection()
    # await db.execute("INSERT INTO users ...", input_data.user_id, input_data.name)

    # Create a "user stored" event envelope (simplified)
    user_stored_event = {
        "event_type": "user.stored",
        "user_id": input_data.user_id,
    }

    # EFFECT can emit events[], but NOT intents, projections, or result.
    return ModelHandlerOutput.for_effect(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="effect.user.storage",
        events=(user_stored_event,),
    )
```

### Node shell (thin -- no logic)

```python
# node.py
"""User storage effect node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeUserStorageEffect(NodeEffect):
    """User storage - EFFECT_GENERIC node.

    All logic in handler_storage:handle_store_user.
    Behavior defined by contract.yaml.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


__all__ = ["NodeUserStorageEffect"]
```

---

## REDUCER -- State Aggregation

REDUCER nodes manage state via FSM (finite state machine) transitions. They are pure fold functions: `reduce(state, event) -> (new_state, projections)`. No I/O.

**When to use**: Workflow state tracking, event sourcing, multi-step process management, data aggregation.

### contract.yaml

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_order_reducer"
node_type: "REDUCER_GENERIC"
description: "Tracks order state transitions via FSM."

input_model:
  name: "ModelReducerInput"
  module: "omnibase_core.models.reducer.model_reducer_input"

output_model:
  name: "ModelReducerOutput"
  module: "omnibase_core.models.reducer.model_reducer_output"

handler:
  path: "myapp.nodes.node_order_reducer.handlers.handler_order_state:handle_order_event"

state_machine:
  state_machine_name: "order_fsm"
  initial_state: "pending"

  states:
    - state_name: "pending"
      description: "Awaiting payment"
    - state_name: "confirmed"
      description: "Payment confirmed"
    - state_name: "completed"
      description: "Order fulfilled"
      is_terminal: true
    - state_name: "failed"
      description: "Order failed"
      is_terminal: true

  transitions:
    - from_state: "pending"
      to_state: "confirmed"
      trigger: "payment_received"
    - from_state: "confirmed"
      to_state: "completed"
      trigger: "order_fulfilled"
    - from_state: "*"
      to_state: "failed"
      trigger: "error_occurred"
```

### Handler (business logic)

```python
# handlers/handler_order_state.py
"""Handler for order state reduction."""

from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


def handle_order_event(
    state: dict[str, str],
    event: dict[str, str],
    *,
    input_envelope_id: UUID,
    correlation_id: UUID,
) -> ModelHandlerOutput[None]:
    """Reduce an order event into a state projection.

    Pure function: delta(state, event) -> (new_state, projections).
    No I/O, no side effects.
    """
    trigger = event.get("trigger", "")
    current_status = state.get("status", "pending")

    # FSM transition logic (driven by contract state_machine definition)
    new_status = current_status
    if trigger == "payment_received" and current_status == "pending":
        new_status = "confirmed"
    elif trigger == "order_fulfilled" and current_status == "confirmed":
        new_status = "completed"
    elif trigger == "error_occurred":
        new_status = "failed"

    projection = {
        "order_id": event.get("order_id"),
        "previous_status": current_status,
        "new_status": new_status,
    }

    # REDUCER can emit projections[], but NOT events, intents, or result.
    return ModelHandlerOutput.for_reducer(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="reducer.order.state",
        projections=(projection,),
    )
```

### Node shell (thin -- no logic)

```python
# node.py
"""Order state reducer node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeReducer

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrderReducer(NodeReducer):
    """Order state reducer - REDUCER_GENERIC node.

    FSM-driven state transitions defined in contract.yaml.
    All logic in handler_order_state:handle_order_event.

    Pattern: reduce(state, event) -> (new_state, projections)
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


__all__ = ["NodeOrderReducer"]
```

---

## ORCHESTRATOR -- Workflow Coordination

ORCHESTRATOR nodes coordinate multi-step workflows. They emit events and intents but never return typed results. Only orchestrators can publish events to the message bus.

**When to use**: Multi-handler workflows, event coordination, routing intents to effects, parallel execution.

### contract.yaml

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

handler:
  path: "myapp.nodes.node_order_workflow.handlers.handler_workflow:handle_order_workflow"

workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: "order_processing"
      workflow_version: { major: 1, minor: 0, patch: 0 }
    execution_graph:
      nodes:
        - node_id: "validate"
          node_type: COMPUTE_GENERIC
          description: "Validate order data"
        - node_id: "reduce_state"
          node_type: REDUCER_GENERIC
          depends_on: ["validate"]
          description: "Update FSM state"
        - node_id: "process_payment"
          node_type: EFFECT_GENERIC
          depends_on: ["reduce_state"]
          description: "Execute payment"

intent_consumption:
  intent_routing_table:
    "payment.process": "node_payment_effect"
    "fulfillment.start": "node_fulfillment_effect"
```

### Handler (business logic)

```python
# handlers/handler_workflow.py
"""Handler for order workflow orchestration."""

from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


def handle_order_workflow(
    event: dict[str, str],
    *,
    input_envelope_id: UUID,
    correlation_id: UUID,
) -> ModelHandlerOutput[None]:
    """Coordinate the order processing workflow.

    Orchestrators emit events and intents but NEVER return results.
    """
    order_id = event.get("order_id", "unknown")

    # Emit an event recording what happened
    order_received_event = {
        "event_type": "order.received",
        "order_id": order_id,
    }

    # Emit an intent requesting a side effect (payment processing)
    payment_intent = {
        "intent_type": "payment.process",
        "target": f"payment://orders/{order_id}",
        "order_id": order_id,
    }

    # ORCHESTRATOR can emit events[] and intents[],
    # but NOT projections or result.
    return ModelHandlerOutput.for_orchestrator(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="orchestrator.order.workflow",
        events=(order_received_event,),
        intents=(payment_intent,),
    )
```

### Node shell (thin -- no logic)

```python
# node.py
"""Order workflow orchestrator node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrderWorkflowOrchestrator(NodeOrchestrator):
    """Order workflow - ORCHESTRATOR_GENERIC node.

    Coordinates multi-step order processing.
    All logic in handler_workflow:handle_order_workflow.

    Only orchestrators can publish events to the message bus.
    Cannot return typed results -- use events[] and intents[] only.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


__all__ = ["NodeOrderWorkflowOrchestrator"]
```

---

## Data Flow Direction

Data flows unidirectionally through the four node types:

```
EFFECT          COMPUTE          REDUCER          ORCHESTRATOR
(External I/O)  (Transform)      (State/FSM)      (Coordinate)
    |               |                |                  |
    | Raw Data      | Processed      | Aggregated       | Events +
    +-------->------+------->--------+-------->---------+ Intents
```

- **EFFECT** ingests external data, emits events
- **COMPUTE** transforms data, returns typed results
- **REDUCER** aggregates state, emits projections
- **ORCHESTRATOR** coordinates the workflow, emits events and intents

No backwards dependencies are allowed.

---

## Common Anti-Patterns to Avoid

| Anti-Pattern | Why It Is Wrong | Correct Pattern |
|---|---|---|
| `async def process(self, input_data: Dict[str, Any])` in node | Business logic in node, untyped signature | Handler function with typed Pydantic models |
| `class MyNode(NodeCompute): def _do_work(self)` | Business logic in node | Move `_do_work` to a handler file |
| `from typing import Optional, Dict, List` | Deprecated typing imports | `X \| None`, `dict[str, Any]`, `list[str]` |
| `def __init__(self, container): super().__init__(container); self.cache = {}` | State in node | Nodes are stateless; use protocol injection |
| No `contract.yaml` | Missing source of truth | Always start with the YAML contract |
| Returning `dict` from handler | Untyped, no constraint enforcement | Return `ModelHandlerOutput.for_*(...)` |
| `ModelContainer` | Wrong container type | `ModelONEXContainer` |
| `pip install` or `python script.py` | Direct execution | `poetry run pytest`, `poetry run python` |

---

## Next Steps

| Goal | Resource |
|------|----------|
| Build a complete node end-to-end | [Build Your First Node](FIRST_NODE.md) |
| Understand each node type in depth | [Node Archetypes Reference](../reference/node-archetypes.md) |
| Learn handler contract features | [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Advanced node patterns | [Node Building Guide](../guides/node-building/README.md) |
| ONEX architecture overview | [Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |

---

**Related Documentation**:
- [Installation Guide](installation.md)
- [Build Your First Node](FIRST_NODE.md)
- [Node Archetypes Reference](../reference/node-archetypes.md)
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
