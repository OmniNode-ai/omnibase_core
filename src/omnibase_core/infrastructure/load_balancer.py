import uuid

"""
Load balancer for distributing workflow operations in NodeOrchestrator.

Provides operation distribution, load balancing, and concurrency control
for workflow orchestration operations.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID


class LoadBalancer:
    """
    Load balancer for distributing workflow operations.
    """

    def __init__(self, max_concurrent_operations: int = 10):
        self.max_concurrent_operations = max_concurrent_operations
        self.active_operations: dict[str, datetime] = {}
        self.operation_counts: dict[str, int] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_operations)

    async def acquire(self, operation_id: UUID) -> bool:
        """Acquire slot for operation execution."""
        await self.semaphore.acquire()
        operation_id_str = str(operation_id)
        self.active_operations[operation_id_str] = datetime.now()
        self.operation_counts[operation_id_str] = (
            self.operation_counts.get(operation_id_str, 0) + 1
        )
        return True

    def release(self, operation_id: UUID) -> None:
        """Release slot after operation completion."""
        operation_id_str = str(operation_id)
        if operation_id_str in self.active_operations:
            del self.active_operations[operation_id_str]
        self.semaphore.release()

    def get_least_loaded_target(self, targets: list[str]) -> str:
        """Get least loaded target for operation distribution."""
        if not targets:
            return ""

        return min(targets, key=lambda t: self.operation_counts.get(t, 0))

    def get_stats(self) -> dict[str, Any]:
        """Get load balancer statistics."""
        return {
            "active_operations": len(self.active_operations),
            "max_concurrent": self.max_concurrent_operations,
            "utilization": len(self.active_operations) / self.max_concurrent_operations,
            "total_operations": sum(self.operation_counts.values()),
        }
