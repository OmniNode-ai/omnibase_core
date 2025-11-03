# REDUCER Node Template - Pure FSM Pattern

## Overview

This template provides the **pure FSM architecture pattern** for ONEX REDUCER nodes. REDUCER nodes aggregate, consolidate, and reduce data from multiple sources using **immutable state** and **Intent emission** for all side effects.

## Core FSM Principles

1. **Immutable State**: `__init__()` contains ONLY immutable configuration
2. **Pure Functions**: `process()` is a pure function returning `(result, intents)`
3. **Intent Emission**: ALL side effects emitted as Intents (logging, metrics, caching, persistence)
4. **No Direct Mutations**: No state changes within the node

## Key Characteristics

- **Data Aggregation**: Combine multiple inputs into consolidated outputs
- **Statistical Reduction**: Perform statistical operations on data sets
- **Pattern Recognition**: Identify patterns across multiple data sources
- **Stream Processing**: Handle continuous data streams with windowing
- **Pure Reduction Logic**: All business logic is side-effect-free

## Directory Structure

```text
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_reducer/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py                  # Pure FSM implementation
│                   ├── config.py                # Immutable configuration
│                   ├── contracts/
│                   │   ├── __init__.py
│                   │   ├── reducer_contract.py
│                   │   └── subcontracts/
│                   │       ├── __init__.py
│                   │       ├── input_subcontract.yaml
│                   │       ├── output_subcontract.yaml
│                   │       └── config_subcontract.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_input.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output.py
│                   │   └── model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_config.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   ├── enum_{DOMAIN}_{MICROSERVICE_NAME}_reduction_type.py
│                   │   └── enum_{DOMAIN}_{MICROSERVICE_NAME}_aggregation_strategy.py
│                   ├── utils/
│                   │   ├── __init__.py
│                   │   ├── data_aggregator.py   # Pure functions
│                   │   ├── stream_processor.py  # Pure functions
│                   │   └── pattern_detector.py  # Pure functions
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_reducer/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_config.py
                    ├── test_contracts.py
                    └── test_models.py
```python

## Template Files

### 1. Pure FSM Node Implementation (`node.py`)

```python
"""Pure FSM REDUCER node for {DOMAIN} {MICROSERVICE_NAME} operations."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import ValidationError

from omnibase_core.nodes.base.node_core_base import NodeCoreBase
from omnibase_core.models.model_onex_container import ModelONEXContainer
from omnibase_core.models.model_intent import ModelIntent
from omnibase_core.models.model_reducer_output import ModelReducerOutput
from omnibase_core.enums.enum_intent_type import EnumIntentType
from omnibase_core.utils.error_sanitizer import ErrorSanitizer

from .config import {DomainCamelCase}{MicroserviceCamelCase}ReducerConfig
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_input import Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output import Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_reduction_type import Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_aggregation_strategy import Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy
from .utils.data_aggregator import aggregate_data
from .utils.stream_processor import process_stream_window
from .utils.pattern_detector import detect_patterns


class Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(NodeCoreBase):
    """Pure FSM REDUCER node for {DOMAIN} {MICROSERVICE_NAME} data reduction.

    This node implements pure functional reduction logic with Intent emission
    for all side effects. NO mutable state is maintained within the node.

    FSM Compliance:
    - ✅ Immutable configuration only
    - ✅ Pure process() function
    - ✅ Intent emission for side effects
    - ✅ No direct state mutations

    Key Features:
    - Sub-{PERFORMANCE_TARGET}ms reduction performance
    - Memory-efficient large dataset processing
    - Stream processing with configurable windows
    - Pattern detection and statistical analysis
    - Intent-based observability
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize the REDUCER node with immutable configuration.

        Args:
            container: ONEX container with dependency injection

        FSM Rules:
            - ONLY immutable configuration allowed
            - NO mutable state (lists, dicts, counters)
            - Configuration values are read-only
        """
        super().__init__(container)

        # ✅ CORRECT: Immutable configuration
        self.batch_size: int = 1000
        self.performance_threshold_ms: float = 5000.0
        self.max_input_sources: int = 10000
        self.enable_pattern_detection: bool = True
        self.aggregation_timeout_ms: float = 10000.0

        # ❌ FORBIDDEN: Mutable state
        # self.metrics = []              # VIOLATION: Mutable list
        # self.cache = {}                # VIOLATION: Mutable dict
        # self.counter = 0               # VIOLATION: Mutable counter
        # self.active_streams = set()    # VIOLATION: Mutable set

        # Error sanitizer (stateless utility)
        self._error_sanitizer = ErrorSanitizer()

    async def process(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> ModelReducerOutput:
        """Pure reduction function with Intent emission.

        This is the core business logic interface providing type-safe reduction
        processing without state mutations. ALL side effects are emitted as Intents.

        Args:
            input_data: Validated input data for reduction

        Returns:
            ModelReducerOutput with result and Intents for side effects

        Raises:
            ValidationError: If input validation fails
            ReductionError: If reduction logic fails

        FSM Guarantees:
            - No state mutations
            - Pure function behavior
            - All side effects via Intents
            - Idempotent for same inputs
        """
        start_time = time.perf_counter()
        intents: List[ModelIntent] = []

        try:
            # Emit pre-processing Intent
            intents.append(ModelIntent(
                intent_type=EnumIntentType.LOG,
                target="logger",
                payload={
                    "level": "info",
                    "message": f"Starting reduction: {input_data.reduction_type.value}",
                    "correlation_id": str(input_data.correlation_id),
                    "input_sources": len(input_data.data_sources)
                }
            ))

            # Execute pure reduction logic (no side effects)
            reduction_result = await self._execute_pure_reduction(input_data)

            # Pattern detection (pure function)
            patterns = []
            if self.enable_pattern_detection and input_data.pattern_detection_enabled:
                patterns = detect_patterns(
                    reduction_result,
                    min_confidence=0.7
                )

            # Calculate metrics (pure computation)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # Emit performance metrics Intent
            intents.append(ModelIntent(
                intent_type=EnumIntentType.METRIC,
                target="metrics_collector",
                payload={
                    "metric_name": "reduction_duration_ms",
                    "value": duration_ms,
                    "tags": {
                        "reduction_type": input_data.reduction_type.value,
                        "aggregation_strategy": input_data.aggregation_strategy.value,
                        "input_count": len(input_data.data_sources)
                    }
                }
            ))

            # Emit caching Intent (if applicable)
            if self._should_cache_result(input_data, reduction_result):
                intents.append(ModelIntent(
                    intent_type=EnumIntentType.CACHE_WRITE,
                    target="result_cache",
                    payload={
                        "cache_key": self._generate_cache_key(input_data),
                        "value": reduction_result,
                        "ttl_seconds": 3600,
                        "tags": ["reduction", input_data.reduction_type.value]
                    }
                ))

            # Emit pattern detection Intent (if patterns found)
            if patterns:
                intents.append(ModelIntent(
                    intent_type=EnumIntentType.EVENT,
                    target="pattern_analyzer",
                    payload={
                        "event_type": "patterns_detected",
                        "patterns": [p.dict() for p in patterns],
                        "reduction_type": input_data.reduction_type.value,
                        "correlation_id": str(input_data.correlation_id)
                    }
                ))

            # Build pure output model
            output = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                reduction_type=input_data.reduction_type,
                aggregation_strategy=input_data.aggregation_strategy,
                reduced_data=reduction_result,
                patterns_detected=patterns,
                success=True,
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                processing_time_ms=duration_ms,
                input_record_count=len(input_data.data_sources),
                output_record_count=self._calculate_output_count(reduction_result),
                metadata={
                    "aggregation_applied": True,
                    "patterns_found": len(patterns),
                    "cache_eligible": self._should_cache_result(input_data, reduction_result)
                }
            )

            # Return output with Intents
            return ModelReducerOutput(
                result=output,
                intents=intents,
                success=True
            )

        except ValidationError as e:
            sanitized_error = self._error_sanitizer.sanitize_validation_error(str(e))

            # Emit error Intent
            intents.append(ModelIntent(
                intent_type=EnumIntentType.LOG,
                target="logger",
                payload={
                    "level": "error",
                    "message": f"Validation failed: {sanitized_error}",
                    "correlation_id": str(input_data.correlation_id),
                    "error_type": "ValidationError"
                }
            ))

            error_output = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                reduction_type=input_data.reduction_type,
                aggregation_strategy=input_data.aggregation_strategy,
                success=False,
                error_message=f"Input validation failed: {sanitized_error}",
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                processing_time_ms=0.0,
                input_record_count=len(input_data.data_sources),
                output_record_count=0
            )

            return ModelReducerOutput(
                result=error_output,
                intents=intents,
                success=False
            )

        except asyncio.TimeoutError:
            # Emit timeout Intent
            intents.append(ModelIntent(
                intent_type=EnumIntentType.LOG,
                target="logger",
                payload={
                    "level": "warning",
                    "message": "Reduction timeout exceeded",
                    "correlation_id": str(input_data.correlation_id),
                    "timeout_ms": self.aggregation_timeout_ms
                }
            ))

            timeout_output = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                reduction_type=input_data.reduction_type,
                aggregation_strategy=input_data.aggregation_strategy,
                success=False,
                error_message="Reduction timeout exceeded",
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                processing_time_ms=self.aggregation_timeout_ms,
                input_record_count=len(input_data.data_sources),
                output_record_count=0
            )

            return ModelReducerOutput(
                result=timeout_output,
                intents=intents,
                success=False
            )

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))

            # Emit exception Intent
            intents.append(ModelIntent(
                intent_type=EnumIntentType.LOG,
                target="logger",
                payload={
                    "level": "error",
                    "message": f"Reduction failed: {sanitized_error}",
                    "correlation_id": str(input_data.correlation_id),
                    "error_type": type(e).__name__
                }
            ))

            error_output = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                reduction_type=input_data.reduction_type,
                aggregation_strategy=input_data.aggregation_strategy,
                success=False,
                error_message=f"Reduction failed: {sanitized_error}",
                correlation_id=input_data.correlation_id,
                timestamp=time.time(),
                processing_time_ms=0.0,
                input_record_count=len(input_data.data_sources),
                output_record_count=0
            )

            return ModelReducerOutput(
                result=error_output,
                intents=intents,
                success=False
            )

    async def _execute_pure_reduction(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> Any:
        """Execute pure reduction logic without side effects.

        This function delegates to pure utility functions based on reduction type.
        NO state mutations occur here.

        Args:
            input_data: Input data for reduction

        Returns:
            Pure reduction result

        Raises:
            ValueError: If reduction type is unsupported
        """
        # Apply timeout wrapper (pure async operation)
        try:
            return await asyncio.wait_for(
                self._reduce_by_type(input_data),
                timeout=self.aggregation_timeout_ms / 1000.0
            )
        except asyncio.TimeoutError:
            raise

    async def _reduce_by_type(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> Any:
        """Route reduction to appropriate pure function.

        Args:
            input_data: Input data for reduction

        Returns:
            Pure reduction result
        """
        if input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.AGGREGATE:
            # Pure aggregation function (from utils)
            return await aggregate_data(
                data_sources=input_data.data_sources,
                strategy=input_data.aggregation_strategy,
                parameters=input_data.aggregation_parameters
            )

        elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.STATISTICAL:
            # Pure statistical reduction
            return self._compute_statistics(
                input_data.data_sources,
                input_data.statistical_operations
            )

        elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.WINDOW:
            # Pure stream window processing (from utils)
            return await process_stream_window(
                data_sources=input_data.data_sources,
                window_config=input_data.window_config
            )

        elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.FILTER:
            # Pure filter reduction
            return self._apply_filter(
                input_data.data_sources,
                input_data.filter_criteria
            )

        elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.GROUP:
            # Pure group reduction
            return self._group_and_aggregate(
                input_data.data_sources,
                input_data.grouping_keys,
                input_data.aggregation_strategy
            )

        else:
            raise ValueError(f"Unsupported reduction type: {input_data.reduction_type}")

    def _compute_statistics(
        self,
        data_sources: List[Dict[str, Any]],
        operations: List[str]
    ) -> Dict[str, Any]:
        """Pure statistical computation.

        Args:
            data_sources: Input data sources
            operations: Statistical operations to perform

        Returns:
            Statistical results dictionary
        """
        import statistics

        # Extract all numeric values (pure operation)
        all_values = []
        for source in data_sources:
            if isinstance(source.get('values'), list):
                all_values.extend([
                    v for v in source['values']
                    if isinstance(v, (int, float))
                ])

        if not all_values:
            return {"error": "No numerical values found"}

        # Compute statistics (pure functions)
        results = {}

        if "mean" in operations:
            results["mean"] = statistics.mean(all_values)

        if "median" in operations:
            results["median"] = statistics.median(all_values)

        if "std_dev" in operations:
            results["standard_deviation"] = (
                statistics.stdev(all_values) if len(all_values) > 1 else 0.0
            )

        if "variance" in operations:
            results["variance"] = (
                statistics.variance(all_values) if len(all_values) > 1 else 0.0
            )

        if "min_max" in operations:
            results["minimum"] = min(all_values)
            results["maximum"] = max(all_values)
            results["range"] = max(all_values) - min(all_values)

        if "percentiles" in operations:
            sorted_values = sorted(all_values)
            results["percentiles"] = {
                "p25": statistics.quantiles(sorted_values, n=4)[0] if len(sorted_values) > 1 else sorted_values[0],
                "p50": statistics.median(sorted_values),
                "p75": statistics.quantiles(sorted_values, n=4)[2] if len(sorted_values) > 1 else sorted_values[0],
                "p95": statistics.quantiles(sorted_values, n=20)[18] if len(sorted_values) > 1 else sorted_values[0]
            }

        results["count"] = len(all_values)
        results["sum"] = sum(all_values)

        return results

    def _apply_filter(
        self,
        data_sources: List[Dict[str, Any]],
        filter_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Pure filter operation.

        Args:
            data_sources: Input data sources
            filter_criteria: Filter criteria dictionary

        Returns:
            Filtered data sources
        """
        return [
            source for source in data_sources
            if self._matches_criteria(source, filter_criteria)
        ]

    def _matches_criteria(
        self,
        data_item: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> bool:
        """Pure predicate for filter matching.

        Args:
            data_item: Data item to check
            criteria: Matching criteria

        Returns:
            True if item matches all criteria
        """
        for key, expected in criteria.items():
            if key not in data_item:
                return False

            value = data_item[key]

            # Range filter
            if isinstance(expected, dict):
                if "min" in expected and value < expected["min"]:
                    return False
                if "max" in expected and value > expected["max"]:
                    return False
                if "pattern" in expected:
                    import re
                    if not re.match(expected["pattern"], str(value)):
                        return False
            # List membership
            elif isinstance(expected, list):
                if value not in expected:
                    return False
            # Exact match
            else:
                if value != expected:
                    return False

        return True

    def _group_and_aggregate(
        self,
        data_sources: List[Dict[str, Any]],
        grouping_keys: List[str],
        strategy: Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy
    ) -> Dict[str, Any]:
        """Pure group-based aggregation.

        Args:
            data_sources: Input data sources
            grouping_keys: Keys to group by
            strategy: Aggregation strategy

        Returns:
            Grouped and aggregated results
        """
        from collections import defaultdict

        # Group data (pure operation)
        groups = defaultdict(list)
        for source in data_sources:
            key = tuple(str(source.get(k, "null")) for k in grouping_keys)
            groups[key].append(source)

        # Aggregate each group (pure)
        results = {}
        for group_key, group_data in groups.items():
            group_name = "_".join(group_key)

            if strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.COUNT:
                results[group_name] = len(group_data)

            elif strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.SUM:
                numeric_sum = {}
                for item in group_data:
                    for k, v in item.items():
                        if isinstance(v, (int, float)):
                            numeric_sum[k] = numeric_sum.get(k, 0) + v
                results[group_name] = numeric_sum

            elif strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.AVERAGE:
                numeric_sum = {}
                counts = {}
                for item in group_data:
                    for k, v in item.items():
                        if isinstance(v, (int, float)):
                            numeric_sum[k] = numeric_sum.get(k, 0) + v
                            counts[k] = counts.get(k, 0) + 1

                numeric_avg = {
                    k: numeric_sum[k] / counts[k]
                    for k in numeric_sum if counts[k] > 0
                }
                results[group_name] = numeric_avg

            elif strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.FIRST:
                results[group_name] = group_data[0] if group_data else None

            elif strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.LAST:
                results[group_name] = group_data[-1] if group_data else None

        return results

    def _calculate_output_count(self, result: Any) -> int:
        """Pure computation of output record count.

        Args:
            result: Reduction result

        Returns:
            Record count
        """
        if isinstance(result, list):
            return len(result)
        elif isinstance(result, dict):
            return len(result)
        else:
            return 1 if result is not None else 0

    def _should_cache_result(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput,
        result: Any
    ) -> bool:
        """Pure predicate for cache eligibility.

        Args:
            input_data: Input data
            result: Reduction result

        Returns:
            True if result should be cached
        """
        # Pure business logic for cache decision
        return (
            len(input_data.data_sources) >= 100 and  # Large dataset
            self._calculate_output_count(result) > 0 and  # Valid result
            input_data.reduction_type in [
                Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.AGGREGATE,
                Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.STATISTICAL
            ]
        )

    def _generate_cache_key(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> str:
        """Pure cache key generation.

        Args:
            input_data: Input data

        Returns:
            Cache key string
        """
        import hashlib
        import json

        # Pure deterministic key generation
        key_data = {
            "reduction_type": input_data.reduction_type.value,
            "aggregation_strategy": input_data.aggregation_strategy.value,
            "source_count": len(input_data.data_sources),
            "parameters": input_data.aggregation_parameters
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return f"reduction:{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"
```python

### 2. Output Model with Intents (`model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output.py`)

```python
"""Output model for {DOMAIN} {MICROSERVICE_NAME} REDUCER operations."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(BaseModel):
    """Output model for reduction operations.

    This model represents the pure result of reduction logic
    without side effects or state mutations.
    """

    # Core reduction results
    reduction_type: str = Field(..., description="Type of reduction performed")
    aggregation_strategy: str = Field(..., description="Aggregation strategy used")
    reduced_data: Any = Field(..., description="Reduced result data")
    patterns_detected: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Patterns detected in reduction results"
    )

    # Status and metadata
    success: bool = Field(..., description="Whether reduction succeeded")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if reduction failed"
    )
    correlation_id: UUID = Field(..., description="Request correlation ID")
    timestamp: float = Field(..., description="Processing timestamp")
    processing_time_ms: float = Field(..., description="Processing duration in milliseconds")

    # Metrics
    input_record_count: int = Field(..., description="Number of input records")
    output_record_count: int = Field(..., description="Number of output records")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional processing metadata"
    )

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
```python

### 3. Pure Utility Functions (`utils/data_aggregator.py`)

```python
"""Pure aggregation functions for REDUCER operations."""

from typing import Any, Dict, List
import asyncio


async def aggregate_data(
    data_sources: List[Dict[str, Any]],
    strategy: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Pure aggregation function.

    This function performs aggregation without any side effects or state mutations.

    Args:
        data_sources: List of data sources to aggregate
        strategy: Aggregation strategy (COUNT, SUM, AVERAGE, etc.)
        parameters: Optional aggregation parameters

    Returns:
        Aggregated result dictionary

    FSM Guarantees:
        - No side effects
        - Deterministic for same inputs
        - No external dependencies
        - Pure computation only
    """
    if not data_sources:
        return {"count": 0, "result": None}

    if strategy == "COUNT":
        return {
            "count": len(data_sources),
            "timestamp": parameters.get("timestamp") if parameters else None
        }

    elif strategy == "SUM":
        # Pure summation
        totals = {}
        for source in data_sources:
            for key, value in source.items():
                if isinstance(value, (int, float)):
                    totals[key] = totals.get(key, 0) + value

        return {
            "count": len(data_sources),
            "sums": totals
        }

    elif strategy == "AVERAGE":
        # Pure averaging
        totals = {}
        counts = {}

        for source in data_sources:
            for key, value in source.items():
                if isinstance(value, (int, float)):
                    totals[key] = totals.get(key, 0) + value
                    counts[key] = counts.get(key, 0) + 1

        averages = {
            key: totals[key] / counts[key]
            for key in totals if counts[key] > 0
        }

        return {
            "count": len(data_sources),
            "averages": averages
        }

    else:
        return {
            "error": f"Unsupported aggregation strategy: {strategy}"
        }
```python

## FSM Compliance Checklist

- ✅ **Immutable State**: Only read-only configuration in `__init__()`
- ✅ **Pure Functions**: `process()` returns `(result, intents)` without mutations
- ✅ **Intent Emission**: All side effects (logging, metrics, caching) via Intents
- ✅ **No Direct Mutations**: No instance variables modified during processing
- ✅ **Utility Purity**: All utility functions are pure (no side effects)
- ✅ **Deterministic**: Same inputs always produce same outputs (excluding timestamps)

## Anti-Patterns to Avoid

### ❌ Mutable State in __init__

```python
# WRONG: Mutable state
def __init__(self, container):
    super().__init__(container)
    self.metrics = []           # ❌ Mutable list
    self.cache = {}             # ❌ Mutable dict
    self.counter = 0            # ❌ Mutable counter
```python

### ❌ Direct Side Effects in process()

```python
# WRONG: Direct side effects
async def process(self, input_data):
    # ❌ Direct logging
    logger.info("Processing reduction")

    # ❌ Direct metrics
    self.metrics.append({"duration": 100})

    # ❌ Direct caching
    self.cache[key] = result

    return result
```python

### ❌ State Mutations

```python
# WRONG: State mutation
async def process(self, input_data):
    # ❌ Modifying instance state
    self.counter += 1
    self.active_streams.add(stream_id)

    return result
```python

## Migration Guide

To migrate existing REDUCER nodes to pure FSM:

1. **Audit __init__**: Remove ALL mutable state, keep only configuration
2. **Extract Side Effects**: Convert all logging, metrics, caching to Intents
3. **Pure Utility Functions**: Move business logic to pure functions in utils/
4. **Update Output Model**: Add `intents: List[ModelIntent]` field
5. **Return ModelReducerOutput**: Return `ModelReducerOutput(result, intents, success)`

## Testing Pure FSM Reducers

```python
async def test_pure_reducer_no_side_effects():
    """Verify reducer has no side effects."""
    container = ModelONEXContainer(...)
    reducer = Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(container)

    input_data = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput(...)

    # Call twice with same input
    result1 = await reducer.process(input_data)
    result2 = await reducer.process(input_data)

    # Results should be identical (excluding timestamps)
    assert result1.result.reduced_data == result2.result.reduced_data
    assert len(result1.intents) == len(result2.intents)


async def test_reducer_emits_intents():
    """Verify reducer emits proper Intents."""
    container = ModelONEXContainer(...)
    reducer = Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(container)

    input_data = Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput(...)

    output = await reducer.process(input_data)

    # Verify Intents were emitted
    assert len(output.intents) > 0

    # Check for expected Intent types
    intent_types = {intent.intent_type for intent in output.intents}
    assert EnumIntentType.LOG in intent_types
    assert EnumIntentType.METRIC in intent_types
```text

## References

- **Core Patterns**: `/docs/architecture/ONEX_PATTERNS.md`
- **Intent System**: `/docs/architecture/INTENT_SYSTEM.md`
- **FSM Architecture**: `/docs/architecture/FSM_ARCHITECTURE.md`
- **Testing Guide**: `/docs/testing/REDUCER_TESTING.md`
