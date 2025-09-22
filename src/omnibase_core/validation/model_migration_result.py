"""
Migration result model for protocol migration operations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelMigrationResult:
    """Result of protocol migration operation."""

    success: bool
    source_repository: str
    target_repository: str
    protocols_migrated: int
    files_created: list[str]
    files_deleted: list[str]
    imports_updated: list[str]
    conflicts_resolved: list[str]
    execution_time_minutes: int
    rollback_available: bool
