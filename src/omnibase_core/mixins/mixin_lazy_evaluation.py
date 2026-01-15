"""
Lazy Evaluation Mixin for Performance Optimization

Provides lazy evaluation patterns to reduce memory usage and improve performance
for expensive operations like model serialization and type conversions.
"""

from __future__ import annotations

import functools
import hashlib
from collections.abc import Callable
from typing import TypeVar, cast

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.types import JsonSerializable
from omnibase_core.types.typed_dict_mixin_types import TypedDictLazyCacheStats

# Define PropertyValue locally to avoid dependency issues
PropertyValue = JsonSerializable

T = TypeVar("T")

# Import extracted lazy value class
from .mixin_lazy_value import MixinLazyValue


class MixinLazyEvaluation:
    """
    Mixin for lazy evaluation of expensive operations.

    Designed to reduce memory usage in type conversions and serialization
    by deferring expensive operations until they're actually needed.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lazy_cache: dict[str, MixinLazyValue[object]] = {}

    def lazy_property(
        self, key: str, func: Callable[[], T], cache: bool = True
    ) -> MixinLazyValue[T]:
        """
        Create or get a lazy property.

        Args:
            key: Unique key for the property
            func: Function to compute the property value
            cache: Whether to cache the result

        Returns:
            MixinLazyValue instance for the property
        """
        if key not in self._lazy_cache:
            self._lazy_cache[key] = MixinLazyValue(func, cache)
        return cast("MixinLazyValue[T]", self._lazy_cache[key])

    def lazy_model_dump(
        self, exclude: set[str] | None = None, by_alias: bool = False
    ) -> MixinLazyValue[dict[str, JsonSerializable]]:
        """
        Create lazy model dump for Pydantic models.

        Args:
            exclude: Fields to exclude from dump
            by_alias: Use field aliases in output

        Returns:
            MixinLazyValue that computes model dump when accessed
        """

        def _compute_dump() -> dict[str, JsonSerializable]:
            if isinstance(self, BaseModel):
                return self.model_dump(exclude=exclude, by_alias=by_alias)
            raise ModelOnexError(
                "lazy_model_dump requires BaseModel instance",
                EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
            )

        # Use deterministic hashing for cache key consistency across processes
        key_str = f"{tuple(sorted(exclude or set()))}_{by_alias}"
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()
        cache_key = f"model_dump_{key_hash}"
        return self.lazy_property(cache_key, _compute_dump)

    def lazy_serialize_nested(
        self, obj: BaseModel | None, key: str
    ) -> MixinLazyValue[dict[str, JsonSerializable] | None]:
        """
        Create lazy serialization for nested objects.

        Args:
            obj: Nested object to serialize
            key: Cache key for the operation

        Returns:
            MixinLazyValue that serializes nested object when accessed
        """

        def _serialize() -> dict[str, JsonSerializable] | None:
            return obj.model_dump() if obj else None

        return self.lazy_property(f"serialize_{key}", _serialize)

    def lazy_string_conversion(
        self, obj: BaseModel | None, key: str
    ) -> MixinLazyValue[str]:
        """
        Create lazy string conversion for nested objects.

        Args:
            obj: Object to convert to string
            key: Cache key for the operation

        Returns:
            MixinLazyValue that converts object to string when accessed
        """

        def _convert() -> str:
            if obj is None:
                return ""
            return str(obj.model_dump()) if hasattr(obj, "model_dump") else str(obj)

        return self.lazy_property(f"str_{key}", _convert)

    def invalidate_lazy_cache(self, pattern: str | None = None) -> None:
        """
        Invalidate lazy cache entries.

        Args:
            pattern: Pattern to match keys (None = all keys)
        """
        if pattern is None:
            # Invalidate all
            for lazy_val in self._lazy_cache.values():
                lazy_val.invalidate()
        else:
            # Invalidate matching pattern
            for key, lazy_val in self._lazy_cache.items():
                if pattern in key:
                    lazy_val.invalidate()

    def get_lazy_cache_stats(self) -> TypedDictLazyCacheStats:
        """
        Get statistics about lazy cache usage.

        Returns:
            Typed dictionary with cache statistics
        """
        total_entries = len(self._lazy_cache)
        computed_entries = sum(
            1 for lv in self._lazy_cache.values() if lv.is_computed()
        )

        return TypedDictLazyCacheStats(
            total_entries=total_entries,
            computed_entries=computed_entries,
            pending_entries=total_entries - computed_entries,
            cache_hit_ratio=(
                computed_entries / total_entries if total_entries > 0 else 0.0
            ),
            memory_efficiency=(
                f"{((total_entries - computed_entries) / total_entries * 100):.1f}%"
                if total_entries > 0
                else "0.0%"
            ),
        )


def lazy_cached(
    cache_key: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., MixinLazyValue[T]]]:
    """
    Decorator for creating lazy cached methods.

    Args:
        cache_key: Custom cache key (defaults to method name)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., MixinLazyValue[T]]:
        @functools.wraps(func)
        def wrapper(
            self: MixinLazyEvaluation, *args: object, **kwargs: object
        ) -> MixinLazyValue[T]:
            if not hasattr(self, "_lazy_cache"):
                self._lazy_cache = {}

            # Use deterministic hashing for cache key consistency across processes
            if cache_key:
                key = cache_key
            else:
                key_str = f"{func.__name__}_{args}_{sorted(kwargs.items())}"
                key_hash = hashlib.sha256(key_str.encode()).hexdigest()
                key = f"{func.__name__}_{key_hash}"

            if key not in self._lazy_cache:

                def compute() -> T:
                    return func(self, *args, **kwargs)

                self._lazy_cache[key] = MixinLazyValue(compute)

            return cast("MixinLazyValue[T]", self._lazy_cache[key])

        return wrapper

    return decorator
