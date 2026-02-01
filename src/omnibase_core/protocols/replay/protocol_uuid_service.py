"""
ProtocolUUIDService - Protocol for UUID injection in replay infrastructure.

This protocol defines the interface for UUID generation in the ONEX pipeline,
enabling deterministic replay by controlling UUID generation.

Design:
    Uses dependency inversion - Core defines the interface, and implementations
    provide either real UUIDs (production mode), recorded UUIDs for later
    replay (recording mode), or pre-recorded UUIDs (replay mode).

Architecture:
    Pipeline context receives a UUID service via injection. UUIDs are
    inherently non-deterministic, so this service allows capturing UUIDs
    during recording and replaying them in sequence for deterministic
    execution.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolUUIDService
        from omnibase_core.services.replay.injector_uuid import InjectorUUID
        from uuid import UUID

        # Production mode - returns real UUIDs
        uuid_service: ProtocolUUIDService = InjectorUUID()
        new_uuid = uuid_service.uuid4()

        # Replay mode - returns pre-recorded UUIDs
        recorded = [UUID("550e8400-e29b-41d4-a716-446655440000")]
        replay_service: ProtocolUUIDService = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING,
            recorded_uuids=recorded,
        )
        replayed = replay_service.uuid4()  # Returns recorded UUID

Key Invariant:
    Recording + Replay -> Same UUIDs in sequence (determinism)

Related:
    - OMN-1150: Replay Safety Enforcement
    - InjectorUUID: Default implementation
    - ctx.uuid.uuid4(): Pattern for accessing UUID service in pipeline context

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ProtocolUUIDService"]

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolUUIDService(Protocol):
    """
    Protocol for UUID injection in replay infrastructure.

    Defines the interface for UUID generation that supports deterministic
    replay. Implementations record UUIDs during recording mode and replay
    them in sequence during replay mode.

    Thread Safety:
        Implementations should use sequence counters that are NOT thread-safe.
        Use separate instances per thread for concurrent usage.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.replay import ProtocolUUIDService
            from omnibase_core.services.replay.injector_uuid import InjectorUUID
            from omnibase_core.enums.replay import EnumRecorderMode

            # Create in recording mode to capture UUIDs
            uuid_svc: ProtocolUUIDService = InjectorUUID(
                mode=EnumRecorderMode.RECORDING
            )

            # Generate UUIDs (they are recorded)
            id1 = uuid_svc.uuid4()
            id2 = uuid_svc.uuid4()

            # Get recorded for persistence
            recorded = uuid_svc.get_recorded()

            # Create replay service with recorded UUIDs
            replay_svc = InjectorUUID(
                mode=EnumRecorderMode.REPLAYING,
                recorded_uuids=recorded,
            )
            assert replay_svc.uuid4() == id1
            assert replay_svc.uuid4() == id2

    .. versionadded:: 0.6.3
    """

    def uuid4(self) -> UUID:
        """
        Generate or replay a UUID4 (random UUID).

        In production/pass-through mode, generates a real random UUID.
        In recording mode, generates a real UUID and records it.
        In replay mode, returns the next pre-recorded UUID in sequence.

        Returns:
            UUID: A UUID4 (either generated or replayed).

        Raises:
            ModelOnexError: If in replay mode and sequence is exhausted.

        Example:
            .. code-block:: python

                uuid_svc = InjectorUUID()
                new_id = uuid_svc.uuid4()
                assert new_id.version == 4
        """
        ...

    def uuid1(self) -> UUID:
        """
        Generate or replay a UUID1 (time-based UUID).

        In production/pass-through mode, generates a real time-based UUID.
        In recording mode, generates a real UUID and records it.
        In replay mode, returns the next pre-recorded UUID in sequence.

        Returns:
            UUID: A UUID1 (either generated or replayed).

        Raises:
            ModelOnexError: If in replay mode and sequence is exhausted.

        Example:
            .. code-block:: python

                uuid_svc = InjectorUUID()
                time_id = uuid_svc.uuid1()
                assert time_id.version == 1
        """
        ...

    def get_recorded(self) -> list[UUID]:
        """
        Get all recorded UUIDs for persistence.

        Returns a copy of the recorded UUIDs list for storage in the
        execution manifest.

        Returns:
            list[UUID]: List of all UUIDs generated during recording.

        Example:
            .. code-block:: python

                uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
                id1 = uuid_svc.uuid4()
                id2 = uuid_svc.uuid4()
                recorded = uuid_svc.get_recorded()
                assert len(recorded) == 2
        """
        ...

    def reset(self) -> None:
        """
        Reset sequence index for replay restart.

        Resets the replay sequence counter to the beginning, allowing
        the same recorded UUIDs to be replayed again. Useful for
        re-running a pipeline with the same recorded data.

        Example:
            .. code-block:: python

                uuid_svc = InjectorUUID(
                    mode=EnumRecorderMode.REPLAYING,
                    recorded_uuids=[...],
                )
                id1 = uuid_svc.uuid4()
                uuid_svc.reset()
                id1_again = uuid_svc.uuid4()
                assert id1 == id1_again
        """
        ...
