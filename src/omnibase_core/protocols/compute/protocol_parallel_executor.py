"""
ProtocolParallelExecutor - Protocol for parallel computation execution.

This protocol defines the interface for parallel execution in NodeCompute.
By using a protocol instead of direct ThreadPoolExecutor usage, NodeCompute
can remain pure while parallelization is handled by infrastructure layer.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (ThreadPoolExecutor wrapper, process pool, etc.)
    satisfy the contract. This allows NodeCompute to be pure computation
    with optional parallelization.

Architecture:
    NodeCompute receives an optional executor via container. If provided,
    the executor is used for parallel computation. If not provided,
    NodeCompute operates sequentially (pure mode).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolParallelExecutor
        from concurrent.futures import ThreadPoolExecutor
        import asyncio

        class ThreadPoolParallelExecutor(ProtocolParallelExecutor):
            def __init__(self, max_workers: int = 4):
                self._pool = ThreadPoolExecutor(max_workers=max_workers)

            async def execute(self, func: Callable[..., T], *args: Any) -> T:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._pool, func, *args)

            async def shutdown(self, wait: bool = True) -> None:
                self._pool.shutdown(wait=wait)

        # Use in NodeCompute
        node = NodeCompute(container)
        # If container provides ProtocolParallelExecutor, parallel execution is enabled

Related:
    - OMN-700: Fix NodeCompute Purity Violations
    - NodeCompute: Consumer of this protocol

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolParallelExecutor"]

from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ProtocolParallelExecutor(Protocol):
    """
    Protocol for parallel computation execution.

    Defines the interface for executing computation functions in parallel
    using thread pools, process pools, or other execution mechanisms.

    Thread Safety:
        Implementations should be thread-safe as they manage concurrent
        execution. The executor itself may be called from multiple
        coroutines concurrently.

    Lifecycle:
        Executors should be initialized before use and shutdown when
        no longer needed. The shutdown method should gracefully terminate
        running tasks.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolParallelExecutor
            from concurrent.futures import ThreadPoolExecutor
            import asyncio

            class ProcessPoolParallelExecutor:
                '''Process pool-based parallel executor.'''

                def __init__(self, max_workers: int = 4):
                    from concurrent.futures import ProcessPoolExecutor
                    self._pool = ProcessPoolExecutor(max_workers=max_workers)

                async def execute(
                    self, func: Callable[..., Any], *args: Any
                ) -> Any:
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(self._pool, func, *args)

                async def shutdown(self, wait: bool = True) -> None:
                    self._pool.shutdown(wait=wait)

            # Verify protocol compliance
            executor: ProtocolParallelExecutor = ProcessPoolParallelExecutor()
            assert isinstance(executor, ProtocolParallelExecutor)

    .. versionadded:: 0.4.0
    """

    async def execute(self, func: Callable[..., Any], *args: Any) -> Any:
        """
        Execute a function in parallel (e.g., in a thread pool).

        Args:
            func: The callable to execute. Should be a pure function
                without side effects for deterministic results.
            *args: Arguments to pass to the function.

        Returns:
            The result of the function execution.

        Raises:
            Exception: If the function raises an exception during execution.

        Example:
            .. code-block:: python

                def expensive_computation(data: list[int]) -> int:
                    return sum(x * x for x in data)

                result = await executor.execute(expensive_computation, [1, 2, 3, 4, 5])
        """
        ...

    async def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the executor and release resources.

        Args:
            wait: If True, wait for pending tasks to complete before
                returning. If False, cancel pending tasks immediately.

        Note:
            After shutdown, the executor should not be used again.
            Calling execute() after shutdown may raise an exception.

        Example:
            .. code-block:: python

                # Graceful shutdown - wait for pending tasks
                await executor.shutdown(wait=True)

                # Immediate shutdown - cancel pending tasks
                await executor.shutdown(wait=False)
        """
        ...
