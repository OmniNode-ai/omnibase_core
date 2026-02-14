> **Navigation**: [Home](../INDEX.md) > Architecture > Handler Architecture

# Handler Architecture

**Version**: 1.0.0
**Last Updated**: 2026-02-14
**Status**: Canonical Reference

This document teaches the end-to-end handler pattern in ONEX: from YAML contract
to thin node shell to handler with business logic to `ModelHandlerOutput`.

---

## 1. Goal and Invariants

The ONEX four-node architecture enforces a strict separation between
**coordination** (nodes) and **business logic** (handlers).

**Invariant 1: Nodes are thin shells.** A node class contains only
`__init__` calling `super().__init__(container)`. It never contains
business logic, validation rules, or data transformation code.

**Invariant 2: Handlers own all business logic.** Computation,
I/O orchestration, state transitions, and workflow coordination
live in handler functions or classes, never in the node itself.

**Invariant 3: YAML contracts define behavior.** The `.onex.yaml`
contract declares what a node does, which handler it binds, and
what I/O models it accepts and returns.

**Invariant 4: Output constraints are non-negotiable.** Each node kind
restricts which fields `ModelHandlerOutput` may populate:

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |

These constraints are enforced by a Pydantic `model_validator` on
`ModelHandlerOutput` at construction time. A violation raises
`ModelOnexError` with error code `CONTRACT_VIOLATION`.

**Why this matters:**

- **Testability**: Handlers can be tested in isolation without any node or
  container. Pass input, assert output.
- **Composability**: The contract defines the interface. Swap the handler
  implementation without changing the node.
- **Separation of concerns**: Nodes handle wiring (container, routing,
  lifecycle). Handlers handle domain logic.

---

## 2. Minimal End-to-End Example

A temperature converter as a COMPUTE node. Three files: contract, handler,
node.

### 2.1 YAML Contract (`contract.onex.yaml`)

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_temperature_converter"
node_type: "COMPUTE_GENERIC"
description: "Converts temperature between Celsius and Fahrenheit."

input_model:
  name: "ModelTemperatureInput"
  module: "myapp.nodes.temperature.models"

output_model:
  name: "ModelTemperatureOutput"
  module: "myapp.nodes.temperature.models"

capabilities:
  - name: "temperature.conversion"

handler_routing:
  version: { major: 1, minor: 0, patch: 0 }
  routing_strategy: payload_type_match
  default_handler: convert_temperature
```

### 2.2 I/O Models

```python
from pydantic import BaseModel, ConfigDict, Field


class ModelTemperatureInput(BaseModel):
    """Input for temperature conversion."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(..., description="Temperature value to convert")
    from_unit: str = Field(..., description="Source unit: 'celsius' or 'fahrenheit'")
    to_unit: str = Field(..., description="Target unit: 'celsius' or 'fahrenheit'")


class ModelTemperatureOutput(BaseModel):
    """Output from temperature conversion."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    original_value: float
    converted_value: float
    from_unit: str
    to_unit: str
```

### 2.3 Handler (Business Logic)

```python
from myapp.nodes.temperature.models import (
    ModelTemperatureInput,
    ModelTemperatureOutput,
)


def convert_temperature(
    node: object,
    input_data: object,
) -> ModelTemperatureOutput:
    """Pure computation: convert temperature between units.

    This function contains ALL the business logic.
    The node shell delegates to this handler via contract-driven routing.
    """
    # Extract typed input from the compute input wrapper
    data: ModelTemperatureInput = input_data.data

    if data.from_unit == "celsius" and data.to_unit == "fahrenheit":
        converted = data.value * 9 / 5 + 32
    elif data.from_unit == "fahrenheit" and data.to_unit == "celsius":
        converted = (data.value - 32) * 5 / 9
    else:
        converted = data.value

    return ModelTemperatureOutput(
        original_value=data.value,
        converted_value=converted,
        from_unit=data.from_unit,
        to_unit=data.to_unit,
    )
```

### 2.4 Thin Node Shell

```python
"""Temperature converter compute node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeTemperatureConverter(NodeCompute):
    """Temperature conversion - COMPUTE_GENERIC node.

    All business logic lives in the handler (convert_temperature).
    This class is a thin shell: only __init__ calling super().__init__.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


__all__ = ["NodeTemperatureConverter"]
```

The node contains zero business logic. The contract's `handler_routing`
section binds the `convert_temperature` handler. `NodeCompute.process()`
resolves the handler via the routing table and dispatches to it.

---

## 3. All Four Node Kinds

Each node kind has a distinct handler output shape. The builder methods on
`ModelHandlerOutput` enforce these constraints.

### 3.1 COMPUTE Handler

COMPUTE handlers are pure transformations. They MUST return `result` and
CANNOT emit events, intents, or projections.

```python
from uuid import UUID
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


def handler_compute_example(
    input_envelope_id: UUID,
    correlation_id: UUID,
    raw_data: list[float],
) -> ModelHandlerOutput[dict]:
    """Pure computation: average a list of numbers."""
    avg = sum(raw_data) / len(raw_data) if raw_data else 0.0
    result = {"average": avg, "count": len(raw_data)}

    return ModelHandlerOutput.for_compute(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="compute.statistics.average",
        result=result,
    )
```

The `result` must be JSON-ledger-safe: `str`, `int`, `float`, `bool`,
`None`, `list`, `dict` (with `str` keys), or a Pydantic `BaseModel`.

### 3.2 EFFECT Handler

EFFECT handlers perform external I/O (database, API, filesystem) and
emit events about what happened. They CANNOT emit intents, projections,
or return a result.

```python
def handler_effect_example(
    input_envelope_id: UUID,
    correlation_id: UUID,
    user_data: dict,
) -> ModelHandlerOutput[None]:
    """Side-effecting I/O: persist user to database."""
    # ... perform database write ...
    user_created_event = create_user_event(user_data)

    return ModelHandlerOutput.for_effect(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="effect.user.storage",
        events=(user_created_event,),
    )
```

### 3.3 REDUCER Handler

REDUCER handlers are pure fold functions: `(state, event) -> (new_state,
projections)`. They CANNOT emit events, intents, or return a result.
No I/O is permitted.

```python
def handler_reducer_example(
    input_envelope_id: UUID,
    correlation_id: UUID,
    current_state: dict,
    event: dict,
) -> ModelHandlerOutput[None]:
    """Pure state fold: update order status projection."""
    updated_projection = {
        **current_state,
        "status": event["new_status"],
        "last_updated": event["timestamp"],
    }

    return ModelHandlerOutput.for_reducer(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="reducer.order.state",
        projections=(updated_projection,),
    )
```

### 3.4 ORCHESTRATOR Handler

ORCHESTRATOR handlers coordinate workflows. They emit events and intents
but NEVER return a typed result. Intents are requests for side effects
that EFFECT nodes will execute.

```python
def handler_orchestrator_example(
    input_envelope_id: UUID,
    correlation_id: UUID,
    order_event: object,
) -> ModelHandlerOutput[None]:
    """Workflow coordination: route order through processing pipeline."""
    validation_event = create_validation_event(order_event)
    payment_intent = create_payment_intent(order_event)

    return ModelHandlerOutput.for_orchestrator(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="orchestrator.order.workflow",
        events=(validation_event,),
        intents=(payment_intent,),
    )
```

Attempting to set `result` on an ORCHESTRATOR output raises:

```
ModelOnexError: ORCHESTRATOR cannot set result - use events[] and intents[] only.
Only COMPUTE nodes return typed results.
```

---

## 4. Dependency Injection and Registry Resolution

Handlers are resolved through the container and handler registry. Direct
instantiation (`handler = MyHandler()`) is forbidden in production code.

### 4.1 Protocol-Based Resolution (Preferred)

Use type-based lookup via the protocol:

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.protocols.runtime.protocol_handler_registry import (
    ProtocolHandlerRegistry,
)

# Inside a node or service:
registry = container.get_service(ProtocolHandlerRegistry)
handler = registry.resolve("compute.temperature.converter")
```

### 4.2 String-Based Resolution

Allowed for late-binding plugins where the handler type is not known
at import time:

```python
# String-based lookup (acceptable for plugin systems)
handler_registry: object = container.get_service("ProtocolHandlerRegistry")
```

**Rules:**
- Prefer type-based resolution for static, known dependencies.
- Use string-based resolution only for late-binding or plugin-loaded
  handlers.
- Never mix both styles in the same module.

### 4.3 Contract-Driven Handler Routing

The `MixinHandlerRouting` mixin (included in all four node base classes)
reads the `handler_routing` section of the YAML contract and builds a
routing table at `__init__` time.

```yaml
# In contract.onex.yaml
handler_routing:
  version: { major: 1, minor: 0, patch: 0 }
  routing_strategy: payload_type_match
  handlers:
    - routing_key: UserData
      handler_key: compute_user_score
    - routing_key: OrderData
      handler_key: compute_order_total
  default_handler: compute_generic
```

When `process()` is called, the node:

1. Checks the routing table for a matching handler key.
2. Resolves the handler callable (direct or via lazy loader).
3. Invokes the handler: `handler(self, input_data)`.
4. Returns the handler's output.

The node never touches the business logic.

### 4.4 Container Types

| Type | Purpose | In Node `__init__` |
|------|---------|-------------------|
| `ModelONEXContainer` | Dependency injection container | **ALWAYS** use this |
| `ModelContainer[T]` | Generic value wrapper | **NEVER** in node `__init__` |

```python
# CORRECT
class NodeMyCompute(NodeCompute):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

# WRONG - ModelContainer is for value wrapping, not DI
class NodeMyCompute(NodeCompute):
    def __init__(self, container: ModelContainer) -> None:  # Wrong type
        super().__init__(container)
```

---

## 5. Handler Lifecycle

### 5.1 Construction

Node construction happens once when the container builds the node.
The `__init__` method calls `super().__init__(container)`, which:

1. Stores the container reference.
2. Generates a `node_id`.
3. Optionally initializes handler routing from the contract.

No handler logic executes during construction.

### 5.2 Execution

When `process()` is called:

1. The node resolves the handler via the routing table.
2. The handler is invoked with `(node, input_data)`.
3. The handler executes business logic and returns a result.
4. The node wraps the result in the appropriate output model.

Handlers may be sync or async. The node detects coroutines and
`await`s them automatically:

```python
handler_result = resolved_handler(self, input_data)
if asyncio.iscoroutine(handler_result):
    result = await handler_result
else:
    result = handler_result
```

### 5.3 Teardown

Node resources are cleaned up via `_cleanup_node_resources()`, called
during container shutdown. Handlers themselves are stateless and require
no teardown.

### 5.4 Stateless Handlers (Default)

Handlers should be stateless. All inputs come from the input model,
and all outputs go to the output model. This enables:

- Safe concurrent invocation.
- Deterministic replay.
- Simple unit testing.

### 5.5 Thread Safety

Nodes are single-request-scoped. Do NOT share node instances across
threads without synchronization.

```python
# WRONG - shared instance, race condition
shared_node = NodeMyCompute(container)
threading.Thread(target=lambda: asyncio.run(shared_node.process(data))).start()

# CORRECT - per-thread instance
def worker():
    node = NodeMyCompute(container)
    asyncio.run(node.process(data))
threading.Thread(target=worker).start()
```

---

## 6. Testing Patterns

### 6.1 Handler Unit Test (No Container Needed)

The primary benefit of the handler pattern: test business logic directly
without any container, node, or DI framework.

```python
import pytest
from myapp.nodes.temperature.models import (
    ModelTemperatureInput,
    ModelTemperatureOutput,
)
from myapp.nodes.temperature.handler import convert_temperature


@pytest.mark.unit
class TestConvertTemperature:
    """Test handler logic directly -- no node, no container."""

    def test_celsius_to_fahrenheit(self) -> None:
        # Arrange: create a minimal input mock
        class FakeComputeInput:
            data = ModelTemperatureInput(
                value=100.0, from_unit="celsius", to_unit="fahrenheit"
            )

        # Act
        result = convert_temperature(node=None, input_data=FakeComputeInput())

        # Assert
        assert isinstance(result, ModelTemperatureOutput)
        assert result.converted_value == pytest.approx(212.0)
        assert result.from_unit == "celsius"
        assert result.to_unit == "fahrenheit"

    def test_fahrenheit_to_celsius(self) -> None:
        class FakeComputeInput:
            data = ModelTemperatureInput(
                value=32.0, from_unit="fahrenheit", to_unit="celsius"
            )

        result = convert_temperature(node=None, input_data=FakeComputeInput())
        assert result.converted_value == pytest.approx(0.0)

    def test_same_unit_returns_unchanged(self) -> None:
        class FakeComputeInput:
            data = ModelTemperatureInput(
                value=42.0, from_unit="celsius", to_unit="celsius"
            )

        result = convert_temperature(node=None, input_data=FakeComputeInput())
        assert result.converted_value == pytest.approx(42.0)
```

### 6.2 Output Constraint Tests

Verify that `ModelHandlerOutput` enforces the constraint matrix:

```python
import pytest
from uuid import uuid4
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestHandlerOutputConstraints:
    """Verify ModelHandlerOutput enforces node-kind constraints."""

    def test_compute_requires_result(self) -> None:
        with pytest.raises(ModelOnexError, match="COMPUTE requires result"):
            ModelHandlerOutput.for_compute(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="test",
                result=None,
            )

    def test_orchestrator_forbids_result(self) -> None:
        with pytest.raises(ModelOnexError, match="ORCHESTRATOR cannot set result"):
            ModelHandlerOutput.for_orchestrator(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="test",
                # Manually constructing to bypass builder:
            )
            # Direct construction to test constraint:
            from omnibase_core.enums.enum_node_kind import EnumNodeKind

            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="test",
                node_kind=EnumNodeKind.ORCHESTRATOR,
                result={"forbidden": True},
            )

    def test_effect_forbids_intents(self) -> None:
        with pytest.raises(ModelOnexError, match="EFFECT cannot emit intents"):
            from omnibase_core.enums.enum_node_kind import EnumNodeKind

            ModelHandlerOutput(
                input_envelope_id=uuid4(),
                correlation_id=uuid4(),
                handler_id="test",
                node_kind=EnumNodeKind.EFFECT,
                intents=("some_intent",),
            )
```

### 6.3 Integration Test with Container

For full integration testing, create a node with a real container:

```python
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.compute.model_compute_input import ModelComputeInput


@pytest.mark.integration
class TestNodeTemperatureIntegration:
    """Integration test: node + container + handler routing."""

    async def test_process_routes_to_handler(
        self, container: ModelONEXContainer
    ) -> None:
        from myapp.nodes.temperature.node import NodeTemperatureConverter

        node = NodeTemperatureConverter(container)

        input_data = ModelComputeInput(
            data={"value": 100.0, "from_unit": "celsius", "to_unit": "fahrenheit"},
            computation_type="convert_temperature",
        )

        result = await node.process(input_data)
        assert result.result is not None
```

---

## 7. Migration from Imperative Nodes

### 7.1 Before: Logic in `process()`

The legacy pattern puts business logic directly in the node:

```python
# WRONG: Business logic lives in the node
class NodePriceCalculator(NodeCompute):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def process(self, input_data):
        # Business logic embedded in the node -- violates invariant
        base_price = input_data.data["price"]
        tax_rate = input_data.data["tax_rate"]
        total = base_price * (1 + tax_rate)

        return ModelComputeOutput(
            result={"total": total},
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
            processing_time_ms=0.0,
            cache_hit=False,
            parallel_execution_used=False,
        )
```

### 7.2 After: Logic in Handler, Node Delegates

```python
# handler_price_calculator.py
def calculate_price(node: object, input_data: object) -> dict:
    """Handler: pure price calculation."""
    base_price = input_data.data["price"]
    tax_rate = input_data.data["tax_rate"]
    return {"total": base_price * (1 + tax_rate)}


# node.py -- thin shell
class NodePriceCalculator(NodeCompute):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


# contract.onex.yaml -- binds handler
# handler_routing:
#   default_handler: calculate_price
```

The node is now a thin shell. `NodeCompute.process()` resolves
`calculate_price` from the routing table and dispatches to it.

### 7.3 Migration Checklist

1. **Identify business logic** in `process()`, `execute_compute()`,
   `execute_effect()`, or similar methods.
2. **Extract to a handler function** with signature
   `(node, input_data) -> output`.
3. **Remove all logic from the node class** except `__init__` calling
   `super().__init__(container)`.
4. **Add `handler_routing` to the YAML contract** with `default_handler`
   pointing to the extracted function.
5. **Register the handler** in the handler registry so the routing table
   can resolve it.
6. **Write handler unit tests** that test the function directly (no
   container required).
7. **Verify constraint compliance**: use the correct
   `ModelHandlerOutput.for_*()` builder for the node kind.
8. **Run existing tests** to confirm no regressions.

---

## Related Documentation

| Topic | Document |
|-------|----------|
| Handler Contract Model | [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Node Archetypes | [Node Archetypes Reference](../reference/node-archetypes.md) |
| Four-Node Architecture | [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Execution Shapes | [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md) |
| Container Types | [Container Types](CONTAINER_TYPES.md) |
| Handler Conversion | [Handler Conversion Guide](../guides/HANDLER_CONVERSION_GUIDE.md) |
| Dependency Injection | [Dependency Injection](DEPENDENCY_INJECTION.md) |
| Threading | [Threading Guide](../guides/THREADING.md) |
| Error Handling | [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) |

### Import Quick Reference

```python
# Node base classes
from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator

# Handler output (the canonical return type)
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

# Node kind enum (for direct ModelHandlerOutput construction)
from omnibase_core.enums.enum_node_kind import EnumNodeKind

# Container for DI
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Handler contract model
from omnibase_core.models.contracts import ModelHandlerContract

# Behavior descriptor
from omnibase_core.models.runtime import ModelHandlerBehaviorDescriptor

# Structured version
from omnibase_core.models.primitives import ModelSemVer

# ONEX errors
from omnibase_core.models.errors.model_onex_error import ModelOnexError
```

---

**Last Updated**: 2026-02-14
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
