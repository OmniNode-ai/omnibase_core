"""
Load balancer model for distributing workflow operations.

This module provides the ModelLoadBalancer class that distributes workflow
operations across available resources using semaphore-based concurrency
control and least-loaded target selection.

Thread Safety:
    ModelLoadBalancer uses asyncio.Semaphore for thread-safe concurrency
    control. The acquire() method is async and properly handles concurrent
    access. However, the internal dictionaries are not synchronized - use
    in single-threaded async context only.

Key Features:
    - Semaphore-based concurrency limiting
    - Least-loaded target selection algorithm
    - Operation tracking with timestamps
    - Statistics collection for monitoring

Example:
    >>> import asyncio
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator import ModelLoadBalancer
    >>>
    >>> async def run_with_load_balancer():
    ...     balancer = ModelLoadBalancer(max_concurrent_operations=5)
    ...
    ...     operation_id = uuid4()
    ...     if await balancer.acquire(operation_id):
    ...         try:
    ...             # Execute operation
    ...             await do_work()
    ...         finally:
    ...             balancer.release(operation_id)
    ...
    ...     # Get least loaded target for distribution
    ...     targets = ["server1", "server2", "server3"]
    ...     best_target = balancer.get_least_loaded_target(targets)
    ...     print(f"Route to: {best_target}")
    ...
    ...     # Monitor utilization
    ...     stats = balancer.get_stats()
    ...     print(f"Utilization: {stats['utilization']:.1%}")

See Also:
    - omnibase_core.models.orchestrator.model_orchestrator_input: Uses load balancer
    - omnibase_core.nodes.node_orchestrator: Integrates load balancing
"""

import asyncio
from datetime import datetime
from uuid import UUID

from omnibase_core.types.typed_dict_load_balancer_stats import (
    TypedDictLoadBalancerStats,
)


class ModelLoadBalancer:
    """
    Load balancer for distributing workflow operations.

    Manages concurrent operation execution using semaphore-based limiting
    and provides least-loaded target selection for operation distribution.
    Tracks operation counts and provides utilization statistics.

    Attributes:
        max_concurrent_operations: Maximum number of operations allowed
            to execute concurrently.
        active_operations: Dictionary mapping operation UUIDs to their
            start timestamps.
        operation_counts: Dictionary tracking operation counts per target
            for load distribution decisions.
        semaphore: Asyncio semaphore for concurrency control.

    Note:
        The load balancer is designed for single-threaded async contexts.
        For multi-threaded usage, external synchronization is required
        for the internal dictionaries.
    """

    def __init__(self, max_concurrent_operations: int = 10):
        self.max_concurrent_operations = max_concurrent_operations
        self.active_operations: dict[UUID, datetime] = {}
        self.operation_counts: dict[str, int] = {}
        self.target_counts: dict[str, int] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_operations)

    async def acquire(self, operation_id: UUID, target: str | None = None) -> bool:
        """Acquire slot for operation execution.

        Blocks until a semaphore slot is available, then registers the operation.

        Args:
            operation_id: UUID of the operation to acquire slot for.
            target: Optional target identifier for load tracking.

        Returns:
            True when slot is acquired (always succeeds after blocking).
        """
        await self.semaphore.acquire()
        self.active_operations[operation_id] = datetime.now()
        operation_key = str(operation_id)
        self.operation_counts[operation_key] = (
            self.operation_counts.get(operation_key, 0) + 1
        )
        if target is not None:
            self.target_counts[target] = self.target_counts.get(target, 0) + 1
        return True

    def release(self, operation_id: UUID) -> None:
        """Release slot after operation completion.

        Only releases the semaphore if the operation was previously acquired.
        This prevents over-release of the semaphore which could corrupt its state.

        Args:
            operation_id: UUID of the operation to release slot for.
        """
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
            self.semaphore.release()

    def get_least_loaded_target(self, targets: list[str]) -> str:
        """Get least loaded target for operation distribution.

        Args:
            targets: List of target identifiers to choose from.

        Returns:
            The target identifier with the lowest operation count, or empty string if no targets.
        """
        if not targets:
            return ""

        return min(targets, key=lambda t: self.target_counts.get(t, 0))

    def get_stats(self) -> TypedDictLoadBalancerStats:
        """Get load balancer statistics.

        Returns:
            TypedDictLoadBalancerStats containing active operations count, max concurrent limit,
            utilization percentage, and total operations processed.
        """
        return TypedDictLoadBalancerStats(
            active_operations=len(self.active_operations),
            max_concurrent=self.max_concurrent_operations,
            utilization=len(self.active_operations) / self.max_concurrent_operations,
            total_operations=sum(self.operation_counts.values()),
        )


__all__ = ["ModelLoadBalancer"]
