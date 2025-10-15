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
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class ModelComputeInput(BaseModel, Generic[T_Input]):
    """
    Input model for NodeCompute operations.

    Strongly typed input wrapper that ensures type safety
    and provides metadata for computation tracking.
    """

    data: T_Input
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    computation_type: str = "default"
    cache_enabled: bool = True
    parallel_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelComputeOutput(BaseModel, Generic[T_Output]):
    """
    Output model for NodeCompute operations.

    Strongly typed output wrapper that includes computation
    metadata and performance metrics.
    """

    result: T_Output
    operation_id: str
    computation_type: str
    processing_time_ms: float
    cache_hit: bool = False
    parallel_execution_used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComputationCache:
    """Caching layer for expensive computations with TTL and memory management."""

    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 30):
        self.max_size = max_size
        self.default_ttl_minutes = default_ttl_minutes
        self._cache: dict[str, tuple[Any, datetime, int]] = {}

    def get(self, cache_key: str) -> Any | None:
        """Get cached value if valid and not expired."""
        if cache_key not in self._cache:
            return None

        value, expiry, access_count = self._cache[cache_key]

        if datetime.now() > expiry:
            del self._cache[cache_key]
            return None

        self._cache[cache_key] = (value, expiry, access_count + 1)
        return value

    def put(self, cache_key: str, value: Any, ttl_minutes: int | None = None) -> None:
        """Cache value with TTL."""
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        ttl = ttl_minutes or self.default_ttl_minutes
        expiry = datetime.now() + timedelta(minutes=ttl)
        self._cache[cache_key] = (value, expiry, 1)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._cache:
            return

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
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Pure computation node for deterministic operations.

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

        # Computation-specific configuration
        self.max_parallel_workers = 4
        self.cache_ttl_minutes = 30
        self.performance_threshold_ms = 100.0

        # Initialize caching layer
        self.computation_cache = ComputationCache(
            max_size=1000, default_ttl_minutes=self.cache_ttl_minutes
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

        STABLE INTERFACE: This method signature is frozen for code generation.

        Args:
            input_data: Strongly typed computation input

        Returns:
            Strongly typed computation output with performance metrics

        Raises:
            ModelOnexError: If computation fails or performance threshold exceeded
        """
        start_time = time.time()

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

            processing_time = (time.time() - start_time) * 1000

            # Validate performance threshold
            if processing_time > self.performance_threshold_ms:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Computation exceeded threshold: {processing_time:.2f}ms",
                    {
                        "node_id": str(self.node_id),
                        "computation_type": input_data.computation_type,
                    },
                )

            # Cache result if enabled
            if input_data.cache_enabled:
                self.computation_cache.put(cache_key, result, self.cache_ttl_minutes)

            # Update metrics
            await self._update_specialized_metrics(
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
            processing_time = (time.time() - start_time) * 1000

            await self._update_specialized_metrics(
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
                    "computation_type": input_data.computation_type,
                },
            ) from e

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
            self.thread_pool.shutdown(wait=True)
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
        """Generate cache key for computation input."""
        data_str = str(input_data.data)
        return f"{input_data.computation_type}:{hash(data_str)}"

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

        loop = asyncio.get_event_loop()
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
                raise ValueError("Input must be a string")
            return data.upper()

        def sum_numbers(data: list[float]) -> float:
            """Sum list of numbers."""
            if not isinstance(data, (list, tuple)):
                raise ValueError("Input must be a list or tuple")
            return sum(data)

        self.register_computation("default", default_transform)
        self.register_computation("string_uppercase", string_uppercase)
        self.register_computation("sum_numbers", sum_numbers)
