"""
ProtocolRNGService - Protocol for RNG injection in replay infrastructure.

This protocol defines the interface for random number generation in the ONEX
pipeline. By using a protocol instead of direct random module usage, nodes
can remain deterministic for replay while production mode uses secure random.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations provide the actual RNG mechanism. This allows
    nodes to generate random values without importing the random module
    directly, enabling deterministic replay when seeded.

Architecture:
    Nodes receive an RNG service via context (ctx.rng). If a specific seed
    is provided (replay mode), the same sequence of random values is
    guaranteed. If no seed is provided (production mode), a secure random
    seed is auto-generated and recorded in the manifest.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolRNGService

        class MyRNGService:
            def __init__(self, seed: int = 42):
                import random
                self._seed = seed
                self._rng = random.Random(seed)

            @property
            def seed(self) -> int:
                return self._seed

            def random(self) -> float:
                return self._rng.random()

            def randint(self, a: int, b: int) -> int:
                return self._rng.randint(a, b)

            def choice(self, seq):
                return self._rng.choice(seq)

        # Use in node via context
        result = ctx.rng.random()

Key Invariant:
    Same seed -> Same sequence (determinism for replay)

    .. code-block:: python

        rng1 = ServiceRNGInjector(seed=42)
        rng2 = ServiceRNGInjector(seed=42)
        assert [rng1.random() for _ in range(10)] == [rng2.random() for _ in range(10)]

Related:
    - OMN-1116: RNG Injector for Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7.1
    - ServiceRNGInjector: Default implementation

.. versionadded:: 0.4.0
"""

__all__ = ["ProtocolRNGService"]

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ProtocolRNGService(Protocol):
    """
    Protocol for RNG injection in replay infrastructure.

    Defines the interface for random number generation that supports
    deterministic replay. Implementations use seeded random.Random
    instances for reproducibility.

    Thread Safety:
        Implementations should use isolated random.Random instances.
        Thread safety is achieved by using separate instances per thread
        rather than sharing a single instance.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.replay import ProtocolRNGService
            from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector

            # Create with specific seed for replay
            rng: ProtocolRNGService = ServiceRNGInjector(seed=42)

            # Use in deterministic context
            value = rng.random()
            index = rng.randint(0, 10)
            item = rng.choice(["a", "b", "c"])

            # Record seed for replay
            manifest_data = {"rng_seed": rng.seed}

    .. versionadded:: 0.4.0
    """

    @property
    def seed(self) -> int:
        """
        Return the seed used for this RNG instance.

        The seed is recorded in the execution manifest for replay.
        For auto-generated seeds, this returns the generated value.

        Returns:
            The seed value as an integer.

        Example:
            .. code-block:: python

                rng = ServiceRNGInjector(seed=42)
                assert rng.seed == 42

                # Record for replay
                manifest["rng_seed"] = rng.seed
        """
        ...

    def random(self) -> float:
        """
        Return a random float in [0.0, 1.0).

        Equivalent to random.Random.random().

        Returns:
            A random float N such that 0.0 <= N < 1.0.

        Example:
            .. code-block:: python

                rng = ServiceRNGInjector(seed=42)
                value = rng.random()
                assert 0.0 <= value < 1.0
        """
        ...

    def randint(self, a: int, b: int) -> int:
        """
        Return a random integer N such that a <= N <= b.

        Equivalent to random.Random.randint(a, b).

        Args:
            a: Lower bound (inclusive).
            b: Upper bound (inclusive).

        Returns:
            A random integer in the range [a, b].

        Example:
            .. code-block:: python

                rng = ServiceRNGInjector(seed=42)
                die_roll = rng.randint(1, 6)
                assert 1 <= die_roll <= 6
        """
        ...

    def choice(self, seq: Sequence[T]) -> T:
        """
        Return a random element from a non-empty sequence.

        Equivalent to random.Random.choice(seq).

        Args:
            seq: A non-empty sequence of elements.

        Returns:
            A randomly selected element from the sequence.

        Raises:
            IndexError: If the sequence is empty.

        Example:
            .. code-block:: python

                rng = ServiceRNGInjector(seed=42)
                colors = ["red", "green", "blue"]
                selected = rng.choice(colors)
                assert selected in colors
        """
        ...
