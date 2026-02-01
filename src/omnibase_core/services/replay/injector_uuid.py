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
    InjectorUUID instances are NOT thread-safe.

    **Mutable State**: ``_sequence_index`` (int), ``_recorded`` (list).

    **Recommended Patterns**:
        - Use separate instances per thread (preferred)
        - Or wrap ``uuid4()``/``uuid1()`` calls with ``threading.Lock``

    See ``docs/guides/THREADING.md`` for comprehensive guidance.

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
        sequence_index: Current position in replay sequence.
        recorded_count: Number of recorded UUIDs.

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

    Integration:
        **With ServiceReplaySafetyEnforcer**:

        The UUID injector integrates with the replay safety enforcer to provide
        deterministic UUID generation during replay. Pass the injector to the
        enforcer for automatic UUID mocking in MOCKED mode:

        .. code-block:: python

            from omnibase_core.services.replay.injector_uuid import InjectorUUID
            from omnibase_core.services.replay.service_replay_safety_enforcer import (
                ServiceReplaySafetyEnforcer,
            )
            from omnibase_core.enums.replay import EnumEnforcementMode, EnumRecorderMode

            # Create UUID injector with recorded data for replay
            uuid_injector = InjectorUUID(
                mode=EnumRecorderMode.REPLAYING,
                recorded_uuids=manifest.recorded_uuids,
            )

            # Pass to enforcer for automatic mocking
            enforcer = ServiceReplaySafetyEnforcer(
                mode=EnumEnforcementMode.MOCKED,
                uuid_injector=uuid_injector,
            )

        **With Pipeline Context**:

        In pipeline execution, the injector is typically accessed via the
        pipeline context for consistent UUID generation across all nodes:

        .. code-block:: python

            class MyEffectNode(NodeEffect):
                async def execute_effect(self, ctx: ProtocolPipelineContext):
                    # Use context's UUID service instead of uuid.uuid4()
                    new_id = ctx.uuid.uuid4()
                    return {"id": str(new_id)}

        **Recording and Replay Workflow**:

        1. **Recording Phase**: Create an injector in RECORDING mode during
           initial execution to capture UUIDs:

           .. code-block:: python

               recorder = InjectorUUID(mode=EnumRecorderMode.RECORDING)
               # Execute pipeline with recorder...
               recorded_uuids = recorder.get_recorded()
               # Store in execution manifest

        2. **Replay Phase**: Create an injector in REPLAYING mode with the
           stored UUIDs to reproduce the exact sequence:

           .. code-block:: python

               replayer = InjectorUUID(
                   mode=EnumRecorderMode.REPLAYING,
                   recorded_uuids=manifest.recorded_uuids,
               )
               # Execute pipeline - UUIDs match original execution

        **With Other Injectors**:

        InjectorUUID follows the same pattern as InjectorTime and InjectorRNG.
        They can be used together for complete determinism:

        .. code-block:: python

            from omnibase_core.services.replay.injector_time import InjectorTime
            from omnibase_core.services.replay.injector_rng import InjectorRNG

            # Create a fully deterministic replay context
            time_injector = InjectorTime(fixed_time=manifest.recorded_time)
            rng_injector = InjectorRNG(seed=manifest.rng_seed)
            uuid_injector = InjectorUUID(
                mode=EnumRecorderMode.REPLAYING,
                recorded_uuids=manifest.recorded_uuids,
            )

    Thread Safety:
        NOT thread-safe. Mutable state: ``_sequence_index``, ``_recorded`` list.
        Use separate instances per thread or synchronize access.
        See ``docs/guides/THREADING.md``.

    See Also:
        - :class:`InjectorTime`: Time injection for replay.
        - :class:`InjectorRNG`: RNG injection for replay.
        - :class:`ServiceReplaySafetyEnforcer`: Policy enforcement integration.
        - :class:`RecorderEffect`: Effect recording for network/database replay.

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
                # Build helpful error context
                recorded_count = len(self._recorded)
                # Show recorded UUIDs if few, for debugging
                recorded_preview = (
                    [str(u) for u in self._recorded[:5]]
                    if recorded_count <= 5
                    else [str(u) for u in self._recorded[:3]] + ["..."]
                )
                raise ModelOnexError(
                    message=(
                        f"UUID replay sequence exhausted: requested UUID "
                        f"#{self._sequence_index + 1} but only {recorded_count} "
                        f"UUID(s) were recorded during the original run. "
                        f"This typically means the code path during replay "
                        f"generated more UUIDs than the original recording. "
                        f"Possible causes: (1) conditional logic that wasn't "
                        f"executed during recording, (2) retry logic generating "
                        f"additional UUIDs, (3) recording was incomplete. "
                        f"To fix: re-record the execution with all code paths "
                        f"exercised, or check for non-deterministic control flow."
                    ),
                    error_code=EnumCoreErrorCode.REPLAY_SEQUENCE_EXHAUSTED,
                    sequence_index=self._sequence_index,
                    recorded_count=recorded_count,
                    recorded_uuids_preview=recorded_preview,
                    hint="Re-run in RECORDING mode to capture all UUIDs",
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
        Return the current sequence index for replay position tracking.

        The sequence index tracks the current position when replaying pre-recorded
        UUIDs. It indicates how many UUIDs have been consumed from the recorded
        sequence during replay.

        Mode-specific behavior:
            - **PASS_THROUGH**: Always 0 (no sequence tracking needed).
            - **RECORDING**: Always 0 (UUIDs are appended to ``_recorded`` list,
              not consumed from a sequence).
            - **REPLAYING**: Increments with each ``uuid4()`` or ``uuid1()`` call,
              indicating the next UUID position to return.

        Returns:
            int: The current position in the UUID sequence. In REPLAYING mode,
                this equals the number of UUIDs that have been replayed. In
                other modes, this is always 0.

        Example:
            >>> from uuid import UUID
            >>> from omnibase_core.services.replay.injector_uuid import InjectorUUID
            >>> from omnibase_core.enums.replay import EnumRecorderMode
            >>>
            >>> # Recording mode: sequence_index stays at 0
            >>> rec_svc = InjectorUUID(mode=EnumRecorderMode.RECORDING)
            >>> rec_svc.sequence_index
            0
            >>> _ = rec_svc.uuid4()
            >>> rec_svc.sequence_index  # Still 0 in recording mode
            0
            >>> rec_svc.recorded_count  # But recorded_count increases
            1
            >>>
            >>> # Replay mode: sequence_index advances with each call
            >>> recorded = rec_svc.get_recorded()
            >>> replay_svc = InjectorUUID(
            ...     mode=EnumRecorderMode.REPLAYING,
            ...     recorded_uuids=recorded,
            ... )
            >>> replay_svc.sequence_index  # Before any calls
            0
            >>> _ = replay_svc.uuid4()
            >>> replay_svc.sequence_index  # After one call
            1

        Note:
            To check how many UUIDs remain in replay mode, compare
            ``sequence_index`` with ``recorded_count``:

            >>> remaining = replay_svc.recorded_count - replay_svc.sequence_index

        See Also:
            - :meth:`recorded_count`: Total number of recorded UUIDs.
            - :meth:`reset`: Resets sequence_index to 0 for replay restart.
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
