"""
ModelReplayContext - Replay context model for deterministic replay infrastructure.

This module provides the ModelReplayContext which bundles all determinism data
(time, RNG seed, effect recordings) needed to replay an execution.

Design:
    ModelReplayContext serves as an immutable value object that captures all
    non-deterministic sources in pipeline execution:

    - **Time**: Fixed timestamp for deterministic time queries
    - **RNG**: Seed value for reproducible random number generation
    - **Effects**: Record IDs for external call stubbing

    The frozen (immutable) design ensures thread-safety and enables functional
    updates via `with_time_capture` and `with_effect_record` methods.

Architecture:
    ReplaySession holds a ModelReplayContext to track the replay state. During
    recording, the context accumulates time captures and effect record IDs.
    During replay, the context provides the frozen time and RNG seed for
    deterministic execution.

    ::

        ExecutorReplay
            |
            +-- create_recording_session()
            |       -> ReplaySession(context=ModelReplayContext(mode=RECORDING))
            |
            +-- create_replay_session()
                    -> ReplaySession(context=ModelReplayContext(mode=REPLAYING))

Thread Safety:
    ModelReplayContext is frozen (immutable) after creation, making it safe
    to share across threads. All update methods return new instances rather
    than mutating in place.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelReplayContext
        from omnibase_core.enums.replay import EnumReplayMode
        from datetime import datetime, timezone
        from uuid import uuid4

        # Recording mode - capture execution data
        ctx = ModelReplayContext(
            mode=EnumReplayMode.RECORDING,
            rng_seed=42,
        )

        # Immutable update - capture time call
        ctx = ctx.with_time_capture(datetime.now(timezone.utc))

        # Immutable update - capture effect record
        ctx = ctx.with_effect_record(uuid4())

        # Replaying mode - use captured data for determinism
        replay_ctx = ModelReplayContext(
            mode=EnumReplayMode.REPLAYING,
            time_frozen_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
            rng_seed=42,
            effect_record_ids=tuple(recorded_ids),
            original_execution_id=original_context_id,
        )

Related:
    - OMN-1116: Implement Replay Infrastructure
    - ReplaySession: Uses ModelReplayContext for state tracking
    - ExecutorReplay: Creates contexts via session factory methods

.. versionadded:: 0.4.0
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode


class ModelReplayContext(BaseModel):
    """Determinism context for replay infrastructure.

    Bundles all data needed to deterministically replay an execution:

    - **Fixed time**: For time injection (frozen clock during replay)
    - **RNG seed**: For random injection (deterministic random numbers)
    - **Effect records**: For external call stubbing (recorded I/O results)

    This model is frozen and immutable, making it thread-safe for concurrent
    read access. Use the `with_time_capture` and `with_effect_record` methods
    for immutable updates that return new instances.

    Attributes:
        context_id: Unique identifier for this context.
        mode: Replay mode (production/recording/replaying).
        time_frozen_at: Fixed time for replay (None = use current time).
        time_captures: All time.now() calls captured during recording.
        rng_seed: Random seed for deterministic RNG.
        effect_record_ids: IDs of effect records (stored separately).
        original_execution_id: ID of original execution (if replaying).
        created_at: When context was created.

    Thread Safety:
        This model is frozen (immutable) after creation, making it thread-safe
        for concurrent read access. All update methods return new instances.

    Example:
        Recording mode - capture execution::

            ctx = ModelReplayContext(
                mode=EnumReplayMode.RECORDING,
                rng_seed=42,
            )

            # Capture time calls
            ctx = ctx.with_time_capture(datetime.now(timezone.utc))

            # Capture effect records
            ctx = ctx.with_effect_record(record_id)

        Replaying mode - use captured data::

            ctx = ModelReplayContext(
                mode=EnumReplayMode.REPLAYING,
                time_frozen_at=recorded_time,
                rng_seed=recorded_seed,
                effect_record_ids=recorded_ids,
                original_execution_id=original_id,
            )

    Key Invariant:
        Same context + same inputs = Same outputs::

            # Using a replay context with frozen time, fixed seed,
            # and recorded effects guarantees deterministic execution
            ctx = ModelReplayContext(
                mode=EnumReplayMode.REPLAYING,
                time_frozen_at=fixed_time,
                rng_seed=42,
                effect_record_ids=recorded_ids,
            )

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identification
    context_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this replay context",
    )

    # Replay mode
    mode: EnumReplayMode = Field(
        default=EnumReplayMode.PRODUCTION,
        description="Replay mode (production/recording/replaying)",
    )

    # Time determinism
    time_frozen_at: datetime | None = Field(
        None,
        description="Fixed time for replay (None = use current time)",
    )
    time_captures: tuple[datetime, ...] = Field(
        default_factory=tuple,
        description="All time.now() calls captured during recording",
    )

    # RNG determinism
    rng_seed: int | None = Field(
        None,
        description="Random seed for deterministic RNG",
    )

    # Effect determinism (reference to effect records)
    effect_record_ids: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="IDs of effect records (stored separately)",
    )

    # Metadata
    original_execution_id: UUID | None = Field(
        None,
        description="ID of original execution (if replaying)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When context was created",
    )

    @property
    def is_production(self) -> bool:
        """Check if in production mode.

        Returns:
            True if mode is PRODUCTION, False otherwise.
        """
        return self.mode == EnumReplayMode.PRODUCTION

    @property
    def is_recording(self) -> bool:
        """Check if in recording mode.

        Returns:
            True if mode is RECORDING, False otherwise.
        """
        return self.mode == EnumReplayMode.RECORDING

    @property
    def is_replaying(self) -> bool:
        """Check if in replay mode.

        Returns:
            True if mode is REPLAYING, False otherwise.
        """
        return self.mode == EnumReplayMode.REPLAYING

    def with_time_capture(self, time: datetime) -> "ModelReplayContext":
        """Return new context with additional time capture.

        Creates a new immutable context with the given time appended to
        the time_captures tuple. The original context is not modified.

        Args:
            time: The datetime to capture.

        Returns:
            A new ModelReplayContext with the time added to time_captures.

        Example:
            >>> ctx = ModelReplayContext(mode=EnumReplayMode.RECORDING)
            >>> now = datetime.now(timezone.utc)
            >>> ctx = ctx.with_time_capture(now)
            >>> len(ctx.time_captures)
            1
        """
        return self.model_copy(update={"time_captures": (*self.time_captures, time)})

    def with_effect_record(self, record_id: UUID) -> "ModelReplayContext":
        """Return new context with additional effect record.

        Creates a new immutable context with the given record ID appended to
        the effect_record_ids tuple. The original context is not modified.

        Args:
            record_id: The UUID of the effect record to add.

        Returns:
            A new ModelReplayContext with the record ID added to effect_record_ids.

        Example:
            >>> ctx = ModelReplayContext(mode=EnumReplayMode.RECORDING)
            >>> record_id = uuid4()
            >>> ctx = ctx.with_effect_record(record_id)
            >>> len(ctx.effect_record_ids)
            1
        """
        return self.model_copy(
            update={"effect_record_ids": (*self.effect_record_ids, record_id)}
        )


__all__ = ["ModelReplayContext"]
