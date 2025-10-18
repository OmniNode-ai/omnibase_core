# What is a Node?

**Reading Time**: 5 minutes
**Prerequisites**: None
**Next**: [Node Types](02_NODE_TYPES.md)

## Definition

A **node** in the ONEX framework is a **self-contained, reusable component** that performs a specific type of operation within a microservices architecture. Think of nodes as specialized workers, each designed to excel at one particular kind of task.

### Simple Analogy

Imagine a restaurant kitchen:

- **EFFECT Node** = The server (interfaces with external world - customers, suppliers)
- **COMPUTE Node** = The chef (transforms ingredients into dishes)
- **REDUCER Node** = The prep cook (aggregates ingredients, combines components)
- **ORCHESTRATOR Node** = The kitchen manager (coordinates all activities)

Each has a specific role. Together, they create a complete system.

## Core Concept

```
┌──────────────────────────────────────────────────────────────┐
│                         ONEX Node                             │
│                                                               │
│  ┌────────┐      ┌───────────┐      ┌────────┐              │
│  │ Input  │ ───▶ │ Process() │ ───▶ │ Output │              │
│  └────────┘      └───────────┘      └────────┘              │
│                                                               │
│  • Strongly typed input/output                               │
│  • Single responsibility                                     │
│  • Dependency injection via container                        │
│  • Error handling built-in                                   │
│  • Performance tracking                                      │
└──────────────────────────────────────────────────────────────┘
```

## Key Characteristics

### 1. Single Responsibility

Each node does **one thing well**:

```python
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

```python
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

```python
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

```python
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

# Nodes raise structured errors
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="Input validation failed",
    context={"field": "email", "value": input_value}
)
```

### 5. Performance Tracking

Every node can track its performance:

```python
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

```python
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

```python
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
                       │    (Aggregate)           │
                       │         │                │
                       │         ▼                │
                       │  ORCHESTRATOR Node ──────┼───▶ Coordinated result
                       │  (Coordinate)            │
```

### Data Flow Example

**Scenario**: Process user signup

```python
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

```python
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
- ✅ Single responsibility: Pure computation
- ✅ Typed input/output
- ✅ Dependency injection via container
- ✅ Built-in caching
- ✅ Performance tracking

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
- A specialized, reusable component in the ONEX framework
- Strongly typed with clear input/output contracts
- Follows single responsibility principle
- Uses dependency injection for flexibility
- Includes built-in error handling and performance tracking

**Four node types**:
1. **EFFECT**: External interactions (APIs, databases, files)
2. **COMPUTE**: Data transformation and computation
3. **REDUCER**: Data aggregation and state management
4. **ORCHESTRATOR**: Workflow coordination

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
# Minimal node structure
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCoreBase):
    """My custom compute node."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Your initialization here

    async def process(self, input_data):
        """Your processing logic here."""
        # Validate input
        # Execute operation
        # Return output
        pass
```

**Essential imports**:
- `NodeCoreBase` - Base class for all nodes
- `ModelONEXContainer` - Dependency injection container
- `ModelOnexError` - Structured error handling
- `EnumCoreErrorCode` - Error code enumeration

**Next step**: [Learn about the four node types →](02_NODE_TYPES.md)
