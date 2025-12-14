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

    Lifecycle:
        1. Create instance: ``executor = ServiceParallelExecutor(max_workers=4)``
        2. Use for parallel execution via ``execute()`` method
        3. Call ``shutdown()`` when done to release thread pool resources

        Warning:
            Failing to call ``shutdown()`` will leak threads. The underlying
            ThreadPoolExecutor maintains worker threads that will not be
            released, leading to resource exhaustion if many executors are
            created without cleanup. Always ensure ``shutdown()`` is called,
            ideally in a try/finally block::

                executor = ServiceParallelExecutor(max_workers=4)
                try:
                    result = await executor.execute(func, data)
                finally:
                    await executor.shutdown()

        Note:
            After ``shutdown()`` is called, the executor cannot be reused.
            Any subsequent calls to ``execute()`` will raise ``ModelOnexError``.
            Create a new instance if additional parallel execution is needed.

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
        """
        Shutdown the executor and release thread pool resources.

        This method signals the executor that no more work will be submitted
        and releases the underlying ThreadPoolExecutor resources.

        Args:
            wait: If True (default), blocks until all pending tasks complete.
                If False, returns immediately; pending tasks may be interrupted.
                Use ``wait=False`` only when you need immediate shutdown and
                can tolerate incomplete work.

        Note:
            After shutdown, this executor instance cannot be reused. Any
            subsequent calls to ``execute()`` will raise ``ModelOnexError``
            with error code ``OPERATION_FAILED``. Create a new instance
            if additional parallel execution is needed.

        Example:
            >>> # Graceful shutdown - wait for pending work
            >>> await executor.shutdown(wait=True)
            >>>
            >>> # Immediate shutdown - may interrupt pending work
            >>> await executor.shutdown(wait=False)
        """
        self._shutdown = True
        self._pool.shutdown(wait=wait)
