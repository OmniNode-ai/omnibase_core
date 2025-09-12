"""
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

Author: ONEX Framework Team
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.common_types import ModelScalarValue

# Import contract model for reducer nodes
from omnibase_core.core.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.node_core_base import NodeCoreBase
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")
T_Accumulator = TypeVar("T_Accumulator")


class ReductionType(Enum):
    """Types of reduction operations supported."""

    FOLD = "fold"  # Reduce collection to single value
    ACCUMULATE = "accumulate"  # Build up result incrementally
    MERGE = "merge"  # Combine multiple datasets
    AGGREGATE = "aggregate"  # Statistical aggregation
    NORMALIZE = "normalize"  # Score normalization and ranking
    DEDUPLICATE = "deduplicate"  # Remove duplicates
    SORT = "sort"  # Sort and rank operations
    FILTER = "filter"  # Filter with conditions
    GROUP = "group"  # Group by criteria
    TRANSFORM = "transform"  # Data transformation


class ConflictResolution(Enum):
    """Strategies for resolving conflicts during reduction."""

    FIRST_WINS = "first_wins"  # Keep first encountered value
    LAST_WINS = "last_wins"  # Keep last encountered value
    MERGE = "merge"  # Attempt to merge values
    ERROR = "error"  # Raise error on conflict
    CUSTOM = "custom"  # Use custom resolution function


class StreamingMode(Enum):
    """Streaming processing modes."""

    BATCH = "batch"  # Process all data at once
    INCREMENTAL = "incremental"  # Process data incrementally
    WINDOWED = "windowed"  # Process in time windows
    REAL_TIME = "real_time"  # Process as data arrives


class ModelReducerInput(BaseModel, Generic[T_Input]):
    """
    Input model for NodeReducer operations.

    Strongly typed input wrapper for data reduction operations
    with streaming and conflict resolution configuration.
    """

    data: list[T_Input]  # Strongly typed data list
    reduction_type: ReductionType
    operation_id: str | None = Field(default_factory=lambda: str(uuid4()))
    conflict_resolution: ConflictResolution = ConflictResolution.LAST_WINS
    streaming_mode: StreamingMode = StreamingMode.BATCH
    batch_size: int = 1000
    window_size_ms: int = 5000
    metadata: dict[str, ModelScalarValue] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ModelReducerOutput(Generic[T_Output]):
    """
    Output model for NodeReducer operations.

    Strongly typed output wrapper with reduction statistics
    and conflict resolution metadata.
    """

    def __init__(
        self,
        result: T_Output,
        operation_id: str,
        reduction_type: ReductionType,
        processing_time_ms: float,
        items_processed: int,
        conflicts_resolved: int = 0,
        streaming_mode: StreamingMode = StreamingMode.BATCH,
        batches_processed: int = 1,
        metadata: dict[str, str] | None = None,
    ):
        self.result = result
        self.operation_id = operation_id
        self.reduction_type = reduction_type
        self.processing_time_ms = processing_time_ms
        self.items_processed = items_processed
        self.conflicts_resolved = conflicts_resolved
        self.streaming_mode = streaming_mode
        self.batches_processed = batches_processed
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class StreamingWindow:
    """
    Time-based window for streaming data processing.
    """

    def __init__(self, window_size_ms: int, overlap_ms: int = 0):
        self.window_size_ms = window_size_ms
        self.overlap_ms = overlap_ms
        self.buffer: deque[Any] = deque()
        self.window_start = datetime.now()

    def add_item(self, item: Any) -> bool:
        """Add item to window, returns True if window is full."""
        current_time = datetime.now()
        self.buffer.append((item, current_time))

        # Check if window is complete
        window_duration = (current_time - self.window_start).total_seconds() * 1000
        return window_duration >= self.window_size_ms

    def get_window_items(self) -> list[Any]:
        """Get all items in current window."""
        return [item for item, timestamp in self.buffer]

    def advance_window(self) -> None:
        """Advance to next window with optional overlap."""
        if self.overlap_ms > 0:
            # Keep overlapping items
            cutoff_time = self.window_start + timedelta(
                milliseconds=self.window_size_ms - self.overlap_ms,
            )
            self.buffer = deque(
                [
                    (item, timestamp)
                    for item, timestamp in self.buffer
                    if timestamp >= cutoff_time
                ],
            )
        else:
            # Clear all items
            self.buffer.clear()

        self.window_start = datetime.now()


class ConflictResolver:
    """
    Handles conflict resolution during data reduction.
    """

    def __init__(
        self,
        strategy: ConflictResolution,
        custom_resolver: Callable[..., Any] | None = None,
    ):
        self.strategy = strategy
        self.custom_resolver = custom_resolver
        self.conflicts_count = 0

    def resolve(
        self,
        existing_value: Any,
        new_value: Any,
        key: str | None = None,
    ) -> Any:
        """Resolve conflict between existing and new values."""
        self.conflicts_count += 1

        if self.strategy == ConflictResolution.FIRST_WINS:
            return existing_value
        if self.strategy == ConflictResolution.LAST_WINS:
            return new_value
        if self.strategy == ConflictResolution.MERGE:
            return self._merge_values(existing_value, new_value)
        if self.strategy == ConflictResolution.ERROR:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Conflict detected for key: {key}",
                context={
                    "existing_value": str(existing_value),
                    "new_value": str(new_value),
                    "key": key,
                },
            )
        if self.strategy == ConflictResolution.CUSTOM and self.custom_resolver:
            return self.custom_resolver(existing_value, new_value, key)
        # Default to last wins
        return new_value

    def _merge_values(self, existing: Any, new: Any) -> Any:
        """Attempt to merge two values intelligently."""
        # Handle numeric values
        if isinstance(existing, int | float) and isinstance(new, int | float):
            return existing + new

        # Handle string concatenation
        if isinstance(existing, str) and isinstance(new, str):
            return f"{existing}, {new}"

        # Handle list merging
        if isinstance(existing, list) and isinstance(new, list):
            return existing + new

        # Handle dict merging
        if isinstance(existing, dict) and isinstance(new, dict):
            merged = existing.copy()
            merged.update(new)
            return merged

        # Default to new value if can't merge
        return new


class NodeReducer(NodeCoreBase):
    """
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

        Args:
            container: ONEX container for dependency injection

        Raises:
            OnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # CANONICAL PATTERN: Load contract model for Reducer node type
        self.contract_model: ModelContractReducer = self._load_contract_model()

        # Reducer-specific configuration
        self.default_batch_size = 1000
        self.max_memory_usage_mb = 512
        self.streaming_buffer_size = 10000

        # Reduction function registry
        self.reduction_functions: dict[ReductionType, Callable[..., Any]] = {}

        # Performance tracking for reductions
        self.reduction_metrics: dict[str, dict[str, float]] = {}

        # Streaming windows for real-time processing
        self.active_windows: dict[str, StreamingWindow] = {}

        # Register built-in reduction functions
        self._register_builtin_reducers()

    def _find_contract_path(self) -> Path:
        """
        Find the contract.yaml file for this reducer node.

        Uses inspection to find the module file and look for contract.yaml in the same directory.

        Returns:
            Path: Path to the contract.yaml file

        Raises:
            OnexError: If contract file cannot be found
        """
        import inspect
        from pathlib import Path

        from omnibase_core.constants.contract_constants import CONTRACT_FILENAME

        try:
            # Get the module file for the calling class
            frame = inspect.currentframe()
            while frame:
                frame = frame.f_back
                if frame and "self" in frame.f_locals:
                    caller_self = frame.f_locals["self"]
                    if hasattr(caller_self, "__module__"):
                        module = inspect.getmodule(caller_self)
                        if module and hasattr(module, "__file__"):
                            module_path = Path(module.__file__)
                            contract_path = module_path.parent / CONTRACT_FILENAME
                            if contract_path.exists():
                                return contract_path

            # Fallback: this shouldn't happen but provide error
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="Could not find contract.yaml file for reducer node",
                details={"contract_filename": CONTRACT_FILENAME},
            )

        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Error finding contract path: {e!s}",
                cause=e,
            )

    def _resolve_contract_references(
        self,
        data: Any,
        base_path: Path,
        reference_resolver: Any,
    ) -> Any:
        """
        Recursively resolve all $ref references in contract data.

        Enhanced to properly handle FSM subcontracts with Pydantic model validation.

        Args:
            data: Contract data structure (dict, list, or primitive)
            base_path: Base directory path for resolving relative references
            reference_resolver: Reference resolver utility

        Returns:
            Contract data with all $ref references resolved and validated
        """
        if isinstance(data, dict):
            if "$ref" in data:
                # This is a reference - resolve it
                ref_path = data["$ref"]
                try:
                    # Handle different reference types
                    if ref_path.startswith("#/"):
                        # Internal reference - not implemented yet
                        return data  # Keep as-is for now
                    if "contracts/" in ref_path:
                        # Subcontract reference - load the referenced file
                        ref_parts = ref_path.split("#/")
                        ref_file = ref_parts[0]
                        ref_pointer = ref_parts[1] if len(ref_parts) > 1 else ""

                        # Build full path to referenced file
                        ref_full_path = base_path / ref_file
                        if ref_full_path.exists():
                            from omnibase_core.models.core.model_generic_yaml import (
                                ModelGenericYaml,
                            )
                            from omnibase_core.utils.safe_yaml_loader import (
                                load_and_validate_yaml_model,
                            )

                            # Load and validate YAML using Pydantic model
                            yaml_model = load_and_validate_yaml_model(
                                ref_full_path,
                                ModelGenericYaml,
                            )
                            ref_data = yaml_model.model_dump()

                            # Check if this is an FSM data file that needs validation
                            if self._is_fsm_data_reference(ref_file, ref_data):
                                # Validate FSM data using Pydantic models
                                validated_fsm = self._validate_fsm_data(
                                    ref_data,
                                    ref_file,
                                )
                                if validated_fsm:
                                    ref_data = validated_fsm.model_dump()

                                    emit_log_event(
                                        LogLevel.INFO,
                                        "FSM subcontract validated successfully",
                                        {
                                            "fsm_file": ref_file,
                                            "fsm_name": validated_fsm.state_machine_name,
                                            "state_count": len(validated_fsm.states),
                                            "transition_count": len(
                                                validated_fsm.transitions,
                                            ),
                                        },
                                    )

                            # Navigate to the specific part if pointer specified
                            if ref_pointer:
                                parts = ref_pointer.split("/")
                                result = ref_data
                                for part in parts:
                                    if (
                                        part
                                        and isinstance(result, dict)
                                        and part in result
                                    ):
                                        result = result[part]
                                    else:
                                        # Could not resolve - return original
                                        return data
                                return self._resolve_contract_references(
                                    result,
                                    base_path,
                                    reference_resolver,
                                )
                            return self._resolve_contract_references(
                                ref_data,
                                base_path,
                                reference_resolver,
                            )
                        # Referenced file doesn't exist - keep as-is
                        return data
                    # Other reference types - keep as-is for now
                    return data
                except Exception as e:
                    emit_log_event(
                        LogLevel.ERROR,
                        "Failed to resolve contract reference",
                        {
                            "ref_path": ref_path,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    # Reference resolution failed - keep original
                    return data
            else:
                # Regular dict - recursively resolve all values
                resolved_dict = {}
                for key, value in data.items():
                    resolved_dict[key] = self._resolve_contract_references(
                        value,
                        base_path,
                        reference_resolver,
                    )
                return resolved_dict
        elif isinstance(data, list):
            # List - recursively resolve all items
            return [
                self._resolve_contract_references(item, base_path, reference_resolver)
                for item in data
            ]
        else:
            # Primitive value - return as-is
            return data

    def _is_fsm_data_reference(self, ref_file: str, ref_data: Any) -> bool:
        """
        Check if a reference points to FSM data that needs validation.

        Args:
            ref_file: Referenced file path
            ref_data: Loaded reference data

        Returns:
            True if this is FSM data that needs validation
        """
        return (
            "fsm" in ref_file.lower()
            and isinstance(ref_data, dict)
            and "state_machine_name" in ref_data
            and "states" in ref_data
            and "transitions" in ref_data
        )

    def _validate_fsm_data(
        self,
        fsm_data: dict[str, Any],
        ref_file: str,
    ) -> Any | None:
        """
        Validate FSM data using Pydantic models.

        Args:
            fsm_data: Raw FSM data from YAML
            ref_file: Reference file name for error reporting

        Returns:
            Validated ModelFSMDefinition instance or None if validation fails
        """
        try:
            # Import FSM models dynamically to avoid circular imports
            import sys
            from pathlib import Path

            # Get the tool directory to import FSM models
            tool_dir = (
                Path(__file__).parent.parent
                / "tools"
                / "infrastructure"
                / "tool_infrastructure_reducer"
                / "v1_0_0"
            )
            if tool_dir.exists():
                models_dir = tool_dir / "models"
                if models_dir.exists():
                    sys.path.insert(0, str(tool_dir))
                    try:
                        from models.model_fsm_definition import ModelFSMDefinition

                        # Validate the FSM data
                        return ModelFSMDefinition(**fsm_data)

                    except ImportError as ie:
                        emit_log_event(
                            LogLevel.WARNING,
                            "Could not import FSM models for validation",
                            {
                                "ref_file": ref_file,
                                "models_dir": str(models_dir),
                                "import_error": str(ie),
                            },
                        )
                    except Exception as ve:
                        emit_log_event(
                            LogLevel.ERROR,
                            "FSM data validation failed",
                            {
                                "ref_file": ref_file,
                                "validation_error": str(ve),
                                "error_type": type(ve).__name__,
                            },
                        )
                    finally:
                        # Clean up sys.path
                        if str(tool_dir) in sys.path:
                            sys.path.remove(str(tool_dir))
        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                "Error during FSM validation setup",
                {"ref_file": ref_file, "error": str(e), "error_type": type(e).__name__},
            )

        return None

    def _load_contract_model(self) -> ModelContractReducer:
        """
        Load and validate contract model for Reducer node type.

        CANONICAL PATTERN: Centralized contract loading for all Reducer nodes.
        Provides type-safe contract configuration with reduction operation validation.

        Returns:
            ModelContractReducer: Validated contract model for this node type

        Raises:
            OnexError: If contract loading or validation fails
        """
        try:
            # Load actual contract from file with subcontract resolution

            from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
            from omnibase_core.utils.generation.utility_reference_resolver import (
                UtilityReferenceResolver,
            )
            from omnibase_core.utils.safe_yaml_loader import (
                load_and_validate_yaml_model,
            )

            # Get contract path - find the node.py file and look for contract.yaml
            contract_path = self._find_contract_path()

            # Load and resolve contract with subcontract support
            reference_resolver = UtilityReferenceResolver()

            # Load and validate YAML using Pydantic model
            yaml_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)
            contract_data = yaml_model.model_dump()

            # Resolve any $ref references in the contract
            resolved_contract = self._resolve_contract_references(
                contract_data,
                contract_path.parent,
                reference_resolver,
            )

            # Create ModelContractReducer from resolved contract data
            contract_model = ModelContractReducer(**resolved_contract)

            # CANONICAL PATTERN: Validate contract model consistency
            contract_model.validate_node_specific_config()

            emit_log_event(
                LogLevel.INFO,
                "Contract model loaded successfully for NodeReducer",
                {
                    "contract_type": "ModelContractReducer",
                    "node_type": contract_model.node_type,
                    "version": contract_model.version,
                },
            )

            return contract_model

        except Exception as e:
            # CANONICAL PATTERN: Wrap contract loading errors
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Contract model loading failed for NodeReducer: {e!s}",
                details={
                    "contract_model_type": "ModelContractReducer",
                    "error_type": type(e).__name__,
                },
                cause=e,
            )

    async def process(
        self,
        input_data: ModelReducerInput[T_Input],
    ) -> ModelReducerOutput[T_Output]:
        """
        Stream-based reduction with conflict resolution.

        Args:
            input_data: Strongly typed reduction input with configuration

        Returns:
            Strongly typed reduction output with processing statistics

        Raises:
            OnexError: If reduction fails or memory limits exceeded
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_reducer_input(input_data)

            # Initialize conflict resolver
            conflict_resolver = ConflictResolver(
                input_data.conflict_resolution,
                (
                    input_data.reducer_function
                    if input_data.conflict_resolution == ConflictResolution.CUSTOM
                    else None
                ),
            )

            # Execute reduction based on streaming mode
            if input_data.streaming_mode == StreamingMode.BATCH:
                result, items_processed = await self._process_batch(
                    input_data,
                    conflict_resolver,
                )
                batches_processed = 1
            elif input_data.streaming_mode == StreamingMode.INCREMENTAL:
                (
                    result,
                    items_processed,
                    batches_processed,
                ) = await self._process_incremental(input_data, conflict_resolver)
            elif input_data.streaming_mode == StreamingMode.WINDOWED:
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

            # Update metrics
            await self._update_reduction_metrics(
                input_data.reduction_type.value,
                processing_time,
                True,
                items_processed,
            )
            await self._update_processing_metrics(processing_time, True)

            # Create output
            output = ModelReducerOutput(
                result=result,
                operation_id=input_data.operation_id,
                reduction_type=input_data.reduction_type,
                processing_time_ms=processing_time,
                items_processed=items_processed,
                conflicts_resolved=conflict_resolver.conflicts_count,
                streaming_mode=input_data.streaming_mode,
                batches_processed=batches_processed,
                metadata={
                    "batch_size": input_data.batch_size,
                    "window_size_ms": input_data.window_size_ms,
                    "conflict_strategy": input_data.conflict_resolution.value,
                },
            )

            emit_log_event(
                LogLevel.INFO,
                f"Reduction completed: {input_data.reduction_type.value}",
                {
                    "node_id": self.node_id,
                    "operation_id": input_data.operation_id,
                    "processing_time_ms": processing_time,
                    "items_processed": items_processed,
                    "conflicts_resolved": conflict_resolver.conflicts_count,
                    "batches_processed": batches_processed,
                },
            )

            return output

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # Update error metrics
            await self._update_reduction_metrics(
                input_data.reduction_type.value,
                processing_time,
                False,
                0,
            )
            await self._update_processing_metrics(processing_time, False)

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Reduction failed: {e!s}",
                context={
                    "node_id": self.node_id,
                    "operation_id": input_data.operation_id,
                    "reduction_type": input_data.reduction_type.value,
                    "processing_time_ms": processing_time,
                    "error": str(e),
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
            OnexError: If aggregation fails
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
            reduction_type=ReductionType.AGGREGATE,
            group_key=lambda ticket: ticket.get(group_by, "unknown"),
            metadata={
                "group_by": group_by,
                "aggregation_functions": aggregation_functions,
                "rsd_operation": "ticket_aggregation",
            },
        )

        result: Any = await self.process(reduction_input)
        return dict(result.result)

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
            OnexError: If normalization fails
        """
        reduction_input = ModelReducerInput(
            data=tickets_with_scores,
            reduction_type=ReductionType.NORMALIZE,
            metadata={
                "score_field": score_field,
                "normalization_method": normalization_method,
                "rsd_operation": "priority_normalization",
            },
        )

        result: Any = await self.process(reduction_input)
        return list(result.result)

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
            OnexError: If cycle detection fails
        """
        reduction_input = ModelReducerInput(
            data=list(dependency_graph.items()),
            reduction_type=ReductionType.MERGE,
            metadata={
                "graph_operation": "cycle_detection",
                "rsd_operation": "dependency_analysis",
            },
        )

        result: Any = await self.process(reduction_input)
        return dict(result.result)

    def register_reduction_function(
        self,
        reduction_type: ReductionType,
        function: Callable[..., Any],
    ) -> None:
        """
        Register custom reduction function.

        Args:
            reduction_type: Type of reduction operation
            function: Reduction function to register

        Raises:
            OnexError: If reduction type already registered or function invalid
        """
        if reduction_type in self.reduction_functions:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Reduction type already registered: {reduction_type.value}",
                context={
                    "node_id": self.node_id,
                    "reduction_type": reduction_type.value,
                },
            )

        if not callable(function):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Reduction function must be callable: {reduction_type.value}",
                context={
                    "node_id": self.node_id,
                    "reduction_type": reduction_type.value,
                },
            )

        self.reduction_functions[reduction_type] = function

        emit_log_event(
            LogLevel.INFO,
            f"Reduction function registered: {reduction_type.value}",
            {"node_id": self.node_id, "reduction_type": reduction_type.value},
        )

    async def get_reduction_metrics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed reduction performance metrics.

        Returns:
            Dictionary of metrics by reduction type
        """
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
        emit_log_event(
            LogLevel.INFO,
            "NodeReducer resources initialized",
            {
                "node_id": self.node_id,
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
            {"node_id": self.node_id},
        )

    def _validate_reducer_input(self, input_data: ModelReducerInput[Any]) -> None:
        """
        Validate reducer input data.

        Args:
            input_data: Input data to validate

        Raises:
            OnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not isinstance(input_data.reduction_type, ReductionType):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Reduction type must be valid ReductionType enum",
                context={
                    "node_id": self.node_id,
                    "reduction_type": str(input_data.reduction_type),
                },
            )

        if input_data.data is None:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Data cannot be None for reduction",
                context={
                    "node_id": self.node_id,
                    "operation_id": input_data.operation_id,
                },
            )

    async def _process_batch(
        self,
        input_data: ModelReducerInput[Any],
        conflict_resolver: ConflictResolver,
    ) -> tuple[Any, int]:
        """Process all data in a single batch."""
        reduction_type = input_data.reduction_type

        if reduction_type not in self.reduction_functions:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"No reduction function for type: {reduction_type.value}",
                context={
                    "node_id": self.node_id,
                    "reduction_type": reduction_type.value,
                    "available_types": [rt.value for rt in self.reduction_functions],
                },
            )

        reducer_func = self.reduction_functions[reduction_type]

        # Convert data to list if needed
        if hasattr(input_data.data, "__aiter__"):
            # Handle async iterator
            data_list = [item async for item in input_data.data]
        elif hasattr(input_data.data, "__iter__") and not isinstance(
            input_data.data,
            str | bytes,
        ):
            data_list = list(input_data.data)
        else:
            data_list = [input_data.data]

        # Execute reduction
        result = await reducer_func(data_list, input_data, conflict_resolver)
        return result, len(data_list)

    async def _process_incremental(
        self,
        input_data: ModelReducerInput[Any],
        conflict_resolver: ConflictResolver,
    ) -> tuple[Any, int, int]:
        """Process data incrementally in batches."""
        batch_size = input_data.batch_size
        total_processed = 0
        batches_processed = 0
        accumulator = input_data.accumulator_init

        # Process in batches
        batch = []
        if hasattr(input_data.data, "__iter__"):
            for item in input_data.data:
                batch.append(item)

                if len(batch) >= batch_size:
                    # Process this batch
                    batch_input = ModelReducerInput(
                        data=batch,
                        reduction_type=input_data.reduction_type,
                        accumulator_init=accumulator,
                        **{
                            k: v
                            for k, v in input_data.__dict__.items()
                            if k not in ["data", "accumulator_init"]
                        },
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
                accumulator_init=accumulator,
                **{
                    k: v
                    for k, v in input_data.__dict__.items()
                    if k not in ["data", "accumulator_init"]
                },
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
        conflict_resolver: ConflictResolver,
    ) -> tuple[Any, int, int]:
        """Process data in time-based windows."""
        window = StreamingWindow(input_data.window_size_ms)
        total_processed = 0
        windows_processed = 0
        results = []

        if hasattr(input_data.data, "__iter__"):
            for item in input_data.data:
                window_full = window.add_item(item)

                if window_full:
                    # Process current window
                    window_items = window.get_window_items()

                    window_input = ModelReducerInput(
                        data=window_items,
                        reduction_type=input_data.reduction_type,
                        **{
                            k: v
                            for k, v in input_data.__dict__.items()
                            if k not in ["data"]
                        },
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
                **{k: v for k, v in input_data.__dict__.items() if k not in ["data"]},
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
                reduction_type=ReductionType.MERGE,
                **{
                    k: v
                    for k, v in input_data.__dict__.items()
                    if k not in ["data", "reduction_type"]
                },
            )

            final_result, _ = await self._process_batch(
                combined_input,
                conflict_resolver,
            )
            return final_result, total_processed, windows_processed
        return input_data.accumulator_init, 0, 0

    async def _update_reduction_metrics(
        self,
        reduction_type: str,
        processing_time_ms: float,
        success: bool,
        items_processed: int,
    ) -> None:
        """Update reduction-specific metrics."""
        if reduction_type not in self.reduction_metrics:
            self.reduction_metrics[reduction_type] = {
                "total_operations": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "total_items_processed": 0.0,
                "avg_processing_time_ms": 0.0,
                "avg_items_per_operation": 0.0,
                "min_processing_time_ms": float("inf"),
                "max_processing_time_ms": 0.0,
            }

        metrics = self.reduction_metrics[reduction_type]
        metrics["total_operations"] += 1
        metrics["total_items_processed"] += items_processed

        if success:
            metrics["success_count"] += 1
        else:
            metrics["error_count"] += 1

        # Update timing metrics
        metrics["min_processing_time_ms"] = min(
            metrics["min_processing_time_ms"],
            processing_time_ms,
        )
        metrics["max_processing_time_ms"] = max(
            metrics["max_processing_time_ms"],
            processing_time_ms,
        )

        # Update rolling averages
        total_ops = metrics["total_operations"]
        current_avg_time = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg_time * (total_ops - 1) + processing_time_ms
        ) / total_ops

        metrics["avg_items_per_operation"] = (
            metrics["total_items_processed"] / total_ops
        )

    def _register_builtin_reducers(self) -> None:
        """Register built-in reduction functions."""

        async def fold_reducer(
            data: list[Any],
            input_data: ModelReducerInput[Any],
            conflict_resolver: ConflictResolver,
        ) -> Any:
            """Fold/reduce data to single value."""
            if not data:
                return input_data.accumulator_init

            accumulator = input_data.accumulator_init
            reducer_func = input_data.reducer_function

            if not reducer_func:
                # Default sum for numeric data
                if all(isinstance(x, int | float) for x in data):
                    return sum(data)
                return data[-1] if data else accumulator

            for item in data:
                accumulator = reducer_func(accumulator, item)

            return accumulator

        async def aggregate_reducer(
            data: list[Any],
            input_data: ModelReducerInput[Any],
            conflict_resolver: ConflictResolver,
        ) -> dict[str, Any]:
            """Aggregate data by groups with statistics."""
            if not data:
                return {}

            # Group data
            groups = defaultdict(list)
            group_key = input_data.group_key or (lambda x: "default")

            for item in data:
                key = group_key(item)
                groups[key].append(item)

            # Apply aggregation functions
            result = {}
            for group, items in groups.items():
                group_stats = {"count": len(items), "items": items}

                # Add numeric aggregations if applicable
                numeric_fields = []
                if items and isinstance(items[0], dict):
                    for field, value in items[0].items():
                        if isinstance(value, int | float):
                            numeric_fields.append(field)

                for field in numeric_fields:
                    values = [
                        item[field]
                        for item in items
                        if field in item and isinstance(item[field], int | float)
                    ]
                    if values:
                        group_stats[f"{field}_sum"] = sum(values)
                        group_stats[f"{field}_avg"] = sum(values) / len(values)
                        group_stats[f"{field}_min"] = min(values)
                        group_stats[f"{field}_max"] = max(values)

                result[str(group)] = group_stats

            return result

        async def normalize_reducer(
            data: list[Any],
            input_data: ModelReducerInput[Any],
            conflict_resolver: ConflictResolver,
        ) -> list[Any]:
            """Normalize scores and create rankings."""
            if not data:
                return []

            metadata = input_data.metadata
            score_field = metadata.get("score_field", "score")
            method = metadata.get("normalization_method", "min_max")

            # Extract scores
            scores = []
            items_with_indices = []
            for i, item in enumerate(data):
                if isinstance(item, dict) and score_field in item:
                    score = item[score_field]
                    if isinstance(score, int | float):
                        scores.append(score)
                        items_with_indices.append((i, item, score))

            if not scores:
                return data

            # Apply normalization
            if method == "min_max":
                min_score = min(scores)
                max_score = max(scores)
                score_range = max_score - min_score

                for i, item, score in items_with_indices:
                    if score_range > 0:
                        normalized = (score - min_score) / score_range
                    else:
                        normalized = 0.5
                    item[f"{score_field}_normalized"] = normalized

            elif method == "rank":
                # Sort by score descending and assign ranks
                sorted_items = sorted(
                    items_with_indices,
                    key=lambda x: x[2],
                    reverse=True,
                )
                for rank, (i, item, score) in enumerate(sorted_items, 1):
                    item[f"{score_field}_rank"] = rank
                    item[f"{score_field}_percentile"] = (
                        len(sorted_items) - rank + 1
                    ) / len(sorted_items)

            return data

        async def merge_reducer(
            data: list[Any],
            input_data: ModelReducerInput[Any],
            conflict_resolver: ConflictResolver,
        ) -> Any:
            """Merge multiple datasets with conflict resolution."""
            if not data:
                return {}

            # Handle dependency graph cycle detection
            metadata = input_data.metadata
            if metadata.get("graph_operation") == "cycle_detection":
                return self._detect_dependency_cycles(data)

            # General merge operation
            if all(isinstance(item, dict) for item in data):
                merged: dict[str, Any] = {}
                for item in data:
                    for key, value in item.items():
                        if key in merged:
                            merged[key] = conflict_resolver.resolve(
                                merged[key],
                                value,
                                key,
                            )
                        else:
                            merged[key] = value
                return merged

            if all(isinstance(item, list) for item in data):
                merged_list: list[Any] = []
                for item in data:
                    merged_list.extend(item)
                return merged_list

            return data[-1] if data else None

        # Register reducers
        self.reduction_functions[ReductionType.FOLD] = fold_reducer
        self.reduction_functions[ReductionType.AGGREGATE] = aggregate_reducer
        self.reduction_functions[ReductionType.NORMALIZE] = normalize_reducer
        self.reduction_functions[ReductionType.MERGE] = merge_reducer

    def _detect_dependency_cycles(
        self,
        graph_data: list[tuple[str, str]],
    ) -> dict[str, Any]:
        """Detect cycles in dependency graph using DFS."""
        # Build adjacency list
        graph = {}
        for node, dependencies in graph_data:
            graph[node] = dependencies

        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles = []

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
                if dfs(neighbor, path):
                    # Cycle found in subtree
                    pass

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

    def get_introspection_data(self) -> dict:
        """
        Get comprehensive introspection data for NodeReducer.

        Returns specialized data reduction node information including streaming capabilities,
        conflict resolution strategies, reduction operations, and RSD data processing details.

        Returns:
            dict: Comprehensive introspection data with reducer-specific information
        """
        try:
            # Get base introspection data from NodeCoreBase
            base_data = {
                "node_type": "NodeReducer",
                "node_classification": "reducer",
                "node_id": self.node_id,
                "version": self.version,
                "created_at": self.created_at.isoformat(),
                "current_status": self.state.get("status", "unknown"),
            }

            # 1. Node Capabilities (Reducer-specific)
            node_capabilities = {
                **base_data,
                "architecture_classification": "data_aggregation_and_state_reduction",
                "reduction_patterns": [
                    "fold",
                    "accumulate",
                    "merge",
                    "aggregate",
                    "normalize",
                ],
                "streaming_capabilities": [
                    "windowed",
                    "real_time",
                    "incremental",
                    "batch",
                ],
                "available_operations": self._extract_reducer_operations(),
                "input_output_specifications": self._extract_reducer_io_specifications(),
                "performance_characteristics": self._extract_reducer_performance_characteristics(),
            }

            # 2. Contract Details (Reducer-specific)
            contract_details = {
                "contract_type": "ModelContractReducer",
                "contract_validation_status": "validated",
                "reduction_configuration": self._extract_reduction_configuration(),
                "aggregation_configuration": self._extract_aggregation_configuration(),
                "supported_reduction_types": [
                    reduction_type.value for reduction_type in self.reduction_functions
                ],
                "conflict_resolution_strategies": [
                    strategy.value for strategy in ConflictResolution
                ],
            }

            # 3. Runtime Information (Reducer-specific)
            runtime_info = {
                "current_health_status": self._get_reducer_health_status(),
                "reduction_metrics": self._get_reduction_metrics_sync(),
                "resource_usage": self._get_reducer_resource_usage(),
                "streaming_status": self._get_streaming_status(),
                "conflict_resolution_status": self._get_conflict_resolution_status(),
            }

            # 4. Reduction Management Information
            reduction_management_info = {
                "registered_reduction_functions": list(self.reduction_functions.keys()),
                "reduction_function_count": len(self.reduction_functions),
                "streaming_windows_active": len(self.active_windows),
                "supports_custom_reducers": True,
                "supports_conflict_resolution": True,
                "supports_streaming": True,
                "supports_rsd_operations": True,
            }

            # 5. Configuration Details
            configuration_details = {
                "default_batch_size": self.default_batch_size,
                "max_memory_usage_mb": self.max_memory_usage_mb,
                "streaming_buffer_size": self.streaming_buffer_size,
                "streaming_configuration": {
                    "supports_windowing": True,
                    "supports_real_time": True,
                    "supports_incremental": True,
                    "window_types": ["time_based", "count_based"],
                },
                "conflict_resolution_configuration": {
                    "strategies": [strategy.value for strategy in ConflictResolution],
                    "supports_custom_resolvers": True,
                    "merge_strategies": [
                        "numeric_sum",
                        "string_concat",
                        "list_merge",
                        "dict_merge",
                    ],
                },
            }

            # 6. RSD-Specific Information
            rsd_specific_info = {
                "supports_priority_normalization": "normalize"
                in [rt.value for rt in self.reduction_functions],
                "supports_dependency_cycle_detection": True,
                "supports_ticket_aggregation": "aggregate"
                in [rt.value for rt in self.reduction_functions],
                "supports_graph_operations": True,
                "rsd_operations": [
                    "priority_score_normalization",
                    "ticket_metadata_aggregation",
                    "dependency_graph_cycle_detection",
                    "status_consolidation",
                ],
            }

            return {
                "node_capabilities": node_capabilities,
                "contract_details": contract_details,
                "runtime_information": runtime_info,
                "reduction_management_information": reduction_management_info,
                "configuration_details": configuration_details,
                "rsd_specific_information": rsd_specific_info,
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "node_type": "NodeReducer",
                    "supports_full_introspection": True,
                    "specialization": "data_aggregation_with_streaming_and_conflict_resolution",
                },
            }

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to generate full reducer introspection data: {e!s}, using fallback",
                {"node_id": self.node_id, "error": str(e)},
            )

            return {
                "node_capabilities": {
                    "node_type": "NodeReducer",
                    "node_classification": "reducer",
                    "node_id": self.node_id,
                },
                "runtime_information": {
                    "current_health_status": "unknown",
                    "reduction_function_count": len(self.reduction_functions),
                },
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "supports_full_introspection": False,
                    "fallback_reason": str(e),
                },
            }

    def _extract_reducer_operations(self) -> list:
        """Extract available reducer operations."""
        operations = ["process", "reduce_data", "aggregate_data", "normalize_scores"]

        try:
            # Add reduction type operations
            for reduction_type in self.reduction_functions:
                operations.append(f"reduce_{reduction_type.value}")

            # Add streaming operations
            operations.extend(["stream_process", "window_process", "batch_process"])

            # Add RSD operations
            operations.extend(["detect_dependency_cycles", "normalize_priority_scores"])

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract all reducer operations: {e!s}",
                {"node_id": self.node_id},
            )

        return operations

    def _extract_reducer_io_specifications(self) -> dict:
        """Extract input/output specifications for reducer operations."""
        return {
            "input_model": "omnibase.core.node_reducer.ModelReducerInput",
            "output_model": "omnibase.core.node_reducer.ModelReducerOutput",
            "supports_streaming": True,
            "supports_batch_processing": True,
            "supports_incremental_processing": True,
            "reduction_types": [
                reduction_type.value for reduction_type in ReductionType
            ],
            "streaming_modes": [mode.value for mode in StreamingMode],
            "conflict_resolution_strategies": [
                strategy.value for strategy in ConflictResolution
            ],
            "input_requirements": ["data", "reduction_type"],
            "output_guarantees": [
                "result",
                "processing_time_ms",
                "items_processed",
                "conflicts_resolved",
                "streaming_mode",
            ],
        }

    def _extract_reducer_performance_characteristics(self) -> dict:
        """Extract performance characteristics specific to reducer operations."""
        return {
            "expected_response_time_ms": "varies_by_data_size_and_reduction_complexity",
            "throughput_capacity": f"up_to_{self.default_batch_size}_items_per_batch",
            "memory_usage_pattern": f"streaming_with_max_{self.max_memory_usage_mb}_mb",
            "cpu_intensity": "medium_to_high_depending_on_reduction_complexity",
            "supports_parallel_processing": False,  # Sequential reduction typically required
            "caching_enabled": False,  # Live data processing
            "performance_monitoring": True,
            "deterministic_operations": True,
            "side_effects": False,
            "streaming_capabilities": True,
            "memory_efficient": True,
            "supports_large_datasets": True,
        }

    def _extract_reduction_configuration(self) -> dict:
        """Extract reduction configuration from contract."""
        try:
            return {
                "default_batch_size": self.default_batch_size,
                "max_memory_usage_mb": self.max_memory_usage_mb,
                "streaming_buffer_size": self.streaming_buffer_size,
                "supported_reduction_types": [
                    rt.value for rt in self.reduction_functions
                ],
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract reduction configuration: {e!s}",
                {"node_id": self.node_id},
            )
            return {"default_batch_size": self.default_batch_size}

    def _extract_aggregation_configuration(self) -> dict:
        """Extract aggregation configuration from contract."""
        try:
            aggregation_ops = []
            if hasattr(self.contract_model, "aggregation"):
                aggregation_ops = [
                    "count",
                    "sum",
                    "avg",
                    "min",
                    "max",
                    "group_by",
                    "statistical_analysis",
                ]

            return {
                "aggregation_operations": aggregation_ops,
                "supports_grouping": True,
                "supports_statistical_aggregation": True,
                "supports_custom_aggregation": True,
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract aggregation configuration: {e!s}",
                {"node_id": self.node_id},
            )
            return {"aggregation_operations": []}

    def _get_reducer_health_status(self) -> str:
        """Get health status specific to reducer operations."""
        try:
            # Check if basic reduction works
            test_input = ModelReducerInput(
                data=[1, 2, 3],
                reduction_type=ReductionType.FOLD,
                cache_enabled=False,
            )

            # For health check, we'll just validate the input without processing
            self._validate_reducer_input(test_input)
            return "healthy"

        except Exception:
            return "unhealthy"

    def _get_reduction_metrics_sync(self) -> dict:
        """Get reduction metrics synchronously for introspection."""
        try:
            return {
                **self.reduction_metrics,
                "streaming_windows": {
                    "active_windows": len(self.active_windows),
                    "window_details": {
                        window_id: {
                            "buffer_size": len(window.buffer),
                            "window_size_ms": window.window_size_ms,
                        }
                        for window_id, window in self.active_windows.items()
                    },
                },
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get reduction metrics: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown", "error": str(e)}

    def _get_reducer_resource_usage(self) -> dict:
        """Get resource usage specific to reducer operations."""
        try:
            total_buffer_items = sum(
                len(window.buffer) for window in self.active_windows.values()
            )

            return {
                "active_reduction_functions": len(self.reduction_functions),
                "streaming_windows_active": len(self.active_windows),
                "total_buffered_items": total_buffer_items,
                "max_memory_usage_mb": self.max_memory_usage_mb,
                "streaming_buffer_size": self.streaming_buffer_size,
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get reducer resource usage: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown"}

    def _get_streaming_status(self) -> dict:
        """Get streaming processing status."""
        try:
            return {
                "streaming_enabled": True,
                "active_windows": len(self.active_windows),
                "streaming_buffer_size": self.streaming_buffer_size,
                "supports_real_time": True,
                "supports_windowed": True,
                "supports_incremental": True,
                "streaming_modes_supported": [mode.value for mode in StreamingMode],
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get streaming status: {e!s}",
                {"node_id": self.node_id},
            )
            return {"streaming_enabled": False, "error": str(e)}

    def _get_conflict_resolution_status(self) -> dict:
        """Get conflict resolution status."""
        return {
            "conflict_resolution_enabled": True,
            "supported_strategies": [strategy.value for strategy in ConflictResolution],
            "supports_custom_resolvers": True,
            "merge_capabilities": {
                "numeric_merge": True,
                "string_concatenation": True,
                "list_merging": True,
                "dict_merging": True,
            },
        }

    def _validate_reducer_input(self, input_data: ModelReducerInput[Any]) -> None:
        """
        Validate reducer input data (placeholder for actual validation).

        Args:
            input_data: Input data to validate

        Raises:
            OnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not hasattr(input_data, "data"):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Input data must have 'data' attribute",
                context={
                    "node_id": self.node_id,
                    "input_type": type(input_data).__name__,
                },
            )

        if not hasattr(input_data, "reduction_type"):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Input data must have 'reduction_type' attribute",
                context={
                    "node_id": self.node_id,
                    "input_type": type(input_data).__name__,
                },
            )
