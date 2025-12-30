# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Middleware composer for onion-style wrapping."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

# Type variable for the result type
T = TypeVar("T")
R = TypeVar("R")

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
        core: Callable[[], Awaitable[T]],
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


# Backwards compatibility alias
MiddlewareComposer = ComposerMiddleware

__all__ = ["ComposerMiddleware", "MiddlewareComposer", "Middleware"]
