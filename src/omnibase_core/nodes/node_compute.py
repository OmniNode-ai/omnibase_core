"""
NodeCompute - Pure Computation Node for 4-Node Architecture.

Specialized node type for pure computational operations with deterministic guarantees.
Focuses on input → transform → output patterns with caching and parallel processing support.

Key Capabilities:
- Pure function patterns with no side effects
- Deterministic operation guarantees
- Computational pipeline with parallel processing
- Caching layer for expensive computations
- Algorithm registration and execution
"""

import asyncio
import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

# ONEX_EXCLUDE: any - Base node class requires Any for generic type parameters [OMN-203]
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure import ModelComputeCache


class NodeCompute[T_Input, T_Output](NodeCoreBase):
    """
    Pure computation node for deterministic operations.

    Generic type parameters:
        T_Input: Type of input data (flows from ModelComputeInput[T_Input])
        T_Output: Type of output result (flows to ModelComputeOutput[T_Output])

    Type flow:
        Input data (T_Input) -> Computation -> Output result (T_Output)

    Implements computational pipeline with input → transform → output pattern.
    Provides caching, parallel processing, and performance optimization for
    compute-intensive operations.

    Key Features:
    - Pure function patterns (no side effects)
    - Deterministic operation guarantees
    - Parallel processing support for batch operations
    - Intelligent caching layer for expensive computations
    - Performance monitoring and optimization
    - Type-safe input/output handling

    Thread Safety:
        - Instance NOT thread-safe due to mutable cache state
        - Use separate instances per thread OR implement cache locking
        - Parallel processing via ThreadPoolExecutor is internally managed
        - See docs/THREADING.md for production guidelines and examples
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeCompute with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Get cache configuration from container
        cache_config = container.compute_cache_config

        # Computation-specific configuration (defaults, overridden in _initialize_node_resources)
        # These defaults are used if ProtocolNodeConfiguration is not available
        self.max_parallel_workers = 4
        self.cache_ttl_minutes = cache_config.get_ttl_minutes() or 30
        self.performance_threshold_ms = 100.0

        # Initialize caching layer with container configuration
        self.computation_cache = ModelComputeCache(
            max_size=cache_config.max_size,
            ttl_seconds=cache_config.ttl_seconds,
            eviction_policy=cache_config.eviction_policy,
            enable_stats=cache_config.enable_stats,
        )

        # Thread pool for parallel execution
        self.thread_pool: ThreadPoolExecutor | None = None

        # Computation registry for algorithm functions
        self.computation_registry: dict[str, Callable[..., Any]] = {}

        # Performance tracking
        self.computation_metrics: dict[str, dict[str, float]] = {}

        # Register built-in computations
        self._register_builtin_computations()

    async def process(
        self, input_data: ModelComputeInput[T_Input]
    ) -> ModelComputeOutput[T_Output]:
        """
        REQUIRED: Execute pure computation.

        Args:
            input_data: Strongly typed computation input

        Returns:
            Strongly typed computation output with performance metrics

        Raises:
            ModelOnexError: If computation fails or performance threshold exceeded
        """
        # Use time.perf_counter() for accurate duration measurement
        # (monotonic, unaffected by system clock adjustments)
        start_time = time.perf_counter()

        try:
            self._validate_compute_input(input_data)

            # Generate cache key
            cache_key = self._generate_cache_key(input_data)

            # Check cache first if enabled
            if input_data.cache_enabled:
                cached_result = self.computation_cache.get(cache_key)
                if cached_result is not None:
                    return ModelComputeOutput(
                        result=cached_result,
                        operation_id=input_data.operation_id,
                        computation_type=input_data.computation_type,
                        processing_time_ms=0.0,
                        cache_hit=True,
                        parallel_execution_used=False,
                        metadata={"cache_retrieval": True},
                    )

            # Execute computation
            if input_data.parallel_enabled and self._supports_parallel_execution(
                input_data
            ):
                result = await self._execute_parallel_computation(input_data)
                parallel_used = True
            else:
                result = await self._execute_sequential_computation(input_data)
                parallel_used = False

            processing_time = (time.perf_counter() - start_time) * 1000

            # Validate performance threshold
            if processing_time > self.performance_threshold_ms:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Computation exceeded threshold: {processing_time:.2f}ms",
                    {
                        "node_id": str(self.node_id),
                        "operation_id": str(input_data.operation_id),
                        "computation_type": input_data.computation_type,
                    },
                )

            # Cache result if enabled
            if input_data.cache_enabled:
                self.computation_cache.put(cache_key, result, self.cache_ttl_minutes)

            # Update metrics
            self._update_specialized_metrics(
                self.computation_metrics,
                input_data.computation_type,
                processing_time,
                True,
            )
            await self._update_processing_metrics(processing_time, True)

            return ModelComputeOutput(
                result=result,
                operation_id=input_data.operation_id,
                computation_type=input_data.computation_type,
                processing_time_ms=processing_time,
                cache_hit=False,
                parallel_execution_used=parallel_used,
                metadata={
                    "input_data_size": len(str(input_data.data)),
                    "cache_enabled": input_data.cache_enabled,
                },
            )

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000

            self._update_specialized_metrics(
                self.computation_metrics,
                input_data.computation_type,
                processing_time,
                False,
            )
            await self._update_processing_metrics(processing_time, False)

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Computation failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "computation_type": input_data.computation_type,
                    "cache_enabled": input_data.cache_enabled,
                    "parallel_enabled": input_data.parallel_enabled,
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time,
                },
            ) from e

    async def execute_compute(
        self,
        contract: ModelContractCompute,
    ) -> ModelComputeOutput[T_Output]:
        """
        Execute computation based on contract specification.

        REQUIRED INTERFACE: This public method implements the ModelContractCompute interface
        per ONEX guidelines. Subclasses implementing custom compute nodes should override
        this method or use the default contract-to-input conversion.

        Args:
            contract: Compute contract specifying the operation configuration

        Returns:
            ModelComputeOutput: Computation results with performance metrics

        Raises:
            ModelOnexError: If computation fails or contract is invalid
        """
        if not isinstance(contract, ModelContractCompute):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid contract type - expected ModelContractCompute, got {type(contract).__name__}",
                context={
                    "node_id": str(self.node_id),
                    "provided_type": type(contract).__name__,
                    "expected_type": "ModelContractCompute",
                },
            )

        # Convert contract to ModelComputeInput
        compute_input: ModelComputeInput[Any] = self._contract_to_input(contract)

        # Execute via existing process() method
        return await self.process(compute_input)

    def _contract_to_input(
        self,
        contract: ModelContractCompute,
    ) -> ModelComputeInput[T_Input]:
        """
        Convert ModelContractCompute to ModelComputeInput.

        Extracts input_state (required) and computation_type from the contract.
        Fails fast if input_state is not provided.

        Args:
            contract: Compute contract to convert

        Returns:
            ModelComputeInput: Input model for process() method

        Raises:
            ModelOnexError: If contract has no input_state or conversion fails

        Note:
            computation_type precedence order (see ModelContractCompute docstring):
            1. algorithm.algorithm_type (preferred - canonical location)
            2. metadata["computation_type"] (fallback - legacy location)
            3. contract.computation_type attribute (fallback - deprecated)
            4. "default" (final fallback - implicit default)
        """
        # Extract input data from contract - input_state is required
        input_data: Any = None
        if hasattr(contract, "input_state") and contract.input_state is not None:
            input_data = contract.input_state

        if input_data is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Contract must have 'input_state' field with valid data",
                context={
                    "node_id": str(self.node_id),
                    "hint": "Set input_state in your contract (input_data is no longer supported)",
                    "input_state_value": str(getattr(contract, "input_state", None)),
                },
            )

        # Extract computation_type with fallback chain (with warning logs for non-preferred sources):
        # 1. algorithm.algorithm_type (preferred - canonical location)
        # 2. metadata["computation_type"] (fallback - legacy location)
        # 3. contract.computation_type attribute (fallback - deprecated)
        # 4. "default" (final fallback - implicit default)
        computation_type: str = "default"
        computation_type_source: str = "default"

        # Try algorithm.algorithm_type first (preferred canonical location)
        if hasattr(contract, "algorithm") and contract.algorithm is not None:
            if (
                hasattr(contract.algorithm, "algorithm_type")
                and contract.algorithm.algorithm_type is not None
            ):
                computation_type = contract.algorithm.algorithm_type
                computation_type_source = "algorithm.algorithm_type"

        # Fallback to metadata.computation_type (legacy location)
        if computation_type == "default":
            contract_metadata = getattr(contract, "metadata", None) or {}
            if (
                isinstance(contract_metadata, dict)
                and "computation_type" in contract_metadata
            ):
                computation_type = contract_metadata["computation_type"]
                computation_type_source = "metadata.computation_type"
                emit_log_event(
                    LogLevel.WARNING,
                    "Using 'metadata.computation_type' fallback - "
                    "please migrate to 'algorithm.algorithm_type' (canonical location). "
                    "This fallback will be removed in v0.5.0.",
                    {
                        "node_id": str(self.node_id),
                        "computation_type": computation_type,
                        "source": computation_type_source,
                    },
                )

        # Fallback to contract.computation_type attribute (deprecated)
        if computation_type == "default":
            if (
                hasattr(contract, "computation_type")
                and contract.computation_type is not None
            ):
                computation_type = contract.computation_type
                computation_type_source = "contract.computation_type"
                emit_log_event(
                    LogLevel.WARNING,
                    "Using deprecated 'contract.computation_type' attribute - "
                    "please migrate to 'algorithm.algorithm_type' (canonical location). "
                    "This fallback will be removed in v0.5.0.",
                    {
                        "node_id": str(self.node_id),
                        "computation_type": computation_type,
                        "source": computation_type_source,
                    },
                )

        # Final fallback to "default" (implicit default)
        if computation_type == "default":
            emit_log_event(
                LogLevel.WARNING,
                "No computation_type specified in contract - using implicit 'default'. "
                "Consider specifying 'algorithm.algorithm_type' explicitly",
                {
                    "node_id": str(self.node_id),
                    "computation_type": computation_type,
                    "source": "implicit_default",
                    "hint": "Set algorithm.algorithm_type in your contract",
                },
            )

        # Extract metadata (normalize None to empty dict)
        # Type matches ModelComputeInput.metadata field
        metadata = getattr(contract, "metadata", None) or {}

        # Extract optional execution settings from metadata
        cache_enabled = metadata.get("cache_enabled", True)
        parallel_enabled = metadata.get("parallel_enabled", False)

        # Log warning if parallel_enabled but data is not parallelizable
        if parallel_enabled and not self._supports_parallel_execution(
            ModelComputeInput(
                data=input_data,
                computation_type=computation_type,
            )
        ):
            emit_log_event(
                LogLevel.WARNING,
                "Parallel execution requested but data is not parallelizable, using sequential execution",
                {"node_id": str(self.node_id), "computation_type": computation_type},
            )

        return ModelComputeInput(
            data=input_data,
            computation_type=computation_type,
            metadata=metadata,
            cache_enabled=cache_enabled,
            parallel_enabled=parallel_enabled,
        )

    def register_computation(
        self, computation_type: str, computation_func: Callable[..., Any]
    ) -> None:
        """
        Register custom computation function.

        Args:
            computation_type: Type identifier for computation
            computation_func: Pure function to register

        Raises:
            ModelOnexError: If computation type already registered
        """
        if computation_type in self.computation_registry:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Computation type already registered: {computation_type}",
                context={"node_id": str(self.node_id)},
            )

        if not callable(computation_func):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Computation function must be callable",
                context={"node_id": str(self.node_id)},
            )

        self.computation_registry[computation_type] = computation_func

        emit_log_event(
            LogLevel.INFO,
            f"Computation registered: {computation_type}",
            {"node_id": str(self.node_id), "computation_type": computation_type},
        )

    async def get_computation_metrics(self) -> dict[str, dict[str, float]]:
        """Get detailed computation performance metrics."""
        cache_stats = self.computation_cache.get_stats()

        return {
            **self.computation_metrics,
            "cache_performance": {
                "total_entries": float(cache_stats["total_entries"]),
                "valid_entries": float(cache_stats["valid_entries"]),
                "cache_utilization": float(cache_stats["valid_entries"])
                / max(cache_stats["max_size"], 1),
                "ttl_minutes": float(self.cache_ttl_minutes),
            },
            "parallel_processing": {
                "max_workers": float(self.max_parallel_workers),
                "thread_pool_active": float(1 if self.thread_pool else 0),
            },
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize computation-specific resources."""
        # Load configuration from NodeConfigProvider if available
        config = self.container.get_service_optional(NodeConfigProvider)
        if config:
            # Load performance configurations with fallback to current defaults
            max_workers_value = await config.get_performance_config(
                "compute.max_parallel_workers", default=self.max_parallel_workers
            )
            cache_ttl_value = await config.get_performance_config(
                "compute.cache_ttl_minutes", default=self.cache_ttl_minutes
            )
            perf_threshold_value = await config.get_performance_config(
                "compute.performance_threshold_ms",
                default=self.performance_threshold_ms,
            )

            # Update configuration values with type checking
            if isinstance(max_workers_value, (int, float)):
                self.max_parallel_workers = int(max_workers_value)
            if isinstance(cache_ttl_value, (int, float)):
                self.cache_ttl_minutes = int(cache_ttl_value)
            if isinstance(perf_threshold_value, (int, float)):
                self.performance_threshold_ms = float(perf_threshold_value)

            emit_log_event(
                LogLevel.INFO,
                "NodeCompute loaded configuration from NodeConfigProvider",
                {
                    "node_id": str(self.node_id),
                    "max_parallel_workers": self.max_parallel_workers,
                    "cache_ttl_minutes": self.cache_ttl_minutes,
                    "performance_threshold_ms": self.performance_threshold_ms,
                },
            )

        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_parallel_workers)

        emit_log_event(
            LogLevel.INFO,
            "NodeCompute resources initialized",
            {
                "node_id": str(self.node_id),
                "max_parallel_workers": self.max_parallel_workers,
                "cache_ttl_minutes": self.cache_ttl_minutes,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup computation-specific resources."""
        if self.thread_pool:
            # Shutdown thread pool with timeout to prevent hanging
            # timeout parameter requires Python 3.9+
            self.thread_pool.shutdown(wait=True, timeout=5.0)  # type: ignore[call-arg]

            # Check if threads are still running (shutdown doesn't guarantee completion)
            # Note: shutdown() doesn't return status, but we log the completion
            emit_log_event(
                LogLevel.INFO,
                "Thread pool shutdown completed (5s timeout)",
                {
                    "node_id": str(self.node_id),
                    "max_workers": self.max_parallel_workers,
                },
            )
            self.thread_pool = None

        self.computation_cache.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeCompute resources cleaned up",
            {"node_id": str(self.node_id)},
        )

    def _validate_compute_input(self, input_data: ModelComputeInput[Any]) -> None:
        """Validate computation input data."""
        super()._validate_input_data(input_data)

        if not hasattr(input_data, "data"):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Input data must have 'data' attribute",
                context={"node_id": str(self.node_id)},
            )

    def _generate_cache_key(self, input_data: ModelComputeInput[Any]) -> str:
        """Generate deterministic cache key for computation input."""
        data_str = str(input_data.data)
        # Use hashlib for deterministic hashing across Python processes
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return f"{input_data.computation_type}:{data_hash}"

    def _supports_parallel_execution(self, input_data: ModelComputeInput[Any]) -> bool:
        """Check if computation supports parallel execution."""
        return bool(
            isinstance(input_data.data, (list, tuple)) and len(input_data.data) > 1
        )

    async def _execute_sequential_computation(
        self, input_data: ModelComputeInput[Any]
    ) -> Any:
        """Execute computation sequentially."""
        computation_type = input_data.computation_type

        if computation_type in self.computation_registry:
            computation_func = self.computation_registry[computation_type]
            return computation_func(input_data.data)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown computation type: {computation_type}",
            context={
                "node_id": str(self.node_id),
                "available_types": list(self.computation_registry.keys()),
            },
        )

    async def _execute_parallel_computation(
        self, input_data: ModelComputeInput[Any]
    ) -> Any:
        """Execute computation in parallel using thread pool."""
        if not self.thread_pool:
            return await self._execute_sequential_computation(input_data)

        computation_type = input_data.computation_type
        computation_func = self.computation_registry.get(computation_type)

        if not computation_func:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Unknown computation type: {computation_type}",
                context={"node_id": str(self.node_id)},
            )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.thread_pool, computation_func, input_data.data
        )

    def _register_builtin_computations(self) -> None:
        """Register built-in computation functions."""

        def default_transform(data: Any) -> Any:
            """Default identity transformation."""
            return data

        def string_uppercase(data: str) -> str:
            """Convert string to uppercase."""
            if not isinstance(data, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Input must be a string",
                    context={"input_type": type(data).__name__},
                )
            return data.upper()

        def sum_numbers(data: list[float]) -> float:
            """Sum list of numbers."""
            if not isinstance(data, (list, tuple)):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Input must be a list or tuple",
                    context={"input_type": type(data).__name__},
                )
            return sum(data)

        self.register_computation("default", default_transform)
        self.register_computation("string_uppercase", string_uppercase)
        self.register_computation("sum_numbers", sum_numbers)
