"""
Projector Column Model.

Defines a column in a projector with event field mapping. Columns specify how
event data is mapped to projection table columns.

This module provides:
    - :class:`ModelProjectorColumn`: Pydantic model for column definition

Column Types:
    The `type` field accepts any SQL type as a string for maximum extensibility.
    Common types include: UUID, TEXT, JSONB, TIMESTAMPTZ, INTEGER, BOOLEAN.

Source Paths:
    The `source` field specifies the path to extract data from the event.
    Examples:
        - "event.payload.node_name" - Field from event payload
        - "event.metadata.event_id" - Field from event metadata
        - "envelope.sequence_number" - Field from envelope

Example Usage:
    >>> from omnibase_core.models.projectors import ModelProjectorColumn
    >>>
    >>> # Simple column mapping
    >>> column = ModelProjectorColumn(
    ...     name="node_name",
    ...     type="TEXT",
    ...     source="event.payload.node_name",
    ... )
    >>>
    >>> # Column with conditional update
    >>> status_col = ModelProjectorColumn(
    ...     name="status",
    ...     type="TEXT",
    ...     source="event.payload.status",
    ...     on_event="node.status.changed.v1",
    ...     default="UNKNOWN",
    ... )

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1166 projector contract models.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelProjectorColumn(BaseModel):
    """Column definition with event field mapping.

    Defines how a column in a projection table is populated from event data.
    Each column specifies its name, SQL type, and the source path for data
    extraction.

    Attributes:
        name: Column name in the projection table. Must be a valid SQL column
            identifier.
        type: SQL column type as a string (e.g., "UUID", "TEXT", "JSONB",
            "TIMESTAMPTZ", "INTEGER", "BOOLEAN"). String type allows maximum
            extensibility for different database backends.
        source: Path to extract data from the event. Supports dotted notation
            for nested access (e.g., "event.payload.node_name",
            "event.metadata.event_id", "envelope.sequence_number").
        on_event: Optional event type filter. When specified, this column is
            only updated when processing events of this specific type.
            Use for columns that should only change on certain events.
        default: Optional default value as a string. Used when the source
            path yields no value or the column is created before any
            relevant event is processed.

    Examples:
        Create a simple text column:

        >>> column = ModelProjectorColumn(
        ...     name="node_name",
        ...     type="TEXT",
        ...     source="event.payload.node_name",
        ... )

        Create a column with conditional update:

        >>> status_col = ModelProjectorColumn(
        ...     name="status",
        ...     type="TEXT",
        ...     source="event.payload.status",
        ...     on_event="node.status.changed.v1",
        ...     default="UNKNOWN",
        ... )

        Create a timestamp column:

        >>> timestamp_col = ModelProjectorColumn(
        ...     name="created_at",
        ...     type="TIMESTAMPTZ",
        ...     source="event.payload.created_at",
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
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        description="Column name in the projection table",
    )

    type: str = Field(
        ...,
        description=(
            "SQL column type (e.g., 'UUID', 'TEXT', 'JSONB', 'TIMESTAMPTZ', "
            "'INTEGER', 'BOOLEAN'). String type for extensibility."
        ),
    )

    source: str = Field(
        ...,
        description=(
            "Path to extract data from the event. Supports dotted notation "
            "(e.g., 'event.payload.node_name', 'envelope.sequence_number')."
        ),
    )

    on_event: str | None = Field(
        default=None,
        description=(
            "Optional event type filter. When specified, column is only "
            "updated when processing events of this specific type."
        ),
    )

    default: str | None = Field(
        default=None,
        description=(
            "Optional default value. Used when source path yields no value "
            "or column is created before any relevant event."
        ),
    )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing column name and type.

        Examples:
            >>> col = ModelProjectorColumn(
            ...     name="status",
            ...     type="TEXT",
            ...     source="event.payload.status",
            ... )
            >>> repr(col)
            "ModelProjectorColumn(name='status', type='TEXT')"
        """
        return f"ModelProjectorColumn(name={self.name!r}, type={self.type!r})"


__all__ = ["ModelProjectorColumn"]
