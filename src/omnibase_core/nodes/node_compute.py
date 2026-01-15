"""
NodeCompute - Pure Computation Node for 4-Node Architecture.

Specialized node type for pure computational operations with deterministic guarantees.
Focuses on input → transform → output patterns.

Key Capabilities:
- Pure function patterns with no side effects
- Deterministic operation guarantees
- Algorithm registration and execution
- Optional infrastructure via protocol injection (caching, timing, parallelization)
- Contract-driven handler routing via MixinHandlerRouting (OMN-1293)

Infrastructure Concerns (Optional via Protocol Injection):
- Caching: Injected via ProtocolComputeCache (OMN-700)
- Timing: Injected via ProtocolTimingService (OMN-700)
- Parallelization: Injected via ProtocolParallelExecutor (OMN-700)

If infrastructure protocols are not provided, NodeCompute operates in pure mode:
- No caching (cache_hit always False)
- No timing (processing_time_ms is 0.0)
- No parallelization (sequential execution only)

.. versionchanged:: 0.4.0
   Moved infrastructure concerns (caching, timing, threading) to optional
   protocol injection per OMN-700. NodeCompute is now pure by default.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.compute import (
    ProtocolComputeCache,
    ProtocolParallelExecutor,
    ProtocolTimingService,
)


class NodeCompute[T_Input, T_Output](NodeCoreBase, MixinHandlerRouting):
    """
    Pure computation node for deterministic operations.

    Generic type parameters:
        T_Input: Type of input data (flows from ModelComputeInput[T_Input])
        T_Output: Type of output result (flows to ModelComputeOutput[T_Output])

    Type flow:
        Input data (T_Input) -> Computation -> Output result (T_Output)

    Implements computational pipeline with input → transform → output pattern.
    Infrastructure concerns (caching, timing, parallelization) are optional
    and injected via protocols.

    Key Features:
    - Pure function patterns (no side effects)
    - Deterministic operation guarantees
    - Type-safe input/output handling
    - Optional caching via ProtocolComputeCache injection
    - Optional timing via ProtocolTimingService injection
    - Optional parallelization via ProtocolParallelExecutor injection
    - Contract-driven handler routing via MixinHandlerRouting

    Handler Routing (via MixinHandlerRouting):
        Enables routing messages to handlers based on YAML contract configuration.
        Use ``payload_type_match`` routing strategy to route by input data type.

        Example handler_routing contract section::

            handler_routing:
              version: { major: 1, minor: 0, patch: 0 }
              routing_strategy: payload_type_match
              handlers:
                - routing_key: UserData
                  handler_key: compute_user_score
                - routing_key: OrderData
                  handler_key: compute_order_total
              default_handler: compute_generic

    Pure Mode (default):
        When infrastructure protocols are not injected, NodeCompute operates
        in pure mode:
        - cache_hit always returns False
        - processing_time_ms is always 0.0
        - parallel_execution_used is always False
        - Computation is executed sequentially

    Thread Safety:
        **MVP Design Decision**: NodeCompute uses mutable state intentionally for the MVP
        phase to prioritize simplicity and rapid iteration. This is a documented trade-off.

        **Mutable State Components**:
        - ``_cache``: Optional compute cache (injected via ProtocolComputeCache)
        - ``computation_registry``: Algorithm function registry (dict[str, Callable])
        - ``computation_metrics``: Performance metrics dictionary (dict[str, dict[str, float]])

        **Current Guarantees**:
        - Instance is thread-safe in pure mode (no mutable state accessed)
        - If cache/executor are injected, thread safety depends on their implementations

        **Production Path**: The protocol injection pattern (OMN-700) enables thread-safe
        implementations to be injected. See ``docs/architecture/MUTABLE_STATE_STRATEGY.md``
        for the production improvement roadmap.

        See ``docs/guides/THREADING.md`` for thread-local instance patterns.

    .. versionchanged:: 0.4.0
       Made caching, timing, and parallelization optional via protocol injection.
       NodeCompute is now pure by default per OMN-700.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeCompute with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection.
                The container may optionally provide:
                - ProtocolComputeCache: For caching computation results
                - ProtocolTimingService: For timing computation duration
                - ProtocolParallelExecutor: For parallel execution

        Raises:
            ModelOnexError: If container is invalid or initialization fails

        .. versionchanged:: 0.4.0
           Infrastructure services are now optional. If not provided,
           NodeCompute operates in pure mode.
        """
        super().__init__(container)

        # Optional infrastructure services (injected via protocols)
        # These are resolved lazily in _initialize_node_resources
        self._cache: ProtocolComputeCache | None = None
        self._timing_service: ProtocolTimingService | None = None
        self._parallel_executor: ProtocolParallelExecutor | None = None

        # Configuration (only used if infrastructure services are available)
        self.cache_ttl_minutes: int = 30
        self.performance_threshold_ms: float = 100.0

        # Computation registry for algorithm functions
        self.computation_registry: dict[str, Callable[..., Any]] = {}

        # Performance tracking (optional, only tracked if timing service available)
        self.computation_metrics: dict[str, dict[str, float]] = {}

        # Register built-in computations
        self._register_builtin_computations()

        # Initialize handler routing from contract (optional - not all compute nodes have it)
        # The handler_routing subcontract enables contract-driven message routing.
        # If the node's contract has handler_routing defined, initialize the routing table.
        handler_routing = None
        if hasattr(self, "contract") and self.contract is not None:
            handler_routing = getattr(self.contract, "handler_routing", None)

        if handler_routing is not None:
            handler_registry: object = container.get_service("ProtocolHandlerRegistry")  # type: ignore[arg-type]  # Protocol-based DI lookup per ONEX conventions
            self._init_handler_routing(handler_routing, handler_registry)  # type: ignore[arg-type]  # Registry retrieved via DI

    # =========================================================================
    # Cache Access Properties
    # =========================================================================

    @property
    def computation_cache(self) -> ProtocolComputeCache:
        """
        Access the computation cache.

        Returns the injected cache, or lazily creates a default implementation
        from container configuration.

        Returns:
            The computation cache instance.

        Note:
            For new code, prefer using protocol injection via the container
            rather than accessing the cache directly.

        .. versionchanged:: 0.4.0
           Uses protocol injection. Creates default implementation if not injected.
        """
        if self._cache is None:
            # Lazily create default cache from container config
            from omnibase_core.services.service_compute_cache import (
                ServiceComputeCache,
            )

            self._cache = ServiceComputeCache(self.container.compute_cache_config)
        return self._cache

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
            ModelOnexError: If computation fails

        Note:
            In pure mode (no infrastructure services injected):
            - cache_hit is always False
            - processing_time_ms is always 0.0
            - parallel_execution_used is always False

        .. versionchanged:: 0.4.0
           Uses optional protocol injection for timing, caching, and
           parallelization. Operates in pure mode if not injected.
        """
        # Start timer if timing service is available
        start_time: float | None = None
        if self._timing_service is not None:
            start_time = self._timing_service.start_timer()

        try:
            self._validate_compute_input(input_data)

            # Check cache first if enabled and cache is available
            if input_data.cache_enabled and self._cache is not None:
                cache_key = self._generate_cache_key(input_data)
                cached_result = self._cache.get(cache_key)
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
            parallel_used = False
            if (
                input_data.parallel_enabled
                and self._parallel_executor is not None
                and self._supports_parallel_execution(input_data)
            ):
                result = await self._execute_parallel_computation(input_data)
                parallel_used = True
            else:
                result = await self._execute_sequential_computation(input_data)

            # Calculate processing time if timing service is available
            processing_time: float = 0.0
            if self._timing_service is not None and start_time is not None:
                processing_time = self._timing_service.stop_timer(start_time)

                # Log performance warning if threshold exceeded
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

            # Cache result if enabled and cache is available
            if input_data.cache_enabled and self._cache is not None:
                cache_key = self._generate_cache_key(input_data)
                self._cache.put(cache_key, result, self.cache_ttl_minutes)

            # Update metrics (only if timing service available)
            if self._timing_service is not None:
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
                    "pure_mode": self._timing_service is None,
                },
            )

        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            # Never catch cancellation/exit signals
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation
            raise
        except ModelOnexError:
            # Re-raise ONEX errors as-is to preserve error context
            raise
        # boundary-ok: wraps user computation exceptions into structured error response with metrics
        except Exception as e:
            # boundary-ok: wrap user computation exceptions in structured ONEX error
            # Calculate processing time for error reporting
            processing_time = 0.0
            if self._timing_service is not None and start_time is not None:
                processing_time = self._timing_service.stop_timer(start_time)

            # Update metrics (only if timing service available)
            if self._timing_service is not None:
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
                    "pure_mode": self._timing_service is None,
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
            computation_type is extracted directly from algorithm.algorithm_type.
            Both algorithm and algorithm_type are required fields in
            ModelContractCompute and ModelAlgorithmConfig respectively.
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

        # Extract computation_type directly from algorithm.algorithm_type
        # Both fields are required in their respective models (no fallback needed)
        computation_type: str = contract.algorithm.algorithm_type

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
        """
        Get detailed computation performance metrics.

        Returns:
            Dictionary with computation metrics, cache performance (if available),
            and execution mode information.

        .. versionchanged:: 0.4.0
           Returns limited metrics in pure mode (no cache/executor available).
        """
        result: dict[str, dict[str, float]] = {**self.computation_metrics}

        # Add cache metrics if cache is available
        if self._cache is not None:
            cache_stats = self._cache.get_stats()
            max_size = cache_stats.get("max_size", 1)
            result["cache_performance"] = {
                "total_entries": float(cache_stats.get("total_entries", 0)),
                "valid_entries": float(cache_stats.get("valid_entries", 0)),
                "cache_utilization": float(cache_stats.get("valid_entries", 0))
                / max(max_size, 1),
                "ttl_minutes": float(self.cache_ttl_minutes),
            }

        # Add execution mode info
        result["execution_mode"] = {
            "pure_mode": float(1 if self._timing_service is None else 0),
            "cache_enabled": float(1 if self._cache is not None else 0),
            "parallel_enabled": float(1 if self._parallel_executor is not None else 0),
        }

        return result

    async def _initialize_node_resources(self) -> None:
        """
        Initialize computation-specific resources.

        Resolution Strategy:
        1. Try to resolve infrastructure services from container via protocols
        2. If not available, create default implementations from container config

        Services initialized:
        - ProtocolComputeCache: For caching computation results
        - ProtocolTimingService: For timing computation duration
        - ProtocolParallelExecutor: For parallel execution

        .. versionchanged:: 0.4.0
           Uses protocol injection for infrastructure services.
        """
        # Try to resolve infrastructure services from container first
        # NOTE(OMN-1302): Protocols are abstract by design but runtime_checkable works at runtime.
        # Safe because get_service_optional returns None if not registered.
        self._cache = self.container.get_service_optional(
            ProtocolComputeCache  # type: ignore[type-abstract]
        )
        self._timing_service = self.container.get_service_optional(
            ProtocolTimingService  # type: ignore[type-abstract]
        )
        self._parallel_executor = self.container.get_service_optional(
            ProtocolParallelExecutor  # type: ignore[type-abstract]
        )

        # If services not available, create default implementations
        if self._cache is None or self._timing_service is None:
            from omnibase_core.services.service_compute_cache import (
                ServiceComputeCache,
            )
            from omnibase_core.services.service_parallel_executor import (
                ServiceParallelExecutor,
            )
            from omnibase_core.services.service_timing import ServiceTiming

            # Create cache from container's compute_cache_config
            if self._cache is None:
                cache_config = self.container.compute_cache_config
                self._cache = ServiceComputeCache(cache_config)
                ttl = cache_config.get_ttl_minutes()
                if ttl is not None:
                    self.cache_ttl_minutes = ttl

            # Create timing service
            if self._timing_service is None:
                self._timing_service = ServiceTiming()

            # Create parallel executor with default workers
            if self._parallel_executor is None:
                self._parallel_executor = ServiceParallelExecutor(max_workers=4)

        # Load configuration from NodeConfigProvider if available
        config = self.container.get_service_optional(NodeConfigProvider)
        if config:
            # Load performance configurations with fallback to current defaults
            cache_ttl_value = await config.get_performance_config(
                "compute.cache_ttl_minutes", default=self.cache_ttl_minutes
            )
            perf_threshold_value = await config.get_performance_config(
                "compute.performance_threshold_ms",
                default=self.performance_threshold_ms,
            )

            # Update configuration values with type checking
            if isinstance(cache_ttl_value, (int, float)):
                self.cache_ttl_minutes = int(cache_ttl_value)
            if isinstance(perf_threshold_value, (int, float)):
                self.performance_threshold_ms = float(perf_threshold_value)

        emit_log_event(
            LogLevel.INFO,
            "NodeCompute resources initialized",
            {
                "node_id": str(self.node_id),
                "cache_available": self._cache is not None,
                "timing_available": self._timing_service is not None,
                "executor_available": self._parallel_executor is not None,
                "cache_ttl_minutes": self.cache_ttl_minutes,
                "performance_threshold_ms": self.performance_threshold_ms,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """
        Cleanup computation-specific resources.

        Shuts down injected infrastructure services:
        - ProtocolParallelExecutor: Shutdown with wait
        - ProtocolComputeCache: Clear cache entries

        .. versionchanged:: 0.4.0
           Cleans up injected services instead of direct resources.
        """
        # Shutdown parallel executor if available
        if self._parallel_executor is not None:
            await self._parallel_executor.shutdown(wait=True)
            emit_log_event(
                LogLevel.INFO,
                "Parallel executor shutdown completed",
                {"node_id": str(self.node_id)},
            )
            self._parallel_executor = None

        # Clear cache if available
        if self._cache is not None:
            self._cache.clear()
            emit_log_event(
                LogLevel.INFO,
                "Computation cache cleared",
                {"node_id": str(self.node_id)},
            )
            self._cache = None

        # Clear timing service reference
        self._timing_service = None

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
                "computation_type": computation_type,
                "available_types": list(self.computation_registry.keys()),
            },
        )

    async def _execute_parallel_computation(
        self, input_data: ModelComputeInput[Any]
    ) -> Any:
        """
        Execute computation in parallel using injected executor.

        Falls back to sequential execution if no executor is available.

        .. versionchanged:: 0.4.0
           Uses ProtocolParallelExecutor instead of direct ThreadPoolExecutor.
        """
        if self._parallel_executor is None:
            return await self._execute_sequential_computation(input_data)

        computation_type = input_data.computation_type
        computation_func = self.computation_registry.get(computation_type)

        if not computation_func:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Unknown computation type: {computation_type}",
                context={"node_id": str(self.node_id)},
            )

        return await self._parallel_executor.execute(computation_func, input_data.data)

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
