"""
Comprehensive unit tests for Protocol Migrator.

Tests cover:
- ProtocolMigrator initialization
- Migration plan creation
- Conflict detection (name conflicts, duplicates)
- Migration execution (dry run and actual)
- Import updates
- Rollback functionality
- Migration step generation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.enums.enum_migration_conflict_type import EnumMigrationConflictType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_migration_conflict_union import (
    ModelMigrationConflictUnion,
)
from omnibase_core.models.validation.model_migration_plan import ModelMigrationPlan
from omnibase_core.models.validation.model_migration_result import ModelMigrationResult
from omnibase_core.validation.migrator_protocol import ProtocolMigrator
from omnibase_core.validation.validation_utils import ModelProtocolInfo

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


class TestProtocolMigratorInitialization:
    """Test ProtocolMigrator initialization."""

    def test_migrator_initialization_defaults(self, tmp_path: Path) -> None:
        """Test migrator initializes with default paths."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        assert migrator.source_path.exists()
        assert migrator.spi_path.exists()
        assert migrator.source_repository is not None

    def test_migrator_initialization_custom_paths(self, tmp_path: Path) -> None:
        """Test migrator with custom paths."""
        custom_source = tmp_path / "custom_source"
        custom_source.mkdir()
        custom_spi = tmp_path / "custom_spi"
        custom_spi.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(custom_source),
            spi_path=str(custom_spi),
        )

        assert migrator.source_path == custom_source.resolve()
        assert migrator.spi_path == custom_spi.resolve()


class TestMigrationPlanCreation:
    """Test migration plan creation."""

    def test_create_plan_empty_protocols(self, tmp_path: Path) -> None:
        """Test creating plan with no protocols."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        (source_path / "src").mkdir()

        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        plan = migrator.create_migration_plan()

        assert isinstance(plan, ModelMigrationPlan)
        assert len(plan.protocols_to_migrate) == 0
        assert len(plan.conflicts_detected) == 0
        assert plan.success is True

    def test_create_plan_with_protocols(self, tmp_path: Path) -> None:
        """Test creating plan with specific protocols."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path=str(source_path / "test_protocol.py"),
                repository="test_repo",
                methods=["method1"],
                signature_hash="test_hash",
                line_count=50,
                imports=["typing"],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=protocols)

        assert isinstance(plan, ModelMigrationPlan)
        assert len(plan.protocols_to_migrate) == 1
        assert plan.protocols_to_migrate[0].name == "TestProtocol"

    def test_create_plan_estimates_time(self, tmp_path: Path) -> None:
        """Test plan includes time estimation."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        protocols = [
            ModelProtocolInfo(
                name=f"Protocol{i}",
                file_path=str(source_path / f"protocol{i}.py"),
                repository="test_repo",
                methods=["method"],
                signature_hash=f"hash{i}",
                line_count=50,
                imports=[],
            )
            for i in range(3)
        ]

        plan = migrator.create_migration_plan(protocols=protocols)

        # Should have time estimate (5 min per protocol + 10 min setup)
        assert plan.estimated_time_minutes == 25  # 3*5 + 10

    def test_create_plan_includes_recommendations(self, tmp_path: Path) -> None:
        """Test plan includes recommendations."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path=str(source_path / "test_protocol.py"),
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=protocols)

        assert len(plan.recommendations) > 0
        assert any("Backup" in rec for rec in plan.recommendations)


class TestConflictDetection:
    """Test conflict detection logic."""

    def test_detect_name_conflict(self, tmp_path: Path) -> None:
        """Test detection of protocol name conflicts."""
        source_protocols = [
            ModelProtocolInfo(
                name="ConflictProtocol",
                file_path="/source/conflict.py",
                repository="source_repo",
                methods=["method1"],
                signature_hash="source_hash",
                line_count=50,
                imports=[],
            ),
        ]

        spi_protocols = [
            ModelProtocolInfo(
                name="ConflictProtocol",  # Same name
                file_path="/spi/conflict.py",
                repository="spi",
                methods=["method2"],  # Different signature
                signature_hash="spi_hash",
                line_count=60,
                imports=[],
            ),
        ]

        migrator = ProtocolMigrator()
        conflicts = migrator._detect_migration_conflicts(
            source_protocols, spi_protocols
        )

        assert len(conflicts) == 1
        assert isinstance(conflicts[0], ModelMigrationConflictUnion)
        assert conflicts[0].conflict_type == EnumMigrationConflictType.NAME_CONFLICT
        assert conflicts[0].protocol_name == "ConflictProtocol"

    def test_detect_duplicate_conflict(self, tmp_path: Path) -> None:
        """Test detection of exact duplicate protocols."""
        source_protocols = [
            ModelProtocolInfo(
                name="DuplicateProtocol",
                file_path="/source/duplicate.py",
                repository="source_repo",
                methods=["method1"],
                signature_hash="same_hash",  # Same signature
                line_count=50,
                imports=[],
            ),
        ]

        spi_protocols = [
            ModelProtocolInfo(
                name="ExistingProtocol",  # Different name
                file_path="/spi/existing.py",
                repository="spi",
                methods=["method1"],  # Same signature
                signature_hash="same_hash",
                line_count=50,
                imports=[],
            ),
        ]

        migrator = ProtocolMigrator()
        conflicts = migrator._detect_migration_conflicts(
            source_protocols, spi_protocols
        )

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == EnumMigrationConflictType.EXACT_DUPLICATE
        assert conflicts[0].signature_hash == "same_hash"

    def test_detect_no_conflicts(self, tmp_path: Path) -> None:
        """Test no conflicts when protocols are unique."""
        source_protocols = [
            ModelProtocolInfo(
                name="SourceProtocol",
                file_path="/source/source.py",
                repository="source_repo",
                methods=["method1"],
                signature_hash="source_hash",
                line_count=50,
                imports=[],
            ),
        ]

        spi_protocols = [
            ModelProtocolInfo(
                name="SpiProtocol",  # Different name and signature
                file_path="/spi/spi.py",
                repository="spi",
                methods=["method2"],
                signature_hash="spi_hash",
                line_count=60,
                imports=[],
            ),
        ]

        migrator = ProtocolMigrator()
        conflicts = migrator._detect_migration_conflicts(
            source_protocols, spi_protocols
        )

        assert len(conflicts) == 0


class TestMigrationExecution:
    """Test migration execution."""

    def test_execute_migration_dry_run(self, tmp_path: Path) -> None:
        """Test migration execution in dry run mode."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path=str(source_path / "test_protocol.py"),
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=protocols)
        result = migrator.execute_migration(plan, dry_run=True)

        assert isinstance(result, ModelMigrationResult)
        assert result.success is True
        assert result.protocols_migrated == 1
        assert result.rollback_available is False  # Dry run doesn't support rollback

    def test_execute_migration_with_conflicts(self, tmp_path: Path) -> None:
        """Test migration execution fails when conflicts exist."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        # Create plan with conflicts
        plan = ModelMigrationPlan(
            success=False,  # Has conflicts
            source_repository="source_repo",
            target_repository="spi",
            protocols_to_migrate=[],
            conflicts_detected=[
                ModelMigrationConflictUnion(
                    conflict_type=EnumMigrationConflictType.NAME_CONFLICT,
                    protocol_name="ConflictProtocol",
                    source_file="/source/conflict.py",
                    spi_file="/spi/conflict.py",
                    recommendation="Rename protocol",
                    source_signature="hash1",
                    spi_signature="hash2",
                ),
            ],
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=[],
        )

        result = migrator.execute_migration(plan, dry_run=True)

        assert result.success is False
        assert result.protocols_migrated == 0

    def test_execute_migration_actual(self, tmp_path: Path) -> None:
        """Test actual migration execution."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        src_dir = source_path / "src"
        src_dir.mkdir()

        spi_path = tmp_path / "spi"
        spi_path.mkdir()
        (spi_path / "src" / "omnibase_spi" / "protocols").mkdir(parents=True)

        # Create source protocol file
        protocol_file = src_dir / "test_protocol.py"
        protocol_file.write_text(
            """
from typing import Protocol

class TestProtocol(Protocol):
    def test_method(self) -> None:
        pass
"""
        )

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path=str(protocol_file),
                repository="test_repo",
                methods=["test_method"],
                signature_hash="hash",
                line_count=6,
                imports=["typing"],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=protocols)
        result = migrator.execute_migration(plan, dry_run=False)

        assert isinstance(result, ModelMigrationResult)
        assert result.success is True
        assert result.protocols_migrated == 1
        assert len(result.files_created) > 0
        assert len(result.files_deleted) > 0


class TestMigrationSteps:
    """Test migration step generation."""

    def test_generate_migration_steps(self, tmp_path: Path) -> None:
        """Test migration steps are generated correctly."""
        migrator = ProtocolMigrator()

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path="/test/protocol.py",
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        steps = migrator._generate_migration_steps(protocols)

        assert len(steps) > 0

        # Check for expected phases
        phases = {step["phase"] for step in steps}
        assert "preparation" in phases
        assert "migration" in phases
        assert "finalization" in phases

        # Check for specific actions
        actions = {step["action"] for step in steps}
        assert "backup_source" in actions
        assert "migrate_protocol" in actions
        assert "update_imports" in actions

    def test_migration_steps_include_time_estimates(self, tmp_path: Path) -> None:
        """Test migration steps include time estimates."""
        migrator = ProtocolMigrator()

        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path="/test/protocol.py",
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        steps = migrator._generate_migration_steps(protocols)

        # All steps should have time estimates
        for step in steps:
            assert "estimated_minutes" in step
            assert isinstance(step["estimated_minutes"], int)
            assert step["estimated_minutes"] > 0


class TestImportUpdates:
    """Test import update functionality."""

    def test_update_spi_imports(self, tmp_path: Path) -> None:
        """Test SPI imports are updated correctly."""
        migrator = ProtocolMigrator()

        # Create test file with imports
        test_file = tmp_path / "test_protocol.py"
        test_file.write_text(
            """
from ..models import SomeModel
from omnibase_core.utils import helper
import omnibase_core
"""
        )

        migrator._update_spi_imports(test_file)

        updated_content = test_file.read_text()

        # Check transformations
        assert "from omnibase_spi." in updated_content
        assert "import omnibase_spi" in updated_content

    def test_update_spi_imports_nonexistent_file(self, tmp_path: Path) -> None:
        """Test updating imports handles nonexistent files gracefully."""
        migrator = ProtocolMigrator()

        nonexistent = tmp_path / "nonexistent.py"

        # Should not raise exception
        migrator._update_spi_imports(nonexistent)

    def test_find_import_references(self, tmp_path: Path) -> None:
        """Test finding files that import a protocol."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        src_dir = source_path / "src"
        src_dir.mkdir()

        # Create protocol file
        protocol_file = src_dir / "test_protocol.py"
        protocol_file.write_text(
            """
class TestProtocol:
    pass
"""
        )

        # Create file that imports the protocol
        importer_file = src_dir / "importer.py"
        importer_file.write_text(
            """
from .test_protocol import TestProtocol
"""
        )

        migrator = ProtocolMigrator(source_path=str(source_path))

        protocol_info = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(protocol_file),
            repository="test_repo",
            methods=[],
            signature_hash="hash",
            line_count=3,
            imports=[],
        )

        references = migrator._find_import_references(protocol_info)

        assert len(references) > 0
        assert any(str(importer_file) in ref for ref in references)

    def test_find_import_references_no_imports(self, tmp_path: Path) -> None:
        """Test finding references when no imports exist."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        src_dir = source_path / "src"
        src_dir.mkdir()

        protocol_file = src_dir / "test_protocol.py"
        protocol_file.write_text("class TestProtocol: pass")

        migrator = ProtocolMigrator(source_path=str(source_path))

        protocol_info = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(protocol_file),
            repository="test_repo",
            methods=[],
            signature_hash="hash",
            line_count=1,
            imports=[],
        )

        references = migrator._find_import_references(protocol_info)

        # Should find no references (only the protocol file itself)
        assert len(references) == 0


class TestRollback:
    """Test rollback functionality."""

    def test_rollback_dry_run(self, tmp_path: Path) -> None:
        """Test rollback fails for dry run migrations."""
        migrator = ProtocolMigrator()

        result = ModelMigrationResult(
            success=True,
            source_repository="source",
            target_repository="spi",
            protocols_migrated=1,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=False,  # Dry run
        )

        rollback_result = migrator.rollback_migration(result)

        assert rollback_result.success is False
        assert "not available" in rollback_result.errors[0].lower()

    def test_rollback_successful(self, tmp_path: Path) -> None:
        """Test successful rollback."""
        migrator = ProtocolMigrator()

        # Create test file
        created_file = tmp_path / "created.py"
        created_file.write_text("# Created during migration")

        result = ModelMigrationResult(
            success=True,
            source_repository="source",
            target_repository="spi",
            protocols_migrated=1,
            files_created=[str(created_file)],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=True,
        )

        rollback_result = migrator.rollback_migration(result)

        assert rollback_result.success is True
        assert not created_file.exists()  # Should be deleted


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_migrator_with_nonexistent_source(self, tmp_path: Path) -> None:
        """Test migrator handles nonexistent source path."""
        nonexistent = tmp_path / "nonexistent"
        spi_path = tmp_path / "spi"
        spi_path.mkdir()

        # Should not raise exception during initialization
        migrator = ProtocolMigrator(
            source_path=str(nonexistent),
            spi_path=str(spi_path),
        )

        assert migrator.source_path == nonexistent.resolve()

    def test_create_plan_filters_protocols(self, tmp_path: Path) -> None:
        """Test plan creation filters to requested protocols."""
        migrator = ProtocolMigrator()

        all_protocols = [
            ModelProtocolInfo(
                name="Protocol1",
                file_path="/test/p1.py",
                repository="test",
                methods=[],
                signature_hash="hash1",
                line_count=10,
                imports=[],
            ),
            ModelProtocolInfo(
                name="Protocol2",
                file_path="/test/p2.py",
                repository="test",
                methods=[],
                signature_hash="hash2",
                line_count=10,
                imports=[],
            ),
        ]

        # Only request Protocol1
        requested = [all_protocols[0]]

        # This would filter if source had both protocols
        # In this case, we're testing the filtering logic
        plan = migrator.create_migration_plan(protocols=requested)

        # Plan should only include requested protocol
        assert all(p.name == "Protocol1" for p in plan.protocols_to_migrate)

    def test_migration_result_metadata(self, tmp_path: Path) -> None:
        """Test migration result includes comprehensive metadata."""
        result = ModelMigrationResult(
            success=True,
            source_repository="source_repo",
            target_repository="target_repo",
            protocols_migrated=5,
            files_created=["/spi/p1.py", "/spi/p2.py"],
            files_deleted=["/source/p1.py", "/source/p2.py"],
            imports_updated=["/source/importer.py"],
            conflicts_resolved=[],
            execution_time_minutes=25,
            rollback_available=True,
        )

        assert result.protocols_migrated == 5
        assert len(result.files_created) == 2
        assert len(result.files_deleted) == 2
        assert len(result.imports_updated) == 1
        assert result.rollback_available is True


class TestValidationErrors:
    """Test validation error handling."""

    def test_create_plan_protocol_without_file_path(self, tmp_path: Path) -> None:
        """Test creating plan with protocol missing file_path returns error result."""
        migrator = ProtocolMigrator()

        # Protocol without file_path
        invalid_protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path="",  # Empty file path
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=invalid_protocols)

        assert plan.success is False
        assert len(plan.recommendations) > 0
        assert any("file_path" in rec.lower() for rec in plan.recommendations)

    def test_create_plan_protocol_without_name(self, tmp_path: Path) -> None:
        """Test creating plan with protocol missing name returns error result."""
        migrator = ProtocolMigrator()

        # Protocol without name
        invalid_protocols = [
            ModelProtocolInfo(
                name="",  # Empty name
                file_path="/test/protocol.py",
                repository="test_repo",
                methods=["method"],
                signature_hash="hash",
                line_count=50,
                imports=[],
            ),
        ]

        plan = migrator.create_migration_plan(protocols=invalid_protocols)

        assert plan.success is False
        assert len(plan.recommendations) > 0
        assert any("name" in rec.lower() for rec in plan.recommendations)

    def test_create_plan_with_conflicts_includes_recommendation(
        self, tmp_path: Path
    ) -> None:
        """Test plan with conflicts includes conflict resolution recommendation."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        (source_path / "src").mkdir()

        spi_path = tmp_path / "spi"
        spi_path.mkdir()
        (spi_path / "src" / "omnibase_spi" / "protocols").mkdir(parents=True)

        # Create a test protocol file in SPI
        spi_protocol = (
            spi_path / "src" / "omnibase_spi" / "protocols" / "protocol_test.py"
        )
        spi_protocol.write_text(
            """
from typing import Protocol

class TestProtocol(Protocol):
    def different_method(self) -> None:
        pass
"""
        )

        migrator = ProtocolMigrator(
            source_path=str(source_path),
            spi_path=str(spi_path),
        )

        # Create protocol with same name but different signature
        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path=str(source_path / "test_protocol.py"),
                repository="test_repo",
                methods=["method"],
                signature_hash="different_hash",
                line_count=50,
                imports=[],
            ),
        ]

        # This will detect conflict and add recommendation
        plan = migrator.create_migration_plan(protocols=protocols)

        # Should have recommendation to resolve conflicts
        assert any(
            "conflict" in rec.lower() for rec in plan.recommendations
        ), f"Expected conflict recommendation but got: {plan.recommendations}"

    def test_find_import_references_with_unreadable_file(self, tmp_path: Path) -> None:
        """Test finding references handles unreadable files gracefully."""
        source_path = tmp_path / "source"
        source_path.mkdir()
        src_dir = source_path / "src"
        src_dir.mkdir()

        protocol_file = src_dir / "test_protocol.py"
        protocol_file.write_text("class TestProtocol: pass")

        # Create a subdirectory with a file that will be unreadable
        subdir = src_dir / "subdir"
        subdir.mkdir()
        unreadable_file = subdir / "unreadable.py"
        unreadable_file.write_text("# This file will have read issues")

        # Make file unreadable by changing permissions (Unix-like systems)
        import platform

        if platform.system() != "Windows":
            Path(unreadable_file).chmod(0o000)

        migrator = ProtocolMigrator(source_path=str(source_path))

        protocol_info = ModelProtocolInfo(
            name="TestProtocol",
            file_path=str(protocol_file),
            repository="test_repo",
            methods=[],
            signature_hash="hash",
            line_count=1,
            imports=[],
        )

        try:
            # Should not raise exception even with unreadable file
            references = migrator._find_import_references(protocol_info)
            # Just verify it completes without error
            assert isinstance(references, list)
        finally:
            # Restore permissions for cleanup
            if platform.system() != "Windows":
                Path(unreadable_file).chmod(0o644)

    def test_rollback_migration_with_error(self, tmp_path: Path) -> None:
        """Test rollback handling when file deletion fails."""
        import uuid

        migrator = ProtocolMigrator()

        # Create a directory with unique name to avoid parallel test conflicts
        unique_id = str(uuid.uuid4())[:8]
        created_dir = tmp_path / f"rollback_test_dir_{unique_id}"

        # Ensure clean state - remove if exists from previous runs
        if created_dir.exists():
            import shutil

            shutil.rmtree(created_dir)

        # Create the directory
        created_dir.mkdir(parents=True, exist_ok=False)

        # Create a file inside to make it non-empty
        test_file = created_dir / "file.txt"
        test_file.write_text("test")

        # Verify test preconditions
        assert created_dir.exists(), "Test setup failed: directory should exist"
        assert created_dir.is_dir(), "Test setup failed: path should be a directory"
        assert test_file.exists(), "Test setup failed: test file should exist"

        result = ModelMigrationResult(
            success=True,
            source_repository="source",
            target_repository="spi",
            protocols_migrated=1,
            files_created=[str(created_dir)],  # Directory path, not file
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=True,
        )

        # Verify directory still exists right before rollback call
        assert created_dir.exists(), "Directory should exist before rollback"

        # Attempting to delete a directory as if it were a file should raise error
        with pytest.raises(ModelOnexError) as exc_info:
            migrator.rollback_migration(result)

        # Verify error code matches expected MIGRATION_ERROR
        assert exc_info.value.error_code == EnumCoreErrorCode.MIGRATION_ERROR
        # Verify error message contains expected text
        assert "rollback failed" in str(exc_info.value.message).lower()
        assert "cannot rollback directory" in str(exc_info.value.message).lower()
