"""
Partial Update Operation Model for Projector Contracts.

Defines a partial update operation that updates only specific columns in a
projection table when triggered by a specific event, without requiring a
full upsert of all columns.

This module provides:
    - :class:`ModelPartialUpdateOperation`: Pydantic model for partial update definition

Use Cases:
    - **Heartbeat Update**: Updates only ``last_heartbeat_at`` and ``liveness_deadline``
      columns when receiving heartbeat events.
    - **State Transition**: Updates only ``current_state`` column without full idempotency
      checking (state transitions are inherently idempotent by design).
    - **Timeout Markers**: Updates single columns like ``ack_timeout_emitted_at`` or
      ``liveness_timeout_emitted_at`` when timeout events occur.

Example Usage:
    >>> from omnibase_core.models.projectors import ModelPartialUpdateOperation
    >>>
    >>> # Heartbeat update
    >>> heartbeat_op = ModelPartialUpdateOperation(
    ...     name="heartbeat",
    ...     columns=["last_heartbeat_at", "liveness_deadline"],
    ...     trigger_event="node.heartbeat.v1",
    ... )
    >>>
    >>> # State transition (skip idempotency)
    >>> state_op = ModelPartialUpdateOperation(
    ...     name="state_transition",
    ...     columns=["current_state", "updated_at"],
    ...     trigger_event="node.state.changed.v1",
    ...     skip_idempotency=True,
    ... )
    >>>
    >>> # Timeout marker with condition
    >>> timeout_op = ModelPartialUpdateOperation(
    ...     name="ack_timeout_marker",
    ...     columns=["ack_timeout_emitted_at"],
    ...     trigger_event="node.ack.timeout.v1",
    ...     condition="ack_timeout_emitted_at IS NULL",
    ... )

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.5.0
    Initial implementation as part of OMN-1170 partial update support.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Event naming pattern: lowercase segments separated by dots, version suffix
# Pattern: ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$
EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$")


class ModelPartialUpdateOperation(BaseModel):
    """Partial update operation definition for projector contracts.

    Defines a named partial update operation that targets specific columns
    and is triggered by a specific event. Partial updates are more efficient
    than full upserts when only a subset of columns needs to be updated.

    Partial updates are particularly useful for:
        - High-frequency updates (e.g., heartbeats) that should not trigger
          full column recalculation.
        - State transitions where only the state column changes.
        - Timeout markers that set a single timestamp column.

    Attributes:
        name: Unique identifier for the partial update operation within the
            projector contract. Used for logging, metrics, and debugging.
        columns: List of column names to update. Must contain at least one
            column. Column names must reference columns defined in the
            projection schema (validated at contract level).
        trigger_event: Event name that triggers this partial update. Must
            match the event naming pattern (lowercase.segments.vN).
        skip_idempotency: Whether to skip idempotency checking for this
            operation. Defaults to False. Set to True for operations that
            are inherently idempotent by design (e.g., state transitions
            where the new state is deterministic).
        condition: Optional SQL condition for when to apply the update.
            Use for conditional updates like "only if not already set".
            Example: ``"ack_timeout_emitted_at IS NULL"``.

    Examples:
        Create a heartbeat update operation:

        >>> op = ModelPartialUpdateOperation(
        ...     name="heartbeat",
        ...     columns=["last_heartbeat_at", "liveness_deadline"],
        ...     trigger_event="node.heartbeat.v1",
        ... )

        Create a state transition operation with idempotency skipped:

        >>> op = ModelPartialUpdateOperation(
        ...     name="state_transition",
        ...     columns=["current_state", "updated_at"],
        ...     trigger_event="node.state.changed.v1",
        ...     skip_idempotency=True,
        ... )

        Create a conditional timeout marker:

        >>> op = ModelPartialUpdateOperation(
        ...     name="ack_timeout_marker",
        ...     columns=["ack_timeout_emitted_at"],
        ...     trigger_event="node.ack.timeout.v1",
        ...     condition="ack_timeout_emitted_at IS NULL",
        ... )

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports the class independently, creating separate
        class objects. The ``from_attributes=True`` flag enables Pydantic's
        "duck typing" mode, allowing fixtures from one worker to be validated
        in another.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.

    See Also:
        - :class:`ModelProjectorContract`: Main contract that contains partial updates
        - :class:`ModelProjectorBehavior`: Main behavior configuration
        - :class:`ModelIdempotencyConfig`: Idempotency configuration
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        description=(
            "Unique identifier for the partial update operation. "
            "Used for logging, metrics, and debugging."
        ),
        min_length=1,
    )

    columns: list[str] = Field(
        ...,
        description=(
            "List of column names to update. Must contain at least one column. "
            "Column names must reference columns defined in the projection schema."
        ),
        min_length=1,
    )

    trigger_event: str = Field(
        ...,
        description=(
            "Event name that triggers this partial update. "
            "Must match pattern: lowercase.segments.vN (e.g., 'node.heartbeat.v1')."
        ),
    )

    skip_idempotency: bool = Field(
        default=False,
        description=(
            "Whether to skip idempotency checking for this operation. "
            "Set to True for inherently idempotent operations like state transitions."
        ),
    )

    condition: str | None = Field(
        default=None,
        description=(
            "Optional SQL condition for when to apply the update. "
            "Example: 'ack_timeout_emitted_at IS NULL' for conditional marker setting."
        ),
    )

    @field_validator("trigger_event")
    @classmethod
    def validate_trigger_event_pattern(cls, v: str) -> str:
        """Validate trigger_event matches the event naming pattern.

        The event name must:
        - Start with a lowercase letter
        - Contain only lowercase letters, digits, underscores, and dots
        - Have segments separated by dots
        - End with a version suffix (e.g., .v1, .v2)

        Args:
            v: Event name to validate

        Returns:
            The validated event name

        Raises:
            ValueError: If event name doesn't match the pattern

        Examples:
            Valid event names:
                - "node.heartbeat.v1"
                - "node.state.changed.v2"
                - "order_management.timeout.v1"

            Invalid event names:
                - "Node.Heartbeat.v1" (uppercase)
                - "node-heartbeat.v1" (hyphen)
                - "node.heartbeat" (missing version)
        """
        if not EVENT_NAME_PATTERN.match(v):
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                f"Invalid trigger_event '{v}'. "
                f"Must match pattern: lowercase.segments.vN "
                f"(e.g., 'node.heartbeat.v1')"
            )
        return v

    def __hash__(self) -> int:
        """Return hash value for the partial update operation.

        Custom implementation to support hashing with list field.
        Converts columns list to tuple for hashing.
        """
        return hash(
            (
                self.name,
                tuple(self.columns),
                self.trigger_event,
                self.skip_idempotency,
                self.condition,
            )
        )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing name, column count, and trigger event.

        Examples:
            >>> op = ModelPartialUpdateOperation(
            ...     name="heartbeat",
            ...     columns=["last_heartbeat_at", "liveness_deadline"],
            ...     trigger_event="node.heartbeat.v1",
            ... )
            >>> repr(op)
            "ModelPartialUpdateOperation(name='heartbeat', columns=2, trigger='node.heartbeat.v1')"
        """
        return (
            f"ModelPartialUpdateOperation(name={self.name!r}, "
            f"columns={len(self.columns)}, trigger={self.trigger_event!r})"
        )


__all__ = ["ModelPartialUpdateOperation"]
