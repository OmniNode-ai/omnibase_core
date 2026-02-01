"""
Canonical message envelope model for commands, events, and intents.

This module provides the unified envelope model for all inter-service messages
in ONEX. It provides essential tracing, correlation, and partitioning fields
that enable distributed workflow tracking.

Fields:
    message_id: Unique identifier for this specific message instance
    correlation_id: Groups all messages in a logical workflow/transaction
    causation_id: References the immediate parent message that caused this one
    emitted_at: Timestamp when this message was created (UTC)
    entity_id: Partition key and identity anchor (e.g., node_id for registration domain)

Thread Safety:
    ModelEnvelope instances are immutable after creation (frozen=True) and thread-safe.
    They can be safely shared across threads without synchronization.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.common.model_envelope import ModelEnvelope
    >>>
    >>> # Create root envelope
    >>> root = ModelEnvelope(
    ...     correlation_id=uuid4(),
    ...     entity_id="node-auth-service-001",
    ... )
    >>>
    >>> # Create child envelope with causation link
    >>> child = root.create_child()
    >>> child.causation_id == root.message_id
    True
    >>> child.correlation_id == root.correlation_id
    True
    >>>
    >>> # Validate envelope fields before creation
    >>> from omnibase_core.models.common.model_envelope import validate_envelope_fields
    >>> result = validate_envelope_fields({
    ...     "correlation_id": uuid4(),
    ...     "entity_id": "node-processor-001",
    ... })
    >>> result.has_errors()
    False
    >>>
    >>> # Validate a causation chain
    >>> from omnibase_core.models.common.model_envelope import validate_causation_chain
    >>> chain_valid = validate_causation_chain([root, child])
    >>> chain_valid
    True

See Also:
    - ModelEnvelopePayload: Payload container for event data
    - ModelEventEnvelope: Full event wrapper including envelope and payload
"""

from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
)


class ModelEnvelope(BaseModel):
    """Canonical message envelope for commands, events, and intents.

    This is the unified envelope model for all inter-service messages in ONEX.
    It provides essential tracing, correlation, and partitioning fields.

    Fields:
        message_id: Unique identifier for this specific message
        correlation_id: Groups all messages in a logical workflow/transaction
        causation_id: References the immediate parent message that caused this one
            (nullable for root messages)
        emitted_at: Timestamp when this message was created (UTC)
        entity_id: Partition key and identity anchor (e.g., node_id for registration domain)

    Thread Safety:
        This model is immutable after creation (frozen=True) and thread-safe.

    Performance:
        All validation is O(1) - constant time complexity. The max_length=512
        constraint on entity_id ensures bounded memory usage and prevents
        database key overflow or message broker header size issues.

    Example:
        >>> envelope = ModelEnvelope(
        ...     correlation_id=uuid4(),
        ...     entity_id="node-123",
        ... )
        >>> child = ModelEnvelope(
        ...     correlation_id=envelope.correlation_id,
        ...     causation_id=envelope.message_id,
        ...     entity_id=envelope.entity_id,
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    # Unique identifier for this message
    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this specific message instance",
    )

    # Groups related messages in a workflow
    correlation_id: UUID = Field(
        ...,
        description="Groups all messages in a logical workflow or transaction",
    )

    # References the immediate parent message_id (nullable for root messages)
    causation_id: UUID | None = Field(
        default=None,
        description="References the immediate parent message_id that caused this one",
    )

    # When the message was created
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this message was created (must be timezone-aware UTC)",
    )

    # Partition key and identity anchor
    entity_id: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Partition key and identity anchor (e.g., node_id for registration domain). Max 512 chars.",
    )

    @field_validator("entity_id", mode="before")
    @classmethod
    def validate_entity_id_not_empty(cls, v: object) -> str:
        """Validate that entity_id is not empty or whitespace-only.

        This validator runs before Pydantic's type coercion and ensures that
        the entity_id field contains a non-empty, non-whitespace string.
        Whitespace is stripped from the value.

        Args:
            v: The raw value to validate (may be any type).

        Returns:
            The stripped string value.

        Raises:
            ModelOnexError: If the value is empty or contains only whitespace.
        """
        if not isinstance(v, str):
            # Let Pydantic handle type coercion/validation for non-strings
            return str(v) if v is not None else ""
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                message="entity_id cannot be empty or whitespace-only",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="entity_id",
                value=v,
            )
        return stripped

    @field_validator("emitted_at", mode="after")
    @classmethod
    def validate_emitted_at_timezone_aware(cls, v: datetime) -> datetime:
        """Validate that emitted_at is timezone-aware.

        All timestamps in ONEX must be timezone-aware to ensure consistent
        handling across distributed services.

        Args:
            v: The datetime value to validate.

        Returns:
            The validated datetime.

        Raises:
            ModelOnexError: If the datetime is naive (no timezone info).
        """
        if v.tzinfo is None:
            raise ModelOnexError(
                message="emitted_at must be timezone-aware (naive datetime not allowed)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="emitted_at",
            )
        return v

    @model_validator(mode="after")
    def validate_no_self_reference(self) -> Self:
        """Validate that causation_id does not equal message_id (self-reference).

        A message cannot be caused by itself. This validation prevents creating
        envelopes where the causation_id points to the same message_id, which
        would create an invalid self-referential causation chain.

        Returns:
            The validated envelope instance.

        Raises:
            ModelOnexError: If causation_id equals message_id.
        """
        if self.causation_id is not None and self.causation_id == self.message_id:
            raise ModelOnexError(
                message="causation_id cannot equal message_id (self-reference)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                field="causation_id",
                message_id=str(self.message_id),
                causation_id=str(self.causation_id),
            )
        return self

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def create_root(cls, correlation_id: UUID, entity_id: str) -> "ModelEnvelope":
        """Create a root message envelope (no causation_id).

        Root messages are the first message in a workflow chain and have no
        causation_id (no parent message).

        Args:
            correlation_id: The correlation ID for the workflow
            entity_id: The partition key / identity anchor

        Returns:
            A new ModelEnvelope instance with no causation_id

        Example:
            >>> from uuid import uuid4
            >>> root = ModelEnvelope.create_root(
            ...     correlation_id=uuid4(),
            ...     entity_id="node-123",
            ... )
            >>> root.causation_id is None
            True
        """
        return cls(
            correlation_id=correlation_id,
            entity_id=entity_id,
            causation_id=None,
        )

    def create_child(
        self,
        entity_id: str | None = None,
    ) -> "ModelEnvelope":
        """Create a child envelope linked to this message via causation_id.

        The child inherits the correlation_id from the parent (same workflow)
        and sets causation_id to the parent's message_id (direct cause).

        Args:
            entity_id: Optional entity_id override. If not provided, inherits
                from the parent envelope.

        Returns:
            A new ModelEnvelope instance linked to this parent

        Example:
            >>> parent = ModelEnvelope(correlation_id=uuid4(), entity_id="node-1")
            >>> child = parent.create_child()
            >>> child.correlation_id == parent.correlation_id
            True
            >>> child.causation_id == parent.message_id
            True
        """
        return ModelEnvelope(
            correlation_id=self.correlation_id,
            causation_id=self.message_id,
            entity_id=entity_id if entity_id is not None else self.entity_id,
        )

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def is_root(self) -> bool:
        """Check if this envelope is a root message (no causation_id).

        Returns:
            True if this is a root message, False otherwise
        """
        return self.causation_id is None

    def has_same_workflow(self, other: "ModelEnvelope") -> bool:
        """Check if another envelope is part of the same workflow.

        Two envelopes are in the same workflow if they share the same
        correlation_id.

        Args:
            other: Another envelope to compare

        Returns:
            True if both envelopes share the same correlation_id
        """
        return self.correlation_id == other.correlation_id

    def is_caused_by(self, other: "ModelEnvelope") -> bool:
        """Check if this envelope was directly caused by another.

        Args:
            other: The potential parent envelope

        Returns:
            True if this envelope's causation_id matches the other's message_id
        """
        return self.causation_id == other.message_id

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            A string with key envelope fields for debugging.
        """
        return (
            f"ModelEnvelope("
            f"message_id={self.message_id!r}, "
            f"correlation_id={self.correlation_id!r}, "
            f"causation_id={self.causation_id!r}, "
            f"entity_id={self.entity_id!r}, "
            f"emitted_at={self.emitted_at.isoformat()!r})"
        )


# -----------------------------------------------------------------------------
# Validation Helper Functions
# -----------------------------------------------------------------------------


def validate_envelope_fields(data: dict[str, object]) -> ModelValidationContainer:
    """Validate envelope fields at the schema level.

    Performs schema-level validation on a dictionary that will be used to
    create a ModelEnvelope. This is useful for validating data before
    attempting to create an envelope instance.

    Args:
        data: Dictionary containing envelope field data

    Returns:
        ModelValidationContainer with any validation errors found

    Example:
        >>> result = validate_envelope_fields({
        ...     "correlation_id": "invalid-uuid",
        ...     "entity_id": "",
        ... })
        >>> result.has_errors()
        True
    """
    container = ModelValidationContainer()

    # Check required fields
    required_fields = ["correlation_id", "entity_id"]
    for field_name in required_fields:
        if field_name not in data:
            container.add_error(
                message=f"Missing required field: {field_name}",
                field=field_name,
                error_code="MISSING_REQUIRED_FIELD",
            )

    # Validate correlation_id is a valid UUID
    if "correlation_id" in data:
        correlation_id = data["correlation_id"]
        if correlation_id is not None:
            if isinstance(correlation_id, str):
                try:
                    UUID(correlation_id)
                except ValueError:
                    container.add_error(
                        message=f"Invalid UUID format for correlation_id: {correlation_id}",
                        field="correlation_id",
                        error_code="INVALID_UUID_FORMAT",
                    )
            elif not isinstance(correlation_id, UUID):
                container.add_error(
                    message=f"correlation_id must be a UUID, got {type(correlation_id).__name__}",
                    field="correlation_id",
                    error_code="INVALID_TYPE",
                )

    # Validate entity_id is non-empty string
    if "entity_id" in data:
        entity_id = data["entity_id"]
        if entity_id is None:
            container.add_error(
                message="entity_id cannot be None",
                field="entity_id",
                error_code="NULL_NOT_ALLOWED",
            )
        elif isinstance(entity_id, str):
            if not entity_id.strip():
                container.add_error(
                    message="entity_id cannot be empty or whitespace-only",
                    field="entity_id",
                    error_code="EMPTY_VALUE",
                )
            # Check max length (512 chars) - security constraint for DB keys and message headers
            elif len(entity_id.strip()) > 512:
                container.add_error(
                    message=f"entity_id exceeds maximum length of 512 characters (got {len(entity_id.strip())})",
                    field="entity_id",
                    error_code="VALUE_TOO_LONG",
                )
        else:
            container.add_error(
                message=f"entity_id must be a string, got {type(entity_id).__name__}",
                field="entity_id",
                error_code="INVALID_TYPE",
            )

    # Validate causation_id if present
    if "causation_id" in data:
        causation_id = data["causation_id"]
        if causation_id is not None:
            if isinstance(causation_id, str):
                try:
                    UUID(causation_id)
                except ValueError:
                    container.add_error(
                        message=f"Invalid UUID format for causation_id: {causation_id}",
                        field="causation_id",
                        error_code="INVALID_UUID_FORMAT",
                    )
            elif not isinstance(causation_id, UUID):
                container.add_error(
                    message=f"causation_id must be a UUID or None, got {type(causation_id).__name__}",
                    field="causation_id",
                    error_code="INVALID_TYPE",
                )

    # Validate message_id if present
    if "message_id" in data:
        message_id = data["message_id"]
        if message_id is not None:
            if isinstance(message_id, str):
                try:
                    UUID(message_id)
                except ValueError:
                    container.add_error(
                        message=f"Invalid UUID format for message_id: {message_id}",
                        field="message_id",
                        error_code="INVALID_UUID_FORMAT",
                    )
            elif not isinstance(message_id, UUID):
                container.add_error(
                    message=f"message_id must be a UUID, got {type(message_id).__name__}",
                    field="message_id",
                    error_code="INVALID_TYPE",
                )

    # Check for self-reference
    if "message_id" in data and "causation_id" in data:
        message_id = data["message_id"]
        causation_id = data["causation_id"]
        if message_id is not None and causation_id is not None:
            # Normalize to UUID for comparison
            try:
                msg_uuid = (
                    UUID(str(message_id)) if isinstance(message_id, str) else message_id
                )
                cause_uuid = (
                    UUID(str(causation_id))
                    if isinstance(causation_id, str)
                    else causation_id
                )
                if msg_uuid == cause_uuid:
                    container.add_error(
                        message="causation_id cannot equal message_id (self-reference)",
                        field="causation_id",
                        error_code="SELF_REFERENCE",
                    )
            except (TypeError, ValueError):
                pass  # UUID validation errors already handled above

    return container


def get_chain_depth(envelopes: list[ModelEnvelope]) -> int:
    """Calculate the maximum depth of a causation chain.

    Traverses the parent-child relationships via causation_id to find the
    longest path from any root message (causation_id=None) to a leaf message.

    The depth is defined as the number of edges in the longest path:
    - Empty list: depth = 0
    - Single root envelope: depth = 0 (no edges)
    - Root -> Child: depth = 1 (one edge)
    - Root -> Child -> Grandchild: depth = 2 (two edges)

    Args:
        envelopes: List of envelopes to analyze for chain depth

    Returns:
        The maximum depth of the causation chain (0 for empty or single-root chains)

    Example:
        >>> root = ModelEnvelope.create_root(uuid4(), "node-1")
        >>> child = root.create_child()
        >>> grandchild = child.create_child()
        >>> get_chain_depth([root, child, grandchild])
        2
        >>> get_chain_depth([root])
        0
        >>> get_chain_depth([])
        0
    """
    if not envelopes:
        return 0

    # Build lookup maps for efficient traversal
    # message_id -> envelope
    envelope_by_id: dict[UUID, ModelEnvelope] = {
        env.message_id: env for env in envelopes
    }
    # causation_id -> list of children message_ids
    children_by_parent: dict[UUID, list[UUID]] = {}
    root_ids: list[UUID] = []

    for env in envelopes:
        if env.causation_id is None:
            root_ids.append(env.message_id)
        else:
            if env.causation_id not in children_by_parent:
                children_by_parent[env.causation_id] = []
            children_by_parent[env.causation_id].append(env.message_id)

    # If no roots found but envelopes exist, the chain is broken
    # Still compute depth from all envelopes as potential starting points
    if not root_ids:
        # Start from envelopes whose causation_id is not in the set
        # (orphaned children - their depth from an external parent)
        for env in envelopes:
            if env.causation_id is not None and env.causation_id not in envelope_by_id:
                root_ids.append(env.message_id)

    # If still no starting points, use all envelopes (handles cycles)
    if not root_ids:
        root_ids = list(envelope_by_id.keys())

    def calculate_depth_from(message_id: UUID, visited: set[UUID]) -> int:
        """Calculate depth starting from a given message_id using DFS."""
        if message_id in visited:
            # Cycle detected - return 0 to avoid infinite recursion
            return 0
        visited.add(message_id)

        children = children_by_parent.get(message_id, [])
        if not children:
            return 0

        max_child_depth = 0
        for child_id in children:
            child_depth = calculate_depth_from(child_id, visited.copy())
            max_child_depth = max(max_child_depth, child_depth)

        return 1 + max_child_depth

    # Calculate maximum depth from all root nodes
    max_depth = 0
    for root_id in root_ids:
        depth = calculate_depth_from(root_id, set())
        max_depth = max(max_depth, depth)

    return max_depth


def validate_causation_chain(
    envelopes: list[ModelEnvelope],
    max_chain_depth: int | None = None,
) -> bool:
    """Validate the integrity of a causation chain.

    Checks that each envelope's causation_id points to a valid message_id
    in the chain (except for root messages which have no causation_id).
    Optionally validates that the chain depth does not exceed a maximum.

    Args:
        envelopes: List of envelopes that should form a valid causation chain
        max_chain_depth: Optional maximum allowed chain depth. If provided,
            returns False if any chain exceeds this depth. If None (default),
            no depth validation is performed (backwards compatible).

    Returns:
        True if the chain is valid (and within depth limit if specified),
        False otherwise

    Example:
        >>> root = ModelEnvelope.create_root(uuid4(), "node-1")
        >>> child = root.create_child()
        >>> validate_causation_chain([root, child])
        True
        >>> validate_causation_chain([root, child], max_chain_depth=1)
        True
        >>> validate_causation_chain([root, child], max_chain_depth=0)
        False
    """
    if not envelopes:
        return True

    # Build set of all message_ids for lookup
    message_ids: set[UUID] = {env.message_id for env in envelopes}

    # Check that each envelope's causation_id exists in the chain (or is None)
    for envelope in envelopes:
        if envelope.causation_id is not None:
            if envelope.causation_id not in message_ids:
                return False

    # Verify all envelopes share the same correlation_id
    correlation_ids: set[UUID] = {env.correlation_id for env in envelopes}
    if len(correlation_ids) > 1:
        return False

    # Validate chain depth if max_chain_depth is specified
    if max_chain_depth is not None:
        chain_depth = get_chain_depth(envelopes)
        if chain_depth > max_chain_depth:
            return False

    return True


__all__ = [
    "ModelEnvelope",
    "get_chain_depth",
    "validate_causation_chain",
    "validate_envelope_fields",
]
