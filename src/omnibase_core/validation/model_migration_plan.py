"""
Migration plan model for protocol migration operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from .migration_types import TypedDictMigrationStepDict
from .model_migration_conflict_union import ModelMigrationConflictUnion
from .validation_utils import ProtocolInfo


@dataclass
class ModelMigrationPlan:
    """Plan for migrating protocols to omnibase_spi."""

    success: bool
    source_repository: str
    target_repository: str
    protocols_to_migrate: list[ProtocolInfo]
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
