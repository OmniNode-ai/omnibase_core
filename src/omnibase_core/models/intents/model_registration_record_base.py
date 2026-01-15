"""
Base class for registration records.

This module provides ModelRegistrationRecordBase, a Pydantic base class that
implements ProtocolRegistrationRecord. Use this as a base for custom
registration records to ensure protocol compliance and consistent behavior.

Design Pattern:
    This base class follows the ONEX pattern of providing both a Protocol
    (for interface contracts) and a concrete base class (for convenience).
    Users can either:
    1. Inherit from ModelRegistrationRecordBase (recommended for most cases)
    2. Implement ProtocolRegistrationRecord directly (for non-Pydantic classes)

Usage:
    >>> from omnibase_core.models.intents import ModelRegistrationRecordBase
    >>>
    >>> class NodeRegistrationRecord(ModelRegistrationRecordBase):
    ...     '''Registration record for compute nodes.'''
    ...     node_id: str
    ...     node_type: str
    ...     status: str
    ...     host: str
    ...     port: int
    >>>
    >>> record = NodeRegistrationRecord(
    ...     node_id="compute-abc123",
    ...     node_type="compute",
    ...     status="active",
    ...     host="192.168.1.100",
    ...     port=8080,
    ... )
    >>>
    >>> # Use with PostgreSQL upsert intent
    >>> from omnibase_core.models.intents import ModelPostgresUpsertRegistrationIntent
    >>> from uuid import uuid4
    >>>
    >>> intent = ModelPostgresUpsertRegistrationIntent(
    ...     record=record,
    ...     correlation_id=uuid4(),
    ... )

Thread Safety:
    ModelRegistrationRecordBase is frozen (immutable) by default, making
    instances thread-safe for concurrent read access after creation.

ConfigDict Settings:
    - frozen=True: Instances are immutable after creation
    - extra="forbid": Extra fields are rejected during validation
    - from_attributes=True: Enables pytest-xdist compatibility
    - validate_assignment=True: Validates values on attribute assignment

See Also:
    omnibase_core.protocols.intents.ProtocolRegistrationRecord:
        The protocol this class implements.
    omnibase_core.models.intents.ModelPostgresUpsertRegistrationIntent:
        The intent that accepts registration records.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any


class ModelRegistrationRecordBase(BaseModel):
    """Base class for registration records used in persistence intents.

    Provides a Pydantic-based implementation of ProtocolRegistrationRecord.
    Subclasses should add domain-specific fields for their registration data.

    This base class provides:
    - ONEX-compliant ConfigDict settings (frozen, extra="forbid", etc.)
    - Default to_persistence_dict() implementation using model_dump(mode="json")
    - Protocol compliance for ProtocolRegistrationRecord

    Subclasses only need to define their specific fields; the serialization
    methods are inherited.

    Attributes:
        Subclasses define their own attributes. This base class has no fields.

    Example:
        >>> class ServiceRecord(ModelRegistrationRecordBase):
        ...     service_id: str
        ...     service_name: str
        ...     endpoint_url: str
        ...     health_check_url: str | None = None
        >>>
        >>> record = ServiceRecord(
        ...     service_id="svc-123",
        ...     service_name="auth-service",
        ...     endpoint_url="http://auth.local:8080",
        ... )
        >>>
        >>> # Serialization for database
        >>> db_data = record.to_persistence_dict()
        >>> assert db_data["service_id"] == "svc-123"

    Note:
        The frozen=True setting means instances cannot be modified after
        creation. Create a new instance if you need different values.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    @allow_dict_any(reason="Serialization method for database persistence")
    def to_persistence_dict(self) -> dict[str, Any]:
        """Serialize the record for database persistence.

        Converts the registration record to a JSON-serializable dictionary
        suitable for database storage. Uses Pydantic's model_dump with
        mode="json" to ensure all values are JSON-compatible.

        This method is called by Effect nodes when persisting registration
        data to PostgreSQL via ModelPostgresUpsertRegistrationIntent.

        Returns:
            Dictionary representation with JSON-serializable values.
            UUIDs are converted to strings, datetimes to ISO format, etc.

        Example:
            >>> from uuid import uuid4
            >>> from datetime import datetime, timezone
            >>>
            >>> class TimestampedRecord(ModelRegistrationRecordBase):
            ...     record_id: uuid4
            ...     created_at: datetime
            >>>
            >>> record = TimestampedRecord(
            ...     record_id=uuid4(),
            ...     created_at=datetime.now(timezone.utc),
            ... )
            >>> data = record.to_persistence_dict()
            >>> isinstance(data["record_id"], str)  # UUID -> string
            True
            >>> isinstance(data["created_at"], str)  # datetime -> ISO string
            True
        """
        return self.model_dump(mode="json")


__all__ = ["ModelRegistrationRecordBase"]
