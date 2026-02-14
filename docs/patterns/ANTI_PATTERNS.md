> **Navigation**: [Home](../INDEX.md) > [Patterns](./README.md) > Anti-Patterns

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# ONEX Anti-Patterns Documentation

This document catalogs prohibited patterns in the ONEX framework. Each anti-pattern includes a code example showing the violation, an explanation of why it is wrong, and the correct alternative.

## Table of Contents

1. [Business Logic in Nodes](#1-business-logic-in-nodes)
2. [Container Type Confusion](#2-container-type-confusion)
3. [ORCHESTRATOR Returning Result](#3-orchestrator-returning-result)
4. [Skipping super().__init__(container)](#4-skipping-superinit-container)
5. [Thread-Unsafe Node Sharing](#5-thread-unsafe-node-sharing)
6. [Reducer Side Effects](#6-reducer-side-effects)
7. [Manual Node Wiring](#7-manual-node-wiring)
8. [Imperative Subclass-and-Override](#8-imperative-subclass-and-override)
9. [String Version Literals](#9-string-version-literals)
10. [Mutable Default Arguments in Pydantic Models](#10-mutable-default-arguments-in-pydantic-models)

---

## 1. Business Logic in Nodes

**Severity**: Critical
**Principle Violated**: "Nodes are thin shells; handlers own all business logic"

Nodes are coordination shells. They initialize with `super().__init__(container)` and nothing else. All business logic, validation, transformation, and domain rules belong in handlers, which are resolved through the container or registry at runtime.

### WRONG -- Logic in the node class

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodePriceCalculator(NodeCompute):
    """WRONG: Business logic lives directly in the node."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.tax_rates = {"US": 0.08, "UK": 0.20, "DE": 0.19}  # WRONG

    async def calculate_price(self, base_price: float, region: str) -> float:
        """WRONG: Domain logic in the node."""
        rate = self.tax_rates.get(region, 0.0)
        return base_price * (1 + rate)
```

### Why It Is Wrong

- Nodes become fat classes that are hard to test in isolation.
- Business rules cannot be swapped, composed, or versioned independently.
- The contract (YAML) should define behavior; code in the node contradicts that principle.
- Handler-based architectures enable registry-driven resolution, where different handlers can be wired for different environments.

### CORRECT -- Thin node, handler owns logic

```python
# node.py -- thin shell, no business logic
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodePriceCalculator(NodeCompute):
    """Thin shell. All pricing logic is in the handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


# handler.py -- all business logic here
class HandlerPriceCalculator:
    """Handler that owns the pricing computation."""

    TAX_RATES: dict[str, float] = {"US": 0.08, "UK": 0.20, "DE": 0.19}

    def calculate_price(self, base_price: float, region: str) -> float:
        rate = self.TAX_RATES.get(region, 0.0)
        return base_price * (1 + rate)
```

---

## 2. Container Type Confusion

**Severity**: Critical
**Principle Violated**: "Dependency injection uses ModelONEXContainer, not ModelContainer"

`ModelContainer[T]` is a generic value wrapper. `ModelONEXContainer` is the dependency injection container used by nodes. Using the wrong one causes silent failures where services cannot be resolved.

### WRONG -- Using ModelContainer in node init

```python
from omnibase_core.models.container.model_container import ModelContainer


class NodeBadExample(NodeCompute):
    def __init__(self, container: ModelContainer) -> None:  # WRONG type
        super().__init__(container)
```

### Why It Is Wrong

- `ModelContainer[T]` wraps a single value. It does not have `get_service()` or any DI capability.
- The base class `NodeCoreBase.__init__` expects `ModelONEXContainer` and will fail or silently degrade if given the wrong type.
- Type checkers will not catch this unless the annotation is correct.

### CORRECT -- Using ModelONEXContainer

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeGoodExample(NodeCompute):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**Quick reference**:

| Type | Purpose | In Node `__init__` |
|------|---------|-------------------|
| `ModelContainer[T]` | Value wrapper | NEVER |
| `ModelONEXContainer` | Dependency injection | ALWAYS |

---

## 3. ORCHESTRATOR Returning Result

**Severity**: Critical
**Principle Violated**: "Orchestrators emit events and intents only -- never return result"

ORCHESTRATOR nodes coordinate workflows. They publish events to the message bus and route intents to effect nodes. Only COMPUTE nodes return typed results. This constraint is enforced by a Pydantic validator on `ModelHandlerOutput`.

### WRONG -- Orchestrator sets result

```python
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.enums.enum_node_kind import EnumNodeKind


# This will raise ValueError at construction time
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=envelope_id,
    correlation_id=correlation_id,
    handler_id="workflow-handler",
    result={"status": "done"},  # WRONG: ORCHESTRATOR cannot set result
)
# Raises: ValueError: ORCHESTRATOR cannot set result
```

### Why It Is Wrong

- Violates the architectural separation: orchestrators coordinate, they do not compute.
- If an orchestrator returns a result, callers become tightly coupled to the orchestrator's internal logic.
- The `ModelHandlerOutput` Pydantic validator rejects this at runtime.

### CORRECT -- Orchestrator emits events and intents

```python
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=envelope_id,
    correlation_id=correlation_id,
    handler_id="workflow-handler",
    events=(order_validated_event,),
    intents=(process_payment_intent,),
)
```

**Handler output constraints reference**:

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| ORCHESTRATOR | events[], intents[] | projections[], result |
| REDUCER | projections[] | events[], intents[], result |
| EFFECT | events[] | intents[], projections[], result |
| COMPUTE | result (required) | events[], intents[], projections[] |

---

## 4. Skipping super().__init__(container)

**Severity**: Critical
**Principle Violated**: "All nodes must call super().__init__(container)"

The base class `NodeCoreBase.__init__` registers the node with the container, sets up lifecycle hooks, initializes metrics, and configures the node identity. Skipping it leaves the node in an uninitialized state that will fail at runtime.

### WRONG -- Missing super call

```python
class NodeBroken(NodeEffect):
    def __init__(self, container: ModelONEXContainer) -> None:
        # WRONG: no super().__init__(container)
        self.db_service = container.get_service("ProtocolDatabase")
```

### Why It Is Wrong

- `self.node_id`, `self.contract`, and lifecycle hooks are never initialized.
- Any downstream code that accesses base-class attributes will raise `AttributeError`.
- Mixins like `MixinHandlerRouting` and `MixinEffectExecution` depend on base initialization.

### CORRECT -- Always call super

```python
class NodeWorking(NodeEffect):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

---

## 5. Thread-Unsafe Node Sharing

**Severity**: Critical
**Principle Violated**: "Nodes are single-request scoped; do not share across threads"

Node instances carry per-request state (correlation IDs, metrics, lifecycle phase). Sharing a single node instance across multiple threads introduces race conditions and corrupted state.

### WRONG -- Sharing a node instance across threads

```python
import threading

container = ModelONEXContainer()
shared_node = NodeDataValidator(container)

# WRONG: Multiple threads use the same node instance
for _ in range(4):
    threading.Thread(target=lambda: asyncio.run(shared_node.process(data))).start()
```

### Why It Is Wrong

- Node instances contain mutable per-request state (metrics counters, correlation context).
- Concurrent mutation of that state causes data races.
- Python's GIL does not protect against logical race conditions in async code.

### CORRECT -- One instance per thread or per request

```python
import threading


def worker(container: ModelONEXContainer, data: dict) -> None:
    node = NodeDataValidator(container)  # Thread-local instance
    asyncio.run(node.process(data))


container = ModelONEXContainer()
for _ in range(4):
    threading.Thread(target=worker, args=(container, data)).start()
```

---

## 6. Reducer Side Effects

**Severity**: Critical
**Principle Violated**: "Reducers are pure -- delta(state, event) -> (new_state, intents[]) with no I/O"

REDUCER nodes are pure functions. They receive state and an event, compute a new state, and emit intents describing what side effects should happen. They never perform I/O, log directly, access databases, or call external APIs.

### WRONG -- Reducer performs I/O

```python
class NodeBadReducer(NodeReducer):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.accumulated = {}  # WRONG: mutable state

    async def reduce(self, state: ModelState, event: ModelEvent) -> ModelState:
        new_state = state.model_copy(deep=True)
        new_state.count += 1

        # WRONG: Direct I/O in a reducer
        await self.db.save(new_state)
        logger.info(f"State updated to {new_state.count}")

        # WRONG: Mutable state accumulation
        self.accumulated[event.id] = new_state

        return new_state
```

### Why It Is Wrong

- I/O makes the reducer non-deterministic and untestable.
- Mutable instance state means the same input can produce different outputs.
- Replay and event sourcing break because re-processing events produces different results.
- The `ModelHandlerOutput` validator forbids events[], intents[], and result for REDUCER -- only projections[] is allowed.

### CORRECT -- Pure function with intent emission

```python
from omnibase_core.models.reducer.model_intent import ModelIntent


class NodeGoodReducer(NodeReducer):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # No mutable state

    def reduce(
        self, state: ModelOrderState, event: ModelEvent
    ) -> tuple[ModelOrderState, tuple[ModelIntent, ...]]:
        """Pure function: delta(state, event) -> (new_state, intents[])."""
        new_state = state.with_count_incremented(event.id)

        intents = (
            ModelIntent(
                intent_type="persist_state",
                target="database_service",
                payload={"state": new_state.model_dump()},
                priority=1,
            ),
        )

        return new_state, intents
```

---

## 7. Manual Node Wiring

**Severity**: Major
**Principle Violated**: "Resolution via container/registry, not direct instantiation"

Nodes should be resolved through the container or registry, not instantiated directly with hardcoded dependencies. Direct instantiation creates tight coupling and prevents contract-driven configuration.

### WRONG -- Direct instantiation with hardcoded wiring

```python
from myapp.nodes.node_payment_effect import NodePaymentEffect
from myapp.services.stripe_client import StripeClient


# WRONG: Hardcoded dependency wiring
stripe = StripeClient(api_key="sk_live_xxx")
payment_node = NodePaymentEffect(container)
payment_node.client = stripe  # WRONG: manual injection
```

### Why It Is Wrong

- Dependencies are invisible to the contract system.
- Testing requires monkey-patching instead of container substitution.
- Environment-specific configuration (dev vs. prod) requires code changes.
- The registry cannot discover or manage the node.

### CORRECT -- Resolution through container

```python
# Register capability in container setup
container.register_service("ProtocolPaymentGateway", stripe_client)

# Node resolves its own dependencies from the container
class NodePaymentEffect(NodeEffect):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # Handler resolves dependency via container at execution time
```

---

## 8. Imperative Subclass-and-Override

**Severity**: Major
**Principle Violated**: "Contracts are source of truth; YAML defines behavior, not code"

The ONEX pattern uses YAML contracts to declare behavior (FSM transitions, handler routing, capabilities). Overriding base class methods to change behavior bypasses the contract system and creates hidden, untraceable logic.

### WRONG -- Overriding base class methods

```python
class NodeCustomOrchestrator(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def _route_event(self, event: ModelEventEnvelope) -> None:
        """WRONG: Overriding internal routing to add custom logic."""
        if event.event_type == "special_case":
            await self._handle_special(event)
        else:
            await super()._route_event(event)

    async def _handle_special(self, event: ModelEventEnvelope) -> None:
        """WRONG: Hidden behavior not declared in contract."""
        pass
```

### Why It Is Wrong

- Hidden behavior that is not visible in the contract YAML.
- Cannot be validated, tested, or audited through the contract system.
- Breaks the declarative model where YAML is the single source of truth.
- Other tools (linters, validators, CI checks) cannot detect the override.

### CORRECT -- Declare behavior in contract YAML

```yaml
# contract.yaml
handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - event_model:
        name: "ModelSpecialEvent"
        module: "myapp.models.events"
      handler:
        name: "HandlerSpecialCase"
        module: "myapp.handlers"
```

```python
# node.py -- thin shell, routing is contract-driven
class NodeCustomOrchestrator(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)


# handler.py -- handler owns the logic
class HandlerSpecialCase:
    async def handle(self, event: ModelSpecialEvent) -> ModelHandlerOutput:
        # Special case logic lives here, declared in contract
        ...
```

---

## 9. String Version Literals

**Severity**: Critical
**Detection**: Pre-commit hook `validate-string-versions`

String version literals bypass type safety and introduce runtime parsing failures that could be caught at compile time. They violate ONEX's principle of "fail fast, fail explicitly."

### WRONG -- String version literals

```python
version = "1.0.0"
version = ModelSemVer.parse("1.0.0")
node.update_version("1.0.0")
```

```yaml
# YAML
version: "1.0.0"
```

### Why It Is Wrong

- IDE autocomplete and mypy cannot validate string versions.
- `ModelSemVer.parse("1.0.0.0")` fails at runtime; `ModelSemVer(1, 0, 0, 0)` fails at type check time.
- Ambiguity between "1.0" and "1.0.0" is eliminated by structured versions.

### CORRECT -- Structured versions

```python
from omnibase_core.models.primitives.model_semver import ModelSemVer

version = ModelSemVer(major=1, minor=0, patch=0)
```

```yaml
# YAML
version:
  major: 1
  minor: 0
  patch: 0
```

### Detection

The `validate-string-versions` pre-commit hook detects `ModelSemVer.parse()` calls, direct string literals in semantic version format, and flat YAML string versions.

### Allowed Exceptions

- Docstring examples
- Regex patterns for version validation
- Test fixture data
- User-facing output strings and logging

---

## 10. Mutable Default Arguments in Pydantic Models

**Severity**: Major
**Principle Violated**: "Always use default_factory for mutable defaults"

Python's mutable default argument problem applies to Pydantic models. Using a mutable default (`[]`, `{}`) means all instances share the same object. Pydantic mitigates this in some cases, but `default_factory` is the only safe pattern.

### WRONG -- Mutable defaults

```python
from pydantic import BaseModel


class ModelConfig(BaseModel):
    tags: list[str] = []          # WRONG: shared mutable default
    metadata: dict[str, str] = {} # WRONG: shared mutable default
    items: list[int] = [1, 2, 3]  # WRONG: shared mutable default
```

### Why It Is Wrong

- Even though Pydantic performs a copy internally, the pattern is misleading and violates the project convention.
- In non-Pydantic contexts (dataclasses, plain classes), this causes real bugs where instances share the same list.
- Consistency: the codebase standardizes on `default_factory` everywhere.

### CORRECT -- Use Field(default_factory=...)

```python
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    items: list[int] = Field(default_factory=lambda: [1, 2, 3])
```

---

## Summary

| # | Anti-Pattern | Severity | Core Principle |
|---|-------------|----------|----------------|
| 1 | Business logic in nodes | Critical | Nodes are thin; handlers own logic |
| 2 | Container type confusion | Critical | Use ModelONEXContainer for DI |
| 3 | ORCHESTRATOR returning result | Critical | Orchestrators emit, never return |
| 4 | Skipping super().__init__ | Critical | Base class initialization required |
| 5 | Thread-unsafe node sharing | Critical | Nodes are single-request scoped |
| 6 | Reducer side effects | Critical | Reducers are pure -- no I/O |
| 7 | Manual node wiring | Major | Resolve via container/registry |
| 8 | Imperative subclass-and-override | Major | YAML contracts define behavior |
| 9 | String version literals | Critical | Use ModelSemVer structured versions |
| 10 | Mutable Pydantic defaults | Major | Always use default_factory |

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) -- Authoritative coding standards
- [Node Archetypes Reference](../reference/node-archetypes.md) -- Node type specifications
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) -- Handler contract authoring
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) -- Error patterns
- [Pydantic Best Practices](../conventions/PYDANTIC_BEST_PRACTICES.md) -- Model standards

---

## Document Metadata

- **Version**: 2.0.0
- **Last Updated**: 2026-02-14
- **Maintainer**: ONEX Core Team
- **Status**: Active
