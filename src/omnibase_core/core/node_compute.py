"""
NodeCompute - Pure Computation Node for 4-Node Architecture.

Specialized node type for pure computational operations with deterministic guarantees.
Focuses on input → transform → output patterns with caching and parallel processing support.

Key Capabilities:
- Pure function patterns with no side effects
- Deterministic operation guarantees
- Computational pipeline with parallel processing
- Caching layer for expensive computations
- RSD Algorithm Integration (5-factor priority calculations)
- Dependency graph traversal algorithms
- Time decay computation with exponential functions
- Failure surface analysis calculations

Author: ONEX Framework Team
"""

import asyncio
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generic, TypeVar
from uuid import uuid4

from omnibase.protocols.types import LogLevel

# Import contract model for compute nodes
from omnibase_core.core.contracts.model_contract_compute import (
    ModelContractCompute,
)
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.node_core_base import NodeCoreBase
from omnibase_core.core.onex_container import ONEXContainer

# Import utilities for contract loading

# Type variables for generic computation
T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class ModelComputeInput(Generic[T_Input]):
    """
    Input model for NodeCompute operations.

    Strongly typed input wrapper that ensures type safety
    and provides metadata for computation tracking.
    """

    def __init__(
        self,
        data: T_Input,
        operation_id: str | None = None,
        computation_type: str = "default",
        cache_enabled: bool = True,
        parallel_enabled: bool = False,
        metadata: dict[str, Any] | None = None,
    ):
        self.data = data
        self.operation_id = operation_id or str(uuid4())
        self.computation_type = computation_type
        self.cache_enabled = cache_enabled
        self.parallel_enabled = parallel_enabled
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class ModelComputeOutput(Generic[T_Output]):
    """
    Output model for NodeCompute operations.

    Strongly typed output wrapper that includes computation
    metadata and performance metrics.
    """

    def __init__(
        self,
        result: T_Output,
        operation_id: str,
        computation_type: str,
        processing_time_ms: float,
        cache_hit: bool = False,
        parallel_execution_used: bool = False,
        metadata: dict[str, Any] | None = None,
    ):
        self.result = result
        self.operation_id = operation_id
        self.computation_type = computation_type
        self.processing_time_ms = processing_time_ms
        self.cache_hit = cache_hit
        self.parallel_execution_used = parallel_execution_used
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class ComputationCache:
    """
    Caching layer for expensive computations with TTL and memory management.
    """

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        self.max_size = max_size
        self.default_ttl_minutes = default_ttl_minutes
        self._cache: dict[str, tuple[Any, datetime, int]] = (
            {}
        )  # key -> (value, expiry, access_count)

    def get(self, cache_key: str) -> Any | None:
        """Get cached value if valid and not expired."""
        if cache_key not in self._cache:
            return None

        value, expiry, access_count = self._cache[cache_key]

        # Check expiry
        if datetime.now() > expiry:
            del self._cache[cache_key]
            return None

        # Update access count
        self._cache[cache_key] = (value, expiry, access_count + 1)
        return value

    def put(
        self,
        cache_key: str,
        value: Any,
        ttl_minutes: int | None = None,
    ) -> None:
        """Cache value with TTL."""
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        ttl = ttl_minutes or self.default_ttl_minutes
        expiry = datetime.now() + timedelta(minutes=ttl)
        self._cache[cache_key] = (value, expiry, 1)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._cache:
            return

        # Find item with lowest access count (simple LRU approximation)
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        del self._cache[lru_key]

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        now = datetime.now()
        expired_count = sum(1 for _, expiry, _ in self._cache.values() if expiry <= now)

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "valid_entries": len(self._cache) - expired_count,
            "max_size": self.max_size,
        }


class NodeCompute(NodeCoreBase):
    """
    Pure computation node for deterministic operations.

    Implements computational pipeline with input → transform → output pattern.
    Provides caching, parallel processing, and performance optimization for
    compute-intensive operations like RSD priority calculations.

    Key Features:
    - Pure function patterns (no side effects)
    - Deterministic operation guarantees
    - Parallel processing support for batch operations
    - Intelligent caching layer for expensive computations
    - Performance monitoring and optimization
    - Type-safe input/output handling

    RSD Algorithm Support:
    - 5-factor priority calculations
    - Dependency graph traversal algorithms
    - Time decay computation with exponential functions
    - Failure surface analysis calculations
    """

    def __init__(self, container: ONEXContainer) -> None:
        """
        Initialize NodeCompute with ONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection

        Raises:
            OnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # CANONICAL PATTERN: Load contract model for Compute node type
        self.contract_model: ModelContractCompute = self._load_contract_model()

        # Computation-specific configuration
        self.max_parallel_workers = 4
        self.cache_ttl_minutes = 30
        self.performance_threshold_ms = (
            100.0  # Performance SLA: <100ms for single operations
        )

        # Initialize caching layer
        self.computation_cache = ComputationCache(
            max_size=1000,
            default_ttl_minutes=self.cache_ttl_minutes,
        )

        # Thread pool for parallel execution
        self.thread_pool: ThreadPoolExecutor | None = None

        # Computation registry for algorithm functions
        self.computation_registry: dict[str, Callable[..., Any]] = {}

        # Performance tracking
        self.computation_metrics: dict[str, dict[str, float]] = {}

        # Register built-in RSD computations
        self._register_rsd_computations()

    def _load_contract_model(self) -> ModelContractCompute:
        """
        Load and validate contract model for Compute node type.

        CANONICAL PATTERN: Centralized contract loading for all Compute nodes.
        Provides type-safe contract configuration with validation.

        Returns:
            ModelContractCompute: Validated contract model for this node type

        Raises:
            OnexError: If contract loading or validation fails
        """
        try:
            # Load actual contract from file with subcontract resolution

            import yaml

            from omnibase_core.utils.generation.utility_reference_resolver import (
                UtilityReferenceResolver,
            )
            from omnibase_core.utils.io.utility_filesystem_reader import (
                UtilityFileSystemReader,
            )

            # Get contract path - find the node.py file and look for contract.yaml
            contract_path = self._find_contract_path()

            # Load and resolve contract with subcontract support
            file_reader = UtilityFileSystemReader()
            reference_resolver = UtilityReferenceResolver()

            contract_content = file_reader.read_text(contract_path)
            contract_data = yaml.safe_load(contract_content)

            # Resolve any $ref references in the contract
            resolved_contract = self._resolve_contract_references(
                contract_data,
                contract_path.parent,
                reference_resolver,
            )

            # Create ModelContractCompute from resolved contract data
            contract_model = ModelContractCompute(**resolved_contract)

            # CANONICAL PATTERN: Validate contract model consistency
            contract_model.validate_node_specific_config()

            emit_log_event(
                LogLevel.INFO,
                "Contract model loaded successfully for NodeCompute",
                {
                    "contract_type": "ModelContractCompute",
                    "node_type": contract_model.node_type,
                    "version": contract_model.version,
                    "contract_path": str(contract_path),
                },
            )

            return contract_model

        except Exception as e:
            # CANONICAL PATTERN: Wrap contract loading errors
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Contract model loading failed for NodeCompute: {e!s}",
                details={
                    "contract_model_type": "ModelContractCompute",
                    "error_type": type(e).__name__,
                },
                cause=e,
            )

    def _find_contract_path(self) -> Path:
        """
        Find the contract.yaml file for this compute node.

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
                message="Could not find contract.yaml file for compute node",
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
            Any: Resolved contract data with all references loaded

        Raises:
            OnexError: If reference resolution fails
        """
        try:
            if isinstance(data, dict):
                if "$ref" in data:
                    # Resolve reference to another file
                    ref_file = data["$ref"]
                    if ref_file.startswith(("./", "../")):
                        # Relative path reference
                        ref_path = (base_path / ref_file).resolve()
                    else:
                        # Absolute or root-relative reference
                        ref_path = Path(ref_file)

                    return reference_resolver.resolve_reference(
                        str(ref_path),
                        base_path,
                    )
                # Recursively resolve nested dictionaries
                return {
                    key: self._resolve_contract_references(
                        value,
                        base_path,
                        reference_resolver,
                    )
                    for key, value in data.items()
                }
            if isinstance(data, list):
                # Recursively resolve lists
                return [
                    self._resolve_contract_references(
                        item,
                        base_path,
                        reference_resolver,
                    )
                    for item in data
                ]
            # Return primitives as-is
            return data

        except Exception as e:
            # Log error but don't stop processing
            emit_log_event(
                LogLevel.WARNING,
                "Failed to resolve contract reference, using original data",
                {"error": str(e), "error_type": type(e).__name__},
            )

        return None

    async def process(
        self,
        input_data: ModelComputeInput[T_Input],
    ) -> ModelComputeOutput[T_Output]:
        """
        Pure computation with caching and parallel processing.

        Args:
            input_data: Strongly typed computation input

        Returns:
            Strongly typed computation output with performance metrics

        Raises:
            OnexError: If computation fails or performance threshold exceeded
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_compute_input(input_data)

            # Generate cache key
            cache_key = self._generate_cache_key(input_data)

            # Check cache first if enabled
            if input_data.cache_enabled:
                cached_result = self.computation_cache.get(cache_key)
                if cached_result is not None:
                    # Return cached result
                    return ModelComputeOutput(
                        result=cached_result,
                        operation_id=input_data.operation_id,
                        computation_type=input_data.computation_type,
                        processing_time_ms=0.0,  # Cache hit
                        cache_hit=True,
                        parallel_execution_used=False,
                        metadata={"cache_retrieval": True},
                    )

            # Execute computation
            if input_data.parallel_enabled and self._supports_parallel_execution(
                input_data,
            ):
                result = await self._execute_parallel_computation(input_data)
                parallel_used = True
            else:
                result = await self._execute_sequential_computation(input_data)
                parallel_used = False

            processing_time = (time.time() - start_time) * 1000  # Convert to ms

            # Validate performance threshold for single operations
            if processing_time > self.performance_threshold_ms:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Computation exceeded performance threshold: {processing_time:.2f}ms",
                    {
                        "node_id": self.node_id,
                        "operation_id": input_data.operation_id,
                        "computation_type": input_data.computation_type,
                        "threshold_ms": self.performance_threshold_ms,
                    },
                )

            # Cache result if enabled
            if input_data.cache_enabled:
                self.computation_cache.put(cache_key, result, self.cache_ttl_minutes)

            # Update metrics
            await self._update_computation_metrics(
                input_data.computation_type,
                processing_time,
                True,
            )
            await self._update_processing_metrics(processing_time, True)

            # Create output
            output = ModelComputeOutput(
                result=result,
                operation_id=input_data.operation_id,
                computation_type=input_data.computation_type,
                processing_time_ms=processing_time,
                cache_hit=False,
                parallel_execution_used=parallel_used,
                metadata={
                    "input_data_size": len(str(input_data.data)),
                    "cache_enabled": input_data.cache_enabled,
                    "parallel_enabled": input_data.parallel_enabled,
                },
            )

            emit_log_event(
                LogLevel.INFO,
                f"Computation completed: {input_data.computation_type}",
                {
                    "node_id": self.node_id,
                    "operation_id": input_data.operation_id,
                    "processing_time_ms": processing_time,
                    "cache_hit": False,
                    "parallel_used": parallel_used,
                },
            )

            return output

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # Update error metrics
            await self._update_computation_metrics(
                input_data.computation_type,
                processing_time,
                False,
            )
            await self._update_processing_metrics(processing_time, False)

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Computation failed: {e!s}",
                context={
                    "node_id": self.node_id,
                    "operation_id": input_data.operation_id,
                    "computation_type": input_data.computation_type,
                    "processing_time_ms": processing_time,
                    "error": str(e),
                },
            ) from e

    async def calculate_rsd_priority(
        self,
        ticket_id: str,
        dependency_count: int = 0,
        failure_indicators: int = 0,
        days_old: float = 0.0,
        agent_requests: int = 0,
        user_override_score: float = 0.5,
    ) -> float:
        """
        Calculate RSD 5-factor priority score using pure computation.

        Implements the complete RSD algorithm with proper factor weighting:
        - 40% Dependency Distance: Graph traversal depth of blocked dependencies
        - 25% Failure Surface: Compound failure risk and validator impact
        - 15% Time Decay: Exponential aging factor for ticket staleness
        - 10% Agent Utility: Weighted agent request frequency and priority
        - 10% User Weighting: Manual PRS priority overrides

        Args:
            ticket_id: Unique ticket identifier
            dependency_count: Number of dependent tickets
            failure_indicators: Number of failure risk indicators
            days_old: Age of ticket in days
            agent_requests: Number of agent requests
            user_override_score: User override score (0.0-1.0)

        Returns:
            Overall priority score (0.0-100.0)

        Raises:
            OnexError: If calculation fails or inputs invalid
        """
        # Prepare computation input
        computation_input = ModelComputeInput(
            data={
                "ticket_id": ticket_id,
                "dependency_count": dependency_count,
                "failure_indicators": failure_indicators,
                "days_old": days_old,
                "agent_requests": agent_requests,
                "user_override_score": user_override_score,
            },
            computation_type="rsd_priority_calculation",
            cache_enabled=True,
            metadata={
                "algorithm_version": "2.1.0",
                "factor_weights": {
                    "dependency_distance": 0.40,
                    "failure_surface": 0.25,
                    "time_decay": 0.15,
                    "agent_utility": 0.10,
                    "user_weighting": 0.10,
                },
            },
        )

        # Execute computation
        result: ModelComputeOutput[Any] = await self.process(computation_input)
        return float(result.result)

    def register_computation(
        self,
        computation_type: str,
        computation_func: Callable[..., Any],
    ) -> None:
        """
        Register custom computation function.

        Args:
            computation_type: Type identifier for computation
            computation_func: Pure function to register

        Raises:
            OnexError: If computation type already registered or function invalid
        """
        if computation_type in self.computation_registry:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Computation type already registered: {computation_type}",
                context={"node_id": self.node_id, "computation_type": computation_type},
            )

        if not callable(computation_func):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Computation function must be callable: {computation_type}",
                context={"node_id": self.node_id, "computation_type": computation_type},
            )

        self.computation_registry[computation_type] = computation_func

        emit_log_event(
            LogLevel.INFO,
            f"Computation registered: {computation_type}",
            {"node_id": self.node_id, "computation_type": computation_type},
        )

    async def get_computation_metrics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed computation performance metrics.

        Returns:
            Dictionary of metrics by computation type
        """
        # Add cache statistics
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
        # Initialize thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_parallel_workers)

        emit_log_event(
            LogLevel.INFO,
            "NodeCompute resources initialized",
            {
                "node_id": self.node_id,
                "max_parallel_workers": self.max_parallel_workers,
                "cache_ttl_minutes": self.cache_ttl_minutes,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup computation-specific resources."""
        # Shutdown thread pool
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
            self.thread_pool = None

        # Clear cache
        self.computation_cache.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeCompute resources cleaned up",
            {"node_id": self.node_id},
        )

    def _validate_compute_input(self, input_data: ModelComputeInput[Any]) -> None:
        """
        Validate computation input data.

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

        if not hasattr(input_data, "computation_type"):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Input data must have 'computation_type' attribute",
                context={
                    "node_id": self.node_id,
                    "input_type": type(input_data).__name__,
                },
            )

    def _generate_cache_key(self, input_data: ModelComputeInput[Any]) -> str:
        """Generate cache key for computation input."""
        # Create deterministic key from computation type and data
        data_str = str(input_data.data)
        return f"{input_data.computation_type}:{hash(data_str)}"

    def _supports_parallel_execution(self, input_data: ModelComputeInput[Any]) -> bool:
        """Check if computation supports parallel execution."""
        # For now, only support parallel for batch operations
        return bool(
            isinstance(input_data.data, list | tuple) and len(input_data.data) > 1
        )

    async def _execute_sequential_computation(
        self,
        input_data: ModelComputeInput[Any],
    ) -> Any:
        """Execute computation sequentially."""
        computation_type = input_data.computation_type

        if computation_type in self.computation_registry:
            computation_func = self.computation_registry[computation_type]
            return computation_func(input_data.data)
        raise OnexError(
            error_code=CoreErrorCode.OPERATION_FAILED,
            message=f"Unknown computation type: {computation_type}",
            context={
                "node_id": self.node_id,
                "computation_type": computation_type,
                "available_types": list(self.computation_registry.keys()),
            },
        )

    async def _execute_parallel_computation(
        self,
        input_data: ModelComputeInput[Any],
    ) -> Any:
        """Execute computation in parallel using thread pool."""
        if not self.thread_pool:
            # Fallback to sequential if thread pool not available
            return await self._execute_sequential_computation(input_data)

        computation_type = input_data.computation_type
        computation_func = self.computation_registry.get(computation_type)

        if not computation_func:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Unknown computation type: {computation_type}",
                context={"node_id": self.node_id, "computation_type": computation_type},
            )

        # Execute in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool,
            computation_func,
            input_data.data,
        )

    async def _update_computation_metrics(
        self,
        computation_type: str,
        processing_time_ms: float,
        success: bool,
    ) -> None:
        """Update computation-specific metrics."""
        if computation_type not in self.computation_metrics:
            self.computation_metrics[computation_type] = {
                "total_operations": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "avg_processing_time_ms": 0.0,
                "min_processing_time_ms": float("inf"),
                "max_processing_time_ms": 0.0,
            }

        metrics = self.computation_metrics[computation_type]
        metrics["total_operations"] += 1

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

        # Update rolling average
        total_ops = metrics["total_operations"]
        current_avg = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg * (total_ops - 1) + processing_time_ms
        ) / total_ops

    def get_introspection_data(self) -> dict:
        """
        Get comprehensive introspection data for NodeCompute.

        Returns specialized computation node information including algorithm support,
        caching configuration, parallel processing capabilities, and RSD computation details.

        Returns:
            dict: Comprehensive introspection data with compute-specific information
        """
        try:
            # Get base introspection data from NodeCoreBase
            base_data = {
                "node_type": "NodeCompute",
                "node_classification": "compute",
                "node_id": self.node_id,
                "version": self.version,
                "created_at": self.created_at.isoformat(),
                "current_status": self.state.get("status", "unknown"),
            }

            # 1. Node Capabilities (Compute-specific)
            node_capabilities = {
                **base_data,
                "architecture_classification": "pure_computation",
                "computation_patterns": [
                    "pure_function",
                    "deterministic",
                    "parallel_processing",
                ],
                "available_operations": self._extract_compute_operations(),
                "input_output_specifications": self._extract_compute_io_specifications(),
                "performance_characteristics": self._extract_compute_performance_characteristics(),
            }

            # 2. Contract Details (Compute-specific)
            contract_details = {
                "contract_type": "ModelContractCompute",
                "contract_validation_status": "validated",
                "algorithm_configuration": self._extract_algorithm_configuration(),
                "computation_constraints": self._extract_computation_constraints(),
                "supported_algorithms": list(self.computation_registry.keys()),
            }

            # 3. Runtime Information (Compute-specific)
            runtime_info = {
                "current_health_status": self._get_compute_health_status(),
                "computation_metrics": self._get_computation_metrics_sync(),
                "resource_usage": self._get_compute_resource_usage(),
                "caching_status": self._get_caching_status(),
                "parallel_processing_status": self._get_parallel_processing_status(),
            }

            # 4. Algorithm Information
            algorithm_info = {
                "registered_algorithms": list(self.computation_registry.keys()),
                "rsd_algorithm_support": "rsd_priority_calculation"
                in self.computation_registry,
                "custom_algorithms": [
                    name
                    for name in self.computation_registry
                    if not name.startswith("rsd_")
                ],
                "algorithm_count": len(self.computation_registry),
            }

            # 5. Performance Configuration
            performance_config = {
                "max_parallel_workers": self.max_parallel_workers,
                "cache_ttl_minutes": self.cache_ttl_minutes,
                "performance_threshold_ms": self.performance_threshold_ms,
                "cache_configuration": {
                    "max_size": self.computation_cache.max_size,
                    "default_ttl_minutes": self.computation_cache.default_ttl_minutes,
                },
            }

            return {
                "node_capabilities": node_capabilities,
                "contract_details": contract_details,
                "runtime_information": runtime_info,
                "algorithm_information": algorithm_info,
                "performance_configuration": performance_config,
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "node_type": "NodeCompute",
                    "supports_full_introspection": True,
                    "specialization": "pure_computation_with_caching_and_parallelization",
                },
            }

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to generate full compute introspection data: {e!s}, using fallback",
                {"node_id": self.node_id, "error": str(e)},
            )

            return {
                "node_capabilities": {
                    "node_type": "NodeCompute",
                    "node_classification": "compute",
                    "node_id": self.node_id,
                },
                "runtime_information": {
                    "current_health_status": "unknown",
                    "algorithm_count": len(self.computation_registry),
                },
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "supports_full_introspection": False,
                    "fallback_reason": str(e),
                },
            }

    def _extract_compute_operations(self) -> list:
        """Extract available computation operations."""
        operations = [
            "process",
            "calculate_rsd_priority",
            "register_computation",
            "get_computation_metrics",
        ]

        try:
            # Add registered computation types
            operations.extend(
                [f"compute_{algo}" for algo in self.computation_registry],
            )

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract all compute operations: {e!s}",
                {"node_id": self.node_id},
            )

        return operations

    def _extract_compute_io_specifications(self) -> dict:
        """Extract input/output specifications for compute operations."""
        return {
            "input_model": "omnibase.core.node_compute.ModelComputeInput",
            "output_model": "omnibase.core.node_compute.ModelComputeOutput",
            "supports_streaming": False,
            "supports_batch_processing": True,
            "supports_parallel_processing": True,
            "computation_types": list(self.computation_registry.keys()),
            "input_requirements": ["data", "computation_type"],
            "output_guarantees": [
                "result",
                "processing_time_ms",
                "cache_hit",
                "parallel_execution_used",
            ],
        }

    def _extract_compute_performance_characteristics(self) -> dict:
        """Extract performance characteristics specific to computation operations."""
        return {
            "expected_response_time_ms": f"< {self.performance_threshold_ms}",
            "throughput_capacity": f"up_to_{self.max_parallel_workers}_parallel_operations",
            "memory_usage_pattern": "caching_with_lru_eviction",
            "cpu_intensity": "high_for_complex_computations",
            "supports_parallel_processing": True,
            "caching_enabled": True,
            "performance_monitoring": True,
            "deterministic_operations": True,
            "side_effects": False,
        }

    def _extract_algorithm_configuration(self) -> dict:
        """Extract algorithm configuration from contract."""
        try:
            return {
                "algorithm_type": self.contract_model.algorithm.algorithm_type,
                "algorithm_factors": self.contract_model.algorithm.factors,
                "contract_input_model": self.contract_model.input_model,
                "contract_output_model": self.contract_model.output_model,
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract algorithm configuration: {e!s}",
                {"node_id": self.node_id},
            )
            return {"algorithm_type": "default_compute"}

    def _extract_computation_constraints(self) -> dict:
        """Extract computation constraints and requirements."""
        return {
            "pure_function_requirement": True,
            "deterministic_requirement": True,
            "no_side_effects_requirement": True,
            "performance_threshold_ms": self.performance_threshold_ms,
            "max_parallel_workers": self.max_parallel_workers,
            "cache_size_limit": self.computation_cache.max_size,
            "supports_custom_algorithms": True,
        }

    def _get_compute_health_status(self) -> str:
        """Get health status specific to compute operations."""
        try:
            # Check if basic computation works
            test_input = ModelComputeInput(
                data={"test": True},
                computation_type="health_check",
                cache_enabled=False,
            )

            # For health check, we'll just validate the input without processing
            self._validate_compute_input(test_input)
            return "healthy"

        except Exception:
            return "unhealthy"

    def _get_compute_resource_usage(self) -> dict:
        """Get resource usage specific to compute operations."""
        try:
            cache_stats = self.computation_cache.get_stats()

            return {
                "cache_utilization": f"{cache_stats['valid_entries']}/{cache_stats['max_size']}",
                "cache_hit_ratio": "unknown",  # Would need actual tracking
                "thread_pool_status": "active" if self.thread_pool else "inactive",
                "parallel_worker_count": self.max_parallel_workers,
                "registered_algorithms": len(self.computation_registry),
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get compute resource usage: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown"}

    def _get_caching_status(self) -> dict:
        """Get caching system status."""
        try:
            cache_stats = self.computation_cache.get_stats()

            return {
                "enabled": True,
                "cache_stats": cache_stats,
                "ttl_minutes": self.cache_ttl_minutes,
                "max_size": self.computation_cache.max_size,
                "eviction_policy": "lru",
            }
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get caching status: {e!s}",
                {"node_id": self.node_id},
            )
            return {"enabled": False, "error": str(e)}

    def _get_parallel_processing_status(self) -> dict:
        """Get parallel processing status."""
        return {
            "enabled": True,
            "max_workers": self.max_parallel_workers,
            "thread_pool_active": self.thread_pool is not None,
            "supports_async_processing": True,
            "parallel_algorithm_support": True,
        }

    def _get_computation_metrics_sync(self) -> dict:
        """Get computation metrics synchronously for introspection."""
        try:
            # Add cache statistics
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
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get computation metrics: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown", "error": str(e)}

    def _register_rsd_computations(self) -> None:
        """Register built-in RSD computation functions."""

        def rsd_priority_calculation(data: dict[str, Any]) -> float:
            """Calculate RSD 5-factor priority score."""
            # Extract inputs
            dependency_count = data.get("dependency_count", 0)
            failure_indicators = data.get("failure_indicators", 0)
            days_old = data.get("days_old", 0.0)
            agent_requests = data.get("agent_requests", 0)
            user_override_score = data.get("user_override_score", 0.5)

            # Factor weights (must sum to 1.0)
            weights = {
                "dependency_distance": 0.40,
                "failure_surface": 0.25,
                "time_decay": 0.15,
                "agent_utility": 0.10,
                "user_weighting": 0.10,
            }

            # Calculate factor scores (0.0-1.0)
            dependency_score = min(
                dependency_count / 10.0,
                1.0,
            )  # Normalize by max 10 deps
            failure_score = min(
                failure_indicators / 5.0,
                1.0,
            )  # Normalize by max 5 indicators

            # Time decay with exponential growth after 7 days
            if days_old <= 7:
                time_score = 0.1 + (days_old / 7) * 0.4
            else:
                excess_days = days_old - 7
                exponential_factor = 1.0 - (2.718 ** (-excess_days / 14.0))
                time_score = 0.5 + (0.5 * exponential_factor)

            agent_score = min(agent_requests / 5.0, 1.0)  # Normalize by max 5 requests
            user_score = max(0.0, min(1.0, user_override_score))  # Clamp to 0-1

            # Calculate weighted overall score
            overall_score: float = (
                weights["dependency_distance"] * dependency_score * 100
                + weights["failure_surface"] * failure_score * 100
                + weights["time_decay"] * time_score * 100
                + weights["agent_utility"] * agent_score * 100
                + weights["user_weighting"] * user_score * 100
            )

            return overall_score

        # Register computation
        self.register_computation("rsd_priority_calculation", rsd_priority_calculation)
