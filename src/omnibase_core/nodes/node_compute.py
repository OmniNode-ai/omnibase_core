"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

NodeCompute - Pure Computation Node for 4-Node Architecture.

Specialized node type for pure computational operations with deterministic guarantees.
Focuses on input → transform → output patterns with caching and parallel processing support.

Key Capabilities:
- Pure function patterns with no side effects
- Deterministic operation guarantees
- Computational pipeline with parallel processing
- Caching layer for expensive computations
- Algorithm registration and execution

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

import asyncio
import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure import ModelComputeCache


class NodeCompute[T_Input, T_Output](NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Pure computation node for deterministic operations.

    Implements computational pipeline with input -> transform -> output pattern.
    Provides caching, parallel processing, and performance optimization for
    compute-intensive operations.

    .. versionadded:: 0.4.0
        Added PEP 695 generic type parameters and execute_compute() contract interface.

    Type Parameters:
        T_Input: The input data type for computations.
            Example: dict[str, Any], ModelUserData, list[ModelMetric]
        T_Output: The output data type from computations.
            Example: ModelComputeResult, dict[str, float], list[ModelPrediction]

    Type flow:
        Input data (T_Input) -> computation -> Output result (T_Output)
        T_Output is typically the same as T_Input or a transformation thereof.

    Example with concrete types::

        class NodeStringProcessor(NodeCompute[str, str]):
            '''Process string inputs to string outputs.'''

            async def process(
                self, input_data: ModelComputeInput[str]
            ) -> ModelComputeOutput[str]:
                result = input_data.data.upper()
                return ModelComputeOutput(
                    result=result,
                    operation_id=input_data.operation_id,
                    computation_type=input_data.computation_type,
                    processing_time_ms=0.0,
                    cache_hit=False,
                    parallel_execution_used=False,
                    metadata={},
                )

        class NodeMetricsAggregator(NodeCompute[list[float], dict[str, float]]):
            '''Aggregate numeric metrics into statistics.'''

            async def process(
                self, input_data: ModelComputeInput[list[float]]
            ) -> ModelComputeOutput[dict[str, float]]:
                values = input_data.data
                result = {
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0.0,
                    "count": float(len(values)),
                }
                return ModelComputeOutput(
                    result=result,
                    operation_id=input_data.operation_id,
                    computation_type="metrics_aggregation",
                    processing_time_ms=0.0,
                    cache_hit=False,
                    parallel_execution_used=False,
                    metadata={},
                )

    Key Features:
        - Pure function patterns (no side effects)
        - Deterministic operation guarantees
        - Parallel processing support for batch operations
        - Intelligent caching layer for expensive computations
        - Performance monitoring and optimization
        - Type-safe input/output handling

    Caching Strategy:
        NodeCompute implements a deterministic caching layer to optimize expensive
        computations. The caching system uses a content-addressable approach with
        SHA256 hashing to ensure consistent cache behavior.

        **Cache Key Generation**:
            Cache keys are generated using SHA256 hashing of the input data combined
            with the computation type. This approach provides:

            - **Determinism**: Identical inputs always produce identical cache keys,
              ensuring consistent cache behavior across process restarts
            - **Collision Resistance**: SHA256's cryptographic properties virtually
              eliminate hash collisions, preventing incorrect cache hits
            - **Cross-Process Consistency**: Unlike Python's built-in ``hash()``,
              SHA256 produces consistent results across different Python processes
              and interpreter sessions

            Format: ``{computation_type}:{sha256_hex_digest}``

            Example: ``sum_numbers:a3b2c1d4e5f6...``

        **Cache Invalidation Policies**:
            The cache supports multiple invalidation strategies:

            1. **TTL-Based Expiration** (Primary):
               - Each cached entry has a time-to-live (TTL) configured via
                 ``cache_ttl_minutes`` (default: 30 minutes)
               - Expired entries are automatically detected on access and removed
               - TTL can be customized per-entry or globally via container config

            2. **Manual Cache Clearing**:
               - Call ``computation_cache.clear()`` to invalidate all entries
               - Useful for forced refresh or during node cleanup
               - Automatically called during ``_cleanup_node_resources()``

            3. **Eviction Policy** (Memory Management):
               - Configured via ``ModelComputeCache.eviction_policy``
               - **LRU** (Least Recently Used): Evicts entries not accessed recently
               - **LFU** (Least Frequently Used): Evicts entries with lowest access count
               - **FIFO** (First In First Out): Evicts oldest entries by insertion time
               - Eviction triggers when cache reaches ``max_size`` (default: 1000)

        **Cache Configuration**:
            Cache behavior is configured through ``ModelONEXContainer.compute_cache_config``:

            - ``max_size``: Maximum number of cached entries (default: 1000)
            - ``ttl_seconds``: Time-to-live in seconds (default: 1800 = 30 min)
            - ``eviction_policy``: LRU, LFU, or FIFO (default: LRU)
            - ``enable_stats``: Enable hit/miss tracking (default: True)

        **Cache Implications**:
            - **Cache Hits**: Return cached result with ``processing_time_ms=0.0``
            - **Cache Misses**: Execute computation, cache result if ``cache_enabled=True``
            - **String Serialization**: Input data is converted to string for hashing;
              complex objects should implement consistent ``__str__`` methods

    Thread Safety:
        - Instance NOT thread-safe due to mutable cache state
        - Use separate instances per thread OR implement cache locking
        - Parallel processing via ThreadPoolExecutor is internally managed
        - See docs/THREADING.md for production guidelines and examples

    Note:
        **Parallel Processing Guidance**

        When to enable parallel processing (``parallel_enabled=True``):
            - Batch operations on independent data items (e.g., transforming a list of records)
            - CPU-bound computations that can be partitioned (e.g., processing chunks of data)
            - Map operations where each element is processed independently

        Computation types that benefit from parallelization:
            - **Batch transformations**: Processing lists/tuples of independent items
            - **Aggregations over large datasets**: sum, average, statistical computations
            - **Independent element processing**: Operations where each list item is processed
              without dependencies on other items

        Computation types that do NOT benefit from parallelization:
            - **Single-value operations**: String transformations, single object processing
            - **Sequential dependencies**: Operations where item N depends on item N-1
            - **Small datasets**: Overhead of thread pool exceeds computation time
            - **I/O-bound operations**: Use NodeEffect for I/O; parallel threads don't help

        Thread pool configuration:
            - Default: 4 workers (configurable via ``max_parallel_workers``)
            - Pool is lazily initialized during ``_initialize_node_resources()``
            - Workers are reused across computations for efficiency
            - Shutdown with 5s timeout during ``_cleanup_node_resources()``

        Performance considerations:
            - Parallel execution adds overhead (~1-5ms for thread pool dispatch)
            - Only use for computations where per-item processing > 10ms
            - Data must be a list or tuple with more than 1 element
            - If data is not parallelizable, falls back to sequential execution with a warning
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

    async def execute_compute(
        self,
        contract: Any,  # ModelContractCompute - imported in method to avoid circular dependency
    ) -> ModelComputeOutput[T_Output]:
        """
        Execute compute operation based on contract specification.

        REQUIRED INTERFACE: This public method implements the ModelContractCompute
        interface per ONEX guidelines. It provides a contract-based entry point
        that delegates to the internal process() method.

        This method validates the contract type before processing to ensure
        type safety and provide clear error messages for invalid contracts.

        .. versionadded:: 0.4.0

        Args:
            contract: The compute contract specification. Must be an instance of
                ModelContractCompute. The contract should contain:
                - input_state: Input data for computation (required)
                - metadata: Optional metadata dict with computation_type, cache_enabled,
                  and parallel_enabled settings

        Returns:
            ModelComputeOutput[T_Output]: Computation results containing:
                - result: The computed output value
                - operation_id: Unique identifier for this operation
                - computation_type: Type of computation performed
                - processing_time_ms: Time taken for computation
                - cache_hit: Whether result was retrieved from cache
                - parallel_execution_used: Whether parallel processing was used
                - metadata: Additional operation metadata

        Raises:
            ModelOnexError: If contract type is invalid (not ModelContractCompute),
                computation fails, or input validation fails. Error codes:
                - VALIDATION_ERROR: Invalid contract type or missing required fields
                - OPERATION_FAILED: Computation execution failure

        Example:
            Using the built-in ``string_uppercase`` computation::

                >>> from omnibase_core.models.contracts import ModelContractCompute
                >>> from omnibase_core.models.contracts import ModelContractAlgorithm
                >>> contract = ModelContractCompute(
                ...     name="uppercase_transform",
                ...     version="1.0.0",
                ...     input_state="hello world",  # Direct string input for string_uppercase
                ...     algorithm=ModelContractAlgorithm(algorithm_type="string_uppercase"),
                ... )
                >>> result = await node.execute_compute(contract)
                >>> print(result.result)  # "HELLO WORLD"

            Using the built-in ``sum_numbers`` computation::

                >>> contract = ModelContractCompute(
                ...     name="sum_values",
                ...     version="1.0.0",
                ...     input_state=[1.0, 2.0, 3.0, 4.0],  # Direct list input for sum_numbers
                ...     algorithm=ModelContractAlgorithm(algorithm_type="sum_numbers"),
                ... )
                >>> result = await node.execute_compute(contract)
                >>> print(result.result)  # 10.0

        Note:
            This method requires a ModelContractCompute instance. If you need
            to process raw input data directly, use the process() method with
            a ModelComputeInput instance instead.
        """
        # Import here to avoid circular dependency
        from omnibase_core.models.contracts.model_contract_compute import (
            ModelContractCompute,
        )

        if not isinstance(contract, ModelContractCompute):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Invalid contract type - must be ModelContractCompute",
                context={
                    "node_id": str(self.node_id),
                    "provided_type": type(contract).__name__,
                    "expected_type": "ModelContractCompute",
                },
            )

        # Convert contract to ModelComputeInput
        compute_input = self._contract_to_input(contract)
        return await self.process(compute_input)

    def _extract_computation_type(self, contract: Any, metadata: dict[str, Any]) -> str:
        """
        Extract computation type from contract or metadata with fallback chain.

        Uses a priority-based extraction strategy to find the computation type
        from various locations in the contract structure, supporting both
        algorithm-based contracts and metadata-based configurations.

        Priority order:
            1. contract.algorithm.algorithm_type (preferred for ModelContractCompute)
            2. metadata["computation_type"] (for legacy or custom contracts)
            3. contract.computation_type (direct attribute, if exists)
            4. Default: "default" (identity transformation)

        Args:
            contract: The compute contract. Expected to be ModelContractCompute
                or compatible object with optional algorithm and computation_type
                attributes.
            metadata: Extracted metadata dictionary, may contain "computation_type"
                key as an alternative source.

        Returns:
            str: The computation type identifier to use for looking up the
                registered computation function. Returns "default" if no
                computation type is found in any source.

        Example:
            >>> # Contract with algorithm configuration (preferred)
            >>> contract.algorithm.algorithm_type = "sum_numbers"
            >>> _extract_computation_type(contract, {})  # Returns "sum_numbers"

            >>> # Contract with metadata-based type
            >>> _extract_computation_type(contract, {"computation_type": "custom"})
            "custom"  # Only if algorithm.algorithm_type not set
        """
        # Check algorithm configuration first (preferred for ModelContractCompute)
        contract_algorithm = getattr(contract, "algorithm", None)
        if contract_algorithm is not None:
            algorithm_type = getattr(contract_algorithm, "algorithm_type", None)
            if algorithm_type is not None:
                return str(algorithm_type)

        # Check metadata next
        if "computation_type" in metadata:
            return str(metadata["computation_type"])

        # Check contract attribute
        contract_computation_type = getattr(contract, "computation_type", None)
        if contract_computation_type is not None:
            return str(contract_computation_type)

        return "default"

    def _contract_to_input(self, contract: Any) -> ModelComputeInput[Any]:
        """
        Convert ModelContractCompute to ModelComputeInput for processing.

        This method extracts computation parameters from a validated contract
        and constructs a ModelComputeInput instance suitable for the process()
        method. It enforces that input data is present and logs warnings for
        missing optional fields.

        Args:
            contract: The compute contract to convert. Must be a validated
                ModelContractCompute instance with:
                - input_state (required): Dict containing input data for computation
                - metadata (optional): Dict with computation settings
                - algorithm (optional): Algorithm configuration with computation_type

        Returns:
            ModelComputeInput[Any]: Input model configured with:
                - data: The input data from contract.input_state
                - computation_type: Type of computation to perform
                - cache_enabled: Whether to use caching (default: True)
                - parallel_enabled: Whether to enable parallel processing (default: False)
                - metadata: Additional metadata from contract

        Raises:
            ModelOnexError: If contract.input_state is missing or None, indicating
                a contract configuration error. Error code: VALIDATION_ERROR

        Example:
            Converting a contract for ``sum_numbers`` computation::

                >>> from omnibase_core.models.contracts import ModelContractCompute
                >>> from omnibase_core.models.contracts import ModelContractAlgorithm
                >>> contract = ModelContractCompute(
                ...     name="sum_values",
                ...     version="1.0.0",
                ...     input_state=[1.0, 2.0, 3.0],  # Direct list - sum_numbers expects list[float]
                ...     algorithm=ModelContractAlgorithm(algorithm_type="sum_numbers"),
                ... )
                >>> compute_input = node._contract_to_input(contract)
                >>> # compute_input.data == [1.0, 2.0, 3.0]
                >>> # compute_input.computation_type == "sum_numbers"

            Converting a contract for ``string_uppercase`` computation::

                >>> contract = ModelContractCompute(
                ...     name="uppercase",
                ...     version="1.0.0",
                ...     input_state="hello",  # Direct string - string_uppercase expects str
                ...     algorithm=ModelContractAlgorithm(algorithm_type="string_uppercase"),
                ... )
                >>> compute_input = node._contract_to_input(contract)
                >>> # compute_input.data == "hello"
                >>> # compute_input.computation_type == "string_uppercase"

        Note:
            This method expects execute_compute() to have already validated
            that contract is a ModelContractCompute instance. Direct calls
            should ensure proper contract type validation.
        """
        # Cache contract attributes to avoid redundant getattr calls
        contract_input_state = getattr(contract, "input_state", None)
        contract_input_data = getattr(contract, "input_data", None)
        contract_metadata = getattr(contract, "metadata", None)

        # Extract input_state from contract - this is the primary input data field
        # for ModelContractCompute (not input_data which is used in simpler contracts)
        input_data: Any = contract_input_state

        # Validate that input_state is present - it's required for computation
        if input_data is None:
            # Check for legacy input_data attribute as fallback
            input_data = contract_input_data

            if input_data is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Contract must have 'input_state' or 'input_data' attribute with computation input",
                    context={
                        "node_id": str(self.node_id),
                        "contract_type": type(contract).__name__,
                        "checked_attributes": ["input_state", "input_data"],
                        "input_state_value": "None",
                        "input_data_value": "None",
                        "hint": "Ensure contract.input_state contains the data to be processed",
                    },
                )

            # Log warning for legacy input_data usage
            emit_log_event(
                LogLevel.WARNING,
                "Contract uses legacy 'input_data' instead of 'input_state'",
                {
                    "node_id": str(self.node_id),
                    "contract_type": type(contract).__name__,
                    "recommendation": "Migrate to using 'input_state' field",
                },
            )

        # Extract metadata from contract (optional field)
        # Use empty dict as default for falsy values (None, empty dict)
        metadata: dict[str, Any] = contract_metadata or {}

        # Extract computation_type using helper method
        computation_type = self._extract_computation_type(contract, metadata)

        # Extract cache and parallel settings from metadata or use defaults
        cache_enabled: bool = bool(metadata.get("cache_enabled", True))
        parallel_enabled: bool = bool(metadata.get("parallel_enabled", False))

        return ModelComputeInput(
            data=input_data,
            computation_type=computation_type,
            cache_enabled=cache_enabled,
            parallel_enabled=parallel_enabled,
            metadata=metadata,
        )

    async def process(
        self, input_data: ModelComputeInput[T_Input]
    ) -> ModelComputeOutput[T_Output]:
        """
        Execute pure computation with caching and parallel processing support.

        STABLE INTERFACE: This method signature is frozen for code generation.
        Subclasses should override this method to implement custom computation logic.

        This is the primary entry point for direct computation without contract
        validation. It handles:
        - Cache lookup and storage (when cache_enabled=True)
        - Parallel execution (when parallel_enabled=True and data is parallelizable)
        - Performance monitoring and threshold warnings
        - Metrics tracking for observability

        Args:
            input_data: Strongly typed computation input containing:
                - data (T_Input): The input data to process
                - computation_type (str): Registered computation type to execute
                - cache_enabled (bool): Whether to use caching (default: True)
                - parallel_enabled (bool): Whether to use parallel execution (default: False)
                - operation_id (UUID): Unique identifier for this operation
                - metadata (dict): Optional additional metadata

        Returns:
            ModelComputeOutput[T_Output]: Computation results containing:
                - result (T_Output): The computed output value
                - operation_id (UUID): Echoed from input for correlation
                - computation_type (str): The computation type that was executed
                - processing_time_ms (float): Time taken in milliseconds
                - cache_hit (bool): True if result was retrieved from cache
                - parallel_execution_used (bool): True if parallel processing was used
                - metadata (dict): Additional output metadata

        Raises:
            ModelOnexError: If computation fails. Error codes:
                - VALIDATION_ERROR: Invalid input data structure
                - OPERATION_FAILED: Computation execution failure or unknown computation type

        Example:
            Direct usage with ModelComputeInput::

                >>> from omnibase_core.models.compute import ModelComputeInput
                >>> input_data = ModelComputeInput(
                ...     data=[1.0, 2.0, 3.0, 4.0],
                ...     computation_type="sum_numbers",
                ...     cache_enabled=True,
                ...     parallel_enabled=False,
                ... )
                >>> result = await node.process(input_data)
                >>> print(result.result)  # 10.0
                >>> print(result.cache_hit)  # False (first call)

            Subsequent call with same input (cache hit)::

                >>> result2 = await node.process(input_data)
                >>> print(result2.cache_hit)  # True

        Note:
            For contract-based execution with validation, use execute_compute() instead.
            Performance warnings are logged when processing_time_ms exceeds
            performance_threshold_ms (default: 100ms).
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
            supports_parallel = self._supports_parallel_execution(input_data)
            if input_data.parallel_enabled and supports_parallel:
                result = await self._execute_parallel_computation(input_data)
                parallel_used = True
            else:
                # Warn if parallel was requested but data is not parallelizable
                if input_data.parallel_enabled and not supports_parallel:
                    data_type = type(input_data.data).__name__
                    data_length = (
                        len(input_data.data)
                        if isinstance(input_data.data, (list, tuple))
                        else "N/A"
                    )
                    emit_log_event(
                        LogLevel.WARNING,
                        "Parallel execution requested but data is not parallelizable. "
                        "Falling back to sequential execution. "
                        "Parallel requires list/tuple with >1 element.",
                        {
                            "node_id": str(self.node_id),
                            "operation_id": str(input_data.operation_id),
                            "computation_type": input_data.computation_type,
                            "data_type": data_type,
                            "data_length": str(data_length),
                            "recommendation": "Set parallel_enabled=False for non-batch data, "
                            "or provide a list/tuple with multiple elements",
                        },
                    )
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

            # Preserve original exception context for debugging
            # Include error_type to distinguish validation vs runtime errors
            # Include cache_enabled and parallel_enabled for configuration debugging
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Computation failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                    "computation_type": input_data.computation_type,
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time,
                    "cache_enabled": input_data.cache_enabled,
                    "parallel_enabled": input_data.parallel_enabled,
                },
            ) from e

    def register_computation(
        self, computation_type: str, computation_func: Callable[..., Any]
    ) -> None:
        """
        Register a custom computation function for use with this node.

        Registered computations can be invoked via process() or execute_compute()
        by specifying the computation_type. Functions should be pure (no side effects)
        for deterministic behavior and safe caching.

        Args:
            computation_type: Unique string identifier for the computation.
                Used to look up the function during execution.
                Example: "calculate_average", "transform_json", "validate_schema"
            computation_func: Pure function to register. Must be callable and accept
                the input data as its first argument. The function signature should
                match the expected T_Input type for this node.
                Example: ``def my_func(data: list[float]) -> float``

        Raises:
            ModelOnexError: If validation fails. Error codes:
                - VALIDATION_ERROR: computation_type already registered or
                  computation_func is not callable

        Example:
            Registering a custom average computation::

                >>> def calculate_average(data: list[float]) -> float:
                ...     if not data:
                ...         return 0.0
                ...     return sum(data) / len(data)
                >>> node.register_computation("calculate_average", calculate_average)

            Using the registered computation::

                >>> input_data = ModelComputeInput(
                ...     data=[10.0, 20.0, 30.0],
                ...     computation_type="calculate_average",
                ... )
                >>> result = await node.process(input_data)
                >>> print(result.result)  # 20.0

        Note:
            Built-in computations ("default", "string_uppercase", "sum_numbers")
            are registered automatically during node initialization.
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
        Get detailed computation performance metrics for monitoring and observability.

        Aggregates metrics from multiple sources including computation execution
        statistics, cache performance, and parallel processing utilization.

        Returns:
            dict[str, dict[str, float]]: Nested metrics dictionary containing:
                - Per-computation-type metrics (keyed by computation_type):
                    - total_executions: Number of times this computation ran
                    - avg_processing_time_ms: Average execution time
                    - success_rate: Ratio of successful executions
                - "cache_performance": Cache statistics
                    - total_entries: Total entries in cache
                    - valid_entries: Non-expired entries
                    - cache_utilization: valid_entries / max_size ratio
                    - ttl_minutes: Cache time-to-live setting
                - "parallel_processing": Thread pool status
                    - max_workers: Maximum parallel workers configured
                    - thread_pool_active: 1.0 if pool is active, 0.0 otherwise

        Example:
            >>> metrics = await node.get_computation_metrics()
            >>> print(metrics["cache_performance"]["cache_utilization"])
            0.75
            >>> print(metrics["sum_numbers"]["avg_processing_time_ms"])
            2.5

        Note:
            Metrics are cumulative for the lifetime of the node instance.
            Call this periodically for monitoring or after specific operations
            for performance analysis.
        """
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
        """
        Generate a deterministic cache key for computation input.

        This method creates a unique, reproducible cache key by combining the
        computation type with a SHA256 hash of the input data. The resulting key
        is used to store and retrieve cached computation results.

        **Cache Key Generation Strategy**:

        The cache key is generated using a content-addressable approach:

        1. **Input Serialization**: The input data is converted to its string
           representation using Python's ``str()`` function. This creates a
           canonical text form of the data that can be hashed.

        2. **SHA256 Hashing**: The string representation is encoded to UTF-8 bytes
           and hashed using SHA256. SHA256 was chosen for several reasons:

           - **Determinism**: Unlike Python's built-in ``hash()`` function, which
             uses randomized salting (PYTHONHASHSEED) and produces different values
             across interpreter sessions, SHA256 always produces the same output
             for the same input, ensuring cache consistency across process restarts.

           - **Collision Resistance**: SHA256's 256-bit output space (2^256 possible
             values) makes hash collisions astronomically unlikely. This prevents
             incorrect cache hits where different inputs might map to the same key.

           - **Cross-Process Consistency**: The same input will produce the same
             cache key regardless of which Python process or machine generates it,
             enabling distributed caching scenarios if needed in the future.

        3. **Key Composition**: The final key combines the computation type and hash
           in the format ``{computation_type}:{sha256_hex_digest}``. Including the
           computation type ensures that identical data processed by different
           computation functions will have distinct cache keys.

        **Key Format**::

            {computation_type}:{64_character_hex_digest}

        **Examples**::

            "sum_numbers:a3b4c5d6e7f8...9a0b"  (64 hex chars after colon)
            "string_uppercase:1234abcd5678..."

        **Cache Key Implications**:

        - **Cache Hits**: When the same input data and computation type are
          processed again, the identical cache key will be generated, allowing
          retrieval of the previously computed result.

        - **Cache Misses**: Any change to the input data (even whitespace) or
          computation type will produce a different hash, resulting in a cache miss.

        - **String Serialization Caveat**: Complex objects should implement
          consistent ``__str__`` methods to ensure deterministic serialization.
          Objects with non-deterministic string representations (e.g., including
          memory addresses or timestamps) will not cache effectively.

        Args:
            input_data: The computation input containing:
                - ``data``: The input data to be hashed (any type with ``__str__``)
                - ``computation_type``: The type of computation to be performed

        Returns:
            str: A cache key in the format ``{computation_type}:{sha256_hex_digest}``
                where the hex digest is a 64-character lowercase hexadecimal string.

        Example:
            >>> input_data = ModelComputeInput(
            ...     data=[1.0, 2.0, 3.0],
            ...     computation_type="sum_numbers",
            ... )
            >>> key = node._generate_cache_key(input_data)
            >>> print(key)
            "sum_numbers:7c9e1d8a3f2b..."  # 64 hex chars after colon

            >>> # Same input produces same key (deterministic)
            >>> key2 = node._generate_cache_key(input_data)
            >>> assert key == key2

            >>> # Different input produces different key
            >>> different_input = ModelComputeInput(
            ...     data=[1.0, 2.0, 4.0],  # Changed value
            ...     computation_type="sum_numbers",
            ... )
            >>> different_key = node._generate_cache_key(different_input)
            >>> assert key != different_key

        Note:
            - This is a private method called internally by ``process()``
            - The cache key is used with ``ModelComputeCache.get()`` and ``put()``
            - See the class-level "Caching Strategy" documentation for full details
              on cache invalidation policies and configuration options
        """
        data_str = str(input_data.data)
        # Use hashlib for deterministic hashing across Python processes
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return f"{input_data.computation_type}:{data_hash}"

    def _supports_parallel_execution(self, input_data: ModelComputeInput[Any]) -> bool:
        """
        Check if computation input data supports parallel execution.

        Determines whether the input data structure is suitable for parallel
        processing based on its type and size. Parallel execution is only
        beneficial when data can be partitioned into independent chunks.

        Parallelizable Data Requirements:
            - Must be a ``list`` or ``tuple`` (iterable with known length)
            - Must contain more than 1 element (otherwise no parallelism benefit)
            - Elements should be independently processable (no inter-element dependencies)

        Computation Types That Benefit from Parallelization:
            - **Batch transformations**: Processing lists of records, documents, or objects
              where each item can be transformed independently
            - **Map operations**: Applying the same function to each element
              (e.g., converting a list of strings to uppercase)
            - **Aggregations over large datasets**: Operations like sum, average,
              or statistical computations that can be partitioned and merged
            - **Independent validations**: Validating each item in a batch independently

        Computation Types That Do NOT Benefit:
            - **Single-value operations**: Strings, numbers, single objects - no partitioning possible
            - **Small datasets**: Lists with 0-1 elements have no parallel work to distribute
            - **Sequential dependencies**: Operations where item N depends on item N-1
            - **Fold/reduce with order**: Sequential reductions where order matters

        Performance Implications:
            - Parallel execution adds ~1-5ms overhead for thread pool dispatch
            - Only beneficial when per-item computation exceeds ~10ms
            - Thread pool workers (default: 4) are reused across calls
            - For small lists (2-10 items), overhead may exceed benefit
            - Large datasets (100+ items) with CPU-bound operations see best gains

        Args:
            input_data: The computation input containing the data to check.
                The ``data`` attribute is examined for type and length.

        Returns:
            bool: True if data is a list/tuple with more than 1 element,
                False otherwise. When False, the process() method will
                use sequential execution instead.

        Example:
            >>> # Parallelizable - list with multiple elements
            >>> input_data = ModelComputeInput(data=[1, 2, 3, 4, 5], ...)
            >>> node._supports_parallel_execution(input_data)
            True

            >>> # NOT parallelizable - single string value
            >>> input_data = ModelComputeInput(data="hello", ...)
            >>> node._supports_parallel_execution(input_data)
            False

            >>> # NOT parallelizable - list with only 1 element
            >>> input_data = ModelComputeInput(data=[42], ...)
            >>> node._supports_parallel_execution(input_data)
            False

            >>> # NOT parallelizable - empty list
            >>> input_data = ModelComputeInput(data=[], ...)
            >>> node._supports_parallel_execution(input_data)
            False

        Note:
            When ``parallel_enabled=True`` but this method returns False,
            a WARNING log is emitted in ``process()`` to alert developers
            that parallel execution was requested but could not be used.
            The computation will fall back to sequential execution automatically.
        """
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
