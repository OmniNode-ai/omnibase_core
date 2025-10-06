import uuid
from typing import Callable, Dict, Generic, List, TypeVar

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
NodeReducer - Data Aggregation Node for 4-Node ModelArchitecture.

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
from collections import defaultdict
from collections.abc import Callable as CallableABC
from collections.abc import Iterable as IterableABC
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, TypeVar
from uuid import UUID

from omnibase_core.enums.enum_conflict_resolution import EnumConflictResolution
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_reduction_type import EnumReductionType
from omnibase_core.enums.enum_streaming_mode import EnumStreamingMode
from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Import contract model for reducer nodes
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

# Import extracted models
from omnibase_core.models.infrastructure.model_conflict_resolver import (
    ModelConflictResolver,
)
from omnibase_core.models.infrastructure.model_streaming_window import (
    ModelStreamingWindow,
)
from omnibase_core.models.operations.model_reducer_input import ModelReducerInput
from omnibase_core.models.operations.model_reducer_output import ModelReducerOutput

T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")
T_Accumulator = TypeVar("T_Accumulator")


# Note: Enums and models have been extracted to separate modules
# - EnumReductionType → omnibase_core.enums.enum_reduction_type
# - EnumConflictResolution → omnibase_core.enums.enum_conflict_resolution
# - EnumStreamingMode → omnibase_core.enums.enum_streaming_mode
# - ModelReducerInput → omnibase_core.models.operations.model_reducer_input
# - ModelReducerOutput → omnibase_core.models.operations.model_reducer_output
# - StreamingWindow → omnibase_core.models.infrastructure.model_streaming_window
# - ConflictResolver → omnibase_core.models.infrastructure.model_conflict_resolver


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
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # CANONICAL PATTERN: Load contract model for Reducer node type
        self.contract_model: ModelContractReducer = self._load_contract_model()

        # Reducer-specific configuration
        self.default_batch_size = 1000
        self.max_memory_usage_mb = 512
        self.streaming_buffer_size = 10000

        # Reduction function registry
        self.reduction_functions: dict[EnumReductionType, Callable[..., Any]] = {}

        # Performance tracking for reductions
        self.reduction_metrics: dict[str, dict[str, float]] = {}

        # Streaming windows for real-time processing
        self.active_windows: dict[str, ModelStreamingWindow] = {}

        # Register built-in reduction functions
        self._register_builtin_reducers()

    def _find_contract_path(self) -> Path:
        """
        Find the contract.yaml file for this reducer node.

        Uses inspection to find the module file and look for contract.yaml in the same directory.

        Returns:
            Path: Path to the contract.yaml file

        Raises:
            ModelOnexError: If contract file cannot be found
        """
        import inspect

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
                            module_path = Path(module.__file__ or "")
                            contract_path = module_path.parent / CONTRACT_FILENAME
                            if contract_path.exists():
                                return contract_path

            # Fallback: this shouldn't happen but provide error
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message="Could not find contract.yaml file for reducer node",
                details={"contract_filename": CONTRACT_FILENAME},
            )

        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
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
            data: Contract data structure (dict[str, Any], list[Any], or primitive)
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
                except (
                    Exception
                ) as e:  # fallback-ok: contract reference resolution is non-critical - return original data to allow contract loading to continue with unresolved references
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
                # Regular dict[str, Any]- recursively resolve all values
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
            ModelOnexError: If contract loading or validation fails
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
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
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
            ModelOnexError: If reduction fails or memory limits exceeded
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_reducer_input(input_data)

            # Initialize conflict resolver
            conflict_resolver = ModelConflictResolver(
                input_data.conflict_resolution,
                None,  # reducer_function is a string, not a callable
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
                    "batch_size": str(input_data.batch_size),
                    "window_size_ms": str(input_data.window_size_ms),
                    "conflict_strategy": input_data.conflict_resolution.value,
                },
            )

            emit_log_event(
                LogLevel.INFO,
                f"Reduction completed: {input_data.reduction_type.value}",
                {
                    "node_id": self.node_id,
                    "operation_id": str(input_data.operation_id),
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

            raise ModelOnexError(
                code=ModelCoreErrorCode.OPERATION_FAILED,
                message=f"Reduction failed: {e!s}",
                context={
                    "node_id": self.node_id,
                    "operation_id": str(input_data.operation_id),
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
            tickets: List of ticket dict[str, Any]ionaries
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
            group_key=group_by,  # Use field name string instead of lambda
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
        return list(result.result)

    async def resolve_dependency_cycles(
        self,
        dependency_graph: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Detect and resolve cycles in RSD dependency graphs.

        Args:
            dependency_graph: Graph as adjacency list[Any](ticket_id -> [dependent_tickets])

        Returns:
            Analysis results with cycle detection and resolution suggestions

        Raises:
            ModelOnexError: If cycle detection fails
        """
        reduction_input = ModelReducerInput(
            data=list[Any](dependency_graph.items()),
            reduction_type=EnumReductionType.MERGE,
            metadata={
                "graph_operation": "cycle_detection",
                "rsd_operation": "dependency_analysis",
            },
        )

        result: Any = await self.process(reduction_input)
        return dict(result.result)

    def register_reduction_function(
        self,
        reduction_type: EnumReductionType,
        function: Callable[..., Any],
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
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Reduction type already registered: {reduction_type.value}",
                context={
                    "node_id": self.node_id,
                    "reduction_type": reduction_type.value,
                },
            )

        if not callable(function):
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
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
            ModelOnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not isinstance(input_data.reduction_type, EnumReductionType):
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message="Reduction type must be valid EnumReductionType enum",
                context={
                    "node_id": self.node_id,
                    "reduction_type": str(input_data.reduction_type),
                },
            )

        if input_data.data is None:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message="Data cannot be None for reduction",
                context={
                    "node_id": self.node_id,
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
                code=ModelCoreErrorCode.OPERATION_FAILED,
                message=f"No reduction function for type: {reduction_type.value}",
                context={
                    "node_id": self.node_id,
                    "reduction_type": reduction_type.value,
                    "available_types": [rt.value for rt in self.reduction_functions],
                },
            )

        reducer_func = self.reduction_functions[reduction_type]

        # Convert data to list[Any]if needed
        if hasattr(input_data.data, "__aiter__"):
            # Handle async iterator
            data_list = [item async for item in input_data.data]
        elif hasattr(input_data.data, "__iter__"):
            # Use type() to avoid MyPy isinstance issues
            data_type = type(input_data.data)
            if data_type is str or data_type is bytes:  # type: ignore [comparison-overlap]
                data_list = [input_data.data]
            else:
                try:
                    data_list = list(input_data.data)
                except TypeError:
                    data_list = [input_data.data]
        else:
            data_list = [input_data.data]

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
        conflict_resolver: ModelConflictResolver,
    ) -> tuple[Any, int, int]:
        """Process data in time-based windows."""
        window = ModelStreamingWindow(input_data.window_size_ms)
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
                reduction_type=EnumReductionType.MERGE,
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
            conflict_resolver: ModelConflictResolver,
        ) -> Any:
            """Fold/reduce data to single value."""
            if not data:
                return input_data.accumulator_init

            accumulator = input_data.accumulator_init
            reducer_func_name = input_data.reducer_function

            if not reducer_func_name:
                # Default sum for numeric data
                if all(isinstance(x, int | float) for x in data):
                    return sum(data)
                return data[-1] if data else accumulator

            # Look up the reducer function by name
            reducer_func = self._get_reducer_function(reducer_func_name)
            if not reducer_func:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown reducer function: {reducer_func_name}",
                    context={"node_id": self.node_id},
                )

            for item in data:
                accumulator = reducer_func(accumulator, item)

            return accumulator

        async def aggregate_reducer(
            data: list[Any],
            input_data: ModelReducerInput[Any],
            conflict_resolver: ModelConflictResolver,
        ) -> dict[str, Any]:
            """Aggregate data by groups with statistics."""
            if not data:
                return {}

            # Group data
            groups: dict[str, list[Any]] = defaultdict(list)

            # Handle group key - if it's a string, use it as a field name
            if input_data.group_key:
                if isinstance(input_data.group_key, str):
                    group_key_func = lambda x: (
                        x.get(input_data.group_key, "default")
                        if hasattr(x, "get")
                        else "default"
                    )
                else:
                    # Handle list of group keys
                    group_key_func = lambda x: tuple(
                        x.get(field, "default") if hasattr(x, "get") else "default"
                        for field in input_data.group_key or []
                    )
            else:
                group_key_func = lambda x: "default"

            for item in data:
                key = group_key_func(item)
                if isinstance(key, tuple):
                    key = str(key)  # Convert tuple to string for dict key
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
            conflict_resolver: ModelConflictResolver,
        ) -> list[Any]:
            """Normalize scores and create rankings."""
            if not data:
                return []

            metadata = input_data.metadata or {}
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
            conflict_resolver: ModelConflictResolver,
        ) -> Any:
            """Merge multiple datasets with conflict resolution."""
            if not data:
                return {}

            # Handle dependency graph cycle detection
            metadata = input_data.metadata or {}
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
        self.reduction_functions[EnumReductionType.FOLD] = fold_reducer
        self.reduction_functions[EnumReductionType.AGGREGATE] = aggregate_reducer
        self.reduction_functions[EnumReductionType.NORMALIZE] = normalize_reducer
        self.reduction_functions[EnumReductionType.MERGE] = merge_reducer

    def _get_reducer_function(self, func_name: str) -> Callable[..., Any] | None:
        """
        Get a reducer function by name.

        Args:
            func_name: Name of the reducer function

        Returns:
            Callable[..., Any] | None: The reducer function or None if not found
        """
        # Built-in reducer functions
        builtin_functions = {
            "sum": lambda x, y: (
                x + y
                if isinstance(x, (int, float)) and isinstance(y, (int, float))
                else x
            ),
            "max": lambda x, y: (
                max(x, y)
                if isinstance(x, (int, float)) and isinstance(y, (int, float))
                else x
            ),
            "min": lambda x, y: (
                min(x, y)
                if isinstance(x, (int, float)) and isinstance(y, (int, float))
                else x
            ),
            "concat": lambda x, y: (
                f"{x}{y}" if isinstance(x, str) and isinstance(y, str) else x
            ),
            "append": lambda x, y: x + [y] if isinstance(x, list) else [x, y],
            "extend": lambda x, y: (
                x + y if isinstance(x, list) and isinstance(y, list) else x
            ),
        }

        return builtin_functions.get(func_name)

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

    async def get_introspection_data(self) -> dict[str, Any]:
        """
        Get comprehensive introspection data for NodeReducer.

        Returns specialized data reduction node information including streaming capabilities,
        conflict resolution strategies, reduction operations, and RSD data processing details.

        Returns:
            dict[str, Any]: Comprehensive introspection data with reducer-specific information
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
                    strategy.value for strategy in EnumConflictResolution
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
                "registered_reduction_functions": list[Any](
                    self.reduction_functions.keys()
                ),
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
                    "strategies": [
                        strategy.value for strategy in EnumConflictResolution
                    ],
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
            # fallback-ok: introspection data generation is informational only - return minimal node metadata to ensure introspection requests always succeed
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

    def _extract_reducer_operations(self) -> list[Any]:
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

    def _extract_reducer_io_specifications(self) -> dict[str, Any]:
        """Extract input/output specifications for reducer operations."""
        return {
            "input_model": "omnibase.core.node_reducer.ModelReducerInput",
            "output_model": "omnibase.core.node_reducer.ModelReducerOutput",
            "supports_streaming": True,
            "supports_batch_processing": True,
            "supports_incremental_processing": True,
            "reduction_types": [
                reduction_type.value for reduction_type in EnumReductionType
            ],
            "streaming_modes": [mode.value for mode in EnumStreamingMode],
            "conflict_resolution_strategies": [
                strategy.value for strategy in EnumConflictResolution
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

    def _extract_reducer_performance_characteristics(self) -> dict[str, Any]:
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

    def _extract_reduction_configuration(self) -> dict[str, Any]:
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
            # fallback-ok: reduction config extraction is for introspection metrics - return minimal config to maintain introspection stability
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract reduction configuration: {e!s}",
                {"node_id": self.node_id},
            )
            return {"default_batch_size": self.default_batch_size}

    def _extract_aggregation_configuration(self) -> dict[str, Any]:
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
            # fallback-ok: aggregation config extraction is for introspection metrics - return empty operations list[Any]to maintain introspection stability
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
                reduction_type=EnumReductionType.FOLD,
                reducer_function="sum",
                accumulator_init=0,
            )

            # For health check, we'll just validate the input without processing
            self._validate_reducer_input(test_input)
            return "healthy"

        except Exception:
            # fallback-ok: health status check is informational only - return unhealthy status rather than raising to allow introspection to continue
            return "unhealthy"

    def _get_reduction_metrics_sync(self) -> dict[str, Any]:
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
            # fallback-ok: reduction metrics gathering is for monitoring/introspection - return unknown status to prevent introspection failures
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get reduction metrics: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown", "error": str(e)}

    def _get_reducer_resource_usage(self) -> dict[str, Any]:
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
            # fallback-ok: resource usage metrics are for monitoring/introspection - return unknown status to prevent introspection failures
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get reducer resource usage: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown"}

    def _get_streaming_status(self) -> dict[str, Any]:
        """Get streaming processing status."""
        try:
            return {
                "streaming_enabled": True,
                "active_windows": len(self.active_windows),
                "streaming_buffer_size": self.streaming_buffer_size,
                "supports_real_time": True,
                "supports_windowed": True,
                "supports_incremental": True,
                "streaming_modes_supported": [mode.value for mode in EnumStreamingMode],
            }
        except Exception as e:
            # fallback-ok: streaming status is for monitoring/introspection - return disabled status to prevent introspection failures
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get streaming status: {e!s}",
                {"node_id": self.node_id},
            )
            return {"streaming_enabled": False, "error": str(e)}

    def _get_conflict_resolution_status(self) -> dict[str, Any]:
        """Get conflict resolution status."""
        return {
            "conflict_resolution_enabled": True,
            "supported_strategies": [
                strategy.value for strategy in EnumConflictResolution
            ],
            "supports_custom_resolvers": True,
            "merge_capabilities": {
                "numeric_merge": True,
                "string_concatenation": True,
                "list_merging": True,
                "dict_merging": True,
            },
        }
