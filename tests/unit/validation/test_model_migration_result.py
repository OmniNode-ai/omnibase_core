"""
Comprehensive unit tests for ModelMigrationResult.

Tests cover:
- Migration result initialization
- Tracking of migrated protocols
- File operation tracking (created, deleted)
- Import update tracking
- Conflict resolution tracking
- Execution time tracking
- Rollback availability
"""

from __future__ import annotations

import pytest

from omnibase_core.models.validation.model_migration_result import ModelMigrationResult


class TestModelMigrationResult:
    """Test ModelMigrationResult class."""

    def test_migration_result_initialization(self) -> None:
        """Test basic migration result initialization."""
        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=5,
            files_created=["/spi/protocol1.py", "/spi/protocol2.py"],
            files_deleted=["/old/protocol1.py"],
            imports_updated=["/core/main.py"],
            conflicts_resolved=["Resolved name conflict"],
            execution_time_minutes=10,
            rollback_available=True,
        )

        assert result.success is True
        assert result.source_repository == "omnibase_core"
        assert result.target_repository == "omnibase_spi"
        assert result.protocols_migrated == 5
        assert len(result.files_created) == 2
        assert len(result.files_deleted) == 1
        assert len(result.imports_updated) == 1
        assert len(result.conflicts_resolved) == 1
        assert result.execution_time_minutes == 10
        assert result.rollback_available is True

    def test_migration_result_successful_no_changes(self) -> None:
        """Test successful migration with no file changes."""
        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=0,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=1,
            rollback_available=False,
        )

        assert result.success is True
        assert result.protocols_migrated == 0
        assert len(result.files_created) == 0
        assert len(result.files_deleted) == 0
        assert result.rollback_available is False

    def test_migration_result_failure(self) -> None:
        """Test failed migration result."""
        result = ModelMigrationResult(
            success=False,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=0,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=True,
        )

        assert result.success is False
        assert result.protocols_migrated == 0
        assert result.rollback_available is True  # Rollback available on failure

    def test_migration_result_multiple_files_created(self) -> None:
        """Test migration result with multiple files created."""
        created_files = [
            "/spi/agent_protocol.py",
            "/spi/workflow_protocol.py",
            "/spi/file_protocol.py",
            "/spi/__init__.py",
        ]

        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=3,
            files_created=created_files,
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=8,
            rollback_available=True,
        )

        assert len(result.files_created) == 4
        assert "/spi/agent_protocol.py" in result.files_created
        assert "/spi/__init__.py" in result.files_created

    def test_migration_result_multiple_files_deleted(self) -> None:
        """Test migration result with multiple files deleted."""
        deleted_files = [
            "/old/legacy_protocol1.py",
            "/old/legacy_protocol2.py",
            "/old/deprecated.py",
        ]

        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=2,
            files_created=[],
            files_deleted=deleted_files,
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=True,
        )

        assert len(result.files_deleted) == 3
        assert "/old/legacy_protocol1.py" in result.files_deleted

    def test_migration_result_import_updates(self) -> None:
        """Test migration result with import updates."""
        imports_updated = [
            "/core/agent_manager.py",
            "/core/workflow_engine.py",
            "/core/__init__.py",
            "/tests/test_protocols.py",
        ]

        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=2,
            files_created=[],
            files_deleted=[],
            imports_updated=imports_updated,
            conflicts_resolved=[],
            execution_time_minutes=12,
            rollback_available=True,
        )

        assert len(result.imports_updated) == 4
        assert "/core/agent_manager.py" in result.imports_updated
        assert "/tests/test_protocols.py" in result.imports_updated

    def test_migration_result_conflict_resolution(self) -> None:
        """Test migration result with resolved conflicts."""
        conflicts_resolved = [
            "Resolved name conflict for AgentProtocol",
            "Merged signature differences in WorkflowProtocol",
            "Updated version for FileProtocol",
        ]

        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=3,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=conflicts_resolved,
            execution_time_minutes=15,
            rollback_available=True,
        )

        assert len(result.conflicts_resolved) == 3
        assert "AgentProtocol" in result.conflicts_resolved[0]
        assert "WorkflowProtocol" in result.conflicts_resolved[1]

    def test_migration_result_execution_time(self) -> None:
        """Test migration result execution time tracking."""
        # Quick migration
        quick_result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=1,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=2,
            rollback_available=True,
        )
        assert quick_result.execution_time_minutes == 2

        # Long migration
        long_result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=20,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=45,
            rollback_available=True,
        )
        assert long_result.execution_time_minutes == 45

    def test_migration_result_rollback_scenarios(self) -> None:
        """Test different rollback availability scenarios."""
        # Rollback available on success
        success_with_rollback = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=5,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=10,
            rollback_available=True,
        )
        assert success_with_rollback.rollback_available is True

        # Rollback not available
        no_rollback = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=3,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=False,
        )
        assert no_rollback.rollback_available is False

    def test_migration_result_complex_scenario(self) -> None:
        """Test complex migration scenario with all components."""
        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=10,
            files_created=[
                "/spi/agent/agent_protocol.py",
                "/spi/agent/__init__.py",
                "/spi/workflow/workflow_protocol.py",
                "/spi/workflow/__init__.py",
                "/spi/core/core_protocol.py",
            ],
            files_deleted=[
                "/old/protocols/agent.py",
                "/old/protocols/workflow.py",
                "/old/protocols/__init__.py",
            ],
            imports_updated=[
                "/core/agent_manager.py",
                "/core/workflow_engine.py",
                "/core/file_handler.py",
                "/tests/test_agent.py",
                "/tests/test_workflow.py",
            ],
            conflicts_resolved=[
                "Resolved naming conflict in AgentProtocol",
                "Merged method signatures in WorkflowProtocol",
            ],
            execution_time_minutes=25,
            rollback_available=True,
        )

        # Comprehensive checks
        assert result.success is True
        assert result.protocols_migrated == 10
        assert len(result.files_created) == 5
        assert len(result.files_deleted) == 3
        assert len(result.imports_updated) == 5
        assert len(result.conflicts_resolved) == 2
        assert result.execution_time_minutes == 25
        assert result.rollback_available is True

    def test_migration_result_zero_protocols_migrated(self) -> None:
        """Test migration result with zero protocols migrated."""
        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=0,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=1,
            rollback_available=False,
        )

        assert result.protocols_migrated == 0
        assert result.success is True  # Can still be successful with 0 protocols

    def test_migration_result_high_protocol_count(self) -> None:
        """Test migration result with many protocols."""
        result = ModelMigrationResult(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=100,
            files_created=[f"/spi/protocol_{i}.py" for i in range(100)],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=60,
            rollback_available=True,
        )

        assert result.protocols_migrated == 100
        assert len(result.files_created) == 100

    def test_migration_result_dataclass_properties(self) -> None:
        """Test that ModelMigrationResult is a proper dataclass."""
        result = ModelMigrationResult(
            success=True,
            source_repository="test_source",
            target_repository="test_target",
            protocols_migrated=1,
            files_created=[],
            files_deleted=[],
            imports_updated=[],
            conflicts_resolved=[],
            execution_time_minutes=5,
            rollback_available=True,
        )

        # Test dataclass fields are accessible
        assert hasattr(result, "success")
        assert hasattr(result, "source_repository")
        assert hasattr(result, "target_repository")
        assert hasattr(result, "protocols_migrated")
        assert hasattr(result, "files_created")
        assert hasattr(result, "files_deleted")
        assert hasattr(result, "imports_updated")
        assert hasattr(result, "conflicts_resolved")
        assert hasattr(result, "execution_time_minutes")
        assert hasattr(result, "rollback_available")

    def test_migration_result_partial_success_scenario(self) -> None:
        """Test partial migration success with some operations completed."""
        result = ModelMigrationResult(
            success=False,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_migrated=3,  # Some protocols were migrated
            files_created=[
                "/spi/protocol1.py",
                "/spi/protocol2.py",
            ],
            files_deleted=["/old/protocol1.py"],
            imports_updated=["/core/main.py"],
            conflicts_resolved=[],
            execution_time_minutes=8,
            rollback_available=True,  # Rollback available for partial migration
        )

        assert result.success is False
        assert result.protocols_migrated == 3  # Partial migration
        assert len(result.files_created) == 2
        assert result.rollback_available is True

    def test_migration_result_string_repositories(self) -> None:
        """Test migration result with various repository names."""
        repositories = [
            ("omnibase_core", "omnibase_spi"),
            ("omniagent", "omnibase_spi"),
            ("omnisearch", "omnibase_spi"),
            ("omnitask", "omnibase_spi"),
        ]

        for source, target in repositories:
            result = ModelMigrationResult(
                success=True,
                source_repository=source,
                target_repository=target,
                protocols_migrated=1,
                files_created=[],
                files_deleted=[],
                imports_updated=[],
                conflicts_resolved=[],
                execution_time_minutes=2,
                rollback_available=True,
            )

            assert result.source_repository == source
            assert result.target_repository == target
