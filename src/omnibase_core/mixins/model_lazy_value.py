from __future__ import annotations

from typing import Callable, Generic, Optional, TypeVar, cast

T = TypeVar("T")


class LazyValue(Generic[T]):
    """Lazy evaluation wrapper for expensive operations."""

    def __init__(self, func: Callable[[], T], cache: bool = True):
        """
        Initialize lazy value with computation function.

        Args:
            func: Function to compute the value when needed
            cache: Whether to cache the result after first computation
        """
        self._func = func
        self._cache = cache
        self._cached_value: Optional[T] = None
        self._computed = False

    def get(self) -> T:
        """Compute and return the value."""
        if not self._computed or not self._cache:
            self._cached_value = self._func()
            self._computed = True
        return cast(T, self._cached_value)

    def __call__(self) -> T:
        """Allow LazyValue to be called directly."""
        return self.get()

    def is_computed(self) -> bool:
        """Check if value has been computed."""
        return self._computed

    def invalidate(self) -> None:
        """Invalidate cached value, forcing recomputation on next access."""
        self._cached_value = None
        self._computed = False
