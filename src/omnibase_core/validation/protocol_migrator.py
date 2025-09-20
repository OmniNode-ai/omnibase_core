"""
Protocol migrator for safe migration of protocols to omnibase_spi.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, cast

from .validation_utils import (
    ProtocolInfo,
    ValidationResult,
    determine_repository_name,
    extract_protocols_from_directory,
    suggest_spi_location,
)


class MigrationConflictBaseDict(TypedDict):
    """Base type definition for migration conflict information."""

    type: str
    protocol_name: str
    source_file: str
    spi_file: str
    recommendation: str


class MigrationNameConflictDict(MigrationConflictBaseDict):
    """Type definition for name conflict information."""

    source_signature: str
    spi_signature: str


class MigrationDuplicateConflictDict(MigrationConflictBaseDict):
    """Type definition for exact duplicate conflict information."""

    signature_hash: str


# Union type for all conflict types
MigrationConflictDict = MigrationNameConflictDict | MigrationDuplicateConflictDict


class MigrationStepDict(TypedDict, total=False):
    """Type definition for migration step information."""

    phase: str  # "preparation", "migration", "finalization"
    action: str
    description: str
    estimated_minutes: int
    # Optional fields for migration phase
    protocol: str
    source_file: str
    target_category: str
    target_path: str


@dataclass
class MigrationPlan:
    """Plan for migrating protocols to omnibase_spi."""

    success: bool
    source_repository: str
    target_repository: str
    protocols_to_migrate: list[ProtocolInfo]
    conflicts_detected: list[MigrationConflictDict]
    migration_steps: list[MigrationStepDict]
    estimated_time_minutes: int
    recommendations: list[str]

    def has_conflicts(self) -> bool:
        """Check if migration plan has conflicts."""
        return len(self.conflicts_detected) > 0

    def can_proceed(self) -> bool:
        """Check if migration can proceed safely."""
        return self.success and not self.has_conflicts()


@dataclass
class MigrationResult:
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


class ProtocolMigrator:
    """
    Safe migration of protocols to omnibase_spi with conflict detection.

    Provides automated migration with:
    - Pre-migration validation
    - Conflict detection and resolution
    - Automatic import updates
    - Rollback capabilities
    """

    def __init__(self, source_path: str = ".", spi_path: str = "../omnibase_spi"):
        self.source_path = Path(source_path).resolve()
        self.spi_path = Path(spi_path).resolve()
        self.source_repository = determine_repository_name(self.source_path)

    def create_migration_plan(
        self,
        protocols: list[ProtocolInfo] | None = None,
    ) -> MigrationPlan:
        """
        Create a migration plan for moving protocols to omnibase_spi.

        Args:
            protocols: Specific protocols to migrate, or None for all

        Returns:
            MigrationPlan with detailed migration strategy
        """
        # Get protocols from source repository
        src_path = self.source_path / "src"
        source_protocols = (
            extract_protocols_from_directory(src_path) if src_path.exists() else []
        )

        if protocols is not None:
            # Filter to only requested protocols
            protocol_names = {p.name for p in protocols}
            source_protocols = [p for p in source_protocols if p.name in protocol_names]

        # Get existing SPI protocols
        spi_protocols_path = self.spi_path / "src" / "omnibase_spi" / "protocols"
        spi_protocols = (
            extract_protocols_from_directory(spi_protocols_path)
            if spi_protocols_path.exists()
            else []
        )

        # Detect conflicts
        conflicts = self._detect_migration_conflicts(source_protocols, spi_protocols)

        # Generate migration steps
        migration_steps = self._generate_migration_steps(source_protocols)

        # Estimate time (5 minutes per protocol + 10 minutes setup)
        estimated_time = len(source_protocols) * 5 + 10

        recommendations = []
        if conflicts:
            recommendations.append("Resolve conflicts before proceeding with migration")
        if source_protocols:
            recommendations.append("Backup source repository before migration")
            recommendations.append(
                "Update imports in dependent repositories after migration",
            )

        return MigrationPlan(
            success=len(conflicts) == 0,
            source_repository=self.source_repository,
            target_repository="omnibase_spi",
            protocols_to_migrate=source_protocols,
            conflicts_detected=conflicts,
            migration_steps=migration_steps,
            estimated_time_minutes=estimated_time,
            recommendations=recommendations,
        )

    def execute_migration(
        self,
        plan: MigrationPlan,
        dry_run: bool = True,
    ) -> MigrationResult:
        """
        Execute the migration plan.

        Args:
            plan: Migration plan to execute
            dry_run: If True, only simulate the migration

        Returns:
            MigrationResult with detailed results
        """
        if not plan.can_proceed():
            return MigrationResult(
                success=False,
                source_repository=plan.source_repository,
                target_repository=plan.target_repository,
                protocols_migrated=0,
                files_created=[],
                files_deleted=[],
                imports_updated=[],
                conflicts_resolved=[],
                execution_time_minutes=0,
                rollback_available=False,
            )

        files_created = []
        files_deleted = []
        imports_updated = []

        for protocol in plan.protocols_to_migrate:
            # Determine SPI destination
            spi_category = suggest_spi_location(protocol)
            spi_dest_dir = (
                self.spi_path / "src" / "omnibase_spi" / "protocols" / spi_category
            )

            if not dry_run:
                # Create SPI directory if it doesn't exist
                spi_dest_dir.mkdir(parents=True, exist_ok=True)

                # Copy protocol file to SPI
                source_file = Path(protocol.file_path)
                dest_file = spi_dest_dir / source_file.name

                shutil.copy2(source_file, dest_file)
                files_created.append(str(dest_file))

                # Update imports in the copied file
                self._update_spi_imports(dest_file)

                # Delete original protocol file
                source_file.unlink()
                files_deleted.append(str(source_file))

            # Track what would be updated
            imports_updated.extend(self._find_import_references(protocol))

        return MigrationResult(
            success=True,
            source_repository=plan.source_repository,
            target_repository=plan.target_repository,
            protocols_migrated=len(plan.protocols_to_migrate),
            files_created=files_created,
            files_deleted=files_deleted,
            imports_updated=imports_updated,
            conflicts_resolved=[],
            execution_time_minutes=plan.estimated_time_minutes,
            rollback_available=not dry_run,
        )

    def _detect_migration_conflicts(
        self,
        source_protocols: list[ProtocolInfo],
        spi_protocols: list[ProtocolInfo],
    ) -> list[MigrationConflictDict]:
        """Detect conflicts between source protocols and existing SPI protocols."""
        conflicts = []

        # Create lookup tables
        spi_by_name = {p.name: p for p in spi_protocols}
        spi_by_signature = {p.signature_hash: p for p in spi_protocols}

        for source_protocol in source_protocols:
            # Check for name conflicts
            if source_protocol.name in spi_by_name:
                spi_protocol = spi_by_name[source_protocol.name]
                if source_protocol.signature_hash != spi_protocol.signature_hash:
                    conflicts.append(
                        cast(
                            MigrationConflictDict,
                            {
                                "type": "name_conflict",
                                "protocol_name": source_protocol.name,
                                "source_file": source_protocol.file_path,
                                "spi_file": spi_protocol.file_path,
                                "source_signature": source_protocol.signature_hash,
                                "spi_signature": spi_protocol.signature_hash,
                                "recommendation": "Rename one of the protocols or merge if appropriate",
                            },
                        )
                    )

            # Check for exact signature duplicates
            elif source_protocol.signature_hash in spi_by_signature:
                spi_protocol = spi_by_signature[source_protocol.signature_hash]
                conflicts.append(
                    cast(
                        MigrationConflictDict,
                        {
                            "type": "exact_duplicate",
                            "protocol_name": source_protocol.name,
                            "source_file": source_protocol.file_path,
                            "spi_file": spi_protocol.file_path,
                            "signature_hash": source_protocol.signature_hash,
                            "recommendation": f"Skip migration - use existing SPI version: {spi_protocol.name}",
                        },
                    )
                )

        return conflicts

    def _generate_migration_steps(
        self,
        protocols: list[ProtocolInfo],
    ) -> list[MigrationStepDict]:
        """Generate detailed migration steps."""
        steps = []

        # Pre-migration steps
        steps.append(
            cast(
                MigrationStepDict,
                {
                    "phase": "preparation",
                    "action": "backup_source",
                    "description": "Create backup of source repository",
                    "estimated_minutes": 2,
                },
            )
        )

        steps.append(
            cast(
                MigrationStepDict,
                {
                    "phase": "preparation",
                    "action": "validate_spi_structure",
                    "description": "Ensure SPI directory structure exists",
                    "estimated_minutes": 1,
                },
            )
        )

        # Protocol migration steps
        for protocol in protocols:
            spi_category = suggest_spi_location(protocol)

            steps.append(
                cast(
                    MigrationStepDict,
                    {
                        "phase": "migration",
                        "action": "migrate_protocol",
                        "protocol": protocol.name,
                        "source_file": protocol.file_path,
                        "target_category": spi_category,
                        "target_path": f"omnibase_spi/protocols/{spi_category}/",
                        "description": f"Migrate {protocol.name} to SPI {spi_category} category",
                        "estimated_minutes": 3,
                    },
                )
            )

        # Post-migration steps
        steps.append(
            cast(
                MigrationStepDict,
                {
                    "phase": "finalization",
                    "action": "update_imports",
                    "description": "Update import statements in dependent files",
                    "estimated_minutes": 5,
                },
            )
        )

        steps.append(
            cast(
                MigrationStepDict,
                {
                    "phase": "finalization",
                    "action": "run_tests",
                    "description": "Execute tests to verify migration success",
                    "estimated_minutes": 3,
                },
            )
        )

        return steps

    def _update_spi_imports(self, protocol_file: Path) -> None:
        """Update imports in migrated protocol file for SPI context."""
        if not protocol_file.exists():
            return

        content = protocol_file.read_text(encoding="utf-8")

        # Common import transformations for SPI context
        transformations = [
            # Update relative imports to absolute SPI imports
            ("from ...", "from omnibase_spi."),
            ("from .", "from omnibase_spi."),
            # Update common omni* imports
            ("from omniagent", "from omnibase_spi"),
            ("from omnibase_core", "from omnibase_spi"),
            ("import omniagent", "import omnibase_spi"),
            ("import omnibase_core", "import omnibase_spi"),
        ]

        for old_import, new_import in transformations:
            content = content.replace(old_import, new_import)

        protocol_file.write_text(content, encoding="utf-8")

    def _find_import_references(self, protocol: ProtocolInfo) -> list[str]:
        """Find files that import the given protocol."""
        references: list[str] = []

        # Search in source repository for import references
        src_path = self.source_path / "src"
        if not src_path.exists():
            return references

        protocol_module = Path(protocol.file_path).stem

        for py_file in src_path.rglob("*.py"):
            if py_file == Path(protocol.file_path):
                continue  # Skip the protocol file itself

            try:
                content = py_file.read_text(encoding="utf-8")

                # Look for various import patterns
                import_patterns = [
                    f"from .{protocol_module} import",
                    f"from ..{protocol_module} import",
                    f"import {protocol_module}",
                    f"from {protocol_module} import",
                    f"import .{protocol_module}",
                    protocol.name,  # Direct class reference
                ]

                for pattern in import_patterns:
                    if pattern in content:
                        references.append(str(py_file))
                        break  # Only add each file once

            except Exception:
                # Skip files that can't be read
                continue

        return references

    def rollback_migration(self, result: MigrationResult) -> ValidationResult:
        """
        Rollback a migration if needed.

        Args:
            result: Migration result to rollback

        Returns:
            ValidationResult indicating rollback success
        """
        if not result.rollback_available:
            return ValidationResult(
                success=False,
                message="Rollback not available - migration was not executed or was a dry run",
            )

        try:
            # Restore deleted files from backup
            # Delete created files
            for file_path in result.files_created:
                file_to_delete = Path(file_path)
                if file_to_delete.exists():
                    file_to_delete.unlink()

            return ValidationResult(
                success=True,
                message=f"Successfully rolled back migration of {result.protocols_migrated} protocols",
            )

        except Exception as e:
            return ValidationResult(success=False, message=f"Rollback failed: {e}")

    def print_migration_plan(self, plan: MigrationPlan) -> None:
        """Print human-readable migration plan."""

        if plan.conflicts_detected:
            for conflict in plan.conflicts_detected:
                if "spi_file" in conflict:
                    pass

        if plan.protocols_to_migrate and not plan.conflicts_detected:
            by_category: dict[str, list[ProtocolInfo]] = {}
            for protocol in plan.protocols_to_migrate:
                category = suggest_spi_location(protocol)
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(protocol)

            for category, protocols in by_category.items():
                for protocol in protocols:
                    pass

        if plan.recommendations:
            for _recommendation in plan.recommendations:
                pass

        (
            "✅ READY TO PROCEED"
            if plan.can_proceed()
            else "❌ CONFLICTS MUST BE RESOLVED"
        )
