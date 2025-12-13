"""
ServiceParallelExecutor - Default ProtocolParallelExecutor implementation.

Provides parallel execution using ThreadPoolExecutor.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ServiceParallelExecutor"]


class ServiceParallelExecutor:
    """
    Default ProtocolParallelExecutor implementation using ThreadPoolExecutor.

    Provides parallel execution using Python's ThreadPoolExecutor,
    running computation functions in a thread pool.

    Thread Safety:
        Thread-safe. ThreadPoolExecutor is designed for concurrent access.

    Example:
        >>> executor = ServiceParallelExecutor(max_workers=4)
        >>> result = await executor.execute(expensive_func, data)
        >>> await executor.shutdown()

    .. versionadded:: 0.4.0
    """

    def __init__(self, max_workers: int = 4) -> None:
        """
        Initialize executor with specified worker count.

        Args:
            max_workers: Maximum number of worker threads
        """
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers
        self._shutdown = False

    @property
    def max_workers(self) -> int:
        """Maximum number of worker threads."""
        return self._max_workers

    async def execute(self, func: Callable[..., Any], *args: Any) -> Any:
        """Execute a function in the thread pool."""
        if self._shutdown:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Executor has been shutdown",
                context={"max_workers": self._max_workers},
            )
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, func, *args)

    async def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        self._shutdown = True
        self._pool.shutdown(wait=wait)
