> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Node Building](./README.md) > What is a Node?

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../../CLAUDE.md).

# What is a Node?

**Reading Time**: 5 minutes
**Prerequisites**: None
**Next**: [Node Types](02_NODE_TYPES.md)

## Definition

A **node** in the ONEX framework is a **self-contained, reusable component** that performs a specific type of operation within a microservices architecture. Think of nodes as specialized workers, each designed to excel at one particular kind of task.

> **Key Concept: Nodes and Handlers**
> Nodes in ONEX are **thin coordination shells**. They do not contain business logic. Instead, they delegate to **handlers**, which are resolved from YAML contracts at runtime. This separation ensures testability, reusability, and contract-driven behavior.
> - **Node**: Coordination shell that manages lifecycle, dependency injection, and contract enforcement.
> - **Handler**: Contains the actual business logic. Selected by the node's YAML contract.
> - **YAML Contract**: Declares the node's behavior, including which handler to use and what output constraints apply.
> See [Handler Architecture](../../architecture/HANDLER_ARCHITECTURE.md) and [MIXIN_ARCHITECTURE.md](../../architecture/MIXIN_ARCHITECTURE.md) for complete details.

### Simple Analogy

Imagine a restaurant kitchen:

- **EFFECT Node** = The server (interfaces with external world - customers, suppliers)
- **COMPUTE Node** = The chef (transforms ingredients into dishes)
- **REDUCER Node** = The prep cook with a recipe card (FSM-driven state aggregation using intents)
- **ORCHESTRATOR Node** = The kitchen manager with a workflow chart (coordinates multi-step activities with leases)

Each has a specific role. Together, they create a complete system.

## Core Concept

```
┌──────────────────────────────────────────────────────────────┐
│                     ONEX Node (thin shell)                    │
│                                                               │
│  ┌────────┐    ┌─────────────────┐    ┌────────┐            │
│  │ Input  │ ──▶│ Handler         │──▶ │ Output │            │
│  └────────┘    │ (business logic)│    └────────┘            │
│                └─────────────────┘                            │
│                        ^                                      │
│                        |                                      │
│                ┌───────────────┐                              │
│                │ YAML Contract │                              │
│                │ (declares     │                              │
│                │  behavior)    │                              │
│                └───────────────┘                              │
│                                                               │
│  • Strongly typed input/output                               │
│  • Node delegates to handler (no logic in node)              │
│  • Dependency injection via ModelONEXContainer                │
│  • Error handling built-in                                   │
│  • Performance tracking                                      │
└──────────────────────────────────────────────────────────────┘
```

## Key Characteristics

### 1. Single Responsibility

Each node does **one thing well**:

```
# ✅ Good: Single responsibility
class NodeDataValidatorCompute:
    """Validates data structure and content."""
    async def process(self, input_data):
        return self.validate(input_data)

# ❌ Bad: Multiple responsibilities
class NodeDataValidatorAndSaverComputeEffect:
    """Validates AND saves data."""  # Too many responsibilities!
    async def process(self, input_data):
        validated = self.validate(input_data)
        self.save_to_database(validated)  # Mixing COMPUTE and EFFECT!
```

### 2. Strongly Typed

Inputs and outputs are **explicitly typed**:

```
# Example from real NodeCompute
async def process(
    self,
    input_data: ModelComputeInput[T_Input]  # ← Typed input
) -> ModelComputeOutput[T_Output]:          # ← Typed output
    """Process with type safety."""
    # Type checking happens automatically via Pydantic
```

### 3. Dependency Injection

Nodes receive dependencies through a **container**:

```
class NodeMyServiceCompute(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Container provides all dependencies
        self.logger = container.logger
        self.config = container.compute_cache_config
```

No manual dependency wiring. The container handles it.

### 4. Error Handling

Structured error handling is **built-in**:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Nodes raise structured errors
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="Input validation failed",
    context={"field": "email", "value": input_value}
)
```

### 5. Performance Tracking

Every node can track its performance:

```
# Built into base classes
start_time = time.time()
result = await self.process(input_data)
processing_time_ms = (time.time() - start_time) * 1000

# Metrics available for monitoring
self.computation_metrics[operation_id] = {
    "duration_ms": processing_time_ms,
    "operation_type": input_data.operation_type
}
```

## Why Nodes?

### Problem: Monolithic Systems

```
# ❌ Monolithic approach
class DataService:
    def process_request(self, data):
        # Fetch from database
        db_data = self.db.get(data.id)
        # Transform data
        transformed = self.transform(db_data)
        # Save results
        self.db.save(transformed)
        # Notify other services
        self.notify(transformed)
        # All responsibilities mixed together!
```

### Solution: Node-Based Architecture

```
# ✅ Node-based approach

# EFFECT: Database interaction
class NodeDataFetcherEffect:
    async def process(self, input_data):
        return await self.db.get(input_data.id)

# COMPUTE: Data transformation
class NodeDataTransformerCompute:
    async def process(self, input_data):
        return self.transform(input_data)

# EFFECT: Database save
class NodeDataSaverEffect:
    async def process(self, input_data):
        await self.db.save(input_data)
        return {"saved": True}

# ORCHESTRATOR: Coordinate workflow
class NodeDataProcessorOrchestrator:
    async def process(self, input_data):
        # Fetch → Transform → Save
        fetched = await self.fetcher.process(input_data)
        transformed = await self.transformer.process(fetched)
        result = await self.saver.process(transformed)
        return result
```

**Benefits**:
- Each component testable in isolation
- Easy to swap implementations
- Clear separation of concerns
- Scalable (each node can scale independently)

## Nodes in the ONEX Ecosystem

### The Four Node Types

```
External World          │      ONEX System        │   Data Flow
                       │                          │
┌─────────────────┐    │                          │
│ APIs, Databases │────┼───▶ EFFECT Node ────────┼───▶ Raw data
│ File Systems    │    │     (Fetch/Save)         │
└─────────────────┘    │                          │
                       │         │                │
                       │         ▼                │
                       │    COMPUTE Node ─────────┼───▶ Transformed data
                       │    (Transform)           │
                       │         │                │
                       │         ▼                │
                       │    REDUCER Node ─────────┼───▶ Aggregated data
                       │    (FSM + Intents)       │
                       │         │                │
                       │         ▼                │
                       │  ORCHESTRATOR Node ──────┼───▶ Coordinated result
                       │  (Workflows + Leases)    │
```

### Data Flow Example

**Scenario**: Process user signup

```
# 1. EFFECT: Validate email via external API
email_valid = await effect_node.process(
    ModelEffectInput(email=user.email)
)

# 2. COMPUTE: Calculate user tier based on data
user_tier = await compute_node.process(
    ModelComputeInput(
        email_status=email_valid,
        signup_data=user.data
    )
)

# 3. REDUCER: Aggregate user profile
user_profile = await reducer_node.process(
    ModelReducerInput(
        user_data=user.data,
        email_valid=email_valid,
        tier=user_tier
    )
)

# 4. EFFECT: Save to database
save_result = await effect_node.process(
    ModelEffectInput(profile=user_profile)
)

# 5. ORCHESTRATOR: Coordinate entire workflow
result = await orchestrator_node.process(
    ModelOrchestratorInput(user_signup_request=user)
)
```

## Real-World Example

Let's look at an actual node from omnibase_core:

```
# From: src/omnibase_core/nodes/node_compute.py

class NodeCompute(NodeCoreBase):
    """
    Pure computation node for deterministic operations.

    Implements computational pipeline with input → transform → output pattern.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize with dependency injection."""
        super().__init__(container)

        # Get configuration from container
        cache_config = container.compute_cache_config

        # Initialize caching layer
        self.computation_cache = ModelComputeCache(
            max_size=cache_config.max_size,
            ttl_seconds=cache_config.ttl_seconds
        )

        # Performance tracking
        self.computation_metrics: dict[str, dict[str, float]] = {}

    async def process(
        self,
        input_data: ModelComputeInput[T_Input]
    ) -> ModelComputeOutput[T_Output]:
        """
        REQUIRED: Execute pure computation.

        Args:
            input_data: Strongly typed computation input

        Returns:
            Strongly typed computation output with performance metrics
        """
        start_time = time.time()

        # Validate input
        self._validate_compute_input(input_data)

        # Check cache
        cache_key = self._generate_cache_key(input_data)
        cached_result = self.computation_cache.get(cache_key)

        if cached_result:
            return ModelComputeOutput(
                result=cached_result,
                cache_hit=True
            )

        # Execute computation
        result = await self._execute_computation(input_data)

        # Track performance
        processing_time = (time.time() - start_time) * 1000

        return ModelComputeOutput(
            result=result,
            processing_time_ms=processing_time,
            cache_hit=False
        )
```

**Notice**:
- The node itself is a thin shell -- it manages caching, validation, and metrics
- Business logic (the actual computation) lives in `_execute_computation()`, which is the handler's responsibility
- The node coordinates lifecycle; the handler owns the domain logic
- Dependency injection via `ModelONEXContainer`
- Typed input/output with Pydantic models

## When to Create a Node

Create a new node when you have:

✅ **A distinct operation** that fits one of the four types
✅ **Reusable logic** that might be used in multiple places
✅ **Testable unit** with clear input/output
✅ **Performance requirements** that benefit from caching/optimization
✅ **Scalability needs** (node can scale independently)

Don't create a node when:

❌ **Simple utility function** would suffice
❌ **One-time script** with no reuse potential
❌ **Tightly coupled** to a specific implementation
❌ **No clear input/output** contract

## Summary

**A node is**:
- A thin coordination shell that delegates business logic to handlers
- Strongly typed with clear input/output contracts defined in YAML
- Follows single responsibility principle
- Uses dependency injection via `ModelONEXContainer`
- Includes built-in error handling and performance tracking
- Never contains business logic directly -- handlers own the logic

**Four node types** (v0.4.0):
1. **EFFECT**: External interactions (APIs, databases, files)
2. **COMPUTE**: Data transformation and computation
3. **REDUCER**: FSM-driven state aggregation using ModelIntent
4. **ORCHESTRATOR**: Workflow coordination with ModelAction and leases

**Key benefits**:
- Testability
- Reusability
- Scalability
- Maintainability

## What's Next?

Now that you understand what nodes are, learn about the **four node types** and when to use each:

→ [Next: Node Types](02_NODE_TYPES.md)

## Quick Reference

```python
# v0.4.0: Import nodes directly from omnibase_core.nodes
from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator

# Nodes are thin shells -- business logic belongs in handlers.
# A node delegates to its handler, which is resolved from its YAML contract.

# Example: Custom compute node (thin shell pattern)
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCoreBase):
    """Custom compute node -- delegates to handler for business logic."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # Resolve services via protocol-based DI
        # Business logic lives in the handler, not here

    async def process(self, input_data):
        """Delegate to handler resolved from YAML contract."""
        handler = self._resolve_handler()
        return await handler.execute(input_data)
```

**Essential imports** (v0.4.0):
- `from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator` - Primary node implementations
- `NodeCoreBase` - Base class for custom nodes
- `ModelONEXContainer` - Dependency injection container (not `ModelContainer`)
- `ModelOnexError` - Structured error handling
- `EnumCoreErrorCode` - Error code enumeration

> **Note**: In v0.4.0, `NodeReducer` and `NodeOrchestrator` are the primary implementations (FSM-driven and workflow-driven respectively). Legacy implementations have been removed from the codebase.

**Next step**: [Learn about the four node types -->](02_NODE_TYPES.md)
