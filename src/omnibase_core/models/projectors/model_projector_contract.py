"""
Projector Contract Model.

Defines the complete declarative contract for a projector, including its
identity, event subscriptions, schema, and behavior configuration.

Core Principle:
    "Projectors are consumers of ModelEventEnvelope streams, not participants
    in handler dispatch. They never emit events, intents, or projections."

This module provides:
    - :class:`ModelProjectorContract`: Complete projector definition

Contract Components:
    - **projector_kind**: Type of projector (currently only "materialized_view")
    - **projector_id**: Unique identifier for the projector
    - **name**: Human-readable name
    - **version**: Contract version string
    - **aggregate_type**: Semantic aggregate type identifier
    - **consumed_events**: List of event names to consume (pattern validated)
    - **projection_schema**: Database schema definition (ModelProjectorSchema)
    - **behavior**: Projection behavior configuration (ModelProjectorBehavior)

Event Naming Pattern:
    Event names must follow the pattern: ``lowercase_segments.separated.by.dots.vN``

    Valid examples:
        - ``node.created.v1``
        - ``order_management.order_line_item_added.v2``
        - ``payment.payment_received.v1``

    Invalid examples:
        - ``Node.Created.v1`` (uppercase not allowed)
        - ``node-service.created.v1`` (hyphens not allowed)
        - ``node.created`` (missing version)

Example Usage:
    >>> from omnibase_core.models.projectors import (
    ...     ModelIdempotencyConfig,
    ...     ModelProjectorBehavior,
    ...     ModelProjectorColumn,
    ...     ModelProjectorContract,
    ...     ModelProjectorSchema,
    ... )
    >>>
    >>> # Define schema
    >>> column = ModelProjectorColumn(
    ...     name="node_id",
    ...     type="UUID",
    ...     source="event.payload.node_id",
    ... )
    >>> schema = ModelProjectorSchema(
    ...     table="node_projections",
    ...     primary_key="node_id",
    ...     columns=[column],
    ... )
    >>>
    >>> # Define behavior
    >>> behavior = ModelProjectorBehavior(
    ...     mode="upsert",
    ...     upsert_key="node_id",
    ...     idempotency=ModelIdempotencyConfig(enabled=True, key="event_id"),
    ... )
    >>>
    >>> # Create contract
    >>> contract = ModelProjectorContract(
    ...     projector_kind="materialized_view",
    ...     projector_id="node-status-projector",
    ...     name="Node Status Projector",
    ...     version="1.0.0",
    ...     aggregate_type="node",
    ...     consumed_events=["node.created.v1", "node.updated.v1"],
    ...     projection_schema=schema,
    ...     behavior=behavior,
    ... )

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1166 projector contract models.
"""

import re
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.projectors.model_partial_update_operation import (
    ModelPartialUpdateOperation,
)
from omnibase_core.models.projectors.model_projector_behavior import (
    ModelProjectorBehavior,
)
from omnibase_core.models.projectors.model_projector_schema import ModelProjectorSchema

# Event naming pattern: lowercase segments separated by dots, version suffix
# Pattern: ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$
# - Must start with lowercase letter
# - Segments can contain lowercase letters, digits, and underscores
# - Segments separated by dots
# - Must end with .vN version suffix
EVENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$")


class ModelProjectorContract(BaseModel):
    """Declarative projector contract definition.

    Defines the complete contract for a projector including its identity,
    event subscriptions, schema definition, and behavior configuration.

    Projectors consume ModelEventEnvelope streams to materialize read-optimized
    views of aggregate state. They never emit events, intents, or projections
    themselves.

    Attributes:
        projector_kind: Type of projector. Currently only "materialized_view"
            is supported. Extensible for future projector types.
        projector_id: Unique identifier for the projector. Used for registration
            and routing.
        name: Human-readable name for the projector.
        version: Contract version string (e.g., "1.0.0"). Used for version
            validation, compatibility checking, and migration tracking.
        aggregate_type: Semantic string identifier for the aggregate type this
            projector handles.
        consumed_events: List of event names this projector subscribes to.
            Each event name must match the pattern: lowercase.segments.vN
        projection_schema: Database schema definition including table, columns,
            and indexes. Named ``projection_schema`` to avoid conflict with
            Pydantic's ``BaseModel.schema`` method.
        behavior: Projection behavior configuration including mode and idempotency.

    Examples:
        Create a node status projector:

        >>> from omnibase_core.models.projectors import (
        ...     ModelProjectorBehavior,
        ...     ModelProjectorColumn,
        ...     ModelProjectorContract,
        ...     ModelProjectorSchema,
        ... )
        >>> column = ModelProjectorColumn(
        ...     name="node_id",
        ...     type="UUID",
        ...     source="event.payload.node_id",
        ... )
        >>> schema = ModelProjectorSchema(
        ...     table="nodes",
        ...     primary_key="node_id",
        ...     columns=[column],
        ... )
        >>> behavior = ModelProjectorBehavior(mode="upsert")
        >>> contract = ModelProjectorContract(
        ...     projector_kind="materialized_view",
        ...     projector_id="node-projector",
        ...     name="Node Projector",
        ...     version="1.0.0",
        ...     aggregate_type="node",
        ...     consumed_events=["node.created.v1"],
        ...     projection_schema=schema,
        ...     behavior=behavior,
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
        - :class:`ModelProjectorSchema`: Schema definition for projection tables
        - :class:`ModelProjectorBehavior`: Behavior configuration for projectors
        - :class:`ModelIdempotencyConfig`: Idempotency configuration
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Class variable for event name pattern (for reference)
    EVENT_NAME_PATTERN: ClassVar[re.Pattern[str]] = EVENT_NAME_PATTERN

    projector_kind: Literal["materialized_view"] = Field(
        ...,
        description="Type of projector. Currently only 'materialized_view' is supported.",
    )

    projector_id: str = Field(  # string-id-ok: user-facing projector identifier
        ...,
        description="Unique identifier for the projector",
        min_length=1,
    )

    name: str = Field(
        ...,
        description="Human-readable name for the projector",
        min_length=1,
    )

    version: str = Field(
        ...,
        description="Contract version string (e.g., '1.0.0')",
        min_length=1,
    )

    aggregate_type: str = Field(
        ...,
        description="Semantic identifier for the aggregate type this projector handles",
        min_length=1,
    )

    consumed_events: list[str] = Field(
        ...,
        description=(
            "List of event names to consume. Must contain at least one event. "
            "Each event name must match pattern: lowercase.segments.vN"
        ),
        min_length=1,
        json_schema_extra={
            "items": {
                "type": "string",
                "pattern": r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$",
            }
        },
    )

    projection_schema: ModelProjectorSchema = Field(
        ...,
        description="Database schema definition for the projection",
    )

    behavior: ModelProjectorBehavior = Field(
        ...,
        description="Projection behavior configuration",
    )

    partial_updates: list[ModelPartialUpdateOperation] = Field(
        default_factory=list,
        description=(
            "Optional list of partial update operations. Each operation defines "
            "a subset of columns to update when triggered by a specific event. "
            "Partial updates are more efficient than full upserts for high-frequency "
            "updates like heartbeats or state transitions."
        ),
        json_schema_extra={"default": []},
    )

    @field_validator("consumed_events")
    @classmethod
    def validate_event_names(cls, v: list[str]) -> list[str]:
        """Validate event names match the naming pattern.

        Each event name must:
        - Start with a lowercase letter
        - Contain only lowercase letters, digits, underscores, and dots
        - Have segments separated by dots
        - End with a version suffix (e.g., .v1, .v2)

        Args:
            v: List of event names to validate

        Returns:
            The validated list of event names

        Raises:
            ValueError: If any event name doesn't match the pattern

        Examples:
            Valid event names:
                - "node.created.v1"
                - "order_management.order_line_item_added.v2"
                - "domain.subdomain.entity.action.v10"

            Invalid event names:
                - "Node.Created.v1" (uppercase)
                - "node-service.created.v1" (hyphen)
                - "node.created" (missing version)
        """
        for event_name in v:
            if not EVENT_NAME_PATTERN.match(event_name):
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    f"Invalid event name '{event_name}'. "
                    f"Must match pattern: lowercase.segments.vN "
                    f"(e.g., 'node.created.v1')"
                )
        return v

    @model_validator(mode="after")
    def validate_upsert_key_exists_in_columns(self) -> Self:
        """Validate that upsert_key references existing column(s) when specified.

        When the behavior mode is 'upsert' and an explicit upsert_key is provided,
        this validator ensures the upsert_key corresponds to column(s) defined in
        the projection schema. Supports both single column (str) and composite
        keys (list[str]).

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any upsert_key column does not exist in the schema.
        """
        if self.behavior.mode == "upsert" and self.behavior.upsert_key is not None:
            column_names = {col.name for col in self.projection_schema.columns}
            # Normalize to list for uniform handling
            upsert_columns = (
                [self.behavior.upsert_key]
                if isinstance(self.behavior.upsert_key, str)
                else self.behavior.upsert_key
            )
            missing = [col for col in upsert_columns if col not in column_names]
            if missing:
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    f"upsert_key column(s) {missing} must reference existing columns. "
                    f"Available columns: {sorted(column_names)}"
                )
        return self

    @model_validator(mode="after")
    def validate_partial_update_columns_exist(self) -> Self:
        """Validate that partial update columns reference existing schema columns.

        Each column specified in a partial update operation must correspond to
        a column defined in the projection schema.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any partial update column does not exist in the schema.
        """
        if not self.partial_updates:
            return self

        column_names = {col.name for col in self.projection_schema.columns}
        for partial_update in self.partial_updates:
            for col_name in partial_update.columns:
                if col_name not in column_names:
                    # error-ok: Pydantic validator requires ValueError
                    raise ValueError(
                        f"Partial update '{partial_update.name}' references non-existent "
                        f"column '{col_name}'. Available columns: {sorted(column_names)}"
                    )
        return self

    @model_validator(mode="after")
    def validate_partial_update_trigger_events_consumed(self) -> Self:
        """Validate that partial update trigger events are in consumed_events.

        Each trigger_event in a partial update operation must be one of the
        events that this projector consumes.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any trigger event is not in consumed_events.
        """
        if not self.partial_updates:
            return self

        consumed_set = set(self.consumed_events)
        for partial_update in self.partial_updates:
            if partial_update.trigger_event not in consumed_set:
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    f"Partial update '{partial_update.name}' trigger_event "
                    f"'{partial_update.trigger_event}' must be in consumed_events. "
                    f"Available events: {sorted(consumed_set)}"
                )
        return self

    @model_validator(mode="after")
    def validate_no_duplicate_partial_update_names(self) -> Self:
        """Validate that all partial update names are unique.

        Partial update operation names must be unique within a contract
        to avoid ambiguity in logging, metrics, and debugging.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any partial update name appears more than once.
        """
        if not self.partial_updates:
            return self

        seen: set[str] = set()
        duplicates: set[str] = set()
        for partial_update in self.partial_updates:
            if partial_update.name in seen:
                duplicates.add(partial_update.name)
            seen.add(partial_update.name)

        if duplicates:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                f"Duplicate partial update names are not allowed: {sorted(duplicates)}"
            )
        return self

    def __hash__(self) -> int:
        """Return hash value for the contract.

        Custom implementation to support hashing with list fields.
        Converts consumed_events and partial_updates lists to tuples for hashing.
        """
        return hash(
            (
                self.projector_kind,
                self.projector_id,
                self.name,
                self.version,
                self.aggregate_type,
                tuple(self.consumed_events),
                self.projection_schema,
                self.behavior,
                tuple(self.partial_updates),
            )
        )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing projector_id, version, event count,
            index count, and partial update count for better debugging visibility.

        Examples:
            >>> contract = ModelProjectorContract(...)
            >>> repr(contract)
            "ModelProjectorContract(id='node-projector', version='1.0.0', events=2, indexes=1, partial_updates=0)"
        """
        return (
            f"ModelProjectorContract(id={self.projector_id!r}, "
            f"version={self.version!r}, events={len(self.consumed_events)}, "
            f"indexes={len(self.projection_schema.indexes)}, "
            f"partial_updates={len(self.partial_updates)})"
        )


__all__ = ["ModelProjectorContract", "EVENT_NAME_PATTERN"]
