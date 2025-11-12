"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

NodeReducer - Data Aggregation Node for 4-Node Architecture.

Specialized node type for data transformation and state reduction operations.
Focuses on streaming data processing, conflict resolution, and state aggregation.

Key Capabilities:
- State aggregation and data transformation
- Reduce operations (fold, accumulate, merge)
- Streaming support for large datasets
- Conflict resolution strategies
- RSD Data Processing (ticket metadata aggregation)
- Priority score normalization and ranking
- Graph dependency resolution and cycle detection
- Status consolidation across ticket collections

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_conflict_resolver import ModelConflictResolver
from omnibase_core.models.model_intent import ModelIntent
from omnibase_core.models.model_reducer_input import ModelReducerInput, T_Input
from omnibase_core.models.model_reducer_output import ModelReducerOutput, T_Output
from omnibase_core.models.model_streaming_window import ModelStreamingWindow


class NodeReducer(NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Data aggregation and state reduction node.

    Implements reduce operations (fold, accumulate, merge) with streaming support
    for large datasets and intelligent conflict resolution. Optimized for RSD
    data processing including ticket metadata aggregation and priority normalization.

    Key Features:
    - Multiple reduction types (fold, accumulate, merge, aggregate)
    - Streaming support for large datasets with windowing
    - Conflict resolution strategies for data conflicts
    - Performance optimization for batch processing
    - Type-safe input/output handling
    - Memory-efficient processing

    RSD Data Processing:
    - Ticket metadata aggregation from multiple sources
    - Priority score normalization and ranking
    - Graph dependency resolution and cycle detection
    - Status consolidation across ticket collections
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeReducer with ModelONEXContainer dependency injection.

        PURE FSM PATTERN: No mutable instance state.
        All state is passed through input/output, side effects emitted as Intents.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Configuration only (defaults, overridden in _initialize_node_resources)
        # These defaults are used if ProtocolNodeConfiguration is not available
        self.default_batch_size = 1000
        self.max_memory_usage_mb = 512
        self.streaming_buffer_size = 10000

        # Configuration: Legacy attribute initialization for existing functionality
        # These attributes support current implementation patterns
        self.reduction_functions: dict[EnumReductionType, Callable[..., Any]] = {}
        self.reduction_metrics: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "total_time_ms": 0.0, "avg_time_ms": 0.0}
        )
        self.active_windows: dict[str, ModelStreamingWindow] = {}

    async def process(
        self,
        input_data: ModelReducerInput[T_Input],
    ) -> ModelReducerOutput[T_Output]:
        """
        REQUIRED: Stream-based reduction with conflict resolution.

        STABLE INTERFACE: This method signature is frozen for code generation.

        Args:
            input_data: Strongly typed reduction input with configuration

        Returns:
            Strongly typed reduction output with processing statistics

        Raises:
            ModelOnexError: If reduction fails or memory limits exceeded
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_reducer_input(input_data)

            # Initialize conflict resolver
            conflict_resolver = ModelConflictResolver(
                input_data.conflict_resolution,
                None,  # Custom resolver would be passed here if needed
            )

            # Execute reduction based on streaming mode
            if input_data.streaming_mode == EnumStreamingMode.BATCH:
                result, items_processed = await self._process_batch(
                    input_data,
                    conflict_resolver,
                )
                batches_processed = 1
            elif input_data.streaming_mode == EnumStreamingMode.INCREMENTAL:
                (
                    result,
                    items_processed,
                    batches_processed,
                ) = await self._process_incremental(input_data, conflict_resolver)
            elif input_data.streaming_mode == EnumStreamingMode.WINDOWED:
                (
                    result,
                    items_processed,
                    batches_processed,
                ) = await self._process_windowed(input_data, conflict_resolver)
            else:
                result, items_processed = await self._process_batch(
                    input_data,
                    conflict_resolver,
                )
                batches_processed = 1

            processing_time = (time.time() - start_time) * 1000

            # PURE FSM: Emit Intents for side effects instead of direct execution
            intents: list[ModelIntent] = []

            # Intent to log metrics
            intents.append(
                ModelIntent(
                    intent_type="log_metric",
                    target="metrics_service",
                    payload={
                        "metric_type": "reduction_metrics",
                        "reduction_type": input_data.reduction_type.value,
                        "processing_time_ms": processing_time,
                        "success": True,
                        "items_processed": items_processed,
                    },
                    priority=3,
                )
            )

            # Intent to log completion event
            intents.append(
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
                            "items_processed": items_processed,
                            "conflicts_resolved": conflict_resolver.conflicts_count,
                            "batches_processed": batches_processed,
                        },
                    },
                    priority=2,
                )
            )

            # Create output with intents
            output = ModelReducerOutput(
                result=result,
                operation_id=input_data.operation_id,
                reduction_type=input_data.reduction_type,
                processing_time_ms=processing_time,
                items_processed=items_processed,
                conflicts_resolved=conflict_resolver.conflicts_count,
                streaming_mode=input_data.streaming_mode,
                batches_processed=batches_processed,
                intents=intents,  # Emit intents for Effect node
                metadata={
                    "batch_size": str(input_data.batch_size),
                    "window_size_ms": str(input_data.window_size_ms),
                    "conflict_strategy": input_data.conflict_resolution.value,
                },
            )

            return output

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # PURE FSM: Even errors emit Intents instead of side effects
            # Note: Intents would be lost on error, so we still raise
            # but document that a proper implementation would capture these

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Reduction failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "reduction_type": input_data.reduction_type.value,
                    "processing_time_ms": processing_time,
                    "error": str(e),
                    # Future: Include intents for error metrics
                    "suggested_intent": {
                        "type": "log_metric",
                        "target": "metrics_service",
                        "payload": {
                            "metric_type": "reduction_error",
                            "reduction_type": input_data.reduction_type.value,
                            "processing_time_ms": processing_time,
                            "success": False,
                        },
                    },
                },
            ) from e

    async def aggregate_rsd_tickets(
        self,
        tickets: list[dict[str, Any]],
        group_by: str = "status",
        aggregation_functions: dict[str, str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate RSD ticket metadata from multiple sources.

        Groups tickets by specified criteria and applies aggregation functions
        to compute summary statistics for each group.

        Args:
            tickets: List of ticket dictionaries
            group_by: Field to group tickets by
            aggregation_functions: Functions to apply (count, sum, avg, min, max)

        Returns:
            Grouped and aggregated ticket data

        Raises:
            ModelOnexError: If aggregation fails
        """
        if aggregation_functions is None:
            aggregation_functions = {
                "count": "count",
                "avg_priority": "avg",
                "max_age_days": "max",
                "total_dependencies": "sum",
            }

        # Prepare reduction input
        reduction_input = ModelReducerInput(
            data=tickets,
            reduction_type=EnumReductionType.AGGREGATE,
            metadata={
                "group_by": group_by,
                "aggregation_functions": str(aggregation_functions),
                "rsd_operation": "ticket_aggregation",
            },
        )

        result: Any = await self.process(reduction_input)
        return dict(result.result) if isinstance(result.result, dict) else {}

    async def normalize_priority_scores(
        self,
        tickets_with_scores: list[dict[str, Any]],
        score_field: str = "priority_score",
        normalization_method: str = "min_max",
    ) -> list[dict[str, Any]]:
        """
        Normalize priority scores and create rankings for RSD tickets.

        Args:
            tickets_with_scores: List of tickets with priority scores
            score_field: Field containing priority scores
            normalization_method: Normalization method (min_max, z_score, rank)

        Returns:
            Tickets with normalized scores and rankings

        Raises:
            ModelOnexError: If normalization fails
        """
        reduction_input = ModelReducerInput(
            data=tickets_with_scores,
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": score_field,
                "normalization_method": normalization_method,
                "rsd_operation": "priority_normalization",
            },
        )

        result: Any = await self.process(reduction_input)
        return list(result.result) if isinstance(result.result, list) else []

    async def resolve_dependency_cycles(
        self,
        dependency_graph: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Detect and resolve cycles in RSD dependency graphs.

        Args:
            dependency_graph: Graph as adjacency list (ticket_id -> [dependent_tickets])

        Returns:
            Analysis results with cycle detection and resolution suggestions

        Raises:
            ModelOnexError: If cycle detection fails
        """
        reduction_input = ModelReducerInput(
            data=list(dependency_graph.items()),
            reduction_type=EnumReductionType.MERGE,
            metadata={
                "graph_operation": "cycle_detection",
                "rsd_operation": "dependency_analysis",
            },
        )

        result: Any = await self.process(reduction_input)
        return dict(result.result) if isinstance(result.result, dict) else {}

    def register_reduction_function(
        self,
        reduction_type: EnumReductionType,
        function: Any,
    ) -> None:
        """
        Register custom reduction function.

        Args:
            reduction_type: Type of reduction operation
            function: Reduction function to register

        Raises:
            ModelOnexError: If reduction type already registered or function invalid
        """
        if reduction_type in self.reduction_functions:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Reduction type already registered: {reduction_type.value}",
                context={
                    "node_id": str(self.node_id),
                    "reduction_type": reduction_type.value,
                },
            )

        if not callable(function):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Reduction function must be callable: {reduction_type.value}",
                context={
                    "node_id": str(self.node_id),
                    "reduction_type": reduction_type.value,
                },
            )

        self.reduction_functions[reduction_type] = function

        emit_log_event(
            LogLevel.INFO,
            f"Reduction function registered: {reduction_type.value}",
            {"node_id": str(self.node_id), "reduction_type": reduction_type.value},
        )

    async def get_reduction_metrics(self) -> dict[str, dict[str, float]]:
        """Get detailed reduction performance metrics."""
        return {
            **self.reduction_metrics,
            "memory_usage": {
                "max_memory_mb": float(self.max_memory_usage_mb),
                "streaming_buffer_size": float(self.streaming_buffer_size),
                "active_windows": float(len(self.active_windows)),
            },
            "streaming_performance": {
                "default_batch_size": float(self.default_batch_size),
            },
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize reducer-specific resources."""
        # Load configuration from NodeConfigProvider if available
        config = self.container.get_service_optional(NodeConfigProvider)
        if config:
            # Load performance configurations
            batch_size_value = await config.get_performance_config(
                "reducer.default_batch_size", default=self.default_batch_size
            )
            max_memory_value = await config.get_performance_config(
                "reducer.max_memory_usage_mb", default=self.max_memory_usage_mb
            )
            buffer_size_value = await config.get_performance_config(
                "reducer.streaming_buffer_size", default=self.streaming_buffer_size
            )

            # Update configuration values with type checking
            if isinstance(batch_size_value, (int, float)):
                self.default_batch_size = int(batch_size_value)
            if isinstance(max_memory_value, (int, float)):
                self.max_memory_usage_mb = int(max_memory_value)
            if isinstance(buffer_size_value, (int, float)):
                self.streaming_buffer_size = int(buffer_size_value)

            emit_log_event(
                LogLevel.INFO,
                "NodeReducer loaded configuration from NodeConfigProvider",
                {
                    "node_id": str(self.node_id),
                    "default_batch_size": self.default_batch_size,
                    "max_memory_usage_mb": self.max_memory_usage_mb,
                    "streaming_buffer_size": self.streaming_buffer_size,
                },
            )

        emit_log_event(
            LogLevel.INFO,
            "NodeReducer resources initialized",
            {
                "node_id": str(self.node_id),
                "default_batch_size": self.default_batch_size,
                "max_memory_usage_mb": self.max_memory_usage_mb,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup reducer-specific resources."""
        # Clear active windows
        self.active_windows.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeReducer resources cleaned up",
            {"node_id": str(self.node_id)},
        )

    def _validate_reducer_input(self, input_data: ModelReducerInput[Any]) -> None:
        """
        Validate reducer input data.

        Args:
            input_data: Input data to validate

        Raises:
            ModelOnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not isinstance(input_data.reduction_type, EnumReductionType):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Reduction type must be valid EnumReductionType enum",
                context={
                    "node_id": str(self.node_id),
                    "reduction_type": str(input_data.reduction_type),
                },
            )

        if input_data.data is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Data cannot be None for reduction",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                },
            )

    async def _process_batch(
        self,
        input_data: ModelReducerInput[Any],
        conflict_resolver: ModelConflictResolver,
    ) -> tuple[Any, int]:
        """Process all data in a single batch."""
        reduction_type = input_data.reduction_type

        if reduction_type not in self.reduction_functions:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"No reduction function for type: {reduction_type.value}",
                context={
                    "node_id": str(self.node_id),
                    "reduction_type": reduction_type.value,
                    "available_types": [rt.value for rt in self.reduction_functions],
                },
            )

        reducer_func = self.reduction_functions[reduction_type]

        # Data is already typed as list[T_Input] in ModelReducerInput
        # No conversion needed, just use it directly
        data_list: list[Any] = input_data.data

        # Execute reduction
        result = await reducer_func(data_list, input_data, conflict_resolver)
        return result, len(data_list)

    async def _process_incremental(
        self,
        input_data: ModelReducerInput[Any],
        conflict_resolver: ModelConflictResolver,
    ) -> tuple[Any, int, int]:
        """Process data incrementally in batches."""
        batch_size = input_data.batch_size
        total_processed = 0
        batches_processed = 0
        accumulator = None

        # Process in batches
        batch: list[Any] = []
        if hasattr(input_data.data, "__iter__"):
            for item in input_data.data:
                batch.append(item)

                if len(batch) >= batch_size:
                    # Process this batch
                    batch_input = ModelReducerInput(
                        data=batch,
                        reduction_type=input_data.reduction_type,
                        operation_id=input_data.operation_id,
                        conflict_resolution=input_data.conflict_resolution,
                        streaming_mode=input_data.streaming_mode,
                        batch_size=input_data.batch_size,
                        window_size_ms=input_data.window_size_ms,
                        metadata=input_data.metadata,
                    )

                    batch_result, batch_count = await self._process_batch(
                        batch_input,
                        conflict_resolver,
                    )
                    accumulator = batch_result
                    total_processed += batch_count
                    batches_processed += 1
                    batch = []

        # Process remaining items
        if batch:
            batch_input = ModelReducerInput(
                data=batch,
                reduction_type=input_data.reduction_type,
                operation_id=input_data.operation_id,
                conflict_resolution=input_data.conflict_resolution,
                streaming_mode=input_data.streaming_mode,
                batch_size=input_data.batch_size,
                window_size_ms=input_data.window_size_ms,
                metadata=input_data.metadata,
            )

            batch_result, batch_count = await self._process_batch(
                batch_input,
                conflict_resolver,
            )
            accumulator = batch_result
            total_processed += batch_count
            batches_processed += 1

        return accumulator, total_processed, batches_processed

    async def _process_windowed(
        self,
        input_data: ModelReducerInput[Any],
        conflict_resolver: ModelConflictResolver,
    ) -> tuple[Any, int, int]:
        """Process data in time-based windows."""
        window = ModelStreamingWindow(input_data.window_size_ms)
        total_processed = 0
        windows_processed = 0
        results: list[Any] = []

        if hasattr(input_data.data, "__iter__"):
            for item in input_data.data:
                window_full = window.add_item(item)

                if window_full:
                    # Process current window
                    window_items = window.get_window_items()

                    window_input = ModelReducerInput(
                        data=window_items,
                        reduction_type=input_data.reduction_type,
                        operation_id=input_data.operation_id,
                        conflict_resolution=input_data.conflict_resolution,
                        streaming_mode=input_data.streaming_mode,
                        batch_size=input_data.batch_size,
                        window_size_ms=input_data.window_size_ms,
                        metadata=input_data.metadata,
                    )

                    window_result, window_count = await self._process_batch(
                        window_input,
                        conflict_resolver,
                    )
                    results.append(window_result)
                    total_processed += window_count
                    windows_processed += 1

                    # Advance to next window
                    window.advance_window()

        # Process final window if it has items
        final_items = window.get_window_items()
        if final_items:
            final_input = ModelReducerInput(
                data=final_items,
                reduction_type=input_data.reduction_type,
                operation_id=input_data.operation_id,
                conflict_resolution=input_data.conflict_resolution,
                streaming_mode=input_data.streaming_mode,
                batch_size=input_data.batch_size,
                window_size_ms=input_data.window_size_ms,
                metadata=input_data.metadata,
            )

            final_result, final_count = await self._process_batch(
                final_input,
                conflict_resolver,
            )
            results.append(final_result)
            total_processed += final_count
            windows_processed += 1

        # Combine window results
        if results:
            combined_input = ModelReducerInput(
                data=results,
                reduction_type=EnumReductionType.MERGE,
                operation_id=input_data.operation_id,
                conflict_resolution=input_data.conflict_resolution,
                streaming_mode=input_data.streaming_mode,
                batch_size=input_data.batch_size,
                window_size_ms=input_data.window_size_ms,
                metadata=input_data.metadata,
            )

            final_result, _ = await self._process_batch(
                combined_input,
                conflict_resolver,
            )
            return final_result, total_processed, windows_processed
        return None, 0, 0

    def _detect_dependency_cycles(
        self,
        graph_data: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        """Detect cycles in dependency graph using DFS."""
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for node, dependencies in graph_data:
            if isinstance(dependencies, list):
                graph[node] = dependencies
            else:
                graph[node] = []

        # DFS to detect cycles
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> bool:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                dfs(neighbor, path)

            path.pop()
            rec_stack.remove(node)
            return False

        # Check all nodes
        for node in graph:
            if node not in visited:
                dfs(node, [])

        return {
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "cycle_count": len(cycles),
            "total_nodes": len(graph),
            "analysis_timestamp": datetime.now().isoformat(),
        }
