# Pure FSM Reducer Pattern

**Status**: Recommended Pattern
**First Introduced**: October 2025
**Applies To**: NodeReducer implementations in ONEX architecture

## Table of Contents

1. [Overview](#overview)
2. [Pure FSM Requirements](#pure-fsm-requirements)
3. [Intent Emission Pattern](#intent-emission-pattern)
4. [Benefits](#benefits)
5. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
6. [Migration from Impure Reducer](#migration-from-impure-reducer)
7. [Testing Pure FSM Reducers](#testing-pure-fsm-reducers)
8. [Real-World Examples](#real-world-examples)
9. [Integration with ONEX Architecture](#integration-with-onex-architecture)

---

## Overview

The Pure FSM (Finite State Machine) Reducer pattern ensures that Reducer nodes operate as deterministic, side-effect-free state transformation machines. This pattern is fundamental to the ONEX 4-node architecture's separation of concerns.

### Core Formula

```
δ(state, action) → (new_state, intents[])
```

Where:
- **δ** (delta) = Pure reduction function
- **state** = Current state (input data)
- **action** = Reduction operation to perform
- **new_state** = Transformed state (result)
- **intents[]** = Side effects to be executed by Effect node

### Key Principles

1. **Purity**: Same inputs always produce same outputs
2. **Determinism**: No randomness, no external state dependencies
3. **Testability**: Easy to test with simple assertions
4. **Composability**: Reducers can be composed without side effects

### ONEX 4-Node Architecture Role

In the ONEX architecture, Reducers are responsible for:
- **Data Aggregation**: Combining multiple inputs into single output
- **State Reduction**: Transforming collections into summary state
- **Conflict Resolution**: Merging conflicting data deterministically
- **Pure Computation**: No I/O, no side effects, just transformations

Side effects (logging, metrics, persistence) are **described as Intents** and executed by Effect nodes.

---

## Pure FSM Requirements

### 1. No Mutable Instance State

Pure FSM Reducers must not maintain mutable state between invocations. Configuration is allowed, but runtime state must flow through input/output.

#### ❌ Anti-pattern: Mutable Instance State

```
class NodeMetricsReducer(NodeReducer):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

        # ❌ WRONG: Mutable state violates FSM purity
        self.metrics: dict[str, float] = {}
        self.windows: dict[str, UtilStreamingWindow] = {}
        self.reduction_count = 0
        self.last_result: Any = None
```

**Why this is wrong:**
- Breaks determinism (results depend on previous calls)
- Impossible to test in isolation
- Race conditions in concurrent execution
- Violates single responsibility (state management + reduction)

#### ✅ Correct: Immutable Configuration Only

```
class NodeMetricsReducer(NodeReducer):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

        # ✅ CORRECT: Immutable configuration
        self.batch_size = 1000
        self.max_memory_mb = 512
        self.aggregation_functions = frozenset(["sum", "avg", "max"])

        # ✅ CORRECT: No mutable runtime state
        # All state flows through ModelReducerInput/ModelReducerOutput
```

**Why this is correct:**
- Configuration is immutable (set once, never changed)
- No runtime state persists between calls
- Same inputs always produce same outputs
- Safe for concurrent execution

---

### 2. No Direct Side Effects

Pure FSM Reducers must not perform I/O operations directly. All side effects must be **described as Intents** and returned for execution by Effect nodes.

#### ❌ Anti-pattern: Direct Side Effects

```
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    # ❌ WRONG: Direct I/O operations
    result = self._reduce(input_data.data)

    # ❌ Direct logging
    await self.logger.info("Reduction completed")

    # ❌ Direct metrics emission
    await self.metrics_service.emit({
        "operation": "reduce",
        "duration_ms": processing_time
    })

    # ❌ Direct database write
    await self.db.save_result(result)

    return ModelReducerOutput(result=result)
```

**Why this is wrong:**
- Cannot test without mocking I/O dependencies
- Side effects hidden in function signature
- Difficult to trace execution flow
- Violates separation of concerns (Reducer doing Effect work)

#### ✅ Correct: Intent Emission

```
async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
    # ✅ CORRECT: Pure reduction
    result = self._reduce(input_data.data)

    # ✅ CORRECT: Describe side effects as Intents
    intents = [
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={
                "level": "INFO",
                "message": "Reduction completed",
                "context": {"operation_id": str(input_data.operation_id)}
            },
            priority=2
        ),
        ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={
                "metric_type": "reduction_duration",
                "value": processing_time,
                "operation": "reduce"
            },
            priority=3
        ),
        ModelIntent(
            intent_type="persist_result",
            target="database_service",
            payload={"result": result, "operation_id": input_data.operation_id},
            priority=1
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

**Why this is correct:**
- Pure function (no hidden I/O)
- Side effects explicit in return value
- Easy to test (inspect intents list)
- Clear separation: Reducer describes, Effect executes

---

### 3. Pure Functions

All reduction logic must be implemented as pure functions: deterministic, referentially transparent, with no side effects.

#### Pure Function Checklist

- ✅ Same inputs → Same outputs (always)
- ✅ No external state dependencies
- ✅ No state mutation (input or external)
- ✅ No I/O operations
- ✅ No randomness (unless seed provided as input)
- ✅ No system time dependencies (use input timestamp)

#### ❌ Anti-pattern: Impure Function

```
async def _reduce_metrics(self, items: list[dict]) -> dict:
    # ❌ WRONG: Depends on system time
    current_time = datetime.now()

    # ❌ WRONG: Mutates input
    for item in items:
        item["processed"] = True

    # ❌ WRONG: Depends on external state
    if self.enable_advanced_aggregation:
        return self._advanced_aggregate(items)

    # ❌ WRONG: Non-deterministic (random sampling)
    sample_size = random.randint(1, len(items))
    return {"sample": items[:sample_size]}
```

#### ✅ Correct: Pure Function

```
async def _reduce_metrics(
    self,
    items: list[dict],
    config: dict[str, Any],
    timestamp: datetime
) -> dict:
    # ✅ CORRECT: Use input timestamp
    processing_time = timestamp

    # ✅ CORRECT: Do not mutate input
    processed_items = [
        {**item, "processed": True}
        for item in items
    ]

    # ✅ CORRECT: Configuration passed as input
    if config.get("advanced_aggregation", False):
        return self._advanced_aggregate(processed_items)

    # ✅ CORRECT: Deterministic (seed from input)
    sample_size = config.get("sample_size", len(items))
    return {"sample": processed_items[:sample_size]}
```

---

## Intent Emission Pattern

The Intent Emission pattern is the mechanism for describing side effects in Pure FSM Reducers. This section provides step-by-step implementation guidance.

### Step 1: Perform Pure Reduction

Execute the reduction logic as a pure function, transforming input data into result.

```
async def process(self, input_data: ModelReducerInput[T]) -> ModelReducerOutput[R]:
    # Step 1: Pure reduction
    result = self._reduce_items(input_data.data)
```

### Step 2: Describe Side Effects as Intents

Create Intent objects that describe what side effects should occur. Do not execute them.

```
    # Step 2: Describe side effects
    intents: list[ModelIntent] = []

    # Intent for metrics
    intents.append(ModelIntent(
        intent_type="log_metric",
        target="metrics_service",
        payload={
            "metric_name": "reduction_items_processed",
            "value": len(input_data.data),
            "operation_id": str(input_data.operation_id)
        },
        priority=3  # Low priority
    ))

    # Intent for logging
    intents.append(ModelIntent(
        intent_type="log_event",
        target="logging_service",
        payload={
            "level": "INFO",
            "message": f"Reduced {len(input_data.data)} items",
            "context": {
                "node_id": str(self.node_id),
                "reduction_type": input_data.reduction_type.value
            }
        },
        priority=2  # Medium priority
    ))
```

### Step 3: Return State + Intents

Return the new state (result) along with the intents describing side effects.

```
    # Step 3: Return state + intents
    return ModelReducerOutput(
        result=result,
        operation_id=input_data.operation_id,
        reduction_type=input_data.reduction_type,
        processing_time_ms=processing_time,
        items_processed=len(input_data.data),
        intents=intents,  # Effect node will execute these
        metadata={"strategy": "pure_fsm"}
    )
```

### Complete Intent Emission Example

```
class NodeDataAggregatorReducer(NodeReducer):
    async def process(
        self,
        input_data: ModelReducerInput[dict]
    ) -> ModelReducerOutput[dict]:
        start_time = time.time()

        # Step 1: Pure reduction
        aggregated = self._aggregate_data(input_data.data)
        processing_time = (time.time() - start_time) * 1000

        # Step 2: Describe side effects as Intents
        intents = [
            # Metrics intent
            ModelIntent(
                intent_type="log_metric",
                target="metrics_service",
                payload={
                    "metric_type": "aggregation_metrics",
                    "processing_time_ms": processing_time,
                    "items_count": len(input_data.data),
                    "aggregation_keys": list(aggregated.keys())
                },
                priority=3
            ),
            # Logging intent
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "INFO",
                    "message": "Data aggregation completed",
                    "context": {
                        "operation_id": str(input_data.operation_id),
                        "items_processed": len(input_data.data)
                    }
                },
                priority=2
            ),
            # Persistence intent (if configured)
            ModelIntent(
                intent_type="persist_aggregation",
                target="database_service",
                payload={
                    "aggregated_data": aggregated,
                    "operation_id": input_data.operation_id
                },
                priority=1  # High priority
            )
        ]

        # Step 3: Return state + intents
        return ModelReducerOutput(
            result=aggregated,
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=processing_time,
            items_processed=len(input_data.data),
            intents=intents,
            metadata={"aggregation_strategy": "pure_fsm"}
        )

    def _aggregate_data(self, items: list[dict]) -> dict:
        """Pure aggregation function."""
        result: dict[str, list[Any]] = {}
        for item in items:
            for key, value in item.items():
                if key not in result:
                    result[key] = []
                result[key].append(value)
        return result
```

---

## Benefits

### 1. Testability

Pure FSM Reducers are trivial to test because they have no side effects or external dependencies.

```
def test_reducer_simple():
    """Test reducer without mocks or complex setup."""
    # Arrange
    container = ModelONEXContainer()
    reducer = NodeDataAggregatorReducer(container)

    input_data = ModelReducerInput(
        data=[{"a": 1}, {"a": 2}, {"b": 3}],
        reduction_type=EnumReductionType.AGGREGATE
    )

    # Act
    output = await reducer.process(input_data)

    # Assert
    assert output.result == {"a": [1, 2], "b": [3]}
    assert output.items_processed == 3
    assert len(output.intents) == 3  # Metrics, logging, persistence

    # Verify intent descriptions (no need to mock services)
    metric_intent = next(i for i in output.intents if i.intent_type == "log_metric")
    assert metric_intent.target == "metrics_service"
    assert metric_intent.payload["items_count"] == 3
```

### 2. Determinism

Pure functions guarantee same inputs always produce same outputs, enabling reliable testing and debugging.

```
def test_reducer_determinism():
    """Verify reducer is deterministic."""
    container = ModelONEXContainer()
    reducer = NodeDataAggregatorReducer(container)

    input_data = ModelReducerInput(
        data=[{"x": 1}, {"x": 2}, {"x": 3}],
        reduction_type=EnumReductionType.AGGREGATE
    )

    # Run reduction 100 times
    results = [await reducer.process(input_data) for _ in range(100)]

    # All results must be identical
    assert all(r.result == results[0].result for r in results)
    assert all(r.items_processed == 3 for r in results)
```

### 3. Composability

Pure reducers can be composed without worrying about side effects or state interference.

```
async def compose_reducers(
    data: list[dict],
    reducer1: NodeReducer,
    reducer2: NodeReducer
) -> dict:
    """Compose reducers safely (no side effect interference)."""
    # First reduction
    input1 = ModelReducerInput(data=data, reduction_type=EnumReductionType.FOLD)
    output1 = await reducer1.process(input1)

    # Second reduction (using output of first)
    input2 = ModelReducerInput(data=[output1.result], reduction_type=EnumReductionType.MERGE)
    output2 = await reducer2.process(input2)

    # Combine intents from both reducers
    all_intents = output1.intents + output2.intents

    return {
        "result": output2.result,
        "intents": all_intents,
        "total_items": output1.items_processed + output2.items_processed
    }
```

### 4. Debuggability

No hidden side effects means complete visibility into what the reducer does.

```
async def debug_reducer_execution(reducer: NodeReducer, input_data: ModelReducerInput):
    """Debug reducer execution with full visibility."""
    output = await reducer.process(input_data)

    print(f"Input: {input_data.data}")
    print(f"Result: {output.result}")
    print(f"Processing time: {output.processing_time_ms}ms")
    print(f"Items processed: {output.items_processed}")
    print(f"Intents emitted: {len(output.intents)}")

    for intent in output.intents:
        print(f"  - {intent.intent_type} → {intent.target} (priority: {intent.priority})")
        print(f"    Payload: {intent.payload}")

    # No hidden side effects to discover!
```

### 5. Concurrency Safety

Pure reducers are inherently thread-safe and can be executed concurrently without locks.

```
async def parallel_reduction(items: list[list[dict]], reducer: NodeReducer):
    """Execute reducer in parallel safely (no shared state)."""
    tasks = [
        reducer.process(ModelReducerInput(data=batch, reduction_type=EnumReductionType.FOLD))
        for batch in items
    ]

    # No race conditions, no locks needed
    results = await asyncio.gather(*tasks)

    return [r.result for r in results]
```

---

## Anti-Patterns to Avoid

### 1. Mutable Instance Variables

**Problem**: State persists between invocations, breaking determinism.

```
# ❌ WRONG
class NodeMetricsReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        self.total_processed = 0  # ❌ Mutable state

    async def process(self, input_data):
        result = self._reduce(input_data.data)
        self.total_processed += len(input_data.data)  # ❌ Mutation
        return ModelReducerOutput(result=result)
```

**Solution**: Pass state through input/output.

```
# ✅ CORRECT
class NodeMetricsReducer(NodeReducer):
    async def process(self, input_data):
        result = self._reduce(input_data.data)

        # State passed through metadata
        previous_total = input_data.metadata.get("total_processed", 0)
        new_total = previous_total + len(input_data.data)

        return ModelReducerOutput(
            result=result,
            metadata={"total_processed": new_total}
        )
```

### 2. Direct Database Calls

**Problem**: I/O operations make testing difficult and violate separation of concerns.

```
# ❌ WRONG
async def process(self, input_data):
    result = self._reduce(input_data.data)
    await self.db.save(result)  # ❌ Direct I/O
    return ModelReducerOutput(result=result)
```

**Solution**: Emit persistence intent.

```
# ✅ CORRECT
async def process(self, input_data):
    result = self._reduce(input_data.data)

    intents = [
        ModelIntent(
            intent_type="persist_result",
            target="database_service",
            payload={"result": result}
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

### 3. Direct Logging Calls

**Problem**: Logging is a side effect that should be described, not executed.

```
# ❌ WRONG
async def process(self, input_data):
    self.logger.info("Starting reduction")  # ❌ Direct logging
    result = self._reduce(input_data.data)
    self.logger.info("Reduction complete")  # ❌ Direct logging
    return ModelReducerOutput(result=result)
```

**Solution**: Emit logging intents.

```
# ✅ CORRECT
async def process(self, input_data):
    result = self._reduce(input_data.data)

    intents = [
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={"level": "INFO", "message": "Reduction complete"}
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

### 4. File I/O Operations

**Problem**: File operations are side effects and make testing complex.

```
# ❌ WRONG
async def process(self, input_data):
    result = self._reduce(input_data.data)
    with open("output.json", "w") as f:  # ❌ File I/O
        json.dump(result, f)
    return ModelReducerOutput(result=result)
```

**Solution**: Emit file write intent.

```
# ✅ CORRECT
async def process(self, input_data):
    result = self._reduce(input_data.data)

    intents = [
        ModelIntent(
            intent_type="write_file",
            target="file_service",
            payload={
                "path": "output.json",
                "content": json.dumps(result)
            }
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

### 5. Network Requests

**Problem**: Network calls introduce non-determinism and external dependencies.

```
# ❌ WRONG
async def process(self, input_data):
    result = self._reduce(input_data.data)
    await self.http_client.post("/api/results", json=result)  # ❌ Network I/O
    return ModelReducerOutput(result=result)
```

**Solution**: Emit HTTP request intent.

```
# ✅ CORRECT
async def process(self, input_data):
    result = self._reduce(input_data.data)

    intents = [
        ModelIntent(
            intent_type="http_post",
            target="http_service",
            payload={
                "url": "/api/results",
                "body": result
            }
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

### 6. System Time Dependencies

**Problem**: `datetime.now()` introduces non-determinism.

```
# ❌ WRONG
async def process(self, input_data):
    current_time = datetime.now()  # ❌ Non-deterministic
    result = self._reduce_with_timestamp(input_data.data, current_time)
    return ModelReducerOutput(result=result)
```

**Solution**: Accept timestamp as input.

```
# ✅ CORRECT
async def process(self, input_data):
    timestamp = input_data.metadata.get("timestamp", datetime.now())
    result = self._reduce_with_timestamp(input_data.data, timestamp)
    return ModelReducerOutput(result=result)
```

---

## Migration from Impure Reducer

This section provides a step-by-step guide for migrating existing impure Reducers to Pure FSM pattern.

### Step 1: Identify Impurities

Audit your Reducer for:
- Mutable instance variables
- Direct I/O operations (logging, database, files, network)
- External state dependencies
- Non-deterministic operations (random, time)

### Step 2: Extract Configuration

Move immutable configuration to `__init__`, remove mutable state.

**Before**:
```
def __init__(self, container):
    super().__init__(container)
    self.metrics = {}  # ❌ Mutable
    self.batch_size = 1000  # ✅ Immutable config (OK)
```

**After**:
```
def __init__(self, container):
    super().__init__(container)
    # self.metrics removed (now passed through state)
    self.batch_size = 1000  # ✅ Immutable config
```

### Step 3: Convert Side Effects to Intents

Replace direct I/O with Intent emission.

**Before**:
```
async def process(self, input_data):
    result = self._reduce(input_data.data)

    # ❌ Direct side effects
    self.metrics["count"] += 1
    await self.logger.info("Reduction complete")
    await self.db.save(result)

    return ModelReducerOutput(result=result)
```

**After**:
```
async def process(self, input_data):
    result = self._reduce(input_data.data)

    # ✅ Intent emission
    intents = [
        ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={"metric": "reduction_count", "value": 1}
        ),
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={"level": "INFO", "message": "Reduction complete"}
        ),
        ModelIntent(
            intent_type="persist_result",
            target="database_service",
            payload={"result": result}
        )
    ]

    return ModelReducerOutput(result=result, intents=intents)
```

### Step 4: Pass State Through Input/Output

Replace instance variables with state passed through `metadata`.

**Before**:
```
def __init__(self, container):
    super().__init__(container)
    self.window = UtilStreamingWindow()  # ❌ Mutable state

async def process(self, input_data):
    self.window.add_items(input_data.data)  # ❌ Mutation
    result = self.window.get_aggregated()
    return ModelReducerOutput(result=result)
```

**After**:
```
async def process(self, input_data):
    # Reconstruct window from input metadata
    window_data = input_data.metadata.get("window_state", {})
    window = UtilStreamingWindow.from_dict(window_data)

    # Pure transformation
    window_copy = window.add_items(input_data.data)  # Returns new window
    result = window_copy.get_aggregated()

    # Pass updated state in output
    return ModelReducerOutput(
        result=result,
        metadata={"window_state": window_copy.to_dict()}
    )
```

### Step 5: Make Functions Pure

Ensure all reduction logic is deterministic.

**Before**:
```
def _reduce(self, items):
    # ❌ Non-deterministic
    sample = random.sample(items, k=min(10, len(items)))
    return sum(sample)
```

**After**:
```
def _reduce(self, items, seed=None):
    # ✅ Deterministic (seed from input)
    if seed is not None:
        random.seed(seed)
    sample = random.sample(items, k=min(10, len(items)))
    return sum(sample)
```

### Complete Migration Example

**Before (Impure)**:
```
class NodeDataReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        self.metrics = defaultdict(int)  # ❌ Mutable
        self.cache = {}  # ❌ Mutable
        self.batch_size = 1000  # ✅ OK

    async def process(self, input_data):
        # ❌ Direct logging
        await self.logger.info(f"Processing {len(input_data.data)} items")

        # ❌ Mutation
        self.metrics["total_processed"] += len(input_data.data)

        # ❌ Non-deterministic
        result = self._reduce(input_data.data, use_cache=True)

        # ❌ Direct I/O
        await self.db.save_metrics(self.metrics)

        return ModelReducerOutput(result=result)

    def _reduce(self, items, use_cache):
        # ❌ Depends on mutable cache
        cache_key = str(items)
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        result = sum(items)
        self.cache[cache_key] = result
        return result
```

**After (Pure FSM)**:
```
class NodeDataReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        self.batch_size = 1000  # ✅ Immutable config only

    async def process(self, input_data):
        # ✅ Pure reduction
        previous_total = input_data.metadata.get("total_processed", 0)
        cache = input_data.metadata.get("cache", {})

        result = self._reduce(input_data.data, cache)
        new_total = previous_total + len(input_data.data)

        # ✅ Intent emission
        intents = [
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "INFO",
                    "message": f"Processing {len(input_data.data)} items"
                }
            ),
            ModelIntent(
                intent_type="persist_metrics",
                target="database_service",
                payload={"total_processed": new_total}
            )
        ]

        return ModelReducerOutput(
            result=result,
            intents=intents,
            metadata={
                "total_processed": new_total,
                "cache": cache
            }
        )

    def _reduce(self, items, cache):
        # ✅ Pure function (cache passed as parameter)
        cache_key = str(items)
        if cache_key in cache:
            return cache[cache_key]

        result = sum(items)
        cache[cache_key] = result  # Local mutation OK (not instance variable)
        return result
```

---

## Testing Pure FSM Reducers

### Basic Purity Test

```
def test_reducer_purity():
    """Verify reducer is pure (same inputs → same outputs)."""
    container = ModelONEXContainer()
    reducer = NodeDataReducer(container)

    input_data = ModelReducerInput(
        data=[1, 2, 3, 4, 5],
        reduction_type=EnumReductionType.FOLD
    )

    # Execute multiple times
    output1 = await reducer.process(input_data)
    output2 = await reducer.process(input_data)
    output3 = await reducer.process(input_data)

    # Results must be identical
    assert output1.result == output2.result == output3.result
    assert output1.items_processed == output2.items_processed == output3.items_processed
    assert output1.intents == output2.intents  # Even intents must match
```

### Intent Verification Test

```
def test_reducer_intent_emission():
    """Verify correct intents are emitted."""
    container = ModelONEXContainer()
    reducer = NodeDataReducer(container)

    input_data = ModelReducerInput(
        data=[1, 2, 3],
        reduction_type=EnumReductionType.FOLD
    )

    output = await reducer.process(input_data)

    # Verify intents
    assert len(output.intents) == 2

    log_intent = next(i for i in output.intents if i.intent_type == "log_event")
    assert log_intent.target == "logging_service"
    assert "Processing 3 items" in log_intent.payload["message"]

    metric_intent = next(i for i in output.intents if i.intent_type == "persist_metrics")
    assert metric_intent.target == "database_service"
    assert metric_intent.payload["total_processed"] == 3
```

### Determinism Test

```
def test_reducer_determinism():
    """Verify reducer produces deterministic results."""
    container = ModelONEXContainer()
    reducer = NodeDataReducer(container)

    # Same input data
    input_data = ModelReducerInput(
        data=list(range(100)),
        reduction_type=EnumReductionType.AGGREGATE,
        metadata={"seed": 42}  # Deterministic seed
    )

    # Run 100 times
    results = [await reducer.process(input_data) for _ in range(100)]

    # All results must be identical
    first_result = results[0].result
    assert all(r.result == first_result for r in results)
```

### Composition Test

```
def test_reducer_composition():
    """Verify reducers can be composed without side effects."""
    container = ModelONEXContainer()
    reducer1 = NodeSumReducer(container)
    reducer2 = NodeAverageReducer(container)

    # First reduction
    input1 = ModelReducerInput(data=[1, 2, 3, 4, 5], reduction_type=EnumReductionType.FOLD)
    output1 = await reducer1.process(input1)
    assert output1.result == 15

    # Second reduction (using output of first)
    input2 = ModelReducerInput(data=[output1.result, 10, 20], reduction_type=EnumReductionType.FOLD)
    output2 = await reducer2.process(input2)
    assert output2.result == 15.0  # (15 + 10 + 20) / 3

    # Combine intents
    all_intents = output1.intents + output2.intents
    assert len(all_intents) == 4  # 2 from each reducer
```

### State Threading Test

```
def test_reducer_state_threading():
    """Verify state flows correctly through input/output."""
    container = ModelONEXContainer()
    reducer = NodeDataReducer(container)

    # First invocation
    input1 = ModelReducerInput(
        data=[1, 2, 3],
        reduction_type=EnumReductionType.FOLD,
        metadata={"total_processed": 0}
    )
    output1 = await reducer.process(input1)
    assert output1.metadata["total_processed"] == 3

    # Second invocation (use state from first)
    input2 = ModelReducerInput(
        data=[4, 5],
        reduction_type=EnumReductionType.FOLD,
        metadata={"total_processed": output1.metadata["total_processed"]}
    )
    output2 = await reducer.process(input2)
    assert output2.metadata["total_processed"] == 5  # 3 + 2
```

### Concurrent Execution Test

```
def test_reducer_concurrent_safety():
    """Verify reducer is safe for concurrent execution."""
    container = ModelONEXContainer()
    reducer = NodeDataReducer(container)

    # Execute 100 reductions concurrently
    tasks = [
        reducer.process(ModelReducerInput(
            data=list(range(i, i + 10)),
            reduction_type=EnumReductionType.FOLD
        ))
        for i in range(100)
    ]

    results = await asyncio.gather(*tasks)

    # Verify each result independently
    for i, output in enumerate(results):
        expected_sum = sum(range(i, i + 10))
        assert output.result == expected_sum
```

---

## Real-World Examples

### Example 1: Ticket Aggregation Reducer

Aggregates tickets by status with conflict resolution.

```
class NodeTicketAggregatorReducer(NodeReducer):
    """Aggregate tickets by status with metadata rollup."""

    async def process(
        self,
        input_data: ModelReducerInput[list[dict]]
    ) -> ModelReducerOutput[dict]:
        start_time = time.time()

        # Pure aggregation
        aggregated = self._aggregate_tickets(
            input_data.data,
            group_by=input_data.metadata.get("group_by", "status")
        )

        processing_time = (time.time() - start_time) * 1000

        # Emit intents for metrics and logging
        intents = [
            ModelIntent(
                intent_type="log_metric",
                target="metrics_service",
                payload={
                    "metric_type": "ticket_aggregation",
                    "processing_time_ms": processing_time,
                    "tickets_processed": len(input_data.data),
                    "groups_created": len(aggregated)
                },
                priority=3
            ),
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "INFO",
                    "message": f"Aggregated {len(input_data.data)} tickets into {len(aggregated)} groups",
                    "context": {"operation_id": str(input_data.operation_id)}
                },
                priority=2
            )
        ]

        return ModelReducerOutput(
            result=aggregated,
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=processing_time,
            items_processed=len(input_data.data),
            intents=intents,
            metadata={"groups": list(aggregated.keys())}
        )

    def _aggregate_tickets(self, tickets: list[dict], group_by: str) -> dict:
        """Pure aggregation function."""
        groups: dict[str, list[dict]] = defaultdict(list)

        for ticket in tickets:
            group_key = ticket.get(group_by, "unknown")
            groups[group_key].append(ticket)

        return {
            group: {
                "count": len(tickets_in_group),
                "tickets": tickets_in_group,
                "avg_priority": sum(t.get("priority", 0) for t in tickets_in_group) / len(tickets_in_group)
            }
            for group, tickets_in_group in groups.items()
        }
```

### Example 2: Metrics Rollup Reducer

Rolls up time-series metrics with windowing.

```
class NodeMetricsRollupReducer(NodeReducer):
    """Roll up time-series metrics into aggregated summaries."""

    async def process(
        self,
        input_data: ModelReducerInput[list[dict]]
    ) -> ModelReducerOutput[dict]:
        start_time = time.time()

        # Pure rollup
        rollup = self._rollup_metrics(
            input_data.data,
            window_size=input_data.metadata.get("window_size_seconds", 60)
        )

        processing_time = (time.time() - start_time) * 1000

        # Emit intents
        intents = [
            ModelIntent(
                intent_type="log_metric",
                target="metrics_service",
                payload={
                    "metric_type": "metrics_rollup",
                    "processing_time_ms": processing_time,
                    "datapoints_processed": len(input_data.data),
                    "windows_created": len(rollup["windows"])
                },
                priority=3
            ),
            ModelIntent(
                intent_type="persist_rollup",
                target="database_service",
                payload={
                    "rollup_data": rollup,
                    "operation_id": input_data.operation_id
                },
                priority=1
            )
        ]

        return ModelReducerOutput(
            result=rollup,
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=processing_time,
            items_processed=len(input_data.data),
            intents=intents,
            metadata={"window_count": len(rollup["windows"])}
        )

    def _rollup_metrics(self, metrics: list[dict], window_size: int) -> dict:
        """Pure metrics rollup function."""
        windows: dict[int, list[dict]] = defaultdict(list)

        for metric in metrics:
            timestamp = metric.get("timestamp", 0)
            window_key = timestamp // window_size
            windows[window_key].append(metric)

        return {
            "windows": {
                window_key: {
                    "start": window_key * window_size,
                    "end": (window_key + 1) * window_size,
                    "count": len(window_metrics),
                    "sum": sum(m.get("value", 0) for m in window_metrics),
                    "avg": sum(m.get("value", 0) for m in window_metrics) / len(window_metrics),
                    "min": min(m.get("value", 0) for m in window_metrics),
                    "max": max(m.get("value", 0) for m in window_metrics)
                }
                for window_key, window_metrics in windows.items()
            }
        }
```

### Example 3: Dependency Graph Reducer

Analyzes dependency graphs for cycles.

```
class NodeDependencyGraphReducer(NodeReducer):
    """Analyze dependency graphs for cycles and critical paths."""

    async def process(
        self,
        input_data: ModelReducerInput[dict]
    ) -> ModelReducerOutput[dict]:
        start_time = time.time()

        # Pure graph analysis
        analysis = self._analyze_dependency_graph(input_data.data)

        processing_time = (time.time() - start_time) * 1000

        # Emit intents
        intents = [
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "WARNING" if analysis["has_cycles"] else "INFO",
                    "message": f"Dependency analysis: {analysis['cycle_count']} cycles found",
                    "context": {
                        "operation_id": str(input_data.operation_id),
                        "cycles": analysis["cycles"]
                    }
                },
                priority=1 if analysis["has_cycles"] else 2
            )
        ]

        return ModelReducerOutput(
            result=analysis,
            operation_id=input_data.operation_id,
            reduction_type=input_data.reduction_type,
            processing_time_ms=processing_time,
            items_processed=len(input_data.data),
            intents=intents,
            metadata={
                "has_cycles": analysis["has_cycles"],
                "cycle_count": analysis["cycle_count"]
            }
        )

    def _analyze_dependency_graph(self, graph: dict[str, list[str]]) -> dict:
        """Pure graph analysis function."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                dfs(neighbor, path[:])

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return {
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "cycle_count": len(cycles),
            "total_nodes": len(graph)
        }
```

---

## Integration with ONEX Architecture

### 4-Node Architecture Flow

```
┌─────────────────┐
│  Orchestrator   │  Coordinates workflow
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Compute      │  Prepares data for reduction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Reducer      │  Pure FSM: δ(state, action) → (new_state, intents[])
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Effect      │  Executes intents (I/O, logging, metrics)
└─────────────────┘
```

### Reducer → Effect Integration

```
# Orchestrator coordinates Reducer → Effect flow
class NodeWorkflowOrchestrator(NodeOrchestrator):
    async def execute_reduction_workflow(self, data: list[dict]) -> dict:
        # Step 1: Compute prepares data
        compute_output = await self.compute_node.process(data)

        # Step 2: Reducer performs pure transformation
        reducer_input = ModelReducerInput(
            data=compute_output.result,
            reduction_type=EnumReductionType.AGGREGATE
        )
        reducer_output = await self.reducer_node.process(reducer_input)

        # Step 3: Effect executes intents
        effect_results = []
        for intent in reducer_output.intents:
            effect_input = ModelEffectInput(
                operation=intent.intent_type,
                target=intent.target,
                payload=intent.payload
            )
            effect_output = await self.effect_node.execute(effect_input)
            effect_results.append(effect_output)

        return {
            "result": reducer_output.result,
            "effects_executed": len(effect_results)
        }
```

### Contract-Based Reducer Definition

```
# model_contract_reducer_ticket_aggregation.yaml
name: "TicketAggregationReducer"
version:
  major: 1
  minor: 0
  patch: 0
node_type: "reducer"
description: "Aggregates tickets by status with conflict resolution"

inputs:
  - name: "tickets"
    type: "list[dict]"
    required: true
  - name: "group_by"
    type: "string"
    required: false
    default: "status"

outputs:
  - name: "aggregated_tickets"
    type: "dict[str, dict]"
  - name: "intents"
    type: "list[ModelIntent]"

reduction_config:
  reduction_type: "aggregate"
  streaming_mode: "batch"
  conflict_resolution: "merge"

fsm_guarantees:
  pure: true
  deterministic: true
  no_side_effects: true
  intent_based: true
```

---

## Related Documentation

- **NodeReducer API**: `/src/omnibase_core/nodes/node_reducer.py`
- **ModelReducerOutput**: `/src/omnibase_core/nodes/model_reducer_output.py`
- **ModelIntent**: `/src/omnibase_core/nodes/model_intent.py`
- **ONEX 4-Node Architecture**: `/docs/architecture/FOUR_NODE_ARCHITECTURE.md`
- **Anti-Patterns**: `/docs/patterns/ANTI_PATTERNS.md`
- **Testing Patterns**: `/docs/testing/REDUCER_TESTING.md`

---

## Document Metadata

- **Version**: 1.0.0
- **Last Updated**: October 20, 2025
- **Maintainer**: ONEX Core Team
- **Status**: Active
- **Applicability**: All NodeReducer implementations
