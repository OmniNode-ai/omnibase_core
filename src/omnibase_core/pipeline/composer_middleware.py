"""Middleware composer for onion-style wrapping."""

from collections.abc import Awaitable, Callable

# Type for middleware: takes next_fn, returns wrapped result
# Using object as the most general type that doesn't require explicit Any
Middleware = Callable[[Callable[[], Awaitable[object]]], Awaitable[object]]


class ComposerMiddleware:
    """
    Composes middleware in onion (decorator) style.

    First middleware added is outermost (executes first on entry, last on exit).
    Last middleware added is innermost (closest to core).

    Usage:
        composer = ComposerMiddleware()
        composer.use(logging_middleware)
        composer.use(timing_middleware)
        wrapped = composer.compose(core_function)
        result = await wrapped()

    Thread Safety
    -------------
    **This class is NOT thread-safe during composition.**

    The ``use()`` method mutates internal state (``_middleware`` list). Once
    ``compose()`` is called and returns a wrapped callable, that callable is
    safe to invoke from multiple concurrent contexts (assuming the middleware
    functions themselves are thread-safe).

    **Safe Pattern** - Build once, execute concurrently::

        # Single-threaded setup
        composer = ComposerMiddleware()
        composer.use(logging_middleware)
        composer.use(timing_middleware)
        wrapped = composer.compose(core_function)

        # Now safe for concurrent execution
        await asyncio.gather(
            wrapped(),  # Task 1
            wrapped(),  # Task 2
        )

    **Unsafe Pattern** - Concurrent modification::

        # UNSAFE - don't modify while composing
        async def worker():
            composer.use(some_middleware)  # Race condition!

    See Also
    --------
    - docs/guides/THREADING.md for comprehensive thread safety guide
    """

    def __init__(self) -> None:
        """Initialize empty middleware stack."""
        self._middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> "ComposerMiddleware":
        """
        Add middleware to the composition.

        Args:
            middleware: Async function taking next_fn and returning result.

        Returns:
            Self for chaining.
        """
        self._middleware.append(middleware)
        return self

    def compose(
        self,
        core: Callable[[], Awaitable[object]],
    ) -> Callable[[], Awaitable[object]]:
        """
        Compose all middleware around the core function.

        Args:
            core: The innermost async function to wrap.

        Returns:
            Wrapped async function.
        """
        if not self._middleware:
            return core

        # Build from inside out (reverse order)
        wrapped: Callable[[], Awaitable[object]] = core
        for middleware in reversed(self._middleware):
            # Create new wrapped that calls middleware with current as next
            wrapped = self._make_wrapper(middleware, wrapped)

        return wrapped

    def _make_wrapper(
        self,
        middleware: Middleware,
        next_fn: Callable[[], Awaitable[object]],
    ) -> Callable[[], Awaitable[object]]:
        """Create a wrapper that calls middleware with next_fn."""

        async def wrapper() -> object:
            return await middleware(next_fn)

        return wrapper


__all__ = ["ComposerMiddleware", "Middleware"]
