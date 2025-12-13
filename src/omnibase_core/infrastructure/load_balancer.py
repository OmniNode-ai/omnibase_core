"""
Load balancer for distributing workflow operations in NodeOrchestrator.

Provides operation distribution, load balancing, and concurrency control
for workflow orchestration operations.
"""

import asyncio
from datetime import datetime
from uuid import UUID

from omnibase_core.models.infrastructure.model_load_balancer_stats import (
    ModelLoadBalancerStats,
)


class LoadBalancer:
    """
    Load balancer for distributing workflow operations.
    """

    def __init__(self, max_concurrent_operations: int = 10):
        self.max_concurrent_operations = max_concurrent_operations
        self.active_operations: dict[str, datetime] = {}
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
        operation_id_str = str(operation_id)
        self.active_operations[operation_id_str] = datetime.now()
        self.operation_counts[operation_id_str] = (
            self.operation_counts.get(operation_id_str, 0) + 1
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
        operation_id_str = str(operation_id)
        if operation_id_str in self.active_operations:
            del self.active_operations[operation_id_str]
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

    def get_stats(self) -> ModelLoadBalancerStats:
        """Get load balancer statistics."""
        return ModelLoadBalancerStats(
            active_operations=len(self.active_operations),
            max_concurrent=self.max_concurrent_operations,
            utilization=len(self.active_operations) / self.max_concurrent_operations,
            total_operations=sum(self.operation_counts.values()),
        )
