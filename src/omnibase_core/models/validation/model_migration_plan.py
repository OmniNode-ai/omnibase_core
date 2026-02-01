"""
Migration plan model for protocol migration operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.models.validation.model_migration_conflict_union import (
    ModelMigrationConflictUnion,
)
from omnibase_core.validation.validator_migration_types import (
    TypedDictMigrationStepDict,
)
from omnibase_core.validation.validator_utils import ModelProtocolInfo


@dataclass
class ModelMigrationPlan:
    """Plan for migrating protocols to omnibase_spi."""

    success: bool
    source_repository: str
    target_repository: str
    protocols_to_migrate: list[ModelProtocolInfo]
    conflicts_detected: list[ModelMigrationConflictUnion]
    migration_steps: list[TypedDictMigrationStepDict]
    estimated_time_minutes: int
    recommendations: list[str]

    def has_conflicts(self) -> bool:
        """Check if migration plan has conflicts."""
        return len(self.conflicts_detected) > 0

    def can_proceed(self) -> bool:
        """Check if migration can proceed safely."""
        return self.success and not self.has_conflicts()
