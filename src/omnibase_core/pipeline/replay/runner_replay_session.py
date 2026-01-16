"""
ModelReplaySession - Active replay session with injected services.

This module provides the ReplaySession dataclass that encapsulates all
services needed for deterministic replay execution.

Design:
    ReplaySession coordinates the three determinism components:
    - ServiceTimeInjector: Provides fixed or current time
    - ServiceRNGInjector: Provides seeded random numbers
    - ServiceEffectRecorder: Records or replays effect results

Architecture:
    Each session is configured for a specific mode (production/recording/replaying)
    and provides the appropriate service implementations. Sessions are created
    by ExecutorReplay and should not be instantiated directly.

Thread Safety:
    ReplaySession instances are NOT thread-safe. Create separate sessions
    per thread for concurrent execution.

Usage:
    .. code-block:: python

        from omnibase_core.pipeline.replay import ExecutorReplay

        executor = ExecutorReplay()

        # Get session from executor (not created directly)
        session = executor.create_recording_session(rng_seed=42)

        # Access services
        current_time = session.time_service.now()
        random_value = session.rng_service.random()

        # Record effects
        session.effect_recorder.record(
            effect_type="http.get",
            intent={"url": "..."},
            result={"status": 200}
        )

Related:
    - OMN-1116: Implement Replay Executor for Replay Infrastructure
    - ExecutorReplay: Creates and manages ReplaySession instances
    - ModelReplayContext: Context model storing replay state

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ReplaySession"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode
from omnibase_core.models.replay.model_replay_context import ModelReplayContext

if TYPE_CHECKING:
    from omnibase_core.services.replay.service_effect_recorder import (
        ServiceEffectRecorder,
    )
    from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector


@dataclass
class ReplaySession:
    """Active replay session with injected services.

    Provides access to time, RNG, and effect recording during execution.
    Each session is configured for a specific mode (production/recording/replaying)
    and provides the appropriate service implementations.

    Attributes:
        session_id: Unique identifier for this session.
        context: ModelReplayContext with mode and determinism data.
        time_service: ServiceTimeInjector for time queries.
        rng_service: ServiceRNGInjector for random number generation.
        effect_recorder: ServiceEffectRecorder for effect recording/replay.

    Thread Safety:
        ReplaySession instances are NOT thread-safe. Create separate sessions
        per thread for concurrent execution.

    Example:
        >>> from omnibase_core.pipeline.replay import ExecutorReplay
        >>> executor = ExecutorReplay()
        >>> session = executor.create_recording_session(rng_seed=42)
        >>> session.rng_service.random()  # Deterministic random
        0.6394267984578837
        >>> session.time_service.now()  # Current or fixed time
        datetime.datetime(...)

    .. versionadded:: 0.4.0
    """

    session_id: UUID = field(default_factory=uuid4)
    context: ModelReplayContext = field(
        default_factory=lambda: ModelReplayContext(
            mode=EnumReplayMode.PRODUCTION,
            time_frozen_at=None,
            rng_seed=None,
            original_execution_id=None,
        )
    )
    time_service: ServiceTimeInjector = field(
        default_factory=lambda: _default_time_service()
    )
    rng_service: ServiceRNGInjector = field(
        default_factory=lambda: _default_rng_service()
    )
    effect_recorder: ServiceEffectRecorder = field(
        default_factory=lambda: _default_effect_recorder()
    )

    @property
    def mode(self) -> EnumReplayMode:
        """Return the replay mode for this session.

        Returns:
            EnumReplayMode: The mode (PRODUCTION, RECORDING, or REPLAYING).

        Example:
            >>> session = executor.create_production_session()
            >>> session.mode
            <EnumReplayMode.PRODUCTION: 'production'>
        """
        return self.context.mode


def _default_time_service() -> ServiceTimeInjector:
    """Create default time service (deferred import to avoid circular deps)."""
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector

    return ServiceTimeInjector()


def _default_rng_service() -> ServiceRNGInjector:
    """Create default RNG service (deferred import to avoid circular deps)."""
    from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector

    return ServiceRNGInjector()


def _default_effect_recorder() -> ServiceEffectRecorder:
    """Create default effect recorder (deferred import to avoid circular deps)."""
    from omnibase_core.services.replay.service_effect_recorder import (
        ServiceEffectRecorder,
    )

    return ServiceEffectRecorder()
