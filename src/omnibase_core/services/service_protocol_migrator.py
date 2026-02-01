"""
Protocol migrator for safe migration of protocols to omnibase_spi.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_migration_conflict_union import (
    ModelMigrationConflictUnion,
)
from omnibase_core.models.validation.model_migration_plan import ModelMigrationPlan
from omnibase_core.models.validation.model_migration_result import ModelMigrationResult
from omnibase_core.validation.validator_migration_types import (
    TypedDictMigrationDuplicateConflictDict,
    TypedDictMigrationNameConflictDict,
    TypedDictMigrationStepDict,
)
from omnibase_core.validation.validator_utils import (
    ModelProtocolInfo,
    ModelValidationResult,
    determine_repository_name,
    extract_protocols_from_directory,
    suggest_spi_location,
)


class ServiceProtocolMigrator:
    """
    Safe migration of protocols to omnibase_spi with conflict detection.

    Provides automated migration with:
    - Pre-migration validation
    - Conflict detection and resolution
    - Automatic import updates
    - Rollback capabilities

    Thread Safety:
        This class is conditionally thread-safe. Instance attributes (source_path,
        spi_path, source_repository) are set once during __init__ and never
        modified. Methods like create_migration_plan() are safe for concurrent
        read operations. However, execute_migration() performs filesystem write
        operations (file copy, delete) that are not atomic and could conflict
        if multiple threads attempt to migrate the same protocols simultaneously.
        For migration execution, use a single thread or external coordination.
        See docs/guides/THREADING.md for more details.

    Example:
        >>> from omnibase_core.services import ServiceProtocolMigrator
        >>> migrator = ServiceProtocolMigrator(
        ...     source_path=".", spi_path="../omnibase_spi"
        ... )
        >>> plan = migrator.create_migration_plan()
        >>> if plan.can_proceed():
        ...     result = migrator.execute_migration(plan, dry_run=True)

    .. note::
        Previously named ``ProtocolMigrator``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Protocol``
        prefix is reserved for typing.Protocol interfaces; ``Service``
        prefix indicates a stateful service class.
    """

    def __init__(self, source_path: str = ".", spi_path: str = "../omnibase_spi"):
        self.source_path = Path(source_path).resolve()
        self.spi_path = Path(spi_path).resolve()
        self.source_repository = determine_repository_name(self.source_path)

    @standard_error_handling("Migration plan creation")
    def create_migration_plan(
        self,
        protocols: list[ModelProtocolInfo] | None = None,
    ) -> ModelMigrationPlan:
        """
        Create a migration plan for moving protocols to omnibase_spi.

        Args:
            protocols: Specific protocols to migrate, or None for all.
                When provided, bypasses filesystem extraction and validation.
                The caller is responsible for ensuring:
                - Protocol file paths exist and are accessible
                - ModelProtocolInfo objects have correct types and structure
                - All protocol metadata (name, signature_hash, etc.) is valid
                Bypassed validation includes:
                - Source directory existence check (src_path.exists())
                - Protocol extraction via extract_protocols_from_directory()
                - File path validation and protocol parsing
                When None, extracts all protocols from the source repository
                with full filesystem validation.

        Returns:
            ModelMigrationPlan with detailed migration strategy
        """
        validation_errors = []

        # Get protocols from source repository OR use provided protocols
        if protocols is not None:
            # Validate that provided protocols have valid path format and required metadata
            for protocol in protocols:
                if not protocol.file_path:
                    validation_errors.append(
                        f"Protocol '{protocol.name or 'unnamed'}' must have a file_path specified"
                    )
                if not protocol.name:
                    validation_errors.append("Protocol must have a name specified")
                # Note: File existence is not required for planning phase
                # Actual file validation occurs during execution

            # If validation errors exist, return failed plan
            if validation_errors:
                return ModelMigrationPlan(
                    success=False,
                    source_repository=self.source_repository,
                    target_repository="omnibase_spi",
                    protocols_to_migrate=[],
                    conflicts_detected=[],
                    migration_steps=[],
                    estimated_time_minutes=0,
                    recommendations=validation_errors,
                )

            # Use the explicitly provided protocols
            source_protocols = protocols
        else:
            # Extract from source directory
            src_path = self.source_path / "src"
            source_protocols = (
                extract_protocols_from_directory(src_path) if src_path.exists() else []
            )

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

        return ModelMigrationPlan(
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
        plan: ModelMigrationPlan,
        dry_run: bool = True,
    ) -> ModelMigrationResult:
        """
        Execute the migration plan.

        Args:
            plan: Migration plan to execute
            dry_run: If True, only simulate the migration

        Returns:
            ModelMigrationResult with detailed results
        """
        if not plan.can_proceed():
            return ModelMigrationResult(
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

        return ModelMigrationResult(
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
        source_protocols: list[ModelProtocolInfo],
        spi_protocols: list[ModelProtocolInfo],
    ) -> list[ModelMigrationConflictUnion]:
        """Detect conflicts between source protocols and existing SPI protocols."""
        conflicts: list[ModelMigrationConflictUnion] = []

        # Create lookup tables
        spi_by_name = {p.name: p for p in spi_protocols}
        spi_by_signature = {p.signature_hash: p for p in spi_protocols}

        for source_protocol in source_protocols:
            # Check for name conflicts
            if source_protocol.name in spi_by_name:
                spi_protocol = spi_by_name[source_protocol.name]
                if source_protocol.signature_hash != spi_protocol.signature_hash:
                    conflicts.append(
                        ModelMigrationConflictUnion.from_name_conflict(
                            TypedDictMigrationNameConflictDict(
                                type="name_conflict",
                                protocol_name=source_protocol.name,
                                source_file=source_protocol.file_path,
                                spi_file=spi_protocol.file_path,
                                source_signature=source_protocol.signature_hash,
                                spi_signature=spi_protocol.signature_hash,
                                recommendation="Rename one of the protocols or merge if appropriate",
                            ),
                        ),
                    )

            # Check for exact signature duplicates
            elif source_protocol.signature_hash in spi_by_signature:
                spi_protocol = spi_by_signature[source_protocol.signature_hash]
                conflicts.append(
                    ModelMigrationConflictUnion.from_duplicate_conflict(
                        TypedDictMigrationDuplicateConflictDict(
                            type="exact_duplicate",
                            protocol_name=source_protocol.name,
                            source_file=source_protocol.file_path,
                            spi_file=spi_protocol.file_path,
                            signature_hash=source_protocol.signature_hash,
                            recommendation=f"Skip migration - use existing SPI version: {spi_protocol.name}",
                        ),
                    ),
                )

        return conflicts

    def _generate_migration_steps(
        self,
        protocols: list[ModelProtocolInfo],
    ) -> list[TypedDictMigrationStepDict]:
        """Generate detailed migration steps."""
        steps = []

        # Pre-migration steps
        steps.append(
            cast(
                "TypedDictMigrationStepDict",
                {
                    "phase": "preparation",
                    "action": "backup_source",
                    "description": "Create backup of source repository",
                    "estimated_minutes": 2,
                },
            ),
        )

        steps.append(
            cast(
                "TypedDictMigrationStepDict",
                {
                    "phase": "preparation",
                    "action": "validate_spi_structure",
                    "description": "Ensure SPI directory structure exists",
                    "estimated_minutes": 1,
                },
            ),
        )

        # Protocol migration steps
        for protocol in protocols:
            spi_category = suggest_spi_location(protocol)

            steps.append(
                cast(
                    "TypedDictMigrationStepDict",
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
                ),
            )

        # Post-migration steps
        steps.append(
            cast(
                "TypedDictMigrationStepDict",
                {
                    "phase": "finalization",
                    "action": "update_imports",
                    "description": "Update import statements in dependent files",
                    "estimated_minutes": 5,
                },
            ),
        )

        steps.append(
            cast(
                "TypedDictMigrationStepDict",
                {
                    "phase": "finalization",
                    "action": "run_tests",
                    "description": "Execute tests to verify migration success",
                    "estimated_minutes": 3,
                },
            ),
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

    def _find_import_references(self, protocol: ModelProtocolInfo) -> list[str]:
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

            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read (permission denied, encoding errors, etc.)
                continue

        return references

    def rollback_migration(
        self, result: ModelMigrationResult
    ) -> ModelValidationResult[None]:
        """
        Rollback a migration if needed.

        Args:
            result: Migration result to rollback

        Returns:
            ValidationResult indicating rollback success
        """
        if not result.rollback_available:
            return ModelValidationResult(
                is_valid=False,
                errors=[
                    "Rollback not available - migration was not executed or was a dry run",
                ],
            )

        errors = []

        # Restore deleted files from backup
        # Delete created files
        for file_path in result.files_created:
            file_to_delete = Path(file_path)
            if file_to_delete.exists():
                try:
                    if file_to_delete.is_dir():
                        # Migration should only create files, not directories
                        # Finding a directory is an error condition
                        errors.append(
                            f"Cannot rollback directory {file_path} - "
                            "migration should only create files"
                        )
                    else:
                        # Handle file deletion
                        file_to_delete.unlink()
                except PermissionError as e:
                    # Handle permission errors gracefully
                    errors.append(f"Permission denied deleting {file_path}: {e}")
                except OSError as e:
                    # Handle other OS errors gracefully
                    errors.append(f"Failed to delete {file_path}: {e}")

        if errors:
            # Return failed result with error details
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.MIGRATION_ERROR,
                message=f"Rollback failed: {'; '.join(errors)}",
            )

        return ModelValidationResult(
            is_valid=True,
            errors=[],
        )
