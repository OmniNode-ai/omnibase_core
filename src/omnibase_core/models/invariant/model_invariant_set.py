"""
Invariant set model - collection of invariants for a node/workflow.

This module provides the ModelInvariantSet class which groups multiple
invariants together for validation of a specific node or workflow.

Thread Safety:
    ModelInvariantSet is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PydanticUndefinedAnnotation

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant.model_invariant import ModelInvariant


class ModelInvariantSet(BaseModel):
    """Collection of invariants for a node or workflow.

    Groups multiple invariants together that should be validated as a unit
    against a specific target node or workflow. Provides helper properties
    for filtering invariants by severity or enabled status.

    Attributes:
        id: Unique identifier for this invariant set (UUID).
        name: Human-readable name for this invariant set.
        target: Node or workflow identifier this set applies to.
        invariants: List of invariants in this set.
        description: Optional description of what this invariant set validates.
        created_at: Timestamp when this invariant set was created.
        version: Semantic version of this invariant set definition.

    Note:
        Both __eq__ and __hash__ use only id, name, target, and version for
        comparison and hashing. This ensures Python's hash/equality contract
        is satisfied (if a == b then hash(a) == hash(b)). Fields excluded:
        - created_at: Uses datetime.now(UTC), varies between identical instances
        - invariants: Unhashable list type
        - description: Optional metadata field
        Two sets are considered equal if they have the same identity (id, name,
        target, version), regardless of their invariants or description.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this invariant set",
    )
    name: str = Field(
        ...,
        description="Human-readable name for this invariant set",
        min_length=1,
    )
    target: str = Field(
        ...,
        description="Node or workflow identifier this set applies to",
    )
    invariants: list[ModelInvariant] = Field(
        default_factory=list,
        description="List of invariants in this set",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of what this invariant set validates",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this invariant set was created",
    )
    version: str = Field(
        default="1.0.0",
        description="Version of this invariant set definition",
    )

    @property
    def critical_invariants(self) -> list[ModelInvariant]:
        """
        Return only critical severity invariants.

        Performance Note:
            Creates a new list on each access via list comprehension.
            For repeated access, consider caching the result locally.

        Returns:
            List of invariants with CRITICAL severity level.
        """
        return [inv for inv in self.invariants if inv.severity == EnumSeverity.CRITICAL]

    @property
    def enabled_invariants(self) -> list[ModelInvariant]:
        """
        Return only enabled invariants.

        Performance Note:
            Creates a new list on each access via list comprehension.
            For repeated access, consider caching the result locally.

        Returns:
            List of invariants where enabled is True.
        """
        return [inv for inv in self.invariants if inv.enabled]

    @property
    def warning_invariants(self) -> list[ModelInvariant]:
        """
        Return only warning severity invariants.

        Performance Note:
            Creates a new list on each access via list comprehension.
            For repeated access, consider caching the result locally.

        Returns:
            List of invariants with WARNING severity level.
        """
        return [inv for inv in self.invariants if inv.severity == EnumSeverity.WARNING]

    @property
    def info_invariants(self) -> list[ModelInvariant]:
        """
        Return only info severity invariants.

        Performance Note:
            Creates a new list on each access via list comprehension.
            For repeated access, consider caching the result locally.

        Returns:
            List of invariants with INFO severity level.
        """
        return [inv for inv in self.invariants if inv.severity == EnumSeverity.INFO]

    def get_invariants_by_type(
        self, invariant_type: EnumInvariantType | str
    ) -> list[ModelInvariant]:
        """
        Return invariants filtered by type.

        Performance Note:
            Creates a new list on each call via list comprehension.
            For repeated access with the same type, consider caching
            the result locally.

        Args:
            invariant_type: The type of invariant to filter by.
                Can be an EnumInvariantType or its string value.

        Returns:
            List of invariants matching the specified type.
        """
        # EnumInvariantType is a str enum, so direct comparison works
        return [inv for inv in self.invariants if inv.type == invariant_type]

    def __eq__(self, other: object) -> bool:
        """
        Compare invariant sets by identity fields only.

        Compares only id, name, target, and version - the same fields used
        by __hash__. This ensures Python's hash/equality contract is satisfied:
        if a == b then hash(a) == hash(b).

        Fields excluded from comparison:
        - created_at: Timestamp varies between identical instances
        - invariants: Would break hash/equality contract (not in __hash__)
        - description: Would break hash/equality contract (not in __hash__)

        Two sets are considered equal if they represent the same invariant set
        definition (same id, name, target, version), regardless of whether they
        contain different invariants or descriptions.

        Args:
            other: Object to compare against.

        Returns:
            True if invariant sets have identical identity fields, False otherwise.
            Returns NotImplemented if other is not a ModelInvariantSet.
        """
        if not isinstance(other, ModelInvariantSet):
            return NotImplemented
        return (
            self.id == other.id
            and self.name == other.name
            and self.target == other.target
            and self.version == other.version
        )

    def __hash__(self) -> int:
        """
        Hash invariant set using identity fields.

        Uses only id, name, target, and version for hash computation -
        the same fields used by __eq__. This ensures Python's hash/equality
        contract is satisfied: if a == b then hash(a) == hash(b).

        Excludes created_at (timestamp), invariants (unhashable list),
        and description (optional field) to ensure:
        1. Hashability (lists cannot be hashed)
        2. Efficient hash computation
        3. Stable hashes for set/dict operations
        4. Consistency with __eq__ (hash/equality contract)

        Returns:
            Hash value based on id, name, target, and version.
        """
        return hash((self.id, self.name, self.target, self.version))


# Rebuild model to resolve forward references
def _rebuild_model() -> None:
    """Rebuild model after ModelInvariant is available."""
    try:
        ModelInvariantSet.model_rebuild()
    except PydanticUndefinedAnnotation:
        # Forward reference not yet available - safe to ignore during import
        pass


_rebuild_model()


__all__ = ["ModelInvariantSet"]
