# REDUCER Node Tutorial: Build a Metrics Aggregator

**Reading Time**: 30 minutes
**Difficulty**: Intermediate
**Prerequisites**: [What is a Node?](01-what-is-a-node.md), [EFFECT Node Tutorial](04-effect-node-tutorial.md)

## What You'll Build

In this tutorial, you'll build a production-ready **Metrics Aggregation Node** that:

✅ Aggregates metrics data from multiple sources
✅ Supports multiple reduction types (fold, aggregate, merge, normalize)
✅ Handles streaming for large datasets
✅ Implements conflict resolution strategies
✅ Provides incremental and windowed processing

**Why REDUCER Nodes?**

REDUCER nodes handle data aggregation and transformation in the ONEX architecture:
- Merging data from multiple sources
- Aggregating metrics and statistics
- Normalizing data for analysis
- Conflict resolution during merges
- State reduction operations

**Tutorial Structure**:
1. Define aggregation models
2. Implement the REDUCER node
3. Add streaming support
4. Write comprehensive tests
5. See real-world usage examples

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

**File**: `src/your_project/nodes/model_metrics_aggregation_output.py`

```python
"""Output model for metrics aggregation REDUCER node."""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ModelMetricsAggregationOutput(BaseModel):
    """
    Results from metrics aggregation operations.

    Provides comprehensive aggregation results with
    processing statistics and conflict resolution details.
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


    class Config:
        """Pydantic configuration."""

        frozen = True
```

---

## Step 2: Implement the REDUCER Node

**File**: `src/your_project/nodes/node_metrics_aggregator_reducer.py`

```python
"""
Metrics Aggregator REDUCER Node - Production Implementation.

Demonstrates REDUCER capabilities:
- Multiple aggregation strategies
- Conflict resolution
- Streaming support for large datasets
- Incremental and windowed processing
"""

import time
from collections import defaultdict

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.model_reducer_input import ModelReducerInput
from omnibase_core.nodes.enum_reducer_types import (
    EnumReductionType,
    EnumStreamingMode,
    EnumConflictResolution,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from your_project.nodes.model_metrics_aggregation_input import (
    ModelMetricsAggregationInput,
    EnumAggregationStrategy,
)
from your_project.nodes.model_metrics_aggregation_output import (
    ModelMetricsAggregationOutput,
)


class NodeMetricsAggregatorReducer(NodeReducer):
    """
    Metrics Aggregator REDUCER Node.

    Aggregates metrics from multiple sources with configurable
    strategies, streaming support, and conflict resolution.

    Key Features:
    - Multiple aggregation strategies (sum, avg, max, min, latest)
    - Conflict resolution for data merges
    - Streaming support for large datasets
    - Incremental and windowed processing modes
    - Performance tracking and statistics
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize metrics aggregator REDUCER node."""
        super().__init__(container)

        # Track aggregation statistics
        self.aggregation_stats = {
            "total_aggregations": 0,
            "total_items_processed": 0,
            "total_conflicts_resolved": 0,
        }


    async def aggregate_metrics(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelMetricsAggregationOutput:
        """
        Aggregate metrics from multiple data sources.

        Args:
            input_data: Aggregation configuration

        Returns:
            ModelMetricsAggregationOutput: Aggregation results
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

            # Build output
            output = ModelMetricsAggregationOutput(
                aggregated_data=aggregated_data,
                sources_processed=len(input_data.data_sources),
                items_processed=reducer_output.items_processed,
                conflicts_resolved=reducer_output.conflicts_resolved,
                batches_processed=reducer_output.batches_processed,
                processing_time_ms=reducer_output.processing_time_ms,
                throughput_items_per_sec=throughput,
                operation_id=input_data.operation_id,
            )

            # Update statistics
            self.aggregation_stats["total_aggregations"] += 1
            self.aggregation_stats["total_items_processed"] += output.items_processed
            self.aggregation_stats["total_conflicts_resolved"] += output.conflicts_resolved

            emit_log_event(
                LogLevel.INFO,
                f"Metrics aggregation completed: {output.sources_processed} sources",
                {
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "items_processed": output.items_processed,
                    "conflicts_resolved": output.conflicts_resolved,
                    "processing_time_ms": output.processing_time_ms,
                },
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


    def _convert_to_reducer_input(
        self,
        input_data: ModelMetricsAggregationInput,
    ) -> ModelReducerInput:
        """Convert domain model to ModelReducerInput."""

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


    def get_aggregation_stats(self) -> dict[str, int | float]:
        """Get aggregation statistics for monitoring."""
        return {
            **self.aggregation_stats,
            "avg_items_per_aggregation": (
                self.aggregation_stats["total_items_processed"] /
                max(self.aggregation_stats["total_aggregations"], 1)
            ),
        }
```

---

## Step 3: Write Comprehensive Tests

**File**: `tests/unit/nodes/test_node_metrics_aggregator_reducer.py`

```python
"""Tests for NodeMetricsAggregatorReducer."""

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
    # Results stored in aggregated_data field


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
async def test_statistics_tracking(aggregator_node):
    """Test aggregation statistics tracking."""
    initial_stats = aggregator_node.get_aggregation_stats()

    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"a": 1},
            {"a": 2},
        ],
        aggregation_strategy=EnumAggregationStrategy.SUM,
    )

    await aggregator_node.aggregate_metrics(input_data)

    final_stats = aggregator_node.get_aggregation_stats()

    assert final_stats["total_aggregations"] == initial_stats["total_aggregations"] + 1
    assert final_stats["total_items_processed"] > initial_stats["total_items_processed"]
```

---

## Step 4: Usage Examples

### Basic Metrics Aggregation

```python
import asyncio
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from your_project.nodes.node_metrics_aggregator_reducer import NodeMetricsAggregatorReducer
from your_project.nodes.model_metrics_aggregation_input import (
    ModelMetricsAggregationInput,
    EnumAggregationStrategy,
)


async def aggregate_server_metrics():
    """Aggregate server metrics from multiple sources."""
    container = ModelONEXContainer()
    aggregator = NodeMetricsAggregatorReducer(container)

    input_data = ModelMetricsAggregationInput(
        data_sources=[
            {"cpu_usage": 45.2, "memory_usage": 60.5, "disk_io": 120},
            {"cpu_usage": 52.1, "memory_usage": 55.3, "disk_io": 180},
            {"cpu_usage": 38.7, "memory_usage": 62.1, "disk_io": 95},
        ],
        aggregation_strategy=EnumAggregationStrategy.AVERAGE,
    )

    result = await aggregator.aggregate_metrics(input_data)

    print(f"📊 Metrics Aggregation Complete:")
    print(f"   Sources: {result.sources_processed}")
    print(f"   Items: {result.items_processed}")
    print(f"   Time: {result.processing_time_ms:.2f}ms")
    print(f"   Throughput: {result.throughput_items_per_sec:.1f} items/sec")

    return result.aggregated_data


asyncio.run(aggregate_server_metrics())
```

### Streaming Large Dataset

```python
async def aggregate_large_dataset(data_sources: list[dict]):
    """Aggregate very large dataset with streaming."""
    container = ModelONEXContainer()
    aggregator = NodeMetricsAggregatorReducer(container)

    input_data = ModelMetricsAggregationInput(
        data_sources=data_sources,
        aggregation_strategy=EnumAggregationStrategy.SUM,
        enable_streaming=True,
        batch_size=5000,
    )

    result = await aggregator.aggregate_metrics(input_data)

    print(f"\n📈 Large Dataset Aggregation:")
    print(f"   Total Items: {result.items_processed:,}")
    print(f"   Batches: {result.batches_processed}")
    print(f"   Conflicts: {result.conflicts_resolved}")
    print(f"   Time: {result.processing_time_ms:,.0f}ms")
```

---

## Quick Reference

### REDUCER Capabilities

| Feature | Purpose | Example |
|---------|---------|---------|
| **Fold** | Reduce to single value | Sum all numbers |
| **Aggregate** | Group and summarize | Group by user_id |
| **Merge** | Combine datasets | Merge user profiles |
| **Normalize** | Scale data | Min-max normalization |
| **Streaming** | Handle large data | Process in batches |

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

## Next Steps

✅ **Congratulations!** You've built a production-ready REDUCER node!

**Continue your journey**:
- [ORCHESTRATOR Node Tutorial](06-orchestrator-node-tutorial.md) - Master workflow coordination
- [Patterns Catalog](07-patterns-catalog.md) - Common REDUCER patterns
- [Testing Guide](08-testing-guide.md) - Advanced testing strategies

**Challenge**: Add custom aggregation functions for domain-specific metrics!

---

**Last Updated**: 2025-01-18
**Framework Version**: omnibase_core 2.0+
**Tutorial Status**: ✅ Complete
