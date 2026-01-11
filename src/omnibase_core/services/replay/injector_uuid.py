# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
InjectorUUID - UUID injector for deterministic replay.

This module provides the default ProtocolUUIDService implementation for
controlled UUID generation in the ONEX pipeline.

Design:
    The injector supports three modes:
    - PASS_THROUGH: Production mode - generates real UUIDs
    - RECORDING: Capture mode - generates real UUIDs and records them
    - REPLAYING: Replay mode - returns pre-recorded UUIDs in sequence

Architecture:
    During recording, each UUID generated is captured and stored for later
    replay. During replay, the injector returns pre-recorded UUIDs in the
    exact sequence they were recorded, ensuring deterministic execution.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.injector_uuid import InjectorUUID
        from omnibase_core.enums.replay import EnumRecorderMode
        from uuid import UUID

        # Production mode (default): generates real UUIDs
        uuid_svc = InjectorUUID()
        new_id = uuid_svc.uuid4()

        # Recording mode: captures UUIDs as they're generated
        recording_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
        id1 = recording_svc.uuid4()
        id2 = recording_svc.uuid4()
        recorded = recording_svc.get_recorded()

        # Replay mode: returns pre-recorded UUIDs in sequence
        replay_svc = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING,
            recorded_uuids=recorded,
        )
        assert replay_svc.uuid4() == id1
        assert replay_svc.uuid4() == id2

Key Invariant:
    Recording + Replay -> Same UUIDs (determinism for replay)

    .. code-block:: python

        # Record
        rec = InjectorUUID(mode=EnumRecorderMode.RECORDING)
        id1 = rec.uuid4()
        id2 = rec.uuid4()
        recorded = rec.get_recorded()

        # Replay
        replay = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING,
            recorded_uuids=recorded,
        )
        assert replay.uuid4() == id1
        assert replay.uuid4() == id2

Thread Safety:
    InjectorUUID instances are NOT thread-safe. The sequence counter
    and internal recording list are mutable state that is not protected.
    Use separate instances per thread for concurrent usage.

Related:
    - OMN-1150: Replay Safety Enforcement
    - ProtocolUUIDService: Protocol definition
    - InjectorRNG: Similar pattern for random number generation
    - InjectorTime: Similar pattern for time injection

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["InjectorUUID"]

import uuid as uuid_module
from collections.abc import Callable
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
from omnibase_core.errors import ModelOnexError
from omnibase_core.protocols.replay.protocol_uuid_service import ProtocolUUIDService


class InjectorUUID:
    """
    UUID injector for deterministic replay.

    Generates real UUIDs in production/recording mode and replays
    pre-recorded UUIDs in sequence during replay mode.

    Args:
        mode: Operating mode (PASS_THROUGH, RECORDING, or REPLAYING).
            Defaults to PASS_THROUGH for production use.
        recorded_uuids: Pre-recorded UUIDs for replay mode. Only used when
            mode is REPLAYING. Defaults to empty list.

    Attributes:
        is_recording: Whether the injector is in recording mode.
        is_replaying: Whether the injector is in replay mode.

    Example:
        >>> from omnibase_core.services.replay.injector_uuid import InjectorUUID
        >>> from omnibase_core.enums.replay import EnumRecorderMode
        >>> # Production mode (default)
        >>> uuid_svc = InjectorUUID()
        >>> uuid_svc.is_recording
        False
        >>> uuid_svc.is_replaying
        False
        >>>
        >>> # Recording mode
        >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
        >>> uuid_svc.is_recording
        True

    Thread Safety:
        Not thread-safe. Use separate instances per thread.

    .. versionadded:: 0.6.3
    """

    def __init__(
        self,
        mode: EnumRecorderMode = EnumRecorderMode.PASS_THROUGH,
        recorded_uuids: list[UUID] | None = None,
    ) -> None:
        """
        Initialize the UUID injector.

        Args:
            mode: Operating mode. Defaults to PASS_THROUGH.
            recorded_uuids: Pre-recorded UUIDs for replay mode.
        """
        self._mode = mode
        self._recorded: list[UUID] = list(recorded_uuids) if recorded_uuids else []
        self._sequence_index = 0

    @property
    def is_recording(self) -> bool:
        """
        Return whether the injector is in recording mode.

        Returns:
            bool: True if in recording mode, False otherwise.

        Example:
            >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
            >>> uuid_svc.is_recording
            True
        """
        return self._mode == EnumRecorderMode.RECORDING

    @property
    def is_replaying(self) -> bool:
        """
        Return whether the injector is in replay mode.

        Returns:
            bool: True if in replay mode, False otherwise.

        Example:
            >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.REPLAYING, recorded_uuids=[])
            >>> uuid_svc.is_replaying
            True
        """
        return self._mode == EnumRecorderMode.REPLAYING

    def _generate_or_replay(self, generator: Callable[[], UUID]) -> UUID:
        """
        Generate a new UUID or replay a recorded one.

        Args:
            generator: Function to call to generate a new UUID (uuid.uuid1 or uuid.uuid4).

        Returns:
            UUID: Either a newly generated UUID or a replayed one.

        Raises:
            ModelOnexError: If in replay mode and sequence is exhausted.
        """
        if self._mode == EnumRecorderMode.REPLAYING:
            if self._sequence_index >= len(self._recorded):
                raise ModelOnexError(
                    message=(
                        f"UUID replay sequence exhausted: requested index "
                        f"{self._sequence_index} but only {len(self._recorded)} "
                        f"UUIDs were recorded"
                    ),
                    error_code=EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED,
                    sequence_index=self._sequence_index,
                    recorded_count=len(self._recorded),
                )
            result = self._recorded[self._sequence_index]
            self._sequence_index += 1
            return result
        else:
            # PASS_THROUGH or RECORDING mode: generate real UUID
            result = generator()
            if self._mode == EnumRecorderMode.RECORDING:
                self._recorded.append(result)
            return result

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
            >>> uuid_svc = InjectorUUID()
            >>> new_id = uuid_svc.uuid4()
            >>> new_id.version == 4  # Random UUID
            True
        """
        return self._generate_or_replay(uuid_module.uuid4)

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
            >>> uuid_svc = InjectorUUID()
            >>> time_id = uuid_svc.uuid1()
            >>> time_id.version == 1  # Time-based UUID
            True
        """
        return self._generate_or_replay(uuid_module.uuid1)

    def get_recorded(self) -> list[UUID]:
        """
        Get all recorded UUIDs for persistence.

        Returns a copy of the recorded UUIDs list for storage in the
        execution manifest. Returns an empty list if not in recording mode.

        Returns:
            list[UUID]: Copy of all UUIDs recorded during this session.

        Example:
            >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
            >>> id1 = uuid_svc.uuid4()
            >>> id2 = uuid_svc.uuid4()
            >>> recorded = uuid_svc.get_recorded()
            >>> len(recorded)
            2
        """
        return list(self._recorded)

    def reset(self) -> None:
        """
        Reset sequence index for replay restart.

        Resets the replay sequence counter to the beginning, allowing
        the same recorded UUIDs to be replayed again. Useful for
        re-running a pipeline with the same recorded data.

        In recording mode, this clears all recorded UUIDs.
        In pass-through mode, this is a no-op.

        Example:
            >>> from uuid import UUID
            >>> recorded = [UUID("550e8400-e29b-41d4-a716-446655440000")]
            >>> uuid_svc = InjectorUUID(
            ...     mode=EnumRecorderMode.REPLAYING,
            ...     recorded_uuids=recorded,
            ... )
            >>> id1 = uuid_svc.uuid4()
            >>> uuid_svc.reset()
            >>> id1_again = uuid_svc.uuid4()
            >>> id1 == id1_again
            True
        """
        self._sequence_index = 0
        if self._mode == EnumRecorderMode.RECORDING:
            self._recorded.clear()

    @property
    def sequence_index(self) -> int:
        """
        Return the current sequence index.

        Returns:
            int: The current position in the UUID sequence.

        Example:
            >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
            >>> uuid_svc.sequence_index
            0
            >>> _ = uuid_svc.uuid4()
            >>> uuid_svc.sequence_index
            0  # Recording mode doesn't advance sequence_index
        """
        return self._sequence_index

    @property
    def recorded_count(self) -> int:
        """
        Return the number of recorded UUIDs.

        Returns:
            int: Number of UUIDs in the recorded list.

        Example:
            >>> uuid_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
            >>> uuid_svc.recorded_count
            0
            >>> _ = uuid_svc.uuid4()
            >>> uuid_svc.recorded_count
            1
        """
        return len(self._recorded)


# Verify protocol compliance at module load time
_uuid_check: ProtocolUUIDService = InjectorUUID()
