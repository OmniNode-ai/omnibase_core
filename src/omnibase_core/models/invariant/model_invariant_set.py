"""
Invariant set model - collection of invariants for a node/workflow.

This module provides the ModelInvariantSet class which groups multiple
invariants together for validation of a specific node or workflow.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
from omnibase_core.models.invariant.model_invariant import ModelInvariant


class ModelInvariantSet(BaseModel):
    """
    Collection of invariants for a node or workflow.

    Groups multiple invariants together that should be validated as a unit
    against a specific target node or workflow. Provides helper properties
    for filtering invariants by severity or enabled status.
    """

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
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


# Rebuild model to resolve forward references
def _rebuild_model() -> None:
    """Rebuild model after ModelInvariant is available."""
    try:
        ModelInvariantSet.model_rebuild()
    except Exception:  # error-ok: model_rebuild may fail during import, safe to ignore
        pass


_rebuild_model()


__all__ = ["ModelInvariantSet"]
