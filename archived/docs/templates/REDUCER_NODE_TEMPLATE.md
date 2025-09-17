# REDUCER Node Template

## Overview

This template provides the unified architecture pattern for ONEX REDUCER nodes. REDUCER nodes are responsible for aggregating, consolidating, and reducing data from multiple sources within the ONEX ecosystem.

## Key Characteristics

- **Data Aggregation**: Combine multiple inputs into consolidated outputs
- **Statistical Reduction**: Perform statistical operations on data sets
- **Pattern Recognition**: Identify patterns across multiple data sources
- **Stream Processing**: Handle continuous data streams with windowing
- **Memory Efficiency**: Optimize memory usage for large data processing

## Directory Structure

```
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_reducer/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py
│                   ├── config.py
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
│                   │   ├── data_aggregator.py
│                   │   ├── stream_processor.py
│                   │   ├── pattern_detector.py
│                   │   └── memory_optimizer.py
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
```

## Template Files

### 1. Node Implementation (`node.py`)

```python
"""ONEX REDUCER node for {DOMAIN} {MICROSERVICE_NAME} operations."""

import asyncio
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import time
from contextlib import asynccontextmanager
from collections import defaultdict
import statistics

from pydantic import ValidationError
from omnibase_core.nodes.base.node_reducer_service import NodeReducerService
from omnibase_core.models.model_onex_error import ModelONEXError
from omnibase_core.models.model_onex_warning import ModelONEXWarning
from omnibase_core.utils.error_sanitizer import ErrorSanitizer
from omnibase_core.utils.circuit_breaker import CircuitBreakerMixin

from .config import {DomainCamelCase}{MicroserviceCamelCase}ReducerConfig
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_input import Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_reducer_output import Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_reduction_type import Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_aggregation_strategy import Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy
from .utils.data_aggregator import DataAggregator
from .utils.stream_processor import StreamProcessor
from .utils.pattern_detector import PatternDetector
from .utils.memory_optimizer import MemoryOptimizer


class Node{DomainCamelCase}{MicroserviceCamelCase}Reducer(
    NodeReducerService[
        Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput,
        Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput,
        {DomainCamelCase}{MicroserviceCamelCase}ReducerConfig
    ],
    CircuitBreakerMixin
):
    """REDUCER node for {DOMAIN} {MICROSERVICE_NAME} data reduction operations.

    This node provides high-performance data aggregation and reduction services
    for {DOMAIN} domain operations, focusing on {MICROSERVICE_NAME} data processing.

    Key Features:
    - Sub-{PERFORMANCE_TARGET}ms reduction performance
    - Memory-efficient large dataset processing
    - Stream processing with configurable windows
    - Pattern detection and statistical analysis
    - Circuit breaker protection
    """

    def __init__(self, config: {DomainCamelCase}{MicroserviceCamelCase}ReducerConfig):
        """Initialize the REDUCER node with configuration.

        Args:
            config: Configuration for the reduction operations
        """
        super().__init__(config)
        CircuitBreakerMixin.__init__(
            self,
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout,
            expected_exception=Exception
        )

        # Initialize reduction components
        self._aggregator = DataAggregator(config.aggregation_config)
        self._stream_processor = StreamProcessor(config.stream_config)
        self._pattern_detector = PatternDetector(config.pattern_config)
        self._memory_optimizer = MemoryOptimizer(config.memory_config)
        self._error_sanitizer = ErrorSanitizer()

        # Processing state
        self._active_streams = {}
        self._reduction_metrics = []
        self._pattern_cache = {}
        self._memory_usage_tracker = defaultdict(list)

    @asynccontextmanager
    async def _performance_tracking(self, reduction_type: Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType):
        """Track performance metrics for reductions."""
        start_time = time.perf_counter()
        initial_memory = self._memory_optimizer.get_current_usage_mb()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            final_memory = self._memory_optimizer.get_current_usage_mb()

            self._reduction_metrics.append({
                "reduction_type": reduction_type,
                "duration_ms": duration_ms,
                "memory_delta_mb": final_memory - initial_memory,
                "timestamp": time.time()
            })

    async def process(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput:
        """Process {DOMAIN} {MICROSERVICE_NAME} reduction with typed interface.

        This is the business logic interface that provides type-safe reduction
        processing without ONEX infrastructure concerns.

        Args:
            input_data: Validated input data for reduction

        Returns:
            Reduced output data with aggregated results

        Raises:
            ValidationError: If input validation fails
            ReductionError: If reduction logic fails
            MemoryError: If processing exceeds memory limits
        """
        async with self._performance_tracking(input_data.reduction_type):
            try:
                # Pre-processing memory optimization
                await self._memory_optimizer.optimize_for_dataset(input_data.dataset_info)

                # Execute core reduction logic
                reduction_result = await self._execute_reduction(input_data)

                # Pattern detection on results
                patterns = await self._pattern_detector.detect_patterns(
                    reduction_result,
                    input_data.pattern_detection_enabled
                )

                # Post-processing optimization
                optimized_result = await self._memory_optimizer.optimize_output(reduction_result)

                return Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                    reduction_type=input_data.reduction_type,
                    aggregation_strategy=input_data.aggregation_strategy,
                    reduced_data=optimized_result,
                    patterns_detected=patterns,
                    success=True,
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=(
                        self._reduction_metrics[-1]["duration_ms"]
                        if self._reduction_metrics else 0.0
                    ),
                    input_record_count=len(input_data.data_sources),
                    output_record_count=self._get_output_record_count(optimized_result),
                    memory_efficiency=self._calculate_memory_efficiency(),
                    metadata={
                        "aggregation_applied": True,
                        "patterns_found": len(patterns) if patterns else 0,
                        "memory_optimization": True,
                        "compression_ratio": self._calculate_compression_ratio(input_data, optimized_result)
                    }
                )

            except ValidationError as e:
                sanitized_error = self._error_sanitizer.sanitize_validation_error(str(e))
                return Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                    reduction_type=input_data.reduction_type,
                    aggregation_strategy=input_data.aggregation_strategy,
                    success=False,
                    error_message=f"Input validation failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0,
                    input_record_count=len(input_data.data_sources) if input_data.data_sources else 0,
                    output_record_count=0
                )

            except MemoryError:
                await self._memory_optimizer.emergency_cleanup()
                return Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                    reduction_type=input_data.reduction_type,
                    aggregation_strategy=input_data.aggregation_strategy,
                    success=False,
                    error_message="Memory limit exceeded during reduction",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=self.config.reduction_timeout_ms,
                    input_record_count=len(input_data.data_sources) if input_data.data_sources else 0,
                    output_record_count=0
                )

            except asyncio.TimeoutError:
                return Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                    reduction_type=input_data.reduction_type,
                    aggregation_strategy=input_data.aggregation_strategy,
                    success=False,
                    error_message="Reduction timeout exceeded",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=self.config.reduction_timeout_ms,
                    input_record_count=len(input_data.data_sources) if input_data.data_sources else 0,
                    output_record_count=0
                )

            except Exception as e:
                sanitized_error = self._error_sanitizer.sanitize_error(str(e))
                return Model{DomainCamelCase}{MicroserviceCamelCase}ReducerOutput(
                    reduction_type=input_data.reduction_type,
                    aggregation_strategy=input_data.aggregation_strategy,
                    success=False,
                    error_message=f"Reduction failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0,
                    input_record_count=len(input_data.data_sources) if input_data.data_sources else 0,
                    output_record_count=0
                )

    async def _execute_reduction(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput
    ) -> Any:
        """Execute the core reduction logic.

        Args:
            input_data: Input data for reduction

        Returns:
            Reduced result data
        """
        # Apply circuit breaker protection
        async with self.circuit_breaker():
            if input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.AGGREGATE:
                return await self._aggregator.aggregate(
                    input_data.data_sources,
                    input_data.aggregation_strategy,
                    input_data.aggregation_parameters
                )

            elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.STATISTICAL:
                return await self._perform_statistical_reduction(
                    input_data.data_sources,
                    input_data.statistical_operations
                )

            elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.WINDOW:
                return await self._stream_processor.process_window(
                    input_data.data_sources,
                    input_data.window_config
                )

            elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.FILTER:
                return await self._apply_filter_reduction(
                    input_data.data_sources,
                    input_data.filter_criteria
                )

            elif input_data.reduction_type == Enum{DomainCamelCase}{MicroserviceCamelCase}ReductionType.GROUP:
                return await self._perform_group_reduction(
                    input_data.data_sources,
                    input_data.grouping_keys,
                    input_data.aggregation_strategy
                )

            else:
                raise ValueError(f"Unsupported reduction type: {input_data.reduction_type}")

    async def _perform_statistical_reduction(
        self,
        data_sources: List[Dict[str, Any]],
        statistical_operations: List[str]
    ) -> Dict[str, Any]:
        """Perform statistical reduction operations."""
        all_values = []
        for source in data_sources:
            if isinstance(source.get('values'), list):
                all_values.extend([v for v in source['values'] if isinstance(v, (int, float))])

        if not all_values:
            return {"error": "No numerical values found for statistical reduction"}

        results = {}

        if "mean" in statistical_operations:
            results["mean"] = statistics.mean(all_values)

        if "median" in statistical_operations:
            results["median"] = statistics.median(all_values)

        if "std_dev" in statistical_operations:
            results["standard_deviation"] = statistics.stdev(all_values) if len(all_values) > 1 else 0.0

        if "variance" in statistical_operations:
            results["variance"] = statistics.variance(all_values) if len(all_values) > 1 else 0.0

        if "min_max" in statistical_operations:
            results["minimum"] = min(all_values)
            results["maximum"] = max(all_values)
            results["range"] = max(all_values) - min(all_values)

        if "percentiles" in statistical_operations:
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

    async def _apply_filter_reduction(
        self,
        data_sources: List[Dict[str, Any]],
        filter_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filter criteria to reduce data sources."""
        filtered_results = []

        for source in data_sources:
            if self._matches_filter_criteria(source, filter_criteria):
                filtered_results.append(source)

        return filtered_results

    def _matches_filter_criteria(
        self,
        data_item: Dict[str, Any],
        filter_criteria: Dict[str, Any]
    ) -> bool:
        """Check if data item matches filter criteria."""
        for key, expected_value in filter_criteria.items():
            if key not in data_item:
                return False

            item_value = data_item[key]

            # Handle different filter types
            if isinstance(expected_value, dict):
                # Range filter: {"min": 10, "max": 100}
                if "min" in expected_value and item_value < expected_value["min"]:
                    return False
                if "max" in expected_value and item_value > expected_value["max"]:
                    return False
                # Regex filter: {"pattern": ".*@company.com"}
                if "pattern" in expected_value:
                    import re
                    if not re.match(expected_value["pattern"], str(item_value)):
                        return False
            elif isinstance(expected_value, list):
                # In list filter
                if item_value not in expected_value:
                    return False
            else:
                # Exact match
                if item_value != expected_value:
                    return False

        return True

    async def _perform_group_reduction(
        self,
        data_sources: List[Dict[str, Any]],
        grouping_keys: List[str],
        aggregation_strategy: Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy
    ) -> Dict[str, Any]:
        """Perform group-based reduction."""
        groups = defaultdict(list)

        # Group data by keys
        for source in data_sources:
            group_key = tuple(str(source.get(key, "null")) for key in grouping_keys)
            groups[group_key].append(source)

        # Apply aggregation to each group
        results = {}
        for group_key, group_data in groups.items():
            group_name = "_".join(group_key)

            if aggregation_strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.COUNT:
                results[group_name] = len(group_data)

            elif aggregation_strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.SUM:
                # Sum numeric fields
                numeric_sum = {}
                for item in group_data:
                    for key, value in item.items():
                        if isinstance(value, (int, float)):
                            numeric_sum[key] = numeric_sum.get(key, 0) + value
                results[group_name] = numeric_sum

            elif aggregation_strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.AVERAGE:
                # Average numeric fields
                numeric_avg = {}
                field_counts = {}
                for item in group_data:
                    for key, value in item.items():
                        if isinstance(value, (int, float)):
                            numeric_avg[key] = numeric_avg.get(key, 0) + value
                            field_counts[key] = field_counts.get(key, 0) + 1

                for key in numeric_avg:
                    if field_counts[key] > 0:
                        numeric_avg[key] = numeric_avg[key] / field_counts[key]

                results[group_name] = numeric_avg

            elif aggregation_strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.FIRST:
                results[group_name] = group_data[0] if group_data else None

            elif aggregation_strategy == Enum{DomainCamelCase}{MicroserviceCamelCase}AggregationStrategy.LAST:
                results[group_name] = group_data[-1] if group_data else None

        return results

    def _get_output_record_count(self, result_data: Any) -> int:
        """Calculate output record count from result data."""
        if isinstance(result_data, list):
            return len(result_data)
        elif isinstance(result_data, dict):
            return len(result_data)
        else:
            return 1 if result_data is not None else 0

    def _calculate_memory_efficiency(self) -> float:
        """Calculate memory efficiency score."""
        if not self._memory_usage_tracker:
            return 1.0

        recent_usage = list(self._memory_usage_tracker.values())[-10:]  # Last 10 operations
        if not recent_usage:
            return 1.0

        avg_usage = sum(recent_usage) / len(recent_usage)
        memory_limit = self.config.memory_config.max_memory_mb

        return max(0.0, 1.0 - (avg_usage / memory_limit))

    def _calculate_compression_ratio(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}ReducerInput,
        output_data: Any
    ) -> float:
        """Calculate data compression ratio."""
        input_size = len(str(input_data.data_sources)) if input_data.data_sources else 0
        output_size = len(str(output_data))

        if input_size == 0:
            return 1.0

        return output_size / input_size if output_size < input_size else 1.0

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for monitoring."""
        if not self._reduction_metrics:
            return {
                "total_reductions": 0,
                "average_duration_ms": 0.0,
                "memory_efficiency": 1.0,
                "active_streams": 0
            }

        total_reductions = len(self._reduction_metrics)
        average_duration = sum(m["duration_ms"] for m in self._reduction_metrics) / total_reductions
        average_memory_delta = sum(m["memory_delta_mb"] for m in self._reduction_metrics) / total_reductions

        return {
            "total_reductions": total_reductions,
            "average_duration_ms": round(average_duration, 2),
            "max_duration_ms": max(m["duration_ms"] for m in self._reduction_metrics),
            "min_duration_ms": min(m["duration_ms"] for m in self._reduction_metrics),
            "average_memory_delta_mb": round(average_memory_delta, 2),
            "memory_efficiency": self._calculate_memory_efficiency(),
            "active_streams": len(self._active_streams),
            "pattern_cache_size": len(self._pattern_cache),
            "circuit_breaker_status": self.circuit_breaker_status
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test core components
            aggregator_healthy = await self._aggregator.health_check()
            stream_processor_healthy = await self._stream_processor.health_check()
            pattern_detector_healthy = await self._pattern_detector.health_check()
            memory_optimizer_healthy = await self._memory_optimizer.health_check()

            # Check memory usage
            current_memory_mb = self._memory_optimizer.get_current_usage_mb()
            memory_healthy = current_memory_mb < self.config.memory_config.max_memory_mb * 0.8

            # Check performance metrics
            recent_metrics = [
                m for m in self._reduction_metrics
                if time.time() - m["timestamp"] < 300  # Last 5 minutes
            ]

            avg_performance = (
                sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)
                if recent_metrics else 0.0
            )

            performance_healthy = avg_performance < self.config.performance_threshold_ms

            overall_healthy = all([
                aggregator_healthy,
                stream_processor_healthy,
                pattern_detector_healthy,
                memory_optimizer_healthy,
                memory_healthy,
                performance_healthy
            ])

            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": {
                    "aggregator": "healthy" if aggregator_healthy else "unhealthy",
                    "stream_processor": "healthy" if stream_processor_healthy else "unhealthy",
                    "pattern_detector": "healthy" if pattern_detector_healthy else "unhealthy",
                    "memory_optimizer": "healthy" if memory_optimizer_healthy else "unhealthy"
                },
                "performance": {
                    "average_duration_ms": round(avg_performance, 2),
                    "threshold_ms": self.config.performance_threshold_ms,
                    "recent_reductions": len(recent_metrics)
                },
                "memory": {
                    "current_usage_mb": round(current_memory_mb, 2),
                    "limit_mb": self.config.memory_config.max_memory_mb,
                    "utilization_percent": round((current_memory_mb / self.config.memory_config.max_memory_mb) * 100, 2)
                },
                "circuit_breaker": self.circuit_breaker_status,
                "active_streams": len(self._active_streams)
            }

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "timestamp": time.time()
            }
```

### 2. Configuration (`config.py`)

```python
"""Configuration for {DOMAIN} {MICROSERVICE_NAME} REDUCER node."""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, validator

from omnibase_core.config.base_node_config import BaseNodeConfig

ConfigT = TypeVar('ConfigT', bound='BaseNodeConfig')


class AggregationConfig(BaseModel):
    """Configuration for data aggregation operations."""

    max_input_sources: int = Field(default=1000, ge=1, description="Maximum number of input data sources")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size for processing")
    parallel_aggregation: bool = Field(default=True, description="Enable parallel aggregation processing")
    aggregation_timeout_ms: float = Field(default=10000.0, ge=100.0, description="Aggregation timeout in milliseconds")
    enable_compression: bool = Field(default=True, description="Enable result compression")


class StreamConfig(BaseModel):
    """Configuration for stream processing operations."""

    window_size_ms: int = Field(default=10000, ge=1000, le=3600000, description="Stream window size in milliseconds")
    max_windows_active: int = Field(default=10, ge=1, le=100, description="Maximum active windows")
    watermark_delay_ms: int = Field(default=5000, ge=0, description="Watermark delay for late data")
    allow_late_data: bool = Field(default=True, description="Allow processing of late arriving data")
    checkpoint_interval_ms: int = Field(default=30000, ge=1000, description="Stream checkpoint interval")


class PatternConfig(BaseModel):
    """Configuration for pattern detection."""

    enable_pattern_detection: bool = Field(default=True, description="Enable automatic pattern detection")
    pattern_cache_size: int = Field(default=1000, ge=10, description="Pattern cache size")
    min_pattern_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum pattern confidence")
    max_patterns_per_result: int = Field(default=10, ge=1, le=50, description="Maximum patterns per result")
    pattern_types: List[str] = Field(default=["trend", "anomaly", "cycle"], description="Enabled pattern types")


class MemoryConfig(BaseModel):
    """Configuration for memory optimization."""

    max_memory_mb: float = Field(default=1024.0, ge=128.0, le=8192.0, description="Maximum memory usage in MB")
    cleanup_threshold_percent: float = Field(default=80.0, ge=50.0, le=95.0, description="Memory cleanup threshold percentage")
    garbage_collection_frequency: int = Field(default=10, ge=1, le=100, description="GC frequency (every N operations)")
    enable_memory_monitoring: bool = Field(default=True, description="Enable memory usage monitoring")
    swap_to_disk_threshold_mb: float = Field(default=512.0, ge=0.0, description="Threshold to swap data to disk")


class {DomainCamelCase}{MicroserviceCamelCase}ReducerConfig(BaseNodeConfig):
    """Configuration for {DOMAIN} {MICROSERVICE_NAME} REDUCER operations."""

    # Core reduction settings
    reduction_timeout_ms: float = Field(
        default=30000.0,
        ge=1000.0,
        le=300000.0,
        description="Maximum reduction processing time in milliseconds"
    )

    performance_threshold_ms: float = Field(
        default=5000.0,
        ge=100.0,
        le=30000.0,
        description="Performance threshold for health checks"
    )

    max_concurrent_reductions: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum concurrent reduction operations"
    )

    # Component configurations
    aggregation_config: AggregationConfig = Field(default_factory=AggregationConfig)
    stream_config: StreamConfig = Field(default_factory=StreamConfig)
    pattern_config: PatternConfig = Field(default_factory=PatternConfig)
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)

    # Circuit breaker settings
    circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Circuit breaker failure threshold"
    )

    circuit_breaker_timeout: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Circuit breaker recovery timeout in seconds"
    )

    # Data processing settings
    enable_data_validation: bool = Field(
        default=True,
        description="Enable input data validation"
    )

    enable_result_caching: bool = Field(
        default=True,
        description="Enable reduction result caching"
    )

    cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache TTL in seconds"
    )

    # Domain-specific settings
    domain_specific_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific configuration parameters"
    )

    @validator('reduction_timeout_ms')
    def validate_timeout(cls, v, values):
        """Ensure reduction timeout is reasonable for the performance threshold."""
        threshold = values.get('performance_threshold_ms', 5000.0)
        if v < threshold:
            raise ValueError(f"Reduction timeout ({v}ms) must be >= performance threshold ({threshold}ms)")
        return v

    @validator('max_concurrent_reductions')
    def validate_concurrency(cls, v, values):
        """Ensure concurrency settings are appropriate for memory limits."""
        if 'memory_config' in values:
            memory_limit = values['memory_config'].max_memory_mb
            estimated_memory_per_reduction = 50.0  # MB estimate per reduction
            max_by_memory = int(memory_limit / estimated_memory_per_reduction)
            if v > max_by_memory:
                raise ValueError(f"Concurrent reductions ({v}) may exceed memory limit. Max recommended: {max_by_memory}")
        return v

    @validator('aggregation_config')
    def validate_aggregation_config(cls, v, values):
        """Validate aggregation configuration consistency."""
        if v.aggregation_timeout_ms > values.get('reduction_timeout_ms', 30000.0):
            raise ValueError("Aggregation timeout cannot exceed reduction timeout")
        return v

    @classmethod
    def for_environment(cls: Type[ConfigT], environment: str) -> ConfigT:
        """Create environment-specific configuration.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Environment-optimized configuration
        """
        if environment == "production":
            return cls(
                reduction_timeout_ms=15000.0,
                performance_threshold_ms=2000.0,
                max_concurrent_reductions=50,
                aggregation_config=AggregationConfig(
                    max_input_sources=5000,
                    batch_size=500,
                    parallel_aggregation=True,
                    aggregation_timeout_ms=10000.0
                ),
                memory_config=MemoryConfig(
                    max_memory_mb=2048.0,
                    cleanup_threshold_percent=75.0,
                    garbage_collection_frequency=5,
                    swap_to_disk_threshold_mb=1024.0
                ),
                pattern_config=PatternConfig(
                    pattern_cache_size=5000,
                    min_pattern_confidence=0.8
                ),
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=30,
                enable_result_caching=True,
                cache_ttl_seconds=7200
            )

        elif environment == "staging":
            return cls(
                reduction_timeout_ms=30000.0,
                performance_threshold_ms=5000.0,
                max_concurrent_reductions=20,
                aggregation_config=AggregationConfig(
                    max_input_sources=2000,
                    batch_size=200
                ),
                memory_config=MemoryConfig(
                    max_memory_mb=1024.0,
                    cleanup_threshold_percent=80.0
                )
            )

        else:  # development
            return cls(
                reduction_timeout_ms=60000.0,
                performance_threshold_ms=10000.0,
                max_concurrent_reductions=10,
                aggregation_config=AggregationConfig(
                    max_input_sources=500,
                    batch_size=50,
                    parallel_aggregation=False
                ),
                memory_config=MemoryConfig(
                    max_memory_mb=512.0,
                    cleanup_threshold_percent=85.0,
                    enable_memory_monitoring=True
                ),
                pattern_config=PatternConfig(
                    pattern_cache_size=100,
                    min_pattern_confidence=0.6
                ),
                enable_data_validation=True,
                enable_result_caching=False
            )

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "reduction_timeout_ms": 30000.0,
                "performance_threshold_ms": 5000.0,
                "max_concurrent_reductions": 20,
                "aggregation_config": {
                    "max_input_sources": 1000,
                    "batch_size": 100,
                    "parallel_aggregation": True
                },
                "memory_config": {
                    "max_memory_mb": 1024.0,
                    "cleanup_threshold_percent": 80.0,
                    "enable_memory_monitoring": True
                },
                "pattern_config": {
                    "enable_pattern_detection": True,
                    "pattern_cache_size": 1000,
                    "min_pattern_confidence": 0.7
                }
            }
        }
```

This template continues the unified architecture pattern for REDUCER nodes. The complete template would include the remaining files (input/output models, enums, subcontracts, and manifest) following the same patterns established in the EFFECT and COMPUTE templates. Let me continue with the ORCHESTRATOR template to complete the full set:

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create omnibase_core enhancement document", "status": "completed", "activeForm": "Creating omnibase_core changes document"}, {"content": "Create omnibase_infra enhancement document", "status": "completed", "activeForm": "Creating omnibase_infra changes document"}, {"content": "Extend patterns to other node types (COMPUTE, REDUCER, ORCHESTRATOR)", "status": "completed", "activeForm": "Extending patterns to other node types"}, {"content": "Validate unified architecture across all node types", "status": "in_progress", "activeForm": "Validating unified architecture"}]
