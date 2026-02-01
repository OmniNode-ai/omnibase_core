"""
ServiceEffectMockRegistry - Registry for effect mocks used during replay.

This module provides a registry for deterministic mock implementations that
replace non-deterministic effects during replay execution with the MOCKED policy.

Design:
    The registry stores callable mocks indexed by effect keys. During replay
    with MOCKED policy, the runtime looks up mocks by effect key and executes
    them instead of the original non-deterministic effects.

Architecture:
    The effect mock registry is part of the replay infrastructure that supports
    the MOCKED policy level in effect classification. Effects classified as
    MOCKED are replaced with deterministic mock implementations during replay,
    allowing predictable test execution.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_effect_mock_registry import (
            ServiceEffectMockRegistry,
        )

        # Create registry
        registry = ServiceEffectMockRegistry()

        # Register mocks for specific effects
        registry.register_mock(
            "network.http_get",
            lambda url, **kwargs: {"status": 200, "body": "mocked"},
        )
        registry.register_mock(
            "time.now",
            lambda: datetime(2025, 1, 1, 12, 0, 0),
        )

        # Use during replay
        if registry.has_mock("network.http_get"):
            mock_fn = registry.get_mock("network.http_get")
            result = mock_fn("https://api.example.com")

Thread Safety:
    ServiceEffectMockRegistry is NOT thread-safe. The internal dictionary
    is not protected by locks. Use external synchronization or thread-local
    registries if concurrent access is needed.

Related:
    - OMN-1147: Effect Classification System - MOCKED policy level
    - ServiceEffectRecorder: Effect recording for RECORDED policy
    - ServiceReplaySafetyEnforcer: Policy enforcement during replay

.. versionadded:: 0.6.4
"""

from __future__ import annotations

__all__ = ["ServiceEffectMockRegistry"]

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ServiceEffectMockRegistry:
    """
    Registry for effect mocks used during replay with MOCKED policy.

    Warning:
        This class is NOT thread-safe. The internal dictionary is not protected
        by locks. Use external synchronization or thread-local registries if
        concurrent access is needed. See Thread Safety section below.

    Stores deterministic mock implementations indexed by effect key. Effects
    classified with MOCKED policy are replaced with these mocks during replay,
    ensuring predictable test execution.

    The registry provides a simple key-value interface where effect keys
    (e.g., "network.http_get", "time.now") map to callable mock implementations.

    Example:
        >>> from omnibase_core.services.replay.service_effect_mock_registry import (
        ...     ServiceEffectMockRegistry,
        ... )
        >>> registry = ServiceEffectMockRegistry()
        >>> registry.register_mock("rng.random", lambda: 0.5)
        >>> registry.has_mock("rng.random")
        True
        >>> mock_fn = registry.get_mock("rng.random")
        >>> mock_fn()
        0.5

    Attributes:
        _mocks: Internal dictionary mapping effect keys to mock callables.

    Thread Safety:
        Not thread-safe. Use external synchronization for concurrent access.

    Note:
        Registered mocks are stored as callable references. If a mock maintains
        internal state (e.g., a counter that increments on each call), that state
        persists across invocations within the same registry instance. For fully
        deterministic replay behavior, prefer stateless mocks or reset mock state
        between test runs by calling :meth:`clear` or re-creating the registry.

    .. versionadded:: 0.6.4
    """

    def __init__(self) -> None:
        """Initialize with empty mock registry."""
        self._mocks: dict[str, Callable[..., Any]] = {}

    def register_mock(self, effect_key: str, mock_callable: Callable[..., Any]) -> None:
        """
        Register a deterministic mock for an effect.

        Replaces any existing mock for the same effect key. The mock callable
        should be deterministic to ensure reproducible replay behavior.

        Args:
            effect_key: Unique identifier for the effect (e.g., "network.http_get",
                "time.now", "rng.random"). Convention uses dot-separated namespaces.
            mock_callable: Deterministic callable to use during replay. Should
                accept the same arguments as the original effect.

        Raises:
            ValueError: If effect_key is empty or whitespace-only.
            ValueError: If mock_callable is not callable.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mock(
            ...     "database.query",
            ...     lambda sql: [{"id": 1, "name": "test"}],
            ... )
        """
        if not effect_key or not effect_key.strip():
            # error-ok: ValueError for public API input validation per project conventions
            raise ValueError("effect_key must not be empty or whitespace-only")

        if not callable(mock_callable):
            # error-ok: ValueError for public API input validation per project conventions
            raise ValueError(
                f"mock_callable must be callable, got {type(mock_callable).__name__}"
            )

        # Normalize key by stripping whitespace for consistent lookup
        effect_key = effect_key.strip()
        self._mocks[effect_key] = mock_callable
        logger.debug("Registered mock for effect '%s'", effect_key)

    def register_mocks(self, mocks: dict[str, Callable[..., Any]]) -> None:
        """
        Register multiple mocks at once.

        Convenience method for registering multiple mocks in a single call,
        useful for test setup. Registration is atomic - if any validation
        fails, no mocks are registered.

        Args:
            mocks: Dictionary mapping effect keys to mock callables.

        Raises:
            ValueError: If any key is empty/whitespace-only or any value
                is not callable. No mocks are registered if validation fails.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mocks({
            ...     "time.now": lambda: datetime(2025, 1, 1),
            ...     "random.random": lambda: 0.5,
            ...     "network.http_get": lambda url: {"status": 200},
            ... })
            >>> registry.mock_count
            3
        """
        # Validate all mocks first (atomic - fail before any registration)
        for effect_key, mock_callable in mocks.items():
            if not effect_key or not effect_key.strip():
                # error-ok: ValueError for public API input validation per project conventions
                raise ValueError("effect_key must not be empty or whitespace-only")
            if not callable(mock_callable):
                # error-ok: ValueError for public API input validation per project conventions
                raise ValueError(
                    f"mock_callable must be callable, got {type(mock_callable).__name__}"
                )

        # All validated - now register atomically
        for effect_key, mock_callable in mocks.items():
            effect_key = effect_key.strip()
            self._mocks[effect_key] = mock_callable
            logger.debug("Registered mock for effect '%s'", effect_key)

    def get_mock(self, effect_key: str) -> Callable[..., Any] | None:
        """
        Retrieve the mock callable for an effect.

        Args:
            effect_key: The effect identifier to look up.

        Returns:
            The mock callable if registered, None if no mock exists for this key.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mock("time.now", lambda: 1234567890)
            >>> mock_fn = registry.get_mock("time.now")
            >>> mock_fn()
            1234567890
            >>> registry.get_mock("nonexistent") is None
            True
        """
        # Normalize key by stripping whitespace for consistent lookup
        return self._mocks.get(effect_key.strip())

    def has_mock(self, effect_key: str) -> bool:
        """
        Check if a mock is registered for an effect.

        Args:
            effect_key: The effect identifier to check.

        Returns:
            True if a mock is registered for this key, False otherwise.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.has_mock("network.http_get")
            False
            >>> registry.register_mock("network.http_get", lambda url: {})
            >>> registry.has_mock("network.http_get")
            True
        """
        # Normalize key by stripping whitespace for consistent lookup
        return effect_key.strip() in self._mocks

    def unregister_mock(self, effect_key: str) -> bool:
        """
        Remove a registered mock.

        Args:
            effect_key: The effect identifier to unregister.

        Returns:
            True if the mock was found and removed, False if no mock was
            registered for this key.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mock("rng.random", lambda: 0.42)
            >>> registry.unregister_mock("rng.random")
            True
            >>> registry.unregister_mock("rng.random")
            False
        """
        # Normalize key by stripping whitespace for consistent lookup
        effect_key = effect_key.strip()
        if effect_key in self._mocks:
            del self._mocks[effect_key]
            logger.debug("Unregistered mock for effect '%s'", effect_key)
            return True
        return False

    def clear(self) -> None:
        """
        Remove all registered mocks.

        Useful for test cleanup or resetting the registry between test runs.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mock("a", lambda: 1)
            >>> registry.register_mock("b", lambda: 2)
            >>> registry.mock_count
            2
            >>> registry.clear()
            >>> registry.mock_count
            0
        """
        count = len(self._mocks)
        self._mocks.clear()
        logger.debug("Cleared %d registered mocks", count)

    def list_registered_effects(self) -> list[str]:
        """
        List all effect keys with registered mocks.

        Returns:
            Sorted list of effect keys that have registered mocks.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.register_mock("time.now", lambda: 0)
            >>> registry.register_mock("network.http_get", lambda url: {})
            >>> registry.list_registered_effects()
            ['network.http_get', 'time.now']
        """
        return sorted(self._mocks.keys())

    @property
    def mock_count(self) -> int:
        """
        Return the number of registered mocks.

        Returns:
            Number of mocks currently registered.

        Example:
            >>> registry = ServiceEffectMockRegistry()
            >>> registry.mock_count
            0
            >>> registry.register_mock("test", lambda: None)
            >>> registry.mock_count
            1
        """
        return len(self._mocks)

    def __str__(self) -> str:
        """Return human-readable summary."""
        return f"ServiceEffectMockRegistry[mocks={len(self._mocks)}]"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        keys = self.list_registered_effects()
        if len(keys) > 10:
            keys_repr = f"<{len(keys)} effects>"
        else:
            keys_repr = repr(keys)
        return f"ServiceEffectMockRegistry(effects={keys_repr})"
