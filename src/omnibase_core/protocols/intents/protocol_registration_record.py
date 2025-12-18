"""
Protocol for registration records used in persistence intents.

This module defines the ProtocolRegistrationRecord protocol, which establishes
the contract for registration records that can be persisted via the
ModelPostgresUpsertRegistrationIntent.

Design Rationale:
    The PostgreSQL upsert intent originally accepted any BaseModel as its record
    field. While flexible, this provided no type safety guarantees about what
    the record should contain. This protocol establishes a minimal contract
    that registration records must fulfill:

    1. to_persistence_dict() - Serialize to a dictionary suitable for database
       persistence. This ensures the Effect node can reliably extract data
       for database operations.

    2. model_dump() - Standard Pydantic serialization method. Required because
       registration records are typically Pydantic models, and this method is
       used during JSON serialization.

    The protocol is intentionally minimal to allow flexibility while ensuring
    the essential persistence contract is met.

Usage Patterns:
    1. Direct Protocol Implementation:
       ```python
       from omnibase_core.protocols.intents import ProtocolRegistrationRecord

       class MyRecord:
           def to_persistence_dict(self) -> dict[str, object]:
               return {"key": "value"}

           def model_dump(self, mode: str | None = None) -> dict[str, object]:
               return self.to_persistence_dict()
       ```

    2. Pydantic Model Implementation (recommended):
       ```python
       from pydantic import BaseModel
       from omnibase_core.protocols.intents import ProtocolRegistrationRecord

       class NodeRecord(BaseModel):
           node_id: str
           node_type: str

           def to_persistence_dict(self) -> dict[str, object]:
               return self.model_dump(mode="json")

       # Type checker validates protocol compliance
       record: ProtocolRegistrationRecord = NodeRecord(...)
       ```

    3. Using ModelRegistrationRecordBase (convenience base class):
       ```python
       from omnibase_core.models.intents import ModelRegistrationRecordBase

       class NodeRecord(ModelRegistrationRecordBase):
           node_id: str
           node_type: str
           # to_persistence_dict() inherited from base class
       ```

Thread Safety:
    Implementations should be immutable (frozen=True) for thread safety,
    following ONEX patterns. The protocol methods are read-only and
    should not mutate state.

See Also:
    omnibase_core.models.intents.ModelPostgresUpsertRegistrationIntent:
        The intent that uses this protocol.
    omnibase_core.models.intents.ModelRegistrationRecordBase:
        Convenience base class implementing this protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolRegistrationRecord(Protocol):
    """Protocol for registration records used in persistence intents.

    Defines the minimal contract for objects that can be used as registration
    records in ModelPostgresUpsertRegistrationIntent. Implementations must
    provide serialization methods for database persistence.

    This protocol is @runtime_checkable, enabling isinstance() checks for
    duck typing validation at runtime.

    Attributes:
        None required - implementations may have any attributes.

    Methods:
        to_persistence_dict: Serialize record for database persistence.
        model_dump: Standard Pydantic-style serialization.

    Example:
        >>> from pydantic import BaseModel
        >>> from omnibase_core.protocols.intents import ProtocolRegistrationRecord
        >>>
        >>> class NodeRecord(BaseModel):
        ...     node_id: str
        ...     status: str
        ...
        ...     def to_persistence_dict(self) -> dict[str, object]:
        ...         return self.model_dump(mode="json")
        >>>
        >>> record = NodeRecord(node_id="123", status="active")
        >>> isinstance(record, ProtocolRegistrationRecord)  # True

    Note:
        Both methods return dict[str, object] for ONEX type safety. The
        to_persistence_dict method is specifically for database operations
        where values should be JSON-serializable primitives. Implementations
        using Pydantic BaseModel inherit model_dump() automatically.
    """

    def to_persistence_dict(self) -> dict[str, object]:
        """Serialize the record for database persistence.

        Converts the registration record to a dictionary suitable for
        database storage operations. The returned dictionary should contain
        only JSON-serializable values.

        This method is called by Effect nodes when persisting registration
        data to PostgreSQL. The Effect is responsible for mapping dictionary
        keys to database columns.

        Returns:
            Dictionary representation of the record suitable for database
            persistence. Keys should be strings, values should be
            JSON-serializable types (str, int, float, bool, None, list, dict).

        Example:
            >>> class NodeRecord(BaseModel):
            ...     node_id: str
            ...     created_at: datetime
            ...
            ...     def to_persistence_dict(self) -> dict[str, object]:
            ...         return {
            ...             "node_id": self.node_id,
            ...             "created_at": self.created_at.isoformat(),
            ...         }
        """
        ...

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Any = None,
        exclude: Any = None,
        context: Any = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | str = True,
        serialize_as_any: bool = False,
    ) -> dict[str, object]:
        """Serialize the record to a dictionary.

        Standard Pydantic serialization method. Implementations using
        Pydantic BaseModel inherit this method automatically.

        This method signature matches Pydantic v2's model_dump() to ensure
        Pydantic models work correctly as registration records.

        Args:
            mode: Serialization mode ("python" or "json"). Defaults to "python".
            include: Fields to include in serialization.
            exclude: Fields to exclude from serialization.
            context: Context for serialization.
            by_alias: Use field aliases in output.
            exclude_unset: Exclude fields that were not explicitly set.
            exclude_defaults: Exclude fields with default values.
            exclude_none: Exclude fields with None values.
            round_trip: Enable round-trip serialization mode.
            warnings: Control warning behavior.
            serialize_as_any: Serialize polymorphic types as their actual type.

        Returns:
            Dictionary representation of the record.

        Note:
            For database persistence, prefer using to_persistence_dict() which
            provides a more constrained contract specifically for database ops.
        """
        ...


__all__ = ["ProtocolRegistrationRecord"]
