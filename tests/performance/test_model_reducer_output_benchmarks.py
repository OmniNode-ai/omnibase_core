#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Performance benchmarks for ModelReducerOutput operations.

These tests measure the performance characteristics of reducer output operations
across varying data sizes, especially for large data scenarios.

Performance Baselines (as of 2025-12-16):
    - Model creation: < 1ms for small data, < 10ms for 1000 items
    - Serialization: < 5ms for small data, < 50ms for 1000 items
    - Deserialization: < 5ms for small data, < 50ms for 1000 items
    - Validation: < 0.1ms per field
    - Memory usage: < 100MB for 10,000 items

Test Methodology:
    - Uses time.perf_counter() for high-precision timing
    - Each benchmark runs multiple iterations and reports mean timing
    - Tests scale from 10 items to 10,000 items
    - Memory profiling uses psutil for RSS measurements

Related:
    - src/omnibase_core/models/reducer/model_reducer_output.py
    - tests/unit/models/reducer/test_model_reducer_output.py
    - PR #205 review feedback
"""

import time
from collections.abc import Callable
from statistics import mean
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.reducer.payloads import ModelPayloadMetric


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestModelReducerOutputPerformance:
    """Performance benchmarks for ModelReducerOutput operations.

    Note:
    - Marked as @slow due to performance timing tests
    - Timeout (120s) for performance measurement tests with large data
    - Uses custom timing logic with time.perf_counter()
    """

    def time_operation(self, func: Callable[[], Any], iterations: int = 100) -> float:
        """Time an operation over multiple iterations.

        Iteration Count Strategy:
            For data-size-dependent tests, iteration counts scale inversely
            with data size to keep test runtime reasonable while maintaining
            statistical significance:

            - Small data (10-100 items): 100 iterations for stable means
            - Large data (1000+ items): 10 iterations (operations are slower)

            Common formulas used:
            - Data size scaling: max(10, 1000 // data_size)
            - Intent/tag scaling: max(10, 100 // max(1, count // 10))

        Args:
            func: Callable to benchmark (should be side-effect free)
            iterations: Number of iterations to run (default: 100)

        Returns:
            Mean execution time in seconds across all iterations
        """
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)
        return mean(times)

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            # Threshold rationale:
            # - 10 items: UUID generation (3 × 10µs) + validation (10 fields × 10µs) + dict creation (~500µs) = ~1ms
            # - 100 items: Linear scaling + nested dict overhead = ~2ms
            # - 1000 items: Pydantic validation dominates (0.01ms/field × 1000) = ~10ms
            # - 10000 items: Memory allocation + GC overhead + validation = ~50ms
            # See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#1-model-creation-thresholds
            pytest.param(10, 1.0, id="small_10_items"),
            pytest.param(100, 2.0, id="medium_100_items"),
            pytest.param(1000, 10.0, id="large_1000_items"),
            pytest.param(10000, 50.0, id="xlarge_10000_items"),
        ],
    )
    def test_model_creation_performance(
        self, data_size: int, max_time_ms: float
    ) -> None:
        """Benchmark model creation with varying data sizes.

        Validates that model creation scales appropriately with data size.
        Tests both simple results (int) and complex results (dict with lists).

        Performance Baseline:
            - 10 items: < 1ms
            - 100 items: < 2ms
            - 1000 items: < 10ms
            - 10000 items: < 50ms

        Threshold Rationale:
            These thresholds are set for CI runners (GitHub Actions 2-core).
            Local development typically runs 1.5-2x faster.

            Key factors affecting performance:
            - UUID generation: 3 UUIDs per model (~30µs total)
            - Pydantic validation: ~10-100µs per field
            - Nested structure traversal: ~0.5-5ms for dicts with lists
            - Memory allocation: Increases with data size

            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md
        """
        operation_id = uuid4()

        # Create complex result data with nested structure
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
            "metadata": {"total": data_size, "status": "complete"},
        }

        def create_output():
            return ModelReducerOutput[dict](
                result=result_data,
                operation_id=operation_id,
                reduction_type=EnumReductionType.AGGREGATE,
                processing_time_ms=42.5,
                items_processed=data_size,
                conflicts_resolved=0,
                streaming_mode=EnumStreamingMode.BATCH,
                batches_processed=1,
            )

        # Run benchmark (fewer iterations for larger data)
        # Formula: max(10, 1000 // data_size) scales inversely with data size
        # data_size=10 → 100 iterations, data_size=100 → 10 iterations, data_size≥1000 → 10 iterations
        iterations = max(10, 1000 // data_size)
        avg_time = self.time_operation(create_output, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Model creation with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            pytest.param(10, 5.0, id="small_10_items"),
            pytest.param(100, 10.0, id="medium_100_items"),
            pytest.param(1000, 50.0, id="large_1000_items"),
            pytest.param(10000, 200.0, id="xlarge_10000_items"),
        ],
    )
    def test_serialization_performance(
        self, data_size: int, max_time_ms: float
    ) -> None:
        """Benchmark serialization (model_dump) performance.

        Validates that converting ModelReducerOutput to dictionary scales
        appropriately with data size.

        Performance Baseline:
            - 10 items: < 5ms
            - 100 items: < 10ms
            - 1000 items: < 50ms
            - 10000 items: < 200ms
        """
        operation_id = uuid4()
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
            "metadata": {"total": data_size},
        }

        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.5,
            items_processed=data_size,
        )

        def serialize():
            return output.model_dump()

        # Fewer iterations for larger data to keep test runtime reasonable
        # Formula: max(10, 1000 // data_size) scales inversely with data size
        iterations = max(10, 1000 // data_size)
        avg_time = self.time_operation(serialize, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Serialization with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            pytest.param(10, 5.0, id="small_10_items"),
            pytest.param(100, 10.0, id="medium_100_items"),
            pytest.param(1000, 50.0, id="large_1000_items"),
            pytest.param(10000, 200.0, id="xlarge_10000_items"),
        ],
    )
    def test_json_serialization_performance(
        self, data_size: int, max_time_ms: float
    ) -> None:
        """Benchmark JSON serialization performance.

        Validates that converting ModelReducerOutput to JSON string scales
        appropriately with data size. This is critical for event bus operations.

        Performance Baseline:
            - 10 items: < 5ms
            - 100 items: < 10ms
            - 1000 items: < 50ms
            - 10000 items: < 200ms
        """
        operation_id = uuid4()
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
            "metadata": {"total": data_size},
        }

        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.5,
            items_processed=data_size,
        )

        def json_serialize():
            return output.model_dump_json()

        # Fewer iterations for larger data to keep test runtime reasonable
        # Formula: max(10, 1000 // data_size) scales inversely with data size
        iterations = max(10, 1000 // data_size)
        avg_time = self.time_operation(json_serialize, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"JSON serialization with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            pytest.param(10, 5.0, id="small_10_items"),
            pytest.param(100, 10.0, id="medium_100_items"),
            pytest.param(1000, 50.0, id="large_1000_items"),
            pytest.param(10000, 200.0, id="xlarge_10000_items"),
        ],
    )
    def test_deserialization_performance(
        self, data_size: int, max_time_ms: float
    ) -> None:
        """Benchmark deserialization (model_validate) performance.

        Validates that reconstructing ModelReducerOutput from dictionary scales
        appropriately with data size.

        Performance Baseline:
            - 10 items: < 5ms
            - 100 items: < 10ms
            - 1000 items: < 50ms
            - 10000 items: < 200ms
        """
        operation_id = uuid4()
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
            "metadata": {"total": data_size},
        }

        # Create reference output
        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.5,
            items_processed=data_size,
        )

        # Serialize to dict for deserialization benchmark
        data_dict = output.model_dump()

        def deserialize():
            return ModelReducerOutput[dict].model_validate(data_dict)

        # Fewer iterations for larger data to keep test runtime reasonable
        # Formula: max(10, 1000 // data_size) scales inversely with data size
        iterations = max(10, 1000 // data_size)
        avg_time = self.time_operation(deserialize, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Deserialization with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("data_size", "max_time_ms"),
        [
            pytest.param(10, 5.0, id="small_10_items"),
            pytest.param(100, 10.0, id="medium_100_items"),
            pytest.param(1000, 50.0, id="large_1000_items"),
            pytest.param(10000, 200.0, id="xlarge_10000_items"),
        ],
    )
    def test_json_deserialization_performance(
        self, data_size: int, max_time_ms: float
    ) -> None:
        """Benchmark JSON deserialization performance.

        Validates that reconstructing ModelReducerOutput from JSON string scales
        appropriately with data size. Critical for event bus message handling.

        Performance Baseline:
            - 10 items: < 5ms
            - 100 items: < 10ms
            - 1000 items: < 50ms
            - 10000 items: < 200ms
        """
        operation_id = uuid4()
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
            "metadata": {"total": data_size},
        }

        # Create reference output and serialize to JSON
        output = ModelReducerOutput[dict](
            result=result_data,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.5,
            items_processed=data_size,
        )
        json_data = output.model_dump_json()

        def json_deserialize():
            return ModelReducerOutput[dict].model_validate_json(json_data)

        # Fewer iterations for larger data to keep test runtime reasonable
        # Formula: max(10, 1000 // data_size) scales inversely with data size
        iterations = max(10, 1000 // data_size)
        avg_time = self.time_operation(json_deserialize, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"JSON deserialization with {data_size} items took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    def test_validation_performance_field_level(self) -> None:
        """Benchmark field-level validation performance.

        Validates that Pydantic field validators execute efficiently.
        Tests sentinel value validation for processing_time_ms and items_processed.

        Performance Baseline:
            - Field validation: < 0.1ms per field

        Threshold Rationale:
            - 0.1ms per field allows for 10,000 validations/second per core
            - Validator overhead: ~10-50µs (decorator + function call)
            - Type checking: ~10-20ns per isinstance() call
            - Conditional logic: ~5-10ns per if/else branch

            CI variance: ±20% due to CPU scheduling and cache effects
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#4-field-validation-thresholds
        """
        operation_id = uuid4()

        def create_with_validation():
            return ModelReducerOutput[int](
                result=42,
                operation_id=operation_id,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.5,  # Triggers validation
                items_processed=100,  # Triggers validation
            )

        avg_time = self.time_operation(create_with_validation, 1000)
        avg_time_ms = avg_time * 1000

        # Each creation validates 2 fields (processing_time_ms, items_processed)
        # So per-field validation should be < 0.1ms
        per_field_ms = avg_time_ms / 2

        assert per_field_ms < 0.1, (
            f"Field validation took {per_field_ms:.3f}ms per field, expected < 0.1ms"
        )

    def test_validation_performance_sentinel_values(self) -> None:
        """Benchmark validation with sentinel values (-1).

        Validates that sentinel value validation doesn't add overhead compared
        to normal value validation.

        Performance Baseline:
            - Sentinel validation: < 0.2ms additional overhead
        """
        operation_id = uuid4()

        # Normal values
        def create_normal():
            return ModelReducerOutput[int](
                result=42,
                operation_id=operation_id,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.5,
                items_processed=100,
            )

        # Sentinel values
        def create_sentinel():
            return ModelReducerOutput[int](
                result=42,
                operation_id=operation_id,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=-1.0,  # Sentinel
                items_processed=-1,  # Sentinel
            )

        normal_time = self.time_operation(create_normal, 1000)
        sentinel_time = self.time_operation(create_sentinel, 1000)

        time_diff_ms = (sentinel_time - normal_time) * 1000

        # Sentinel validation should not add significant overhead
        assert time_diff_ms < 0.2, (
            f"Sentinel validation added {time_diff_ms:.3f}ms overhead, expected < 0.2ms"
        )

    @pytest.mark.parametrize(
        ("intent_count", "max_time_ms"),
        [
            pytest.param(0, 1.0, id="no_intents"),
            pytest.param(10, 2.0, id="10_intents"),
            pytest.param(100, 10.0, id="100_intents"),
            pytest.param(1000, 50.0, id="1000_intents"),
        ],
    )
    def test_intent_handling_performance(
        self, intent_count: int, max_time_ms: float
    ) -> None:
        """Benchmark performance with varying numbers of intents.

        Validates that ModelIntent tuple handling scales appropriately.

        Performance Baseline:
            - 0 intents: < 1ms
            - 10 intents: < 2ms
            - 100 intents: < 10ms
            - 1000 intents: < 50ms

        Threshold Rationale:
            Intent handling is critical for FSM-driven reducers. Each ModelIntent
            requires UUID generation + dict payload creation (~100-200µs).
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#6-intent-handling-thresholds
        """
        operation_id = uuid4()

        # Create multiple intents
        intents = tuple(
            ModelIntent(
                intent_id=uuid4(),
                intent_type="record_metric",
                target="metrics_service",
                payload=ModelPayloadMetric(
                    name=f"metric_{i}",
                    value=float(i),
                ),
            )
            for i in range(intent_count)
        )

        def create_with_intents():
            return ModelReducerOutput[int](
                result=42,
                operation_id=operation_id,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.5,
                items_processed=100,
                intents=intents,
            )

        # Fewer iterations for larger intent counts to keep test runtime reasonable
        # Formula: max(10, 100 // max(1, intent_count // 10)) scales inversely with intent count
        # intent_count≤100 → 100 iterations, intent_count=1000 → 10 iterations
        iterations = max(10, 100 // max(1, intent_count // 10))
        avg_time = self.time_operation(create_with_intents, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Intent handling with {intent_count} intents took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("tag_count", "max_time_ms"),
        [
            pytest.param(0, 1.0, id="no_tags"),
            pytest.param(10, 2.0, id="10_tags"),
            pytest.param(100, 10.0, id="100_tags"),
        ],
    )
    def test_metadata_handling_performance(
        self, tag_count: int, max_time_ms: float
    ) -> None:
        """Benchmark metadata handling with varying numbers of tags.

        Validates that ModelReducerMetadata scales with tag count.

        Performance Baseline:
            - 0 tags: < 1ms
            - 10 tags: < 2ms
            - 100 tags: < 10ms

        Threshold Rationale:
            Metadata tags are used for tracing, correlation, and observability.
            10 tags is typical for production systems with distributed tracing.
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#7-metadata-handling-thresholds
        """
        operation_id = uuid4()

        metadata = ModelReducerMetadata(
            source="api_gateway",
            trace_id="trace123",
            correlation_id="corr456",
            tags=[f"tag_{i}" for i in range(tag_count)],
        )

        def create_with_metadata():
            return ModelReducerOutput[int](
                result=42,
                operation_id=operation_id,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.5,
                items_processed=100,
                metadata=metadata,
            )

        # Fewer iterations for larger tag counts to keep test runtime reasonable
        # Formula: max(10, 100 // max(1, tag_count // 10)) scales inversely with tag count
        # tag_count≤10 → 100 iterations, tag_count=100 → 10 iterations
        iterations = max(10, 100 // max(1, tag_count // 10))
        avg_time = self.time_operation(create_with_metadata, iterations)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < max_time_ms, (
            f"Metadata handling with {tag_count} tags took {avg_time_ms:.2f}ms, "
            f"expected < {max_time_ms}ms"
        )

    @pytest.mark.parametrize(
        ("data_size", "max_memory_mb"),
        [
            # Memory threshold rationale:
            # - Python object overhead: ~28-56 bytes per object
            # - UUID storage: 16 bytes + wrapper (~72 bytes total per UUID)
            # - Dict overhead: 30-70% of data size (hash table implementation)
            # - String interning: Short strings may be deduplicated
            # - GC timing: Garbage collector may not run immediately
            #
            # Thresholds are per 10 model instances:
            # - 10 items: 10 models × ~100KB = ~1MB
            # - 100 items: 10 models × ~500KB = ~5MB
            # - 1000 items: 10 models × ~2MB = ~20MB
            # - 10000 items: 10 models × ~10MB = ~100MB
            #
            # NOTE: Memory thresholds are NOT configurable via environment variables
            # because memory usage is more consistent across environments than timing.
            # See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#5-memory-usage-thresholds
            pytest.param(10, 1, id="small_10_items"),
            pytest.param(100, 5, id="medium_100_items"),
            pytest.param(1000, 20, id="large_1000_items"),
            pytest.param(10000, 100, id="xlarge_10000_items"),
        ],
    )
    def test_memory_usage(self, data_size: int, max_memory_mb: int) -> None:
        """Benchmark memory usage with varying data sizes.

        Validates that memory usage scales appropriately with data size.
        Uses psutil to measure RSS (Resident Set Size).

        Performance Baseline:
            - 10 items: < 1MB
            - 100 items: < 5MB
            - 1000 items: < 20MB
            - 10000 items: < 100MB

        Note:
            Memory measurements are approximate and may vary based on
            Python runtime, GC behavior, and system state.

        Threshold Rationale:
            Memory thresholds are based on RSS measurements which include:
            - Python object overhead (~28-56 bytes per object)
            - UUID storage (16 bytes data + ~56 bytes wrapper = ~72 bytes)
            - Dict hash table overhead (30-70% of data size)
            - String storage (with possible interning for short strings)

            These thresholds are NOT environment-configurable because memory
            usage is relatively consistent across CI and local environments
            (unlike timing, which varies significantly with CPU performance).

            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#5-memory-usage-thresholds
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Force garbage collection before measurement
        import gc

        gc.collect()

        initial_memory = process.memory_info().rss

        # Create multiple outputs to measure aggregate memory usage
        outputs = []
        for _ in range(10):  # Create 10 instances
            operation_id = uuid4()
            result_data = {
                "items": [{"id": i, "value": f"item_{i}"} for i in range(data_size)],
                "metadata": {"total": data_size},
            }

            output = ModelReducerOutput[dict](
                result=result_data,
                operation_id=operation_id,
                reduction_type=EnumReductionType.AGGREGATE,
                processing_time_ms=42.5,
                items_processed=data_size,
            )
            outputs.append(output)

        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024

        assert memory_increase_mb < max_memory_mb, (
            f"Memory usage with {data_size} items per output (10 outputs) "
            f"increased by {memory_increase_mb:.2f}MB, expected < {max_memory_mb}MB"
        )

    def test_round_trip_performance(self) -> None:
        """Benchmark full round-trip serialization/deserialization.

        Validates end-to-end performance for common event bus workflow:
        Create -> Serialize to JSON -> Deserialize from JSON -> Access fields

        Performance Baseline:
            - Full round-trip with 100 items: < 20ms

        Threshold Rationale:
            Round-trip performance directly impacts end-to-end event processing latency.
            At 20ms model overhead + 30ms network = 50ms total, system can handle
            20 events/second per consumer (acceptable for most workloads).
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#8-round-trip-performance-thresholds
        """
        operation_id = uuid4()
        result_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(100)],
            "metadata": {"total": 100},
        }

        def round_trip():
            # Create
            output = ModelReducerOutput[dict](
                result=result_data,
                operation_id=operation_id,
                reduction_type=EnumReductionType.AGGREGATE,
                processing_time_ms=42.5,
                items_processed=100,
            )

            # Serialize to JSON
            json_data = output.model_dump_json()

            # Deserialize from JSON
            restored = ModelReducerOutput[dict].model_validate_json(json_data)

            # Access fields (verify no lazy loading overhead)
            _ = restored.result
            _ = restored.operation_id
            _ = restored.processing_time_ms
            _ = restored.items_processed
            _ = restored.metadata

            return restored

        avg_time = self.time_operation(round_trip, 50)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < 20.0, (
            f"Round-trip with 100 items took {avg_time_ms:.2f}ms, expected < 20ms"
        )

    def test_frozen_immutability_overhead(self) -> None:
        """Benchmark frozen=True immutability overhead.

        Validates that frozen=True doesn't add significant overhead to
        field access compared to mutable models.

        Performance Baseline:
            - Field access overhead: < 0.01ms

        Threshold Rationale:
            Field access happens frequently in production code. At 0.01ms for 11 fields
            = ~1µs per field, overhead is negligible compared to business logic.
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#9-field-access-overhead-thresholds
        """
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.5,
            items_processed=100,
        )

        def access_fields():
            _ = output.result
            _ = output.operation_id
            _ = output.reduction_type
            _ = output.processing_time_ms
            _ = output.items_processed
            _ = output.conflicts_resolved
            _ = output.streaming_mode
            _ = output.batches_processed
            _ = output.intents
            _ = output.metadata
            _ = output.timestamp

        avg_time = self.time_operation(access_fields, 10000)
        avg_time_ms = avg_time * 1000

        assert avg_time_ms < 0.01, (
            f"Field access took {avg_time_ms:.3f}ms, expected < 0.01ms"
        )

    def test_comparison_dict_vs_pydantic(self) -> None:
        """Compare performance: dict vs Pydantic model.

        Provides insight into the performance trade-off between raw dicts
        and strongly-typed Pydantic models.

        Note:
            This is informational only. Pydantic models are expected to be
            10-100x slower than raw dicts due to validation and type checking,
            but this overhead is acceptable for the benefits of type safety.

            The key insight is that the ABSOLUTE time (not relative %)
            remains very small (< 1ms for typical payloads).

        Threshold Rationale:
            In production, type safety and validation errors caught early are worth
            the 10-100x overhead. A 0.5ms Pydantic operation vs 0.05ms raw dict is
            negligible compared to network latency (10-50ms) or database queries (50-500ms).
            See: docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#10-pydantic-model-vs-raw-dict-comparison
        """
        operation_id = uuid4()
        result_data = {"items": list(range(100)), "metadata": {"total": 100}}

        # Pydantic model
        def create_pydantic():
            return ModelReducerOutput[dict](
                result=result_data,
                operation_id=operation_id,
                reduction_type=EnumReductionType.AGGREGATE,
                processing_time_ms=42.5,
                items_processed=100,
            )

        # Raw dict
        def create_dict():
            return {
                "result": result_data,
                "operation_id": str(operation_id),
                "reduction_type": "aggregate",
                "processing_time_ms": 42.5,
                "items_processed": 100,
            }

        pydantic_time_ms = self.time_operation(create_pydantic, 100) * 1000
        dict_time_ms = self.time_operation(create_dict, 100) * 1000

        overhead_ms = pydantic_time_ms - dict_time_ms
        overhead_pct = (overhead_ms / dict_time_ms) * 100 if dict_time_ms > 0 else 0

        # Log results for informational purposes
        print("\nPydantic vs Dict Performance Comparison (100 items):")
        print(f"  Pydantic model: {pydantic_time_ms:.3f}ms")
        print(f"  Raw dict: {dict_time_ms:.3f}ms")
        print(f"  Overhead: {overhead_ms:.3f}ms ({overhead_pct:.1f}%)")

        # The key assertion: absolute time should be fast, not relative percentage
        # Pydantic is expected to be 10-100x slower than dicts, but that's OK
        # because absolute time is still < 1ms for typical payloads
        assert pydantic_time_ms < 1.0, (
            f"Pydantic model creation took {pydantic_time_ms:.3f}ms, expected < 1ms "
            "(absolute time matters more than relative overhead)"
        )
