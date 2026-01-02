"""
Invariant set model - collection of invariants for a node/workflow.

This module provides the ModelInvariantSet class which groups multiple
invariants together for validation of a specific node or workflow.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PydanticUndefinedAnnotation

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
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
        The __eq__ and __hash__ methods exclude created_at from comparison
        to ensure consistent equality for logically identical sets created
        at different times.
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

        Returns:
            List of invariants with CRITICAL severity level.
        """
        return [
            inv
            for inv in self.invariants
            if inv.severity == EnumInvariantSeverity.CRITICAL
        ]

    @property
    def enabled_invariants(self) -> list[ModelInvariant]:
        """
        Return only enabled invariants.

        Returns:
            List of invariants where enabled is True.
        """
        return [inv for inv in self.invariants if inv.enabled]

    @property
    def warning_invariants(self) -> list[ModelInvariant]:
        """
        Return only warning severity invariants.

        Returns:
            List of invariants with WARNING severity level.
        """
        return [
            inv
            for inv in self.invariants
            if inv.severity == EnumInvariantSeverity.WARNING
        ]

    @property
    def info_invariants(self) -> list[ModelInvariant]:
        """
        Return only info severity invariants.

        Returns:
            List of invariants with INFO severity level.
        """
        return [
            inv for inv in self.invariants if inv.severity == EnumInvariantSeverity.INFO
        ]

    def get_invariants_by_type(
        self, invariant_type: EnumInvariantType | str
    ) -> list[ModelInvariant]:
        """
        Return invariants filtered by type.

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
        Compare invariant sets, excluding timestamps.

        The created_at field uses datetime.now(UTC) in default_factory,
        which means two logically identical ModelInvariantSet instances
        created at different times would have different timestamps.
        This breaks equality checks and can cause issues with pytest-xdist
        parallel testing. We exclude created_at from equality comparisons.

        Args:
            other: Object to compare against.

        Returns:
            True if invariant sets are logically equal, False otherwise.
            Returns NotImplemented if other is not a ModelInvariantSet.
        """
        if not isinstance(other, ModelInvariantSet):
            return NotImplemented
        return (
            self.id == other.id
            and self.name == other.name
            and self.target == other.target
            and self.invariants == other.invariants
            and self.description == other.description
            and self.version == other.version
        )

    def __hash__(self) -> int:
        """
        Hash invariant set, excluding timestamps.

        Consistent with __eq__, we exclude created_at from the hash
        computation to ensure that logically equivalent instances
        hash to the same value.

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
