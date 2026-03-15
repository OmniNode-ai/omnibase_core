> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Node Class Hierarchy

# Node Class Hierarchy Guide

**Version**: 1.3.1
**Last Updated**: 2025-12-06
**Status**: ✅ Complete
**Correlation ID**: `a3c8f7d4-2b5e-4a19-9f3a-8d6e1c4b7a2f`

> **UPDATE (v0.4.0)**: `NodeReducer` and `NodeOrchestrator` are now the **PRIMARY declarative implementations**. The "Declarative" suffix has been removed. Legacy imperative implementations have been removed.

---

## Table of Contents

1. [Overview](#overview)
2. [The Three-Tier System](#the-three-tier-system)
3. [Tier 1: ModelService* Wrappers (RECOMMENDED)](#tier-1-modelservice-wrappers-recommended)
4. [Tier 2: Node* Classes (ADVANCED)](#tier-2-node-classes-advanced)
5. [Tier 3: NodeCoreBase (EXPERT)](#tier-3-nodecorebase-expert)
6. [Decision Matrix](#decision-matrix)
7. [Feature Comparison](#feature-comparison)
8. [Migration Paths](#migration-paths)
9. [Common Scenarios](#common-scenarios)
10. [When to Use Which Tier](#when-to-use-which-tier)
11. [Naming Convention Migration (v0.4.0)](#naming-convention-migration-v040---completed)

---

## Overview

omnibase_core provides **three tiers** of node base classes, each optimized for different use cases and levels of control. Understanding which tier to use is critical for building maintainable, production-ready ONEX nodes.

### Abbreviations Used in This Guide

| Abbreviation | Meaning |
|--------------|---------|
| **DI** | Dependency Injection |
| **FSM** | Finite State Machine |
| **MCP** | Model Context Protocol (for AI tool invocation) |
| **MRO** | Method Resolution Order (Python's class inheritance order) |
| **I/O** | Input/Output operations |
| **SLA** | Service Level Agreement |
| **TTL** | Time To Live (cache expiration) |

### The Hierarchy

```text
┌──────────────────────────────────────────────────────────┐
│  Tier 1: ModelService* Wrappers (RECOMMENDED)           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Production-ready Pydantic models with pre-wired mixins  │
│  Use for: 95% of production nodes                        │
│  Examples: ModelServiceCompute, ModelServiceEffect       │
└──────────────────────────────────────────────────────────┘
                           ▲
                           │ inherits from
┌──────────────────────────────────────────────────────────┐
│  Tier 2: Node* Classes (ADVANCED)                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Specialized node implementations with node-specific     │
│  features and customizable mixin composition             │
│  Use for: 4% of nodes needing custom composition         │
│  Examples: NodeCompute, NodeEffect, NodeReducer          │
└──────────────────────────────────────────────────────────┘
                           ▲
                           │ inherits from
┌──────────────────────────────────────────────────────────┐
│  Tier 3: NodeCoreBase (EXPERT)                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Bare-metal foundation with minimal boilerplate          │
│  Use for: 1% of nodes requiring complete custom control  │
│  Examples: Custom node types, framework development      │
└──────────────────────────────────────────────────────────┘
```

### Architectural Invariant: Thin Nodes, Fat Handlers

Regardless of which tier you use, **nodes are thin coordination shells**. Business logic belongs in handlers, not in the node class. Nodes wire up handlers via the container; handlers contain the domain logic. This separation makes handlers independently testable and keeps nodes focused on lifecycle and infrastructure concerns.

### Quick Decision Guide

| If you need... | Use Tier |
|----------------|----------|
| **Production node with standard features** | Tier 1 (ModelService*) |
| **Custom mixin composition** | Tier 2 (Node*) |
| **Completely new node type** | Tier 3 (NodeCoreBase) |

---

## The Three-Tier System

### Design Philosophy

The three-tier hierarchy provides a **spectrum of abstraction**:

1. **Tier 1** (Highest abstraction) - Maximize productivity, minimize boilerplate
2. **Tier 2** (Medium abstraction) - Balance control and convenience
3. **Tier 3** (Lowest abstraction) - Maximum flexibility, minimum assumptions

Each tier inherits from the one below, **adding features without removing flexibility**.

---

## Tier 1: ModelService* Wrappers (RECOMMENDED)

### What They Are

**Production-ready Pydantic models** that wrap Node* classes with pre-configured mixin compositions optimized for common production scenarios.

### Key Characteristics

✅ **Pre-wired mixins** - Essential production features included automatically
✅ **Pydantic validation** - Strong type safety and automatic validation
✅ **Zero boilerplate** - 80+ lines of initialization code eliminated
✅ **Production-tested** - Battle-tested compositions used across ONEX ecosystem
✅ **Immediate productivity** - Start building business logic immediately

### Available Classes

| Class | Node Type | Pre-wired Mixins | Best For |
|-------|-----------|------------------|----------|
| `ModelServiceEffect` | EFFECT | NodeService, HealthCheck, EventBus, Metrics | I/O operations, API calls, database writes |
| `ModelServiceCompute` | COMPUTE | NodeService, HealthCheck, Caching, Metrics | Data transformations, calculations |
| `ModelServiceReducer` | REDUCER | NodeService, HealthCheck, StateManagement, Metrics | State aggregation, event reduction |
| `ModelServiceOrchestrator` | ORCHESTRATOR | NodeService, HealthCheck, WorkflowSupport, Metrics | Multi-step workflows, coordination |

### When to Use Tier 1

✅ **Use ModelService* when**:
- Building standard production nodes (95% of cases)
- Need production features out-of-the-box
- Want minimal setup and maximum productivity
- Following standard ONEX patterns
- Building MCP servers or long-lived services
- Don't need custom mixin composition

❌ **Don't use ModelService* when**:
- Need custom mixin combinations
- Require selective feature inclusion/exclusion
- Building framework-level infrastructure
- Performance-critical paths requiring minimal overhead

### Complete Example: COMPUTE Node

**Architecture note**: Nodes are thin shells. Business logic belongs in handlers. The node wires up the handler; the handler contains the computation.

**File**: `src/your_project/nodes/node_price_calculator_compute/node.py`

```python
"""Price calculator node - thin shell."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.infrastructure.infra_bases import ModelServiceCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodePriceCalculatorCompute(ModelServiceCompute):
    """Price calculator with automatic caching and metrics.

    Built-in features from ModelServiceCompute:
    - MixinNodeService, MixinHealthCheck, MixinCaching, MixinMetrics.

    Business logic lives in HandlerPriceCalculator.
    """

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
```

**File**: `src/your_project/nodes/node_price_calculator_compute/handlers/handler_price_calculator.py`

```python
"""Handler containing price calculation business logic."""

from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError


DISCOUNT_RATES: dict[str, float] = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "VIP": 0.25,
}


class HandlerPriceCalculator:
    """COMPUTE handler - must return result (required).

    COMPUTE output constraints:
        - Allowed: result (required)
        - Forbidden: events[], intents[], projections[]
    """

    async def handle(
        self,
        operation: dict[str, Any],
        *,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[dict[str, Any]]:
        """Calculate price with tax and discounts."""
        items = operation.get("items", [])
        discount_code = operation.get("discount_code")
        tax_rate = operation.get("tax_rate", 0.08)

        if not items:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Cart must contain at least one item",
                context={"items_count": 0},
            )

        subtotal = sum(item["price"] * item["quantity"] for item in items)

        discount = 0.0
        if discount_code and discount_code in DISCOUNT_RATES:
            discount = subtotal * DISCOUNT_RATES[discount_code]

        discounted_subtotal = subtotal - discount
        tax = discounted_subtotal * tax_rate
        total = discounted_subtotal + tax

        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            result={
                "subtotal": round(subtotal, 2),
                "discount": round(discount, 2),
                "discount_code": discount_code,
                "tax": round(tax, 2),
                "tax_rate": tax_rate,
                "total": round(total, 2),
            },
        )
```

**Key Benefits**:
- Thin node with zero business logic
- Handler is independently testable without container setup
- Output constraints enforced by `ModelHandlerOutput.for_compute()`
- Built-in caching, metrics, and health checks from ModelServiceCompute

### Complete Example: EFFECT Node

**File**: `src/your_project/nodes/node_database_writer_effect/node.py`

```python
"""Database writer effect node - thin shell."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.infrastructure.infra_bases import ModelServiceEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeDatabaseWriterEffect(ModelServiceEffect):
    """Database writer with transaction management and event publishing.

    Built-in features from ModelServiceEffect:
    - MixinNodeService, MixinHealthCheck, MixinEventBus, MixinMetrics.

    Business logic lives in HandlerDatabaseWriter.
    """

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
```

**File**: `src/your_project/nodes/node_database_writer_effect/handlers/handler_database_writer.py`

```python
"""Handler for database write operations."""

from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class HandlerDatabaseWriter:
    """EFFECT handler - returns events[].

    EFFECT output constraints:
        - Allowed: events[]
        - Forbidden: intents[], projections[], result
    """

    def __init__(self, db: Any) -> None:
        self.db = db

    async def handle(
        self,
        operation: dict[str, Any],
        *,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        """Write records to database and emit completion event."""
        records = operation.get("records", [])
        table_name = operation.get("table", "default")

        if not records:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="No records to write",
                context={"table": table_name},
            )

        result = await self.db.insert_many(table_name, records)

        return ModelHandlerOutput.for_effect(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            events=[
                ModelEventEnvelope(
                    event_type="database.write.completed",
                    payload={
                        "table": table_name,
                        "records_written": result["count"],
                    },
                ),
            ],
        )
```

### Testing Tier 1 Nodes

```python
"""Test ModelServiceCompute node."""

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import ModelComputeInput

from your_project.nodes.node_price_calculator_compute import NodePriceCalculatorCompute


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def calculator(container):
    """Create calculator node."""
    return NodePriceCalculatorCompute(container)


@pytest.mark.asyncio
async def test_price_calculation(calculator):
    """Test basic price calculation."""
    input_data = ModelComputeInput(
        operation_data={
            "items": [
                {"name": "Widget", "price": 10.00, "quantity": 2},
                {"name": "Gadget", "price": 25.00, "quantity": 1}
            ],
            "discount_code": "SAVE10",
            "tax_rate": 0.08
        }
    )

    result = await calculator.execute_compute(input_data)

    assert result.success is True
    assert result.result["subtotal"] == 45.00
    assert result.result["discount"] == 4.50  # 10% off
    assert result.result["tax"] == 3.24       # 8% tax
    assert result.result["total"] == 43.74


@pytest.mark.asyncio
async def test_caching(calculator):
    """Test that results are cached."""
    input_data = ModelComputeInput(
        operation_data={
            "items": [{"name": "Widget", "price": 10.00, "quantity": 1}],
            "tax_rate": 0.08
        }
    )

    # First call - should compute
    result1 = await calculator.execute_compute(input_data)

    # Second call - should use cache
    result2 = await calculator.execute_compute(input_data)

    assert result1.result == result2.result
    # Cache hit tracked in metrics automatically
```

---

## Tier 2: Node* Classes (ADVANCED)

### What They Are

**Specialized node implementations** that provide node-type-specific features with customizable mixin composition. These are the foundation classes that ModelService* wrappers build upon.

### Key Characteristics

🔧 **Selective composition** - Choose exactly which mixins to include
🔧 **Node-specific features** - Type-safe input/output, caching (Compute), transactions (Effect)
🔧 **Performance optimization** - Lower overhead than ModelService* wrappers
🔧 **Framework alignment** - Direct alignment with ONEX four-node architecture

### Available Classes

| Class | Specialization | Key Features | Use Case |
|-------|----------------|--------------|----------|
| `NodeCompute` | Pure computations | Caching, parallel processing, deterministic ops | Custom compute pipelines |
| `NodeEffect` | I/O operations | Transactions, circuit breaker, retry logic | Custom I/O patterns |
| `NodeReducer` | State aggregation | FSM support, event reduction, snapshot management | Custom state machines |
| `NodeOrchestrator` | Workflow coordination | Parallel execution, dependency graphs, rollback | Custom orchestration |

### When to Use Tier 2

✅ **Use Node* when**:
- Need custom mixin composition (add/remove specific mixins)
- Want selective feature inclusion (not all ModelService* features)
- Building custom node wrappers for your organization
- Performance-critical paths (reduce overhead)
- Non-standard patterns requiring flexibility

❌ **Don't use Node* when**:
- Standard ModelService* composition works (95% of cases)
- Building completely new node type (use NodeCoreBase)
- Don't need node-specific features (use NodeCoreBase)

### Complete Example: Custom COMPUTE Node

```python
"""Custom COMPUTE node with selective mixin composition."""

from omnibase_core.nodes import NodeCompute, ModelComputeInput, ModelComputeOutput
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
# Note: Intentionally NOT including MixinCaching for this use case
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeCustomAnalyticsCompute(
    NodeCompute,           # Core COMPUTE features
    MixinHealthCheck,      # ✅ Health monitoring
    MixinMetrics,          # ✅ Performance metrics
    # ❌ NOT including MixinCaching - results change too frequently
):
    """
    Custom analytics compute node with selective features.

    Why custom composition?
    - Results are time-sensitive (no caching benefit)
    - Need health monitoring for production
    - Want performance metrics for SLA tracking
    - Don't need event bus (pure computation)

    Method Resolution Order:
    NodeCustomAnalyticsCompute → NodeCompute → MixinHealthCheck
    → MixinMetrics → NodeCoreBase → ABC
    """

    def __init__(self, container: ModelONEXContainer):
        # Initialize all classes in MRO
        super().__init__(container)

        # Custom initialization
        self.analytics_engine = container.get_service("ProtocolAnalytics")

    async def execute_compute(
        self,
        input_data: ModelComputeInput
    ) -> ModelComputeOutput:
        """
        Compute analytics with custom logic.

        Features from Node* tier:
        - Type-safe input/output (NodeCompute)
        - Health monitoring (MixinHealthCheck)
        - Metrics tracking (MixinMetrics)
        - NO caching (intentionally excluded)
        """
        # Access NodeCompute-specific features
        operation = input_data.operation_data
        dataset = operation.get("dataset")

        # Use compute-specific parallel processing
        results = await self._process_in_parallel(dataset)

        return ModelComputeOutput(
            success=True,
            result={"analytics": results}
        )

    async def _process_in_parallel(self, dataset):
        """Use NodeCompute's parallel processing capabilities."""
        # NodeCompute provides ThreadPoolExecutor
        # Custom parallel processing logic here
        return await self.analytics_engine.analyze(dataset)
```

### Complete Example: Custom EFFECT Node

```python
"""Custom EFFECT node with retry-focused composition."""

from omnibase_core.nodes import NodeEffect, ModelEffectInput, ModelEffectOutput
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeCustomApiClientEffect(
    NodeEffect,           # Core EFFECT features (transactions, retry, circuit breaker)
    MixinMetrics,         # ✅ Performance tracking
    # ❌ NOT including MixinHealthCheck - managed externally
    # ❌ NOT including MixinEventBus - no event publishing needed
):
    """
    Custom API client with aggressive retry logic.

    Why custom composition?
    - Need NodeEffect's built-in retry and circuit breaker
    - Require metrics for API call monitoring
    - Health checks handled by external monitoring
    - No event publishing required

    Focuses on:
    - Transaction boundaries for API calls
    - Exponential backoff on failures
    - Circuit breaker to prevent cascade failures
    """

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

        # Configure NodeEffect retry behavior
        self.max_retries = 5
        self.retry_delay_seconds = 1.0
        self.circuit_breaker_threshold = 10

        self.api_client = container.get_service("ProtocolHttpClient")

    async def execute_effect(
        self,
        input_data: ModelEffectInput
    ) -> ModelEffectOutput:
        """
        Call external API with retry and circuit breaker.

        NodeEffect automatically provides:
        - Transaction management
        - Retry with exponential backoff
        - Circuit breaker protection
        """
        operation = input_data.operation_data
        endpoint = operation.get("endpoint")
        payload = operation.get("payload")

        # NodeEffect handles retry logic automatically
        response = await self.api_client.post(endpoint, json=payload)

        return ModelEffectOutput(
            success=True,
            result={"status_code": response.status, "data": response.json()}
        )
```

### Mixin Composition Guidelines

When building Tier 2 nodes, **order matters** in MRO:

```python
# ✅ CORRECT - Service mode first, then base node, then features
class MyNode(
    MixinNodeService,     # 1. Service mode (if needed)
    NodeCompute,          # 2. Base node type
    MixinHealthCheck,     # 3. Feature mixins
    MixinMetrics,
):
    pass

# ❌ WRONG - Base node must come after service mode
class MyNode(
    NodeCompute,          # Wrong order
    MixinNodeService,
    MixinMetrics,
):
    pass
```

**Mixin Selection Guide**:

| Mixin | Provides | Include When |
|-------|----------|--------------|
| `MixinNodeService` | Persistent service mode, tool invocation | Building MCP servers, long-lived services |
| `MixinHealthCheck` | Health monitoring | Production deployments, monitoring required |
| `MixinCaching` | Result caching | Expensive computations, repeatable inputs |
| `MixinEventBus` | Event publishing | Need to emit events, inter-service communication |
| `MixinMetrics` | Performance tracking | Need SLA monitoring, performance analysis |
| `MixinWorkflowSupport` | Workflow coordination | Multi-step processes, orchestration |

---

## Tier 3: NodeCoreBase (EXPERT)

### What It Is

**Bare-metal node foundation** providing only essential lifecycle management and container integration. This is the base class that all nodes inherit from, either directly or indirectly.

### Key Characteristics

🛠️ **Minimal assumptions** - Only core lifecycle and container DI
🛠️ **Maximum flexibility** - Build any node type from scratch
🛠️ **Zero pre-configuration** - No mixins, no features, just foundation
🛠️ **Framework development** - Used for building new node types

### What's Included

- ✅ Container-based dependency injection
- ✅ Basic lifecycle: `initialize` → `process` → `complete` → `cleanup`
- ✅ Node ID and metadata tracking
- ✅ Event emission for lifecycle transitions
- ✅ Protocol-based service resolution
- ✅ Error handling foundation

### What's NOT Included

- ❌ No health checks (add MixinHealthCheck)
- ❌ No caching (add MixinCaching)
- ❌ No event publishing (add MixinEventBus)
- ❌ No metrics tracking (add MixinMetrics)
- ❌ No node-type-specific features (use Node*)
- ❌ No transaction management (use NodeEffect)
- ❌ No result validation (use Node* or implement manually)

### When to Use Tier 3

✅ **Use NodeCoreBase when**:
- Building completely new node type (not EFFECT/COMPUTE/REDUCER/ORCHESTRATOR)
- Framework-level development
- Implementing custom node architecture
- Need absolute minimum overhead
- Research or experimental node types

❌ **Don't use NodeCoreBase when**:
- Building standard EFFECT/COMPUTE/REDUCER/ORCHESTRATOR nodes (use Node*)
- Need any standard features (use Node* or ModelService*)
- Want production-ready functionality (use ModelService*)

### Complete Example: Custom Node Type

> **Note**: For standard EFFECT/COMPUTE/REDUCER/ORCHESTRATOR nodes, use the v0.4.0 top-level API:
> `from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator`.
> `NodeCoreBase` is intentionally NOT exported from the top-level API because it's for expert use cases only (building entirely new node types).

```python
"""Custom VALIDATOR node type using NodeCoreBase."""

from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from pydantic import BaseModel
from typing import Any


class ValidatorInput(BaseModel):
    """Input for validator node."""
    data: dict[str, Any]
    schema_name: str
    strict_mode: bool = False


class ValidatorOutput(BaseModel):
    """Output from validator node."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class NodeCustomValidator(NodeCoreBase):
    """
    Custom VALIDATOR node type - not part of standard 4-node architecture.

    Built directly on NodeCoreBase for complete control.
    The node is a thin shell; validation logic belongs in a handler.

    Why NodeCoreBase?
    - New node type (VALIDATOR) not in standard architecture
    - Need complete control over validation logic
    - Want minimal overhead (no caching, no events)
    - Framework experimentation
    """

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Wire up handler - business logic lives there
        self.handler = ValidatorHandler(
            validator=container.get_service("ProtocolValidator"),
            schema_registry=container.get_service("ProtocolSchemaRegistry"),
        )

    async def validate(self, input_data: ValidatorInput) -> ValidatorOutput:
        """Delegate to handler for validation logic."""
        return await self.handler.handle(input_data)


class ValidatorHandler:
    """Handler containing validation business logic.

    Separated from the node so the node remains a thin coordination shell.
    """

    def __init__(self, validator: Any, schema_registry: Any) -> None:
        self.validator = validator
        self.schema_registry = schema_registry

    async def handle(self, input_data: ValidatorInput) -> ValidatorOutput:
        """Validate data against schema."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        schema = await self.schema_registry.get_schema(input_data.schema_name)
        if not schema:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Schema not found: {input_data.schema_name}",
                context={"schema_name": input_data.schema_name},
            )

        result = await self.validator.validate(
            data=input_data.data,
            schema=schema,
            strict=input_data.strict_mode,
        )

        return ValidatorOutput(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
        )
```

### Adding Features to NodeCoreBase

To add features, **compose with mixins manually**. This pattern forms the foundation for ONEX's declarative node architecture (v0.4.0), where nodes define their behavior through configuration rather than inheritance. See [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) for the declarative approach.

> **v0.4.0 Recommendation**: For most use cases, prefer the top-level API:
> `from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator`.
> Only use `NodeCoreBase` directly when building entirely new node types outside the 4-node architecture.

```python
"""NodeCoreBase with manual mixin composition."""

from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics


class NodeCustomValidatorWithFeatures(
    NodeCoreBase,
    MixinHealthCheck,
    MixinMetrics,
):
    """
    Custom node type with selective features.

    Now includes:
    - NodeCoreBase foundation
    - Health monitoring (MixinHealthCheck)
    - Metrics tracking (MixinMetrics)

    Still manual:
    - Input/output handling
    - Business logic
    - Validation specifics
    """

    def __init__(self, container: ModelONEXContainer):
        # Initialize all classes in MRO
        super().__init__(container)

        # Your custom initialization
        self.validator = container.get_service("ProtocolValidator")
```

---

## Decision Matrix

### Visual Decision Tree

```text
START: What are you building?
│
├─ Standard production node? ───────────────────────┐
│  (EFFECT/COMPUTE/REDUCER/ORCHESTRATOR)            │
│  └─ YES ──────────────────────────────────────────┤
│     └─ Need custom mixin composition? ────────┐  │
│        ├─ NO ─────────────────────────────────┤  │
│        │  └─ Use Tier 1: ModelService*        │  │
│        │     (RECOMMENDED - 95% of cases)     │  │
│        │                                       │  │
│        └─ YES ────────────────────────────────┤  │
│           └─ Use Tier 2: Node*                │  │
│              (ADVANCED - 4% of cases)         │  │
│                                                │  │
├─ New node type? ──────────────────────────────┘  │
│  (Not EFFECT/COMPUTE/REDUCER/ORCHESTRATOR)       │
│  └─ YES ──────────────────────────────────────────┤
│     └─ Use Tier 3: NodeCoreBase                  │
│        (EXPERT - 1% of cases)                     │
│                                                    │
└─ Framework development? ──────────────────────────┘
   └─ YES ──────────────────────────────────────────┐
      └─ Use Tier 3: NodeCoreBase                   │
         (Building new Node* classes)               │
                                                     │
END ──────────────────────────────────────────────────┘
```

### Decision Questions

Ask yourself these questions in order:

#### Question 1: Is this a standard node type?

| Node Type | Description | Answer |
|-----------|-------------|--------|
| EFFECT | I/O operations, external APIs, database writes | ✅ Standard |
| COMPUTE | Data transformations, calculations, pure functions | ✅ Standard |
| REDUCER | State aggregation, event reduction, FSM | ✅ Standard |
| ORCHESTRATOR | Workflow coordination, multi-step processes | ✅ Standard |
| VALIDATOR, FILTER, CUSTOM | New node types | ❌ Not standard → Use Tier 3 |

**Standard node?** → Go to Question 2
**Not standard?** → **Use Tier 3 (NodeCoreBase)**

#### Question 2: Do you need custom mixin composition?

| Scenario | Need Custom Composition? | Tier |
|----------|-------------------------|------|
| Standard production features work | ❌ No | Tier 1 |
| Need to remove default mixins | ✅ Yes | Tier 2 |
| Need to add non-standard mixins | ✅ Yes | Tier 2 |
| Need different mixin order | ✅ Yes | Tier 2 |
| Performance-critical (minimize overhead) | ✅ Yes | Tier 2 |

**Need custom composition?** → **Use Tier 2 (Node*)**
**Standard composition works?** → **Use Tier 1 (ModelService*)**

### Common Scenarios

| Scenario | Recommended Tier | Rationale |
|----------|------------------|-----------|
| MCP server with standard features | **Tier 1** | ModelService* has everything pre-wired |
| API client with aggressive retries | **Tier 2** | Need custom circuit breaker config |
| Calculator with expensive computations | **Tier 1** | Caching is critical, ModelServiceCompute has it |
| Real-time analytics (no caching) | **Tier 2** | Exclude caching, keep metrics |
| Workflow with 10+ steps | **Tier 1** | ModelServiceOrchestrator handles complexity |
| Custom validation engine | **Tier 3** | New node type, not in 4-node architecture |
| Database writer with events | **Tier 1** | ModelServiceEffect has transactions + events |
| High-frequency state machine | **Tier 2** | Performance-critical, custom composition |

---

## Feature Comparison

### Comprehensive Feature Matrix

| Feature | Tier 1 (ModelService*) | Tier 2 (Node*) | Tier 3 (NodeCoreBase) |
|---------|------------------------|----------------|----------------------|
| **Setup Complexity** | ⭐ Simple (3 lines) | ⭐⭐ Moderate (5-10 lines) | ⭐⭐⭐ Complex (20+ lines) |
| **Boilerplate Code** | ⚡ Minimal (~3 lines) | 🔧 Moderate (~10 lines) | 📝 Extensive (~50+ lines) |
| **Health Checks** | ✅ Built-in | 🔧 Manual composition | ❌ Not included |
| **Event Publishing** | ✅ Built-in (Effect) | 🔧 Manual composition | ❌ Not included |
| **Result Caching** | ✅ Built-in (Compute) | ✅ Built-in (Compute) | ❌ Not included |
| **Metrics Tracking** | ✅ Built-in | 🔧 Manual composition | ❌ Not included |
| **Transaction Management** | ✅ Built-in (Effect) | ✅ Built-in (Effect) | ❌ Not included |
| **Circuit Breaker** | ✅ Built-in (Effect) | ✅ Built-in (Effect) | ❌ Not included |
| **Retry Logic** | ✅ Built-in (Effect) | ✅ Built-in (Effect) | ❌ Not included |
| **Service Mode** | ✅ Built-in (MCP) | 🔧 Manual composition | ❌ Not included |
| **Type Validation** | ✅ Pydantic | ✅ Python types | ✅ Python types |
| **Input/Output Models** | ✅ Predefined | ✅ Predefined | 🔧 Manual definition |
| **Mixin Composition** | 🔒 Fixed | ✅ Fully flexible | ✅ Fully flexible |
| **Mixin Selection** | 🔒 Pre-selected | ✅ Choose any | ✅ Choose any |
| **Performance Overhead** | ⚡ Excellent | ⚡⚡ Better | ⚡⚡⚡ Best |
| **Memory Footprint** | 🔧 Moderate | ⚡ Lower | ⚡⚡ Lowest |
| **Startup Time** | 🔧 Moderate | ⚡ Faster | ⚡⚡ Fastest |
| **Learning Curve** | ⭐ Easy | ⭐⭐ Moderate | ⭐⭐⭐ Steep |
| **Documentation** | ✅ Comprehensive | ✅ Good | 🔧 Basic |
| **Use Case Coverage** | 95% | 99% | 100% |
| **Production Ready** | ✅ Yes | ✅ Yes | 🔧 Requires work |
| **Recommended For** | Most production nodes | Custom compositions | Framework development |

### Legend

- ✅ **Included** - Feature is built-in and ready to use
- 🔧 **Manual** - Feature requires manual implementation or composition
- ❌ **Not Included** - Feature is not available at this tier
- 🔒 **Fixed** - Cannot be changed (pre-configured)
- ⚡ **Performance Rating** - More ⚡ = better performance
- ⭐ **Complexity Rating** - More ⭐ = more complex

---

## Migration Paths

### Moving Up the Hierarchy (More Features)

#### NodeCoreBase → Node*

**When**: Adding node-type-specific features (caching, transactions, etc.)

**Steps**:

```python
# BEFORE: NodeCoreBase (Tier 3)
class MyNode(NodeCoreBase):
    def __init__(self, container):
        super().__init__(container)
        # Lots of manual setup...

# AFTER: NodeCompute (Tier 2)
class MyNode(NodeCompute):
    def __init__(self, container):
        super().__init__(container)
        # Caching, parallel processing now automatic!
```

**Benefits**: Gain node-specific features without changing much code

#### Node* → ModelService*

**When**: Want pre-configured production features

**Steps**:

```python
# BEFORE: NodeCompute with manual mixins (Tier 2)
class MyNode(
    NodeCompute,
    MixinHealthCheck,
    MixinCaching,
    MixinMetrics
):
    def __init__(self, container):
        super().__init__(container)
        # Manual mixin initialization...

# AFTER: ModelServiceCompute (Tier 1)
class MyNode(ModelServiceCompute):
    def __init__(self, container):
        super().__init__(container)
        # Everything automatic!
```

**Benefits**: Less code, same features, production-tested composition

### Moving Down the Hierarchy (More Control)

#### ModelService* → Node*

**When**: Need custom mixin composition

**Steps**:

```python
# BEFORE: ModelServiceCompute (Tier 1 - fixed composition)
class MyNode(ModelServiceCompute):
    # Includes: NodeService, HealthCheck, Caching, Metrics
    pass

# AFTER: NodeCompute with custom composition (Tier 2)
class MyNode(
    NodeCompute,
    MixinMetrics,
    # Intentionally excluding:
    # - MixinNodeService (not needed)
    # - MixinHealthCheck (external monitoring)
    # - MixinCaching (results too dynamic)
):
    pass
```

**Benefits**: Remove unwanted features, reduce overhead

#### Node* → NodeCoreBase

**When**: Building completely new node type

**Steps**:

```python
# BEFORE: NodeCompute (Tier 2 - COMPUTE semantics)
class MyNode(NodeCompute):
    # Has caching, parallel processing
    pass

# AFTER: NodeCoreBase (Tier 3 - no semantics)
class MyNode(NodeCoreBase):
    # Only foundation, build everything custom
    pass
```

**Benefits**: Complete freedom, no assumptions

### Migration Checklist

When migrating between tiers:

#### Moving Up (Adding Features)

- [ ] Identify which new features you'll gain
- [ ] Remove manual implementations of those features
- [ ] Update tests to use new automatic features
- [ ] Verify performance (may have slight overhead)
- [ ] Update documentation

#### Moving Down (Adding Control)

- [ ] Identify which features you need to keep
- [ ] Add necessary mixin imports
- [ ] Implement any removed features manually
- [ ] Update constructor to compose mixins
- [ ] Verify all features still work
- [ ] Update tests for new composition
- [ ] Benchmark performance improvements

---

## Common Scenarios

### Scenario 1: Building an MCP Server

**Requirements**:
- Long-lived service mode
- Health check endpoint
- Performance metrics
- Standard COMPUTE operations

**Solution**: **Tier 1 - ModelServiceCompute**

```python
from omnibase_core.infrastructure.infra_bases import ModelServiceCompute

class NodeMcpCalculatorCompute(ModelServiceCompute):
    """MCP server with all features built-in."""

    def __init__(self, container):
        super().__init__(container)  # Everything pre-wired!
```

**Why Tier 1?**
- ✅ MixinNodeService included (MCP server mode)
- ✅ Health checks automatic
- ✅ Metrics tracking automatic
- ✅ Caching for expensive calculations
- ✅ Zero boilerplate

**Note on COMPUTE Constraints**: COMPUTE nodes in MCP server mode must remain stateless and side-effect-free. The `MixinNodeService` provides tool invocation handlers that expect deterministic responses. This constraint ensures that cached results remain valid and that parallel tool invocations don't interfere with each other. For stateful operations or side effects, use `ModelServiceEffect` instead.

---

### Scenario 2: High-Performance API Client

**Requirements**:
- External API calls (EFFECT)
- Aggressive retry logic
- Custom circuit breaker config
- Metrics tracking
- NO health checks (external monitoring)
- NO event publishing (not needed)

**Solution**: **Tier 2 - NodeEffect + Custom Mixins**

```python
from omnibase_core.nodes import NodeEffect
from omnibase_core.mixins.mixin_metrics import MixinMetrics

class NodeHighPerfApiEffect(
    NodeEffect,      # Transactions, retry, circuit breaker
    MixinMetrics,    # Track performance
    # Excluding: MixinHealthCheck, MixinEventBus
):
    def __init__(self, container):
        super().__init__(container)

        # Custom circuit breaker configuration
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 30
```

**Why Tier 2?**
- 🔧 Need to exclude default mixins
- 🔧 Custom circuit breaker config
- ⚡ Performance-critical path
- ✅ NodeEffect retry logic needed

---

### Scenario 3: Real-Time Analytics Engine

**Requirements**:
- Pure computations (COMPUTE)
- Time-sensitive data (NO caching)
- Performance metrics essential
- Health monitoring needed
- Standard production deployment

**Solution**: **Tier 2 - NodeCompute + Selective Mixins**

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics

class NodeRealtimeAnalyticsCompute(
    NodeCompute,
    MixinHealthCheck,
    MixinMetrics,
    # Intentionally NO MixinCaching - data changes too frequently
):
    pass
```

**Why Tier 2?**
- ❌ Caching would hurt (stale data)
- ✅ Need health + metrics
- 🔧 Custom composition required

---

### Scenario 4: Custom Validation Engine

**Requirements**:
- New node type (VALIDATOR)
- Not EFFECT/COMPUTE/REDUCER/ORCHESTRATOR
- Custom validation logic
- Minimal overhead
- Framework experimentation

**Solution**: **Tier 3 - NodeCoreBase**

> **Note**: For standard EFFECT/COMPUTE/REDUCER/ORCHESTRATOR nodes, use the v0.4.0 top-level API instead:
> `from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator`

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

class NodeCustomValidator(NodeCoreBase):
    """Custom VALIDATOR node type."""

    def __init__(self, container):
        super().__init__(container)
        # Everything built from scratch
```

**Why Tier 3?**
- 🆕 New node type (not in 4-node architecture)
- 🛠️ Need complete control
- ⚡ Minimal overhead required
- 🔬 Framework experimentation

---

### Scenario 5: Database Writer with Event Publishing

**Requirements**:
- Database writes (EFFECT)
- Transaction management
- Event publishing on completion
- Health monitoring
- Standard production features

**Solution**: **Tier 1 - ModelServiceEffect**

```python
from omnibase_core.infrastructure.infra_bases import ModelServiceEffect

class NodeDatabaseWriterEffect(ModelServiceEffect):
    """Database writer with all features."""

    async def execute_effect(self, input_data):
        # Write to database
        result = await self.db.write(input_data.operation_data)

        # Publish event (automatic correlation tracking)
        await self.publish_event("write.completed", result)

        return ModelEffectOutput(success=True, result=result)
```

**Why Tier 1?**
- ✅ Transactions built-in
- ✅ Event publishing built-in
- ✅ Health checks automatic
- ✅ Standard composition works perfectly

---

## When to Use Which Tier

### Quick Reference Table

| Use Case | Tier | Class | Reason |
|----------|------|-------|--------|
| **Standard production node** | 1 | ModelService* | Pre-configured, production-tested |
| **MCP server** | 1 | ModelService* | Service mode included |
| **API client** | 1 or 2 | ModelServiceEffect or NodeEffect | Depends on retry config |
| **Calculator with caching** | 1 | ModelServiceCompute | Caching is critical |
| **Real-time analytics** | 2 | NodeCompute | Exclude caching |
| **Database writer** | 1 | ModelServiceEffect | Transactions + events |
| **Workflow orchestrator** | 1 | ModelServiceOrchestrator | Complex coordination |
| **Custom mixin composition** | 2 | Node* | Need flexibility |
| **Performance-critical** | 2 | Node* | Reduce overhead |
| **New node type** | 3 | NodeCoreBase | Not in 4-node architecture |
| **Framework development** | 3 | NodeCoreBase | Building Node* classes |

### Decision Flowchart Summary

```text
┌─────────────────────────────────────┐
│  Is it EFFECT/COMPUTE/REDUCER/ORCH? │
└───────────┬─────────────────────────┘
            │
            ├─YES──► Standard production needs? ──YES──► TIER 1: ModelService*
            │                     │
            │                     NO
            │                     │
            │                     ► Custom mixin composition? ──YES──► TIER 2: Node*
            │                     │
            │                     NO ─────────────────────────► TIER 2: Node*
            │
            └─NO───► New node type? ──YES──► TIER 3: NodeCoreBase
                             │
                             NO
                             │
                             ► Framework dev? ──YES──► TIER 3: NodeCoreBase
                                           │
                                           NO
                                           │
                                           ► Reconsider requirements!
```

---

## Best Practices

### Do's

✅ **Start with Tier 1** - ModelService* covers 95% of cases
✅ **Profile before optimizing** - Don't move to Tier 2 for performance without measurements
✅ **Use Node* for custom composition** - When you need specific mixin combinations
✅ **Document tier choice** - Explain why you chose specific tier in docstrings
✅ **Test tier-specific features** - Ensure caching, events, metrics work as expected
✅ **Follow MRO guidelines** - Service mode first, base node second, features third

### Don'ts

❌ **Don't use Tier 3 for standard nodes** - Use Node* or ModelService*
❌ **Don't optimize prematurely** - Stay at Tier 1 until proven bottleneck
❌ **Don't mix tiers** - Pick one tier and stick with it
❌ **Don't skip super().__init__()** - Required for proper initialization
❌ **Don't reinvent features** - Use mixins instead of reimplementing
❌ **Don't ignore MRO order** - Wrong order breaks functionality

---

## Summary

### The Three Tiers

1. **Tier 1 (ModelService*)** - Production-ready wrappers with pre-configured mixins
   - **Use for**: 95% of production nodes
   - **Trade-off**: Less control, more productivity

2. **Tier 2 (Node*)** - Specialized node classes with flexible mixin composition
   - **Use for**: 4% of nodes needing custom composition
   - **Trade-off**: Balanced control and convenience

3. **Tier 3 (NodeCoreBase)** - Bare-metal foundation with minimal assumptions
   - **Use for**: 1% of nodes requiring complete custom control
   - **Trade-off**: Maximum flexibility, maximum effort

### Key Takeaway

**Start with Tier 1 (ModelService*) and only move down the hierarchy when you have a specific, proven need for more control.**

---

## Related Documentation

### In This Repository

- **[Node Building Guide](../guides/node-building/README.md)** - Step-by-step tutorials for building nodes
- **[COMPUTE Node Tutorial](../guides/node-building/03_COMPUTE_NODE_TUTORIAL.md)** - Practical COMPUTE node example
- **[EFFECT Node Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md)** - Practical EFFECT node example
- **[ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)** - Understanding the 4-node pattern
- **[Mixin Architecture](MIXIN_ARCHITECTURE.md)** - Deep dive into mixin system
- **[Container Types](CONTAINER_TYPES.md)** - ModelContainer vs ModelONEXContainer
- **[Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)** - Structured error handling
- **[Threading Guide](../guides/THREADING.md)** - Thread safety considerations

### Cross-Repository References

The node class hierarchy is used across the ONEX ecosystem:

- **omnibase_core.protocols** - Protocol definitions that nodes implement (`ProtocolNode`, `ProtocolService`)
- **omniintelligence** - AI/ML nodes using `ModelServiceCompute` for inference pipelines
- **omniagent** - Agent nodes using `ModelServiceOrchestrator` for multi-step workflows
- **omnimcp** - MCP server implementations using `ModelServiceEffect` for tool invocation

---

**Ready to build?** → [Node Building Guide](../guides/node-building/README.md) ⭐

**Questions?** → [Documentation Index](../INDEX.md)

---

## Naming Convention Migration (v0.4.0) - COMPLETED

As of v0.4.0, the declarative nodes ARE the default implementation. The "Declarative" suffix has been removed because these ARE the standard now.

### Node Classes (v0.4.0+)

| Node Type | Class | Location | Pattern |
|-----------|-------|----------|---------|
| **Reducer** | `NodeReducer` | `nodes/node_reducer.py` | FSM-driven |
| **Orchestrator** | `NodeOrchestrator` | `nodes/node_orchestrator.py` | Workflow-driven |
| **Compute** | `NodeCompute` | `nodes/node_compute.py` | Contract-based |
| **Effect** | `NodeEffect` | `nodes/node_effect.py` | Transaction-based |

### Key Points

- **`NodeReducer`** and **`NodeOrchestrator`** are FSM/workflow-driven by default
- **No "Declarative" suffix** - these ARE the standard implementations
- **All nodes use declarative YAML contracts**

### Import Examples

```python
# v0.4.0+ Top-Level API (RECOMMENDED)
from omnibase_core.nodes import (
    NodeCompute,
    NodeEffect,
    NodeOrchestrator,
    NodeReducer,
    # Input/Output models also available from top-level
    ModelComputeInput,
    ModelComputeOutput,
    ModelEffectInput,
    ModelEffectOutput,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    ModelReducerInput,
    ModelReducerOutput,
)
```

### Import Patterns

| Pattern | Import | Status |
|---------|--------|--------|
| **Top-level API** | `from omnibase_core.nodes import NodeReducer, ...` | **RECOMMENDED** |
| **Direct module** | `from omnibase_core.nodes.node_reducer import NodeReducer` | Supported (internal) |

**Note**: Legacy imperative nodes were removed in v0.4.0. All nodes now use declarative YAML contracts.

Migration to declarative nodes was completed in v0.4.0.

---

**Correlation ID**: `a3c8f7d4-2b5e-4a19-9f3a-8d6e1c4b7a2f`
**Document Version**: 1.3.1
**Last Updated**: 2025-12-06
