# REDUCER Node Tutorial: Build a Pure FSM Metrics Aggregator

**Reading Time**: 35 minutes
**Difficulty**: Intermediate
**Prerequisites**: [What is a Node?](01_WHAT_IS_A_NODE.md), [EFFECT Node Tutorial](04_EFFECT_NODE_TUTORIAL.md)

## What You'll Build

In this tutorial, you'll build a production-ready **Metrics Aggregation Node** as a **pure FSM** that:

✅ Aggregates metrics data from multiple sources as pure state transitions
✅ Supports multiple reduction types (fold, aggregate, merge, normalize)
✅ Handles streaming for large datasets
✅ Implements conflict resolution strategies
✅ **Emits Intents for side effects** (no direct execution)
✅ **Maintains no mutable state** (pure functional pattern)

**Why Pure FSM REDUCER Nodes?**

REDUCER nodes in ONEX are **pure finite state machines**:
- **Input → (Output, Intents)**: Pure function transformation
- **No Mutable State**: All state flows through input/output
- **Intent Emission**: Describe side effects, don't execute them
- **Effect Delegation**: Let Effect nodes handle I/O, logging, metrics

**Core Concept**:
```text
δ(state, action) → (new_state, intents[])
```

**Tutorial Structure**:
1. Understand pure FSM vs. stateful patterns
2. Define aggregation models with Intent support
3. Implement pure REDUCER node
4. Add Intent emission for side effects
5. Write comprehensive tests
6. See real-world usage examples

---

## Pure FSM Pattern: Key Principles

### ❌ Old Pattern (Stateful, Side Effects)
```python
class NodeMetricsAggregatorReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        # ❌ WRONG: Mutable state
        self.aggregation_stats = {"total": 0}
        self.active_windows = {}

    async def aggregate_metrics(self, input_data):
        result = await self._aggregate(input_data)

        # ❌ WRONG: Direct state mutation
        self.aggregation_stats["total"] += 1

        # ❌ WRONG: Direct side effect execution
        emit_log_event(LogLevel.INFO, "Aggregation complete")

        return result
```

### ✅ New Pattern (Pure FSM, Intent Emission)
```python
class NodeMetricsAggregatorReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        # ✅ CORRECT: No mutable state

    async def aggregate_metrics(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelMetricsAggregationOutput:
        """Pure function: input → (result, intents)"""

        # ✅ Pure transformation
        aggregated_data = self._reduce_data(input_data.data_sources)

        # ✅ Describe side effects as Intents
        intents = [
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "INFO",
                    "message": "Aggregation complete",
                    "context": {"items": len(aggregated_data)},
                },
                priority=3,
            ),
            ModelIntent(
                intent_type="record_metric",
                target="metrics_service",
                payload={
                    "metric_name": "aggregations_completed",
                    "value": 1,
                    "tags": {"strategy": input_data.aggregation_strategy},
                },
                priority=2,
            ),
        ]

        # ✅ Return result + intents (no execution)
        return ModelMetricsAggregationOutput(
            aggregated_data=aggregated_data,
            sources_processed=len(input_data.data_sources),
            items_processed=len(aggregated_data),
            intents=intents,  # Side effects described, not executed
        )
```

**Key Difference**:
- **Reducer**: Describes what side effects *should* happen (Intents)
- **Effect Node**: Executes those side effects
- **Orchestrator**: Routes Intents to appropriate Effect nodes

---

## Prerequisites Check

```bash
# Verify Poetry and environment
poetry --version
pwd  # Should end with /omnibase_core

# Install dependencies
poetry install

# Run existing reducer tests
poetry run pytest tests/unit/nodes/test_node_reducer.py -v --maxfail=1
```

---

## Step 1: Define Input/Output Models

### Input Model

**File**: `src/your_project/nodes/model_metrics_aggregation_input.py`

```python
"""Input model for metrics aggregation REDUCER node."""

from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class EnumAggregationStrategy(str, Enum):
    """Aggregation strategies for conflict resolution."""

    SUM = "sum"
    AVERAGE = "average"
    MAX = "max"
    MIN = "min"
    LATEST = "latest"
    MERGE_LISTS = "merge_lists"


class ModelMetricsAggregationInput(BaseModel):
    """
    Input configuration for metrics aggregation.

    Defines how multiple data sources should be aggregated
    with conflict resolution and streaming support.

    NOTE: Immutable input - Reducer maintains no state.
    """

    # Data to aggregate
    data_sources: list[dict[str, object]] = Field(
        ...,
        description="List of data sources to aggregate",
        min_length=1,
    )

    # Aggregation configuration
    group_by_field: str | None = Field(
        default=None,
        description="Field to group data by (optional)",
    )

    aggregation_strategy: EnumAggregationStrategy = Field(
        default=EnumAggregationStrategy.SUM,
        description="Strategy for resolving conflicts",
    )

    # Streaming configuration
    enable_streaming: bool = Field(
        default=False,
        description="Enable streaming for large datasets",
    )

    batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Batch size for streaming operations",
    )

    window_size_ms: int = Field(
        default=5000,
        ge=1000,
        le=60000,
        description="Time window for windowed processing (ms)",
    )

    # Operation tracking
    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique operation identifier",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional operation metadata",
    )


    class Config:
        """Pydantic configuration."""

        frozen = True
```

### Output Model with Intent Support

**File**: `src/your_project/nodes/model_metrics_aggregation_output.py`

```python
"""Output model for metrics aggregation REDUCER node."""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ModelIntent(BaseModel):
    """
    Intent for side effects.

    Reducer nodes emit Intents describing side effects.
    Effect nodes execute them.
    """

    intent_type: str = Field(
        ...,
        description="Type of intent (log_event, record_metric, etc.)",
    )

    target: str = Field(
        ...,
        description="Target service/node for execution",
    )

    payload: dict[str, object] = Field(
        ...,
        description="Intent payload data",
    )

    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Execution priority (1=highest, 10=lowest)",
    )

    class Config:
        frozen = True


class ModelMetricsAggregationOutput(BaseModel):
    """
    Results from metrics aggregation operations.

    Provides comprehensive aggregation results with
    processing statistics and Intent emission.

    NOTE: Pure output - contains result + intents, no state mutation.
    """

    # Aggregation results
    aggregated_data: dict[str, object] = Field(
        ...,
        description="Aggregated metrics data",
    )

    # Processing statistics
    sources_processed: int = Field(
        ...,
        ge=0,
        description="Number of data sources processed",
    )

    items_processed: int = Field(
        ...,
        ge=0,
        description="Total items processed",
    )

    conflicts_resolved: int = Field(
        default=0,
        ge=0,
        description="Number of conflicts resolved",
    )

    # Streaming details (if applicable)
    batches_processed: int = Field(
        default=1,
        ge=1,
        description="Number of batches processed",
    )

    # Performance metrics
    processing_time_ms: float = Field(
        ...,
        ge=0,
        description="Total processing time",
    )

    throughput_items_per_sec: float = Field(
        ...,
        ge=0,
        description="Processing throughput",
    )

    # Operation tracking
    operation_id: UUID = Field(
        ...,
        description="Operation identifier",
    )

    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="Completion timestamp",
    )

    # Intent emission (NEW)
    intents: list[ModelIntent] = Field(
        default_factory=list,
        description="Side effects to be executed by Effect nodes",
    )


    class Config:
        """Pydantic configuration."""

        frozen = True
```

---

## Step 2: Implement Pure FSM REDUCER Node

**File**: `src/your_project/nodes/node_metrics_aggregator_reducer.py`

```python
"""
Metrics Aggregator REDUCER Node - Pure FSM Implementation.

Demonstrates pure FSM REDUCER capabilities:
- Pure state transformations (no mutable state)
- Intent emission for side effects
- Multiple aggregation strategies
- Conflict resolution
- Streaming support for large datasets

CRITICAL: This is a PURE FUNCTION node:
- No mutable instance state (self.*)
- No direct side effects (logging, metrics)
- Returns (result, intents) tuple concept
"""

import time
from collections import defaultdict

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.models.model_reducer_input import ModelReducerInput
from omnibase_core.enums.enum_reducer_types import (
    EnumReductionType,
    EnumStreamingMode,
    EnumConflictResolution,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

from your_project.nodes.model_metrics_aggregation_input import (
    ModelMetricsAggregationInput,
    EnumAggregationStrategy,
)
from your_project.nodes.model_metrics_aggregation_output import (
    ModelMetricsAggregationOutput,
    ModelIntent,
)


class NodeMetricsAggregatorReducer(NodeReducer):
    """
    Metrics Aggregator REDUCER Node - Pure FSM Implementation.

    Key Principles:
    ✅ Pure state transformations: input → (result, intents)
    ✅ No mutable state (no self.* accumulation)
    ✅ Intent emission for side effects
    ✅ Effect delegation (not direct execution)

    This node demonstrates the core ONEX pattern:
    - Reducer: Transforms data, emits Intents
    - Effect: Executes Intents (logging, metrics, I/O)
    - Orchestrator: Routes Intents to Effect nodes
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize pure FSM metrics aggregator.

        NOTE: No mutable state initialized.
        All state flows through input/output.
        """
        super().__init__(container)
        # ✅ CORRECT: No mutable state
        # (No self.aggregation_stats, no self.active_windows)


    async def aggregate_metrics(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelMetricsAggregationOutput:
        """
        Pure FSM aggregation: input → (result, intents).

        This is a PURE FUNCTION:
        - Same input always produces same output
        - No mutable state access/mutation
        - Side effects described as Intents, not executed

        Args:
            input_data: Immutable aggregation configuration

        Returns:
            ModelMetricsAggregationOutput: Result + Intents
        """
        start_time = time.time()

        # Convert to ModelReducerInput
        reducer_input = self._convert_to_reducer_input(input_data)

        try:
            # Execute reduction via base NodeReducer.process()
            reducer_output = await self.process(reducer_input)

            # Extract aggregated data
            aggregated_data = reducer_output.result

            # Calculate throughput
            processing_time_s = reducer_output.processing_time_ms / 1000
            throughput = (
                reducer_output.items_processed / processing_time_s
                if processing_time_s > 0 else 0
            )

            # ✅ CORRECT: Emit Intents for side effects
            intents = self._create_intents(
                input_data=input_data,
                reducer_output=reducer_output,
                aggregated_data=aggregated_data,
            )

            # Build pure output
            output = ModelMetricsAggregationOutput(
                aggregated_data=aggregated_data,
                sources_processed=len(input_data.data_sources),
                items_processed=reducer_output.items_processed,
                conflicts_resolved=reducer_output.conflicts_resolved,
                batches_processed=reducer_output.batches_processed,
                processing_time_ms=reducer_output.processing_time_ms,
                throughput_items_per_sec=throughput,
                operation_id=input_data.operation_id,
                intents=intents,  # Side effects described, not executed
            )

            return output

        except ModelOnexError:
            raise
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Metrics aggregation failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "sources": len(input_data.data_sources),
                    "processing_time_ms": processing_time,
                },
            ) from e


    def _create_intents(
        self,
        input_data: ModelMetricsAggregationInput,
        reducer_output,
        aggregated_data: dict[str, object],
    ) -> list[ModelIntent]:
        """
        Create Intents for side effects.

        This is where Reducer describes what should happen,
        without executing it directly.

        Intents will be routed to Effect nodes for execution:
        - log_event → LoggingEffectNode
        - record_metric → MetricsEffectNode
        - persist_data → DatabaseEffectNode
        """
        intents = []

        # Intent: Log completion event
        intents.append(
            ModelIntent(
                intent_type="log_event",
                target="logging_service",
                payload={
                    "level": "INFO",
                    "message": f"Metrics aggregation completed: {len(input_data.data_sources)} sources",
                    "context": {
                        "node_id": str(self.node_id),
                        "operation_id": str(input_data.operation_id),
                        "items_processed": reducer_output.items_processed,
                        "conflicts_resolved": reducer_output.conflicts_resolved,
                        "processing_time_ms": reducer_output.processing_time_ms,
                    },
                },
                priority=3,
            )
        )

        # Intent: Record metrics
        intents.append(
            ModelIntent(
                intent_type="record_metric",
                target="metrics_service",
                payload={
                    "metrics": [
                        {
                            "name": "aggregations_completed_total",
                            "value": 1,
                            "tags": {
                                "strategy": input_data.aggregation_strategy.value,
                                "streaming": str(input_data.enable_streaming),
                            },
                        },
                        {
                            "name": "aggregation_items_processed",
                            "value": reducer_output.items_processed,
                            "tags": {"operation_id": str(input_data.operation_id)},
                        },
                        {
                            "name": "aggregation_conflicts_resolved",
                            "value": reducer_output.conflicts_resolved,
                            "tags": {"strategy": input_data.aggregation_strategy.value},
                        },
                        {
                            "name": "aggregation_processing_time_ms",
                            "value": reducer_output.processing_time_ms,
                            "tags": {"batches": str(reducer_output.batches_processed)},
                        },
                    ],
                },
                priority=2,
            )
        )

        # Intent: Persist aggregation result (if needed)
        if input_data.metadata.get("persist_result") == "true":
            intents.append(
                ModelIntent(
                    intent_type="persist_aggregation",
                    target="database_service",
                    payload={
                        "operation_id": str(input_data.operation_id),
                        "aggregated_data": aggregated_data,
                        "metadata": {
                            "sources_count": len(input_data.data_sources),
                            "strategy": input_data.aggregation_strategy.value,
                            "completed_at": reducer_output.completed_at.isoformat() if hasattr(reducer_output, 'completed_at') else None,
                        },
                    },
                    priority=1,  # Highest priority for persistence
                )
            )

        return intents


    def _convert_to_reducer_input(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelReducerInput:
        """
        Convert domain model to ModelReducerInput.

        This is a pure transformation - no state mutation.
        """

        # Map aggregation strategy to conflict resolution
        conflict_resolution_map = {
            EnumAggregationStrategy.SUM: EnumConflictResolution.SUM,
            EnumAggregationStrategy.AVERAGE: EnumConflictResolution.AVERAGE,
            EnumAggregationStrategy.MAX: EnumConflictResolution.TAKE_MAX,
            EnumAggregationStrategy.MIN: EnumConflictResolution.TAKE_MIN,
            EnumAggregationStrategy.LATEST: EnumConflictResolution.TAKE_LATEST,
            EnumAggregationStrategy.MERGE_LISTS: EnumConflictResolution.MERGE,
        }

        conflict_resolution = conflict_resolution_map.get(
            input_data.aggregation_strategy,
            EnumConflictResolution.SUM,
        )

        # Determine reduction type
        if input_data.group_by_field:
            reduction_type = EnumReductionType.AGGREGATE
        else:
            reduction_type = EnumReductionType.MERGE

        # Determine streaming mode
        if input_data.enable_streaming:
            if input_data.window_size_ms > 0:
                streaming_mode = EnumStreamingMode.WINDOWED
            else:
                streaming_mode = EnumStreamingMode.INCREMENTAL
        else:
            streaming_mode = EnumStreamingMode.BATCH

        return ModelReducerInput(
            data=input_data.data_sources,
            reduction_type=reduction_type,
            operation_id=input_data.operation_id,
            conflict_resolution=conflict_resolution,
            streaming_mode=streaming_mode,
            batch_size=input_data.batch_size,
            window_size_ms=input_data.window_size_ms,
            metadata={
                "group_by": input_data.group_by_field or "none",
                "strategy": input_data.aggregation_strategy.value,
                **input_data.metadata,
            },
        )
```

---

## Step 3: Intent Execution Pattern

### How Intents Flow to Effect Nodes

```python
"""
Intent Flow Example:

1. Reducer emits Intents:
   result = await reducer.aggregate_metrics(input_data)
   intents = result.intents  # List of ModelIntent

2. Orchestrator routes Intents to Effect nodes:
   for intent in intents:
       if intent.intent_type == "log_event":
           await logging_effect_node.execute(intent)
       elif intent.intent_type == "record_metric":
           await metrics_effect_node.execute(intent)
       elif intent.intent_type == "persist_aggregation":
           await database_effect_node.execute(intent)

3. Effect nodes execute side effects:
   class LoggingEffectNode(NodeEffect):
       async def execute(self, intent: ModelIntent):
           # NOW we execute the side effect
           emit_log_event(
               intent.payload["level"],
               intent.payload["message"],
               intent.payload["context"],
           )
"""
```

### Effect Node for Intent Execution

**File**: `src/your_project/nodes/node_intent_executor_effect.py`

```python
"""Effect node that executes Intents from Reducer nodes."""

from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from your_project.nodes.model_metrics_aggregation_output import ModelIntent


class NodeIntentExecutorEffect(NodeEffect):
    """
    Intent Executor Effect Node.

    Executes side effects described by Reducer-emitted Intents.
    This is where actual I/O, logging, metrics happen.
    """

    async def execute_intent(self, intent: ModelIntent) -> None:
        """Execute a single Intent."""

        if intent.intent_type == "log_event":
            self._execute_log_event(intent)
        elif intent.intent_type == "record_metric":
            self._execute_record_metric(intent)
        elif intent.intent_type == "persist_aggregation":
            await self._execute_persist_aggregation(intent)
        else:
            # Unknown intent type - log warning
            emit_log_event(
                LogLevel.WARNING,
                f"Unknown intent type: {intent.intent_type}",
                {"intent": intent.dict()},
            )

    def _execute_log_event(self, intent: ModelIntent) -> None:
        """Execute logging Intent."""
        payload = intent.payload

        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
        }

        level = level_map.get(payload["level"], LogLevel.INFO)
        message = payload["message"]
        context = payload.get("context", {})

        # NOW we execute the side effect
        emit_log_event(level, message, context)

    def _execute_record_metric(self, intent: ModelIntent) -> None:
        """Execute metrics recording Intent."""
        payload = intent.payload

        # Send metrics to monitoring system
        for metric in payload.get("metrics", []):
            # In real implementation, send to Prometheus, Datadog, etc.
            print(f"📊 Metric: {metric['name']} = {metric['value']} {metric.get('tags', {})}")

    async def _execute_persist_aggregation(self, intent: ModelIntent) -> None:
        """Execute database persistence Intent."""
        payload = intent.payload

        # In real implementation, write to database
        print(f"💾 Persisting aggregation: {payload['operation_id']}")
```

---

## Step 4: Write Comprehensive Tests

**File**: `tests/unit/nodes/test_node_metrics_aggregator_reducer.py`

```python
"""Tests for Pure FSM NodeMetricsAggregatorReducer."""

import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from your_project.nodes.node_metrics_aggregator_reducer import (
    NodeMetricsAggregatorReducer,
)
from your_project.nodes.model_metrics_aggregation_input import (
    ModelMetricsAggregationInput,
    EnumAggregationStrategy,
)


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def aggregator_node(container):
    """Create metrics aggregator node."""
    return NodeMetricsAggregatorReducer(container)


@pytest.mark.asyncio
async def test_pure_fsm_no_mutable_state(aggregator_node):
    """Test that node maintains no mutable state."""
    # First call
    input_1 = ModelMetricsAggregationInput(
        data_sources=[
            {"metric_a": 10},
            {"metric_a": 20},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    result_1 = await aggregator_node.aggregate_metrics(input_1)

    # Second call with same input
    result_2 = await aggregator_node.aggregate_metrics(input_1)

    # ✅ VERIFY: Pure function - same input produces same result
    assert result_1.sources_processed == result_2.sources_processed
    assert result_1.items_processed == result_2.items_processed

    # ✅ VERIFY: No mutable state leaked between calls
    # (If there was mutable state, results might differ)


@pytest.mark.asyncio
async def test_intent_emission(aggregator_node):
    """Test that Intents are emitted for side effects."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"value": 10},
            {"value": 20},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    # ✅ VERIFY: Intents emitted
    assert len(result.intents) > 0

    # ✅ VERIFY: Logging intent present
    log_intents = [i for i in result.intents if i.intent_type == "log_event"]
    assert len(log_intents) >= 1

    # ✅ VERIFY: Metrics intent present
    metric_intents = [i for i in result.intents if i.intent_type == "record_metric"]
    assert len(metric_intents) >= 1

    # ✅ VERIFY: Intent structure
    log_intent = log_intents[0]
    assert log_intent.target == "logging_service"
    assert "message" in log_intent.payload
    assert "context" in log_intent.payload


@pytest.mark.asyncio
async def test_persistence_intent_when_requested(aggregator_node):
    """Test conditional Intent emission for persistence."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"value": 10},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
        metadata={"persist_result": "true"},  # Request persistence
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    # ✅ VERIFY: Persistence intent emitted when requested
    persist_intents = [
        i for i in result.intents
        if i.intent_type == "persist_aggregation"
    ]
    assert len(persist_intents) == 1

    # ✅ VERIFY: Intent has correct payload
    persist_intent = persist_intents[0]
    assert persist_intent.target == "database_service"
    assert "aggregated_data" in persist_intent.payload
    assert persist_intent.priority == 1  # Highest priority


@pytest.mark.asyncio
async def test_simple_sum_aggregation(aggregator_node):
    """Test simple numeric sum aggregation."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"metric_a": 10, "metric_b": 20},
            {"metric_a": 15, "metric_b": 25},
            {"metric_a": 20, "metric_b": 30},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    assert result.sources_processed == 3
    assert result.items_processed > 0
    assert len(result.intents) > 0  # Intents emitted


@pytest.mark.asyncio
async def test_average_aggregation(aggregator_node):
    """Test average aggregation strategy."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ],
        aggregation_strategy=EnumAggregationStrategy.AVERAGE,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    assert result.sources_processed == 3
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_max_aggregation(aggregator_node):
    """Test max aggregation strategy."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"temperature": 20.5},
            {"temperature": 25.3},
            {"temperature": 22.1},
        ],
        aggregation_strategy=EnumAggregationStrategy.MAX,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    assert result.sources_processed == 3


@pytest.mark.asyncio
async def test_conflict_resolution(aggregator_node):
    """Test conflict resolution during merge."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"user_id": "user1", "login_count": 5},
            {"user_id": "user1", "login_count": 3},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    assert result.conflicts_resolved >= 0


@pytest.mark.asyncio
async def test_streaming_aggregation(aggregator_node):
    """Test streaming mode for large datasets."""
    # Create large dataset
    large_dataset = [
        {"value": i} for i in range(5000)
    ]

    input_data = ModelMetricsAggregationInput(
        data_sources=large_dataset,
        aggregation_strategy=EnumAggregationStrategy.SUM,
        enable_streaming=True,
        batch_size=1000,
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    assert result.sources_processed == 5000
    assert result.batches_processed > 1


@pytest.mark.asyncio
async def test_intent_priority_ordering(aggregator_node):
    """Test that Intents have correct priority ordering."""
    input_data = ModelMetricsAggregationInput(
        data_sources=[{"value": 10}],
        aggregation_strategy=EnumAggregationStrategy.SUM,
        metadata={"persist_result": "true"},
    )

    result = await aggregator_node.aggregate_metrics(input_data)

    # ✅ VERIFY: High-priority intents first
    persist_intents = [
        i for i in result.intents
        if i.intent_type == "persist_aggregation"
    ]

    if persist_intents:
        assert persist_intents[0].priority == 1  # Highest priority
```

---

## Step 5: Usage Examples

### Basic Metrics Aggregation with Intent Execution

```python
import asyncio
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from your_project.nodes.node_metrics_aggregator_reducer import NodeMetricsAggregatorReducer
from your_project.nodes.node_intent_executor_effect import NodeIntentExecutorEffect
from your_project.nodes.model_metrics_aggregation_input import (
    ModelMetricsAggregationInput,
    EnumAggregationStrategy,
)


async def aggregate_server_metrics():
    """
    Demonstrate pure FSM pattern:
    1. Reducer transforms data + emits Intents
    2. Effect executor executes Intents
    """
    container = ModelONEXContainer()

    # Pure FSM Reducer node
    aggregator = NodeMetricsAggregatorReducer(container)

    # Effect node for Intent execution
    intent_executor = NodeIntentExecutorEffect(container)

    # Input data
    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"cpu_usage": 45.2, "memory_usage": 60.5, "disk_io": 120},
            {"cpu_usage": 52.1, "memory_usage": 55.3, "disk_io": 180},
            {"cpu_usage": 38.7, "memory_usage": 62.1, "disk_io": 95},
        ],
        aggregation_strategy=EnumAggregationStrategy.AVERAGE,
        metadata={"persist_result": "true"},
    )

    # Step 1: Pure transformation (Reducer)
    result = await aggregator.aggregate_metrics(input_data)

    print(f"📊 Metrics Aggregation Complete:")
    print(f"   Sources: {result.sources_processed}")
    print(f"   Items: {result.items_processed}")
    print(f"   Time: {result.processing_time_ms:.2f}ms")
    print(f"   Throughput: {result.throughput_items_per_sec:.1f} items/sec")
    print(f"   Intents Emitted: {len(result.intents)}")

    # Step 2: Execute Intents (Effect)
    print(f"\n🎯 Executing {len(result.intents)} Intents:")
    for intent in sorted(result.intents, key=lambda i: i.priority):
        print(f"   - {intent.intent_type} (priority {intent.priority})")
        await intent_executor.execute_intent(intent)

    return result.aggregated_data


asyncio.run(aggregate_server_metrics())
```

### Orchestrator Pattern for Full Workflow

```python
"""
Full orchestration pattern showing Reducer → Effect flow.
"""

class MetricsAggregationOrchestrator:
    """Orchestrates Reducer + Effect nodes for metrics aggregation."""

    def __init__(self, container: ModelONEXContainer):
        self.reducer = NodeMetricsAggregatorReducer(container)
        self.effect_executor = NodeIntentExecutorEffect(container)

    async def aggregate_and_execute(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelMetricsAggregationOutput:
        """
        Full workflow:
        1. Reducer: Transform data + emit Intents
        2. Effect: Execute Intents
        3. Return final result
        """
        # Step 1: Pure transformation (Reducer)
        result = await self.reducer.aggregate_metrics(input_data)

        # Step 2: Execute Intents (Effect)
        # Sort by priority (1=highest, 10=lowest)
        sorted_intents = sorted(result.intents, key=lambda i: i.priority)

        for intent in sorted_intents:
            try:
                await self.effect_executor.execute_intent(intent)
            except Exception as e:
                # Log Intent execution failure, but continue
                print(f"⚠️  Intent execution failed: {intent.intent_type} - {e}")

        return result


# Usage
async def main():
    container = ModelONEXContainer()
    orchestrator = MetricsAggregationOrchestrator(container)

    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"requests": 1000, "errors": 5},
            {"requests": 1500, "errors": 8},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    result = await orchestrator.aggregate_and_execute(input_data)
    print(f"✅ Aggregation complete: {result.items_processed} items")


asyncio.run(main())
```

---

## Quick Reference

### Pure FSM REDUCER Pattern

| Concept | Implementation | Example |
|---------|----------------|---------|
| **Pure Function** | Same input → same output | `aggregate_metrics(input)` |
| **No Mutable State** | No `self.*` accumulation | No `self.stats = {}` |
| **Intent Emission** | Describe side effects | `intents.append(ModelIntent(...))` |
| **Effect Delegation** | Let Effect nodes execute | `await effect.execute_intent(intent)` |

### Intent Types

```python
# Common Intent types for Reducer nodes
INTENT_TYPES = {
    "log_event": "Logging Effect Node",
    "record_metric": "Metrics Effect Node",
    "persist_data": "Database Effect Node",
    "send_notification": "Notification Effect Node",
    "trigger_workflow": "Workflow Orchestrator Node",
}
```

### Conflict Resolution Strategies

```python
# Available strategies
EnumConflictResolution.SUM          # Add values together
EnumConflictResolution.AVERAGE      # Average conflicting values
EnumConflictResolution.TAKE_MAX     # Keep maximum value
EnumConflictResolution.TAKE_MIN     # Keep minimum value
EnumConflictResolution.TAKE_LATEST  # Use latest value
EnumConflictResolution.MERGE        # Merge lists/objects
```

---

## Using MixinIntentPublisher for Event Publishing

### Overview

While `ModelIntent` is used for general side effects, **MixinIntentPublisher** provides a specialized pattern for publishing events to Kafka topics while maintaining node purity.

**When to use MixinIntentPublisher**:
- ✅ REDUCER needs to publish aggregated results as events
- ✅ COMPUTE needs to publish computed results for downstream processing
- ✅ Node wants to coordinate event publishing without direct Kafka I/O
- ✅ Testing needs to verify intent publishing without real Kafka

### Adding MixinIntentPublisher to Your REDUCER

**Step 1: Inherit from Mixin**

```python
from omnibase_core.mixins import MixinIntentPublisher
from omnibase_core.nodes.node_reducer import NodeReducer

class NodeMetricsAggregatorReducer(NodeReducer, MixinIntentPublisher):
    """REDUCER with event publishing capability via intents."""

    def __init__(self, container):
        super().__init__(container)
        # Initialize intent publisher (REQUIRED)
        self._init_intent_publisher(container)
```

**Step 2: Publish Events as Intents**

```python
async def aggregate_metrics(
    self,
    input_data: ModelMetricsAggregationInput,
) -> ModelMetricsAggregationOutput:
    """
    Aggregate metrics and publish results via intent.

    This maintains reducer purity - we build the event (pure)
    and publish an intent (coordination I/O), but don't
    publish directly to Kafka (domain I/O).
    """
    # Pure aggregation
    aggregated_data = self._reduce_data(input_data.data_sources)

    # Build event (pure - just data construction)
    metrics_event = MetricsAggregatedEvent(
        metric_name=input_data.metric_name,
        aggregated_value=aggregated_data.total,
        count=len(input_data.data_sources),
        timestamp=datetime.now(UTC),
    )

    # Publish intent (coordination I/O)
    await self.publish_event_intent(
        target_topic="dev.omninode-bridge.metrics.aggregated.v1",
        target_key=f"metrics-{input_data.metric_name}",
        event=metrics_event,
        correlation_id=input_data.correlation_id,
        priority=5
    )

    # Return result
    return ModelMetricsAggregationOutput(
        aggregated_data=aggregated_data,
        sources_processed=len(input_data.data_sources),
        items_processed=len(aggregated_data),
    )
```

**Step 3: Update Contract**

```yaml
# contract.yaml
subcontracts:
  refs:
    - "./contracts/intent_publisher.yaml"

mixins:
  - "MixinIntentPublisher"
```

### Testing with MixinIntentPublisher

```python
import pytest
from tests.fixtures.fixture_intent_publisher import MockKafkaClient

@pytest.mark.asyncio
async def test_reducer_publishes_aggregated_metrics():
    """Test REDUCER publishes aggregated metrics via intent."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    reducer = NodeMetricsAggregatorReducer(container)

    input_data = ModelMetricsAggregationInput(
        metric_name="api_latency",
        data_sources=[
            {"value": 100},
            {"value": 200},
            {"value": 150},
        ],
        aggregation_strategy=EnumAggregationStrategy.AVERAGE,
    )

    # Act
    result = await reducer.aggregate_metrics(input_data)

    # Assert - Aggregation is correct
    assert result.aggregated_data.average == 150.0

    # Assert - Intent was published
    assert mock_kafka.get_message_count() == 1
    assert mock_kafka.published_messages[0]["topic"] == "dev.omninode-bridge.intents.event-publish.v1"

    # Assert - Intent contains correct target
    import json
    intent_envelope = json.loads(mock_kafka.published_messages[0]["value"])
    intent_payload = intent_envelope["payload"]
    assert intent_payload["target_topic"] == "dev.omninode-bridge.metrics.aggregated.v1"
    assert intent_payload["target_event_payload"]["aggregated_value"] == 150.0
```

### Pattern Comparison

**ModelIntent (General Side Effects)**:
```python
# Use for: Logging, metrics, notifications, general I/O
intents = [
    ModelIntent(
        intent_type="log_event",
        target="logging_service",
        payload={"message": "Aggregation complete"},
    )
]
return ModelMetricsAggregationOutput(result=data, intents=intents)
```

**MixinIntentPublisher (Event Publishing)**:
```python
# Use for: Publishing domain events to Kafka topics
await self.publish_event_intent(
    target_topic="my.events.v1",
    target_key="event-123",
    event=my_event_model
)
return ModelMetricsAggregationOutput(result=data)
```

**Key Differences**:
- ModelIntent: Returned in output, executed by orchestrator
- MixinIntentPublisher: Awaited directly, publishes to intent topic immediately
- ModelIntent: For general side effects
- MixinIntentPublisher: Specifically for event publishing coordination

### Complete Example

```python
from datetime import UTC, datetime
from uuid import uuid4

from omnibase_core.mixins import MixinIntentPublisher
from omnibase_core.nodes.node_reducer import NodeReducer


class NodeMetricsAggregatorReducer(NodeReducer, MixinIntentPublisher):
    """
    REDUCER that aggregates metrics and publishes results via intent.

    Demonstrates:
    - Pure FSM aggregation logic
    - ModelIntent for side effects (logging, metrics)
    - MixinIntentPublisher for event publishing
    """

    def __init__(self, container):
        super().__init__(container)
        self._init_intent_publisher(container)

    async def aggregate_metrics(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelMetricsAggregationOutput:
        """Aggregate metrics and coordinate result publishing."""
        start_time = datetime.now(UTC)

        # PURE: Aggregate data
        aggregated = self._aggregate_data(input_data.data_sources)

        # PURE: Build event
        event = MetricsAggregatedEvent(
            metric_name=input_data.metric_name,
            value=aggregated.total,
            count=aggregated.count,
        )

        # COORDINATION I/O: Publish event intent
        await self.publish_event_intent(
            target_topic="dev.metrics.aggregated.v1",
            target_key=f"metrics-{input_data.metric_name}",
            event=event,
            correlation_id=input_data.correlation_id or uuid4(),
        )

        # PURE: Build side effect intents
        processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
        intents = [
            ModelIntent(
                intent_type="log_metric",
                target="metrics_service",
                payload={
                    "metric": "aggregation_time_ms",
                    "value": processing_time,
                },
            )
        ]

        return ModelMetricsAggregationOutput(
            aggregated_data=aggregated,
            sources_processed=len(input_data.data_sources),
            intents=intents,
        )

    def _aggregate_data(self, sources):
        """Pure aggregation logic (no I/O)."""
        # Implementation...
        pass
```

### Further Reading

- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Comprehensive testing guide
- [MODEL_INTENT_ARCHITECTURE.md](../../architecture/MODEL_INTENT_ARCHITECTURE.md) - Intent pattern details
- [MixinIntentPublisher Implementation](../../../src/omnibase_core/mixins/mixin_intent_publisher.py)

---

## Key Takeaways

### ✅ Pure FSM Pattern Benefits

1. **Predictable**: Same input always produces same output
2. **Testable**: No hidden state, easy to test
3. **Composable**: Reducers can be chained without side effects
4. **Debuggable**: All state transitions visible in input/output
5. **Parallelizable**: Pure functions safe for concurrent execution

### ✅ Intent Emission Benefits

1. **Separation of Concerns**: Reducer describes, Effect executes
2. **Testability**: Test Intent emission without executing side effects
3. **Flexibility**: Route Intents to different Effect implementations
4. **Observability**: Track all side effects through Intent logs
5. **Retry Logic**: Re-execute Intents without re-running Reducer

### ❌ Anti-Patterns to Avoid

```python
# ❌ WRONG: Mutable state
class NodeBadReducer(NodeReducer):
    def __init__(self, container):
        super().__init__(container)
        self.total_count = 0  # WRONG!

    async def process(self, input_data):
        self.total_count += 1  # WRONG!
        return result

# ❌ WRONG: Direct side effects
async def process(self, input_data):
    result = self._aggregate(input_data)
    emit_log_event(LogLevel.INFO, "Done")  # WRONG!
    return result

# ✅ CORRECT: Pure FSM with Intents
async def process(self, input_data):
    result = self._aggregate(input_data)
    intents = [
        ModelIntent(
            intent_type="log_event",
            target="logging_service",
            payload={"level": "INFO", "message": "Done"},
        )
    ]
    return ModelOutput(result=result, intents=intents)
```

---

## Next Steps

✅ **Congratulations!** You've built a pure FSM REDUCER node with Intent emission!

**Continue your journey**:
- [ORCHESTRATOR Node Tutorial](06_ORCHESTRATOR_NODE_TUTORIAL.md) - Master workflow coordination
- [Patterns Catalog](07_PATTERNS_CATALOG.md) - Common patterns and advanced Intent handling
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Testing strategies

**Challenge**: Build an Effect node that executes Intents with retry logic and circuit breakers!

---

**Last Updated**: 2025-01-20
**Framework Version**: omnibase_core 2.0+
**Tutorial Status**: ✅ Complete (Pure FSM Pattern)
