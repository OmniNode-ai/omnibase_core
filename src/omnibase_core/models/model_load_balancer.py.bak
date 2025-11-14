"""
ModelLoadBalancer - Load balancer for distributing workflow operations.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID


class ModelLoadBalancer:
    """
    Load balancer for distributing workflow operations.
    """

    def __init__(self, max_concurrent_operations: int = 10):
        self.max_concurrent_operations = max_concurrent_operations
        self.active_operations: dict[UUID, datetime] = {}
        self.operation_counts: dict[str, int] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_operations)

    async def acquire(self, operation_id: UUID) -> bool:
        """Acquire slot for operation execution.

        Args:
            operation_id: UUID of the operation to acquire slot for.

        Returns:
            True if slot acquired successfully, False otherwise.
        """
        async with self.semaphore:
            if len(self.active_operations) < self.max_concurrent_operations:
                self.active_operations[operation_id] = datetime.now()
                operation_key = str(operation_id)
                self.operation_counts[operation_key] = (
                    self.operation_counts.get(operation_key, 0) + 1
                )
                return True
            return False

    def release(self, operation_id: UUID) -> None:
        """Release slot after operation completion.

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

        return min(targets, key=lambda t: self.operation_counts.get(t, 0))

    def get_stats(self) -> dict[str, Any]:
        """Get load balancer statistics.

        Returns:
            Dictionary containing active operations count, max concurrent limit,
            utilization percentage, and total operations processed.
        """
        return {
            "active_operations": len(self.active_operations),
            "max_concurrent": self.max_concurrent_operations,
            "utilization": len(self.active_operations) / self.max_concurrent_operations,
            "total_operations": sum(self.operation_counts.values()),
        }
