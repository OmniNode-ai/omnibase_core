"""
ServiceRNGInjector - RNG injector for deterministic replay.

This module provides the default ProtocolRNGService implementation using
Python's random.Random class for isolated, seeded random number generation.

Design:
    Each ServiceRNGInjector instance contains its own random.Random instance,
    ensuring isolation and thread safety when using separate instances
    per thread. The seed is recorded for manifest storage and replay.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector

        # Replay mode: use specific seed
        rng = ServiceRNGInjector(seed=42)
        value = rng.random()

        # Production mode: auto-generate secure seed
        rng = ServiceRNGInjector()
        seed_for_manifest = rng.seed

Key Invariant:
    Same seed -> Same sequence (determinism for replay)

    .. code-block:: python

        rng1 = ServiceRNGInjector(seed=42)
        rng2 = ServiceRNGInjector(seed=42)
        assert [rng1.random() for _ in range(10)] == [rng2.random() for _ in range(10)]

Thread Safety:
    ServiceRNGInjector instances are NOT thread-safe. Use separate instances
    per thread for concurrent usage. The underlying random.Random
    instance is per-injector, providing isolation.

Related:
    - OMN-1116: RNG Injector for Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7.1
    - ProtocolRNGService: Protocol definition

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceRNGInjector"]

import os
import random
from collections.abc import Sequence
from typing import TypeVar

from omnibase_core.protocols.replay import ProtocolRNGService

T = TypeVar("T")


class ServiceRNGInjector:
    """
    RNG injector for deterministic replay.

    Uses seeded random.Random for reproducible randomness.
    Seed is recorded for replay.

    Args:
        seed: Optional seed for deterministic replay. If None, a secure
            random seed is auto-generated using os.urandom.

    Attributes:
        seed: The seed used for this RNG instance (read-only property).

    Example:
        >>> rng = ServiceRNGInjector(seed=42)
        >>> rng.random()  # Returns deterministic value
        0.6394267984578837
        >>> rng.randint(1, 10)
        1
        >>> rng.choice(["a", "b", "c"])
        'c'

    Thread Safety:
        NOT thread-safe. Use separate instances per thread.

    .. versionadded:: 0.4.0
    """

    def __init__(self, seed: int | None = None) -> None:
        """
        Initialize the RNG injector.

        Args:
            seed: Optional seed for deterministic replay. If None,
                a cryptographically random seed is generated using
                os.urandom(4) and converted to an integer.
        """
        if seed is not None:
            self._seed = seed
        else:
            # Generate a secure random seed
            # Using 4 bytes gives us a 32-bit integer
            self._seed = int.from_bytes(os.urandom(4), "big")

        self._rng = random.Random(self._seed)

    @property
    def seed(self) -> int:
        """
        Return the seed used for this RNG instance.

        The seed is recorded in the execution manifest for replay.
        For auto-generated seeds, this returns the generated value.

        Returns:
            The seed value as an integer.

        Example:
            >>> rng = ServiceRNGInjector(seed=42)
            >>> rng.seed
            42
            >>> rng_auto = ServiceRNGInjector()
            >>> isinstance(rng_auto.seed, int)
            True
        """
        return self._seed

    def random(self) -> float:
        """
        Return a random float in [0.0, 1.0).

        Returns:
            A random float N such that 0.0 <= N < 1.0.

        Example:
            >>> rng = ServiceRNGInjector(seed=42)
            >>> value = rng.random()
            >>> 0.0 <= value < 1.0
            True
        """
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """
        Return a random integer N such that a <= N <= b.

        Args:
            a: Lower bound (inclusive).
            b: Upper bound (inclusive).

        Returns:
            A random integer in the range [a, b].

        Example:
            >>> rng = ServiceRNGInjector(seed=42)
            >>> die_roll = rng.randint(1, 6)
            >>> 1 <= die_roll <= 6
            True
        """
        return self._rng.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        """
        Return a random element from a non-empty sequence.

        Args:
            seq: A non-empty sequence of elements.

        Returns:
            A randomly selected element from the sequence.

        Raises:
            IndexError: If the sequence is empty.

        Example:
            >>> rng = ServiceRNGInjector(seed=42)
            >>> colors = ["red", "green", "blue"]
            >>> rng.choice(colors) in colors
            True
        """
        return self._rng.choice(seq)


# Verify protocol compliance at module load time
_rng_check: ProtocolRNGService = ServiceRNGInjector(seed=0)
