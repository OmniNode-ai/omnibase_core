> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > ModelIntent Architecture

# ModelIntent Architecture

> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions. This document expands on the **Intent** concept from the terminology guide.

## Overview

**ModelIntent** is a declarative side effect model that enables pure functional state machine (FSM) patterns in the ONEX 4-Node Architecture. Instead of executing side effects directly, nodes (particularly Reducers) emit Intents describing what side effects should occur. Effect nodes then consume and execute these Intents, maintaining strict separation between state transformation and side effect execution.

### Role in Pure FSM Reducer Pattern

The Reducer node implements a pure function that transforms state without performing I/O or side effects:

```
δ(state, action) → (new_state, intents[])
```

**Key Principles**:
- **Purity**: Reducer contains no I/O, no logging, no metrics collection
- **Declarative**: Reducer describes side effects via Intents, doesn't execute them
- **Separation**: Effect node consumes Intents and handles all external interactions
- **Testability**: Pure functions are deterministic and easily testable without mocks

### Side Effect Declaration vs Execution

The Intent pattern separates **what** should happen (Intent declaration) from **how** it happens (Intent execution):

1. **Reducer**: Emits ModelIntent objects describing desired side effects
2. **Effect Node**: Receives Intents and executes them with retry, transactions, circuit breakers

This separation enables:
- Pure, deterministic state transformations
- Centralized side effect management
- Consistent error handling and retry logic
- Better observability through Intent tracking

---

## Pure FSM Pattern

### Formula

The Reducer implements a pure finite state machine:

```
δ(state, action) → (new_state, intents[])
```

Where:
- **δ** (delta): Pure transformation function
- **state**: Current state (immutable input)
- **action**: Input data to process
- **new_state**: Transformed state (immutable output)
- **intents[]**: List of side effects to execute (declarative)

### Reducer Describes, Effect Executes

**Reducer Responsibilities** (Pure):
- Transform input data to output data
- Aggregate, merge, fold, normalize
- Detect conflicts and resolve them
- Emit Intents for metrics, logging, notifications

**Effect Responsibilities** (Impure):
- Execute Intents with transaction support
- Handle retries, timeouts, circuit breakers
- Perform actual I/O (files, databases, APIs)
- Rollback on failures

### FSM Purity Guarantees

A pure Reducer FSM guarantees:

1. **Determinism**: Same input always produces same output
2. **No Hidden State**: No instance variables modified during execution
3. **No Side Effects**: No I/O, logging, or external interactions
4. **Referential Transparency**: Function calls can be replaced with their results
5. **Testability**: Easy to test without mocks or infrastructure

**Impure Code (Anti-Pattern)**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # ❌ Direct side effects - breaks purity
    self.logger.info("Reduction complete")
    self.metrics.increment("reductions")
    await self.db.save(result)

    return ModelReducerOutput(result=result)
```

**Pure Code (Intent Pattern)**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # ✅ Emit Intents - maintains purity
    intents = [
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={"level": "INFO", "message": "Reduction complete"},
        ),
        ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={"metric": "reductions", "value": 1},
        ),
        ModelIntent(
            intent_type="write",
            target="database_service",
            payload={"collection": "results", "data": result},
        ),
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

---

## Intent vs Direct Side Effects

### Comparison Table

| Aspect | Intent Emission (Pure) | Direct Execution (Impure) |
|--------|------------------------|---------------------------|
| **Purity** | ✅ Pure function | ❌ Impure function |
| **Determinism** | ✅ Same input → same output | ❌ Output depends on external state |
| **Testability** | ✅ Easy to test, no mocks | ❌ Requires mocks, complex setup |
| **Error Handling** | ✅ Centralized in Effect node | ❌ Scattered across codebase |
| **Retry Logic** | ✅ Handled by Effect node | ❌ Must implement per side effect |
| **Transactions** | ✅ Effect node manages rollback | ❌ Manual transaction management |
| **Observability** | ✅ Intents are traceable | ❌ Side effects are hidden |
| **Composability** | ✅ Intents can be combined, filtered | ❌ Side effects can't be composed |
| **Performance** | ✅ Parallel intent execution | ❌ Sequential side effect execution |

### Benefits of Intent Pattern

**1. Testability**

Pure functions with Intents are trivially testable:

```
def test_reducer_emits_metric_intent():
    reducer = NodeReducer(container)
    input_data = ModelReducerInput(data=[1, 2, 3], reduction_type=EnumReductionType.SUM)

    output = await reducer.process(input_data)

    # Assert on result (pure computation)
    assert output.result == 6

    # Assert on Intents (side effect declarations)
    metric_intents = [i for i in output.intents if i.intent_type == "log_metric"]
    assert len(metric_intents) == 1
    assert metric_intents[0].payload["metric_type"] == "reduction_metrics"
```

No mocks, no infrastructure, no external dependencies.

**2. Determinism**

Pure functions always produce the same output for the same input:

```
# Called twice with same input
output1 = await reducer.process(input_data)
output2 = await reducer.process(input_data)

# Always produces identical results
assert output1.result == output2.result
assert output1.intents == output2.intents
```

**3. Composability**

Intents can be filtered, transformed, or composed before execution:

```
# Filter high-priority Intents
high_priority = [i for i in output.intents if i.priority >= 8]

# Transform Intents (e.g., add correlation context)
enriched = [
    i.model_copy(update={"payload": {**i.payload, "correlation_id": str(uuid4())}})
    for i in output.intents
]

# Execute Intents in priority order
sorted_intents = sorted(output.intents, key=lambda i: i.priority, reverse=True)
for intent in sorted_intents:
    await effect_node.execute_intent(intent)
```

**4. Centralized Error Handling**

All side effect errors are handled in one place (Effect node):

```
# Effect node handles retries, circuit breakers, rollbacks
async def execute_intent(self, intent: ModelIntent):
    try:
        result = await self._execute_with_retry(intent)
        return result
    except Exception as e:
        # Centralized error handling
        await self._handle_intent_failure(intent, e)
        raise
```

### FSM Purity Guarantees

**Guarantee 1: No Hidden State**

```
class NodeReducer(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

        # ✅ Configuration only (immutable)
        self.default_batch_size = 1000
        self.max_memory_usage_mb = 512

        # ❌ NO MUTABLE STATE
        # - No self.reduction_metrics (emit Intents instead)
        # - No self.active_windows (pass through state)
        # - No self.cache (stateless processing)
```

**Guarantee 2: Referential Transparency**

```
# Function call can be replaced with its value
output = await reducer.process(input_data)

# Equivalent to:
output = ModelReducerOutput(
    result=6,
    intents=[
        ModelIntent(intent_type="log_metric", target="metrics_service", ...),
        ModelIntent(intent_type="log_event", target="logging_service", ...),
    ],
)
```

**Guarantee 3: No Side Effects During Execution**

```
async def process(self, input_data):
    # ✅ Pure computation only
    result = self._reduce(input_data.items)

    # ✅ Emit Intents (declarations, not executions)
    intents = self._create_intents(result, processing_time)

    # ❌ NO side effects here
    # - No logging
    # - No metrics
    # - No database writes
    # - No API calls

    return ModelReducerOutput(result=result, intents=intents)
```

---

## ModelIntent Fields

### Field Specification

```
class ModelIntent(BaseModel):
    """Intent declaration for side effects from pure Reducer FSM."""

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )

    intent_type: str = Field(
        ...,
        description="Type of intent (log_metric, log_event, write, notify)",
        min_length=1,
        max_length=100,
    )

    target: str = Field(
        ...,
        description="Target service to execute intent (metrics_service, logging_service)",
        min_length=1,
        max_length=200,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Intent payload data",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    lease_id: UUID | None = Field(
        default=None,
        description="Optional lease ID if this intent relates to a leased workflow",
    )

    epoch: int | None = Field(
        default=None,
        description="Optional epoch if this intent relates to versioned state",
        ge=0,
    )
```

### Field Descriptions

**intent_id** (UUID):
- Unique identifier for this Intent
- Auto-generated via `uuid4()`
- Used for tracking, correlation, deduplication

**intent_type** (str):
- Type of side effect to perform
- Common types: `log_metric`, `log_event`, `write`, `notify`
- Determines which handler processes the Intent
- Length: 1-100 characters

**target** (str):
- Service or system that executes the Intent
- Examples: `metrics_service`, `logging_service`, `database_service`, `event_bus`
- Maps to specific Effect handlers
- Length: 1-200 characters

**payload** (dict[str, Any]):
- Intent-specific data
- Structure depends on `intent_type` and `target`
- Examples:
  - `log_metric`: `{"metric": "processing_time", "value": 123.45}`
  - `log_event`: `{"level": "INFO", "message": "Operation complete"}`
  - `write`: `{"collection": "results", "data": {...}}`

**priority** (int):
- Execution priority (1-10, higher = more urgent)
- Default: 1 (low priority)
- Effect node can sort Intents by priority before execution
- Use cases:
  - Priority 10: Critical notifications, alerts
  - Priority 5-7: Important metrics, audit logs
  - Priority 1-3: Optional logging, debug events

**lease_id** (UUID | None):
- Optional lease identifier for single-writer workflows
- Links Intent to a specific workflow execution
- Enables lease-based conflict resolution
- Default: None

**epoch** (int | None):
- Optional version/epoch for state synchronization
- Enables optimistic concurrency control
- Monotonically increasing per workflow
- Default: None

---

## Usage Patterns

### Emitting Intents from Reducer

**Basic Pattern**:

```
from omnibase_core.models.model_intent import ModelIntent
from omnibase_core.models.model_reducer_output import ModelReducerOutput

async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    start_time = time.time()

    # Pure computation (state transformation)
    result = self._reduce(input_data.items)

    processing_time = (time.time() - start_time) * 1000

    # Emit Intents for side effects
    intents = [
        # Intent 1: Log metrics
        ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={
                "metric_type": "reduction_metrics",
                "reduction_type": input_data.reduction_type.value,
                "processing_time_ms": processing_time,
                "success": True,
                "items_processed": len(input_data.items),
            },
            priority=3,
        ),

        # Intent 2: Log completion event
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={
                "level": "INFO",
                "message": f"Reduction completed: {input_data.reduction_type.value}",
                "context": {
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "processing_time_ms": processing_time,
                    "items_processed": len(input_data.items),
                },
            },
            priority=2,
        ),
    ]

    return ModelReducerOutput(
        result=result,
        operation_id=input_data.operation_id,
        reduction_type=input_data.reduction_type,
        processing_time_ms=processing_time,
        items_processed=len(input_data.items),
        intents=intents,  # Attach Intents to output
    )
```

**Advanced Pattern: Conditional Intents**:

```
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    result = self._reduce(input_data.items)
    intents = []

    # Always emit metrics
    intents.append(
        ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={"metric": "reductions_total", "value": 1},
            priority=3,
        )
    )

    # Conditional: Emit alert if processing time exceeds threshold
    if processing_time > 5000:  # 5 seconds
        intents.append(
            ModelIntent(
                intent_type="notify",
                target="alert_service",
                payload={
                    "severity": "WARNING",
                    "message": f"Slow reduction: {processing_time}ms",
                    "operation_id": str(input_data.operation_id),
                },
                priority=8,  # High priority for alerts
            )
        )

    # Conditional: Emit write Intent if persistence enabled
    if input_data.metadata.get("persist_result"):
        intents.append(
            ModelIntent(
                intent_type="write",
                target="database_service",
                payload={
                    "collection": "reduction_results",
                    "data": result,
                    "operation_id": str(input_data.operation_id),
                },
                priority=5,
            )
        )

    return ModelReducerOutput(result=result, intents=intents)
```

**Pattern: Lease-Tracked Intents**:

```
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    result = self._reduce(input_data.items)

    # Create Intent with lease tracking
    intent = ModelIntent(
        intent_type="write",
        target="database_service",
        payload={"collection": "results", "data": result},
        priority=5,
        lease_id=input_data.lease_id,  # Link to workflow lease
        epoch=input_data.epoch,         # Link to state version
    )

    return ModelReducerOutput(result=result, intents=[intent])
```

### Processing Intents (Effect Node)

Effect nodes are thin coordination shells that delegate Intent execution to handlers
resolved from the DI container. The node does not contain inline routing logic.

**Intent Consumption Pattern**:

```
from omnibase_core.models.model_intent import ModelIntent
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeIntentExecutor(NodeCoreBase):
    """Effect node that delegates Intent execution to registered handlers."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Resolve the handler registry -- handlers own the execution logic
        self.handler_registry = container.get_service("intent_handler_registry")

    async def execute_intents(
        self,
        intents: list[ModelIntent],
    ) -> dict[UUID, Any]:
        """
        Execute list of Intents with priority-based ordering.

        Returns:
            Dict mapping intent_id to execution result.
        """
        results: dict[UUID, Any] = {}

        # Sort by priority (highest first)
        sorted_intents = sorted(intents, key=lambda i: i.priority, reverse=True)

        for intent in sorted_intents:
            try:
                # Delegate to the appropriate handler from registry
                handler = self.handler_registry.get(intent.intent_type)
                result = await handler.execute(intent)
                results[intent.intent_id] = result
            except Exception as e:
                await self._handle_intent_failure(intent, e)
                results[intent.intent_id] = {"error": str(e)}

        return results
```

Each Intent type (e.g., `log_metric`, `log_event`, `write`, `notify`) has a
corresponding handler registered in the `intent_handler_registry`. The node
coordinates execution order and error handling; the handlers own the business logic.

**Error Handling for Failed Intents**:

```python
async def _handle_intent_failure(
    self,
    intent: ModelIntent,
    error: Exception
) -> None:
    """Handle Intent execution failure with retry and logging."""

    # Log failure
    emit_log_event(
        LogLevel.ERROR,
        f"Intent execution failed: {intent.intent_type}",
        {
            "intent_id": str(intent.intent_id),
            "intent_type": intent.intent_type,
            "target": intent.target,
            "error": str(error),
        },
    )

    # Retry for critical Intents (priority >= 8)
    if intent.priority >= 8:
        try:
            await asyncio.sleep(1.0)  # Backoff
            handler = self.handler_registry.get(intent.intent_type)
            await handler.execute(intent)
        except Exception as retry_error:
            emit_log_event(
                LogLevel.CRITICAL,
                f"Critical Intent failed after retry: {intent.intent_type}",
                {
                    "intent_id": str(intent.intent_id),
                    "retry_error": str(retry_error),
                },
            )

    # Update failure metrics
    await self._update_effect_metrics(
        effect_type=intent.intent_type,
        processing_time_ms=0,
        success=False,
    )
```

---

## Intent Types

### Standard Intent Types

**1. log_metric**

Records metrics for monitoring and observability.

```
ModelIntent(
    intent_type="log_metric",
    target="metrics_service",
    payload={
        "metric_type": "reduction_metrics",
        "reduction_type": "sum",
        "processing_time_ms": 123.45,
        "success": True,
        "items_processed": 1000,
    },
    priority=3,
)
```

**Use Cases**:
- Performance metrics (processing time, throughput)
- Business metrics (items processed, operations completed)
- Resource utilization (memory, CPU)

---

**2. log_event**

Logs structured events for debugging and audit trails.

```
ModelIntent(
    intent_type="log_event",
    target="logging_service",
    payload={
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "message": "Reduction completed successfully",
        "context": {
            "node_id": "reducer-123",
            "operation_id": "op-456",
            "processing_time_ms": 123.45,
        },
    },
    priority=2,
)
```

**Use Cases**:
- Operational logging (completion, progress)
- Error logging (failures, warnings)
- Audit trails (state changes, user actions)

---

**3. write**

Persists data to storage (database, file system, cache).

```
ModelIntent(
    intent_type="write",
    target="database_service",
    payload={
        "collection": "reduction_results",
        "data": {"sum": 12345, "count": 100},
        "operation_id": "op-789",
    },
    priority=5,
)
```

**Use Cases**:
- Database writes (results, state)
- File writes (reports, exports)
- Cache writes (intermediate results)

---

**4. notify**

Sends notifications to external systems or users.

```
ModelIntent(
    intent_type="notify",
    target="notification_service",
    payload={
        "severity": "WARNING",  # INFO, WARNING, ERROR, CRITICAL
        "message": "Processing time exceeded threshold",
        "recipients": ["admin@example.com"],
        "channel": "email",  # email, slack, pagerduty
    },
    priority=8,
)
```

**Use Cases**:
- Alerts (SLA violations, errors)
- Notifications (completion, status updates)
- Integrations (webhooks, external APIs)

---

## Best Practices

### 1. Emit Intents for ALL Side Effects

**Rule**: Never perform side effects directly in Reducer. Always emit Intents.

**❌ Anti-Pattern**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # Direct side effects - breaks purity
    logger.info("Reduction complete")
    metrics.increment("reductions")

    return ModelReducerOutput(result=result)
```

**✅ Best Practice**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # Emit Intents for all side effects
    intents = [
        ModelIntent(intent_type="log_event", target="logging_service", ...),
        ModelIntent(intent_type="log_metric", target="metrics_service", ...),
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

---

### 2. Never Perform I/O Directly in Reducer

**Rule**: Reducer must be pure - no I/O operations (files, network, database).

**❌ Anti-Pattern**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # Direct I/O - breaks purity
    await db.save(result)
    with open("results.json", "w") as f:
        json.dump(result, f)

    return ModelReducerOutput(result=result)
```

**✅ Best Practice**:
```
async def process(self, input_data):
    result = self._reduce(input_data.items)

    # Emit write Intents instead
    intents = [
        ModelIntent(
            intent_type="write",
            target="database_service",
            payload={"collection": "results", "data": result},
        ),
        ModelIntent(
            intent_type="write",
            target="file_service",
            payload={"file_path": "results.json", "data": result},
        ),
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

---

### 3. Use Priority for Execution Order

**Rule**: Assign priorities based on criticality and time sensitivity.

**Priority Guidelines**:
- **10**: Critical alerts, system failures
- **8-9**: Important notifications, SLA violations
- **5-7**: Business metrics, audit logs
- **3-4**: Operational metrics, info logs
- **1-2**: Debug logs, optional metrics

**Example**:
```
intents = [
    # Critical alert - execute first
    ModelIntent(
        intent_type="notify",
        target="pagerduty",
        payload={"severity": "CRITICAL", "message": "System failure"},
        priority=10,
    ),

    # Important metric - execute second
    ModelIntent(
        intent_type="log_metric",
        target="metrics_service",
        payload={"metric": "error_rate", "value": 0.15},
        priority=7,
    ),

    # Debug log - execute last
    ModelIntent(
        intent_type="log_event",
        target="logging_service",
        payload={"level": "DEBUG", "message": "Processing details"},
        priority=1,
    ),
]
```

---

### 4. Include lease_id for Workflow Tracking

**Rule**: Link Intents to workflows via `lease_id` for traceability and conflict resolution.

**Example**:
```
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    result = self._reduce(input_data.items)

    # Extract lease_id from input metadata
    lease_id = input_data.metadata.get("lease_id")
    epoch = input_data.metadata.get("epoch", 0)

    intents = [
        ModelIntent(
            intent_type="write",
            target="database_service",
            payload={"collection": "results", "data": result},
            lease_id=lease_id,  # Link to workflow
            epoch=epoch,        # Link to state version
        ),
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

**Benefits**:
- Enables lease-based conflict resolution
- Provides workflow traceability
- Supports optimistic concurrency control

---

### 5. Test Intents, Not Side Effects

**Rule**: Test Intent emission, not Intent execution. Effect node tests handle execution.

**✅ Best Practice**:
```
async def test_reducer_emits_completion_intent():
    """Test that Reducer emits completion log intent."""
    reducer = NodeReducer(container)
    input_data = ModelReducerInput(
        data=[1, 2, 3],
        reduction_type=EnumReductionType.SUM,
    )

    output = await reducer.process(input_data)

    # Assert on result
    assert output.result == 6

    # Assert on Intent emission (not execution)
    log_intents = [i for i in output.intents if i.intent_type == "log_event"]
    assert len(log_intents) == 1
    assert log_intents[0].payload["level"] == "INFO"
    assert "completed" in log_intents[0].payload["message"].lower()
```

**Separation of Concerns**:
- **Reducer Tests**: Assert Intent emission (what side effects are requested)
- **Effect Tests**: Assert Intent execution (how side effects are performed)

---

### 6. Use Descriptive Intent Types and Targets

**Rule**: Use clear, consistent naming for `intent_type` and `target` fields.

**Naming Conventions**:
- **intent_type**: Lowercase, underscore-separated verbs (e.g., `log_event`, `send_notification`)
- **target**: Service name or identifier (e.g., `metrics_service`, `event_bus`, `slack_notifier`)

**❌ Anti-Pattern**:
```
ModelIntent(
    intent_type="do_thing",  # Vague
    target="service1",        # Non-descriptive
    payload={"data": 123},
)
```

**✅ Best Practice**:
```
ModelIntent(
    intent_type="log_metric",      # Clear action
    target="prometheus_exporter",   # Specific target
    payload={"metric": "processing_time", "value": 123},
)
```

---

## Summary

**ModelIntent** enables pure functional programming in ONEX nodes by separating side effect declaration (Intents) from side effect execution (Effect node). This pattern provides:

- **Purity**: Reducer is a pure FSM with no I/O or hidden state
- **Determinism**: Same input always produces same output
- **Testability**: Easy to test without mocks or infrastructure
- **Composability**: Intents can be filtered, transformed, combined
- **Centralized Error Handling**: All side effects managed in Effect node
- **Observability**: Intents provide traceable side effect declarations

**Key Takeaways**:

1. Reducer emits Intents, Effect executes them
2. Never perform I/O directly in Reducer
3. Use priorities to control execution order
4. Link Intents to workflows via `lease_id`
5. Test Intent emission, not execution

**Related Documentation**:
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Reducer Node Guide](../guides/node-building/02_NODE_TYPES.md#reducer-node)
- [Effect Node Guide](../guides/node-building/02_NODE_TYPES.md#effect-node)
