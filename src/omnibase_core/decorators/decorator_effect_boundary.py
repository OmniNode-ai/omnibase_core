"""Effect Boundary Decorator for annotating functions with effect metadata.

Provides the @effect_boundary decorator to mark functions as effect boundaries,
attaching ModelEffectBoundary metadata for runtime replay safety enforcement.
Part of the effect boundary system for OMN-1147.

Async Support:
    The decorator automatically detects async functions using
    asyncio.iscoroutinefunction() and creates the appropriate wrapper:
    - Async functions get an async wrapper that properly awaits the original
    - Sync functions get a sync wrapper that calls the original directly

    This ensures proper coroutine handling and preserves the async nature
    of decorated functions.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.models.effects.model_effect_boundary import ModelEffectBoundary
from omnibase_core.models.effects.model_effect_classification import (
    ModelEffectClassification,
)

__all__ = [
    "EFFECT_BOUNDARY_ATTR",
    "effect_boundary",
    "get_effect_boundary",
    "has_effect_boundary",
]

P = ParamSpec("P")
R = TypeVar("R")

# Attribute name for storing boundary metadata on decorated functions
EFFECT_BOUNDARY_ATTR = "_effect_boundary"


def effect_boundary(
    boundary_id: str,  # string-id-ok: human-readable identifier, not UUID
    categories: list[EnumEffectCategory] | None = None,
    policy: EnumEffectPolicyLevel = EnumEffectPolicyLevel.WARN,
    determinism_marker: bool = True,
    isolation_mechanisms: list[str] | None = None,
    description: str = "",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to mark a function as an effect boundary.

    Attaches ModelEffectBoundary metadata to the function for runtime
    policy enforcement during replay execution. The metadata is discoverable
    via introspection using get_effect_boundary().

    This decorator supports both sync and async functions. It automatically
    detects async functions using asyncio.iscoroutinefunction() and creates
    the appropriate wrapper type to preserve async behavior.

    Args:
        boundary_id: Unique identifier for this effect boundary.
        categories: Effect categories this boundary encompasses. Each category
            generates a ModelEffectClassification in the boundary.
        policy: Default policy level for this boundary (WARN, STRICT, etc.).
        determinism_marker: Whether this marks a determinism boundary crossing.
            Defaults to True since most effect boundaries cross determinism lines.
        isolation_mechanisms: Available isolation mechanisms for this boundary
            (e.g., "DATABASE_READONLY_SNAPSHOT", "MOCK_NETWORK").
        description: Human-readable description of the effect. Used in
            classification descriptions if provided.

    Returns:
        Decorated function with ModelEffectBoundary metadata attached.
        For async functions, returns an async wrapper. For sync functions,
        returns a sync wrapper.

    Example:
        # Async function example
        @effect_boundary(
            boundary_id="user_service.fetch_user",
            categories=[EnumEffectCategory.NETWORK, EnumEffectCategory.DATABASE],
            policy=EnumEffectPolicyLevel.MOCKED,
            description="Fetches user data from external service and cache",
        )
        async def fetch_user(user_id: str) -> User:
            ...

        # Sync function example
        @effect_boundary(
            boundary_id="file_service.read_config",
            categories=[EnumEffectCategory.FILESYSTEM],
            policy=EnumEffectPolicyLevel.WARN,
        )
        def read_config(path: str) -> dict:
            ...

        # Later, retrieve metadata for policy enforcement:
        boundary = get_effect_boundary(fetch_user)
        if boundary and boundary.default_policy == EnumEffectPolicyLevel.STRICT:
            raise ReplayBlockedError("Effect blocked during replay")
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Build classifications from categories
        classifications: list[ModelEffectClassification] = []
        for cat in categories or []:
            classifications.append(
                ModelEffectClassification(
                    category=cat,
                    description=description or f"Effect boundary: {boundary_id}",
                    nondeterministic=True,
                )
            )

        # Create boundary model with tuple conversions for frozen model
        boundary = ModelEffectBoundary(
            boundary_id=boundary_id,
            classifications=tuple(classifications),
            default_policy=policy,
            determinism_marker=determinism_marker,
            isolation_mechanisms=tuple(isolation_mechanisms or []),
        )

        # Create appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                # NOTE(OMN-1147): mypy cannot track R through async/await with ParamSpec.
                # Safe because we're awaiting the same func that was passed in.
                return await func(*args, **kwargs)  # type: ignore[no-any-return]

            # Attach metadata to the async wrapper
            setattr(async_wrapper, EFFECT_BOUNDARY_ATTR, boundary)
            # NOTE(OMN-1147): mypy cannot infer that async_wrapper matches Callable[P, R]
            # when R comes from an async function. Safe because async_wrapper preserves
            # the signature and return type of the original async function.
            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return func(*args, **kwargs)

            # Attach metadata to the sync wrapper
            setattr(sync_wrapper, EFFECT_BOUNDARY_ATTR, boundary)
            return sync_wrapper

    return decorator


def get_effect_boundary(func: Callable[..., object]) -> ModelEffectBoundary | None:
    """Retrieve effect boundary metadata from a decorated function.

    Args:
        func: The function to check for effect boundary metadata.

    Returns:
        The ModelEffectBoundary if the function was decorated with
        @effect_boundary, None otherwise.

    Example:
        @effect_boundary("my.boundary", categories=[EnumEffectCategory.NETWORK])
        def my_func():
            pass

        boundary = get_effect_boundary(my_func)
        assert boundary is not None
        assert boundary.boundary_id == "my.boundary"
    """
    return getattr(func, EFFECT_BOUNDARY_ATTR, None)


def has_effect_boundary(func: Callable[..., object]) -> bool:
    """Check if a function has effect boundary metadata.

    Args:
        func: The function to check.

    Returns:
        True if the function was decorated with @effect_boundary.
    """
    return hasattr(func, EFFECT_BOUNDARY_ATTR)
