"""
Comprehensive unit tests for ModelMigrationPlan.

Tests cover:
- Migration plan initialization
- Conflict detection
- Safety checks for proceeding with migration
- Various migration scenarios
"""

from __future__ import annotations

import pytest

from omnibase_core.models.validation.model_migration_conflict_union import (
    ModelMigrationConflictUnion,
)
from omnibase_core.models.validation.model_migration_plan import ModelMigrationPlan
from omnibase_core.validation.migration_types import TypedDictMigrationStepDict
from omnibase_core.validation.validation_utils import ModelProtocolInfo


class TestModelMigrationPlan:
    """Test ModelMigrationPlan class."""

    def test_migration_plan_initialization(self) -> None:
        """Test basic migration plan initialization."""
        protocols = [
            ModelProtocolInfo(
                name="TestProtocol",
                file_path="/path/to/protocol.py",
                repository="omnibase_core",
                methods=["method1", "method2"],
                signature_hash="abc123",
                line_count=50,
                imports=["typing"],
            ),
        ]

        steps: list[TypedDictMigrationStepDict] = [
            {
                "step_number": 1,
                "action": "create",
                "target_path": "/spi/test_protocol.py",
                "description": "Create protocol file",
            },
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=protocols,
            conflicts_detected=[],
            migration_steps=steps,
            estimated_time_minutes=5,
            recommendations=["Review protocol design"],
        )

        assert plan.success is True
        assert plan.source_repository == "omnibase_core"
        assert plan.target_repository == "omnibase_spi"
        assert len(plan.protocols_to_migrate) == 1
        assert len(plan.conflicts_detected) == 0
        assert len(plan.migration_steps) == 1
        assert plan.estimated_time_minutes == 5
        assert len(plan.recommendations) == 1

    def test_has_conflicts_with_no_conflicts(self) -> None:
        """Test has_conflicts returns False when no conflicts."""
        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=[],
        )

        assert plan.has_conflicts() is False

    def test_has_conflicts_with_conflicts(self) -> None:
        """Test has_conflicts returns True when conflicts exist."""
        from omnibase_core.enums.enum_migration_conflict_type import (
            EnumMigrationConflictType,
        )

        conflicts = [
            ModelMigrationConflictUnion(
                conflict_type=EnumMigrationConflictType.NAME_CONFLICT,
                protocol_name="DuplicateProtocol",
                source_file="/path/to/source.py",
                spi_file="/path/to/spi.py",
                recommendation="Rename one of the protocols or merge if appropriate",
                source_signature="abc123",
                spi_signature="def456",
            ),
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=conflicts,
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=[],
        )

        assert plan.has_conflicts() is True
        assert len(plan.conflicts_detected) == 1

    def test_can_proceed_success_no_conflicts(self) -> None:
        """Test can_proceed returns True when successful and no conflicts."""
        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=[],
        )

        assert plan.can_proceed() is True

    def test_can_proceed_failure(self) -> None:
        """Test can_proceed returns False when plan is not successful."""
        plan = ModelMigrationPlan(
            success=False,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=["Fix errors before proceeding"],
        )

        assert plan.can_proceed() is False

    def test_can_proceed_with_conflicts(self) -> None:
        """Test can_proceed returns False when conflicts exist."""
        from omnibase_core.enums.enum_migration_conflict_type import (
            EnumMigrationConflictType,
        )

        conflicts = [
            ModelMigrationConflictUnion(
                conflict_type=EnumMigrationConflictType.EXACT_DUPLICATE,
                protocol_name="ConflictProtocol",
                source_file="/path/to/source.py",
                spi_file="/path/to/spi.py",
                recommendation="Skip migration - use existing SPI version",
                signature_hash="abc123",
            ),
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=conflicts,
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=[],
        )

        assert plan.can_proceed() is False

    def test_migration_plan_with_multiple_protocols(self) -> None:
        """Test migration plan with multiple protocols."""
        protocols = [
            ModelProtocolInfo(
                name="Protocol1",
                file_path="/path/to/protocol1.py",
                repository="omnibase_core",
                methods=["method1"],
                signature_hash="hash1",
                line_count=30,
                imports=[],
            ),
            ModelProtocolInfo(
                name="Protocol2",
                file_path="/path/to/protocol2.py",
                repository="omnibase_core",
                methods=["method2", "method3"],
                signature_hash="hash2",
                line_count=50,
                imports=["typing"],
            ),
            ModelProtocolInfo(
                name="Protocol3",
                file_path="/path/to/protocol3.py",
                repository="omnibase_core",
                methods=["method4"],
                signature_hash="hash3",
                line_count=40,
                imports=["abc"],
            ),
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=protocols,
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=15,
            recommendations=[],
        )

        assert len(plan.protocols_to_migrate) == 3
        assert plan.estimated_time_minutes == 15

    def test_migration_plan_with_multiple_steps(self) -> None:
        """Test migration plan with multiple migration steps."""
        steps: list[TypedDictMigrationStepDict] = [
            {
                "step_number": 1,
                "action": "create",
                "target_path": "/spi/protocol1.py",
                "description": "Create first protocol",
            },
            {
                "step_number": 2,
                "action": "update",
                "target_path": "/spi/__init__.py",
                "description": "Update __init__.py",
            },
            {
                "step_number": 3,
                "action": "delete",
                "target_path": "/old/protocol1.py",
                "description": "Remove old protocol",
            },
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=steps,
            estimated_time_minutes=10,
            recommendations=[],
        )

        assert len(plan.migration_steps) == 3
        assert plan.migration_steps[0]["step_number"] == 1
        assert plan.migration_steps[1]["action"] == "update"
        assert plan.migration_steps[2]["target_path"] == "/old/protocol1.py"

    def test_migration_plan_with_recommendations(self) -> None:
        """Test migration plan with multiple recommendations."""
        recommendations = [
            "Review protocol design for consistency",
            "Ensure all imports are updated",
            "Run tests after migration",
            "Update documentation",
        ]

        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=5,
            recommendations=recommendations,
        )

        assert len(plan.recommendations) == 4
        assert "Review protocol design" in plan.recommendations[0]

    def test_migration_plan_complex_scenario(self) -> None:
        """Test complex migration scenario with all components."""
        from omnibase_core.enums.enum_migration_conflict_type import (
            EnumMigrationConflictType,
        )

        protocols = [
            ModelProtocolInfo(
                name="AgentProtocol",
                file_path="/core/agent_protocol.py",
                repository="omnibase_core",
                methods=["execute", "validate"],
                signature_hash="agent_hash",
                line_count=100,
                imports=["abc", "typing"],
            ),
        ]

        conflicts = [
            ModelMigrationConflictUnion(
                conflict_type=EnumMigrationConflictType.NAME_CONFLICT,
                protocol_name="AgentProtocol",
                source_file="/core/agent_protocol.py",
                spi_file="/spi/agent_protocol.py",
                recommendation="Rename one of the protocols or merge if appropriate",
                source_signature="old_hash",
                spi_signature="new_hash",
            ),
        ]

        steps: list[TypedDictMigrationStepDict] = [
            {
                "step_number": 1,
                "action": "backup",
                "target_path": "/backup/agent_protocol.py",
                "description": "Backup existing protocol",
            },
            {
                "step_number": 2,
                "action": "create",
                "target_path": "/spi/agent_protocol.py",
                "description": "Create new protocol version",
            },
        ]

        plan = ModelMigrationPlan(
            success=False,  # Not successful due to conflicts
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=protocols,
            conflicts_detected=conflicts,
            migration_steps=steps,
            estimated_time_minutes=20,
            recommendations=["Resolve version conflict before proceeding"],
        )

        # Comprehensive checks
        assert plan.has_conflicts() is True
        assert plan.can_proceed() is False
        assert len(plan.protocols_to_migrate) == 1
        assert len(plan.conflicts_detected) == 1
        assert len(plan.migration_steps) == 2
        assert plan.conflicts_detected[0].protocol_name == "AgentProtocol"
        assert plan.conflicts_detected[0].is_name_conflict() is True

    def test_migration_plan_empty_protocols_list(self) -> None:
        """Test migration plan with no protocols to migrate."""
        plan = ModelMigrationPlan(
            success=True,
            source_repository="omnibase_core",
            target_repository="omnibase_spi",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=0,
            recommendations=["No protocols to migrate"],
        )

        assert len(plan.protocols_to_migrate) == 0
        assert (
            plan.can_proceed() is True
        )  # Can proceed since successful and no conflicts

    def test_migration_plan_dataclass_properties(self) -> None:
        """Test that ModelMigrationPlan is a proper dataclass."""
        plan = ModelMigrationPlan(
            success=True,
            source_repository="test_source",
            target_repository="test_target",
            protocols_to_migrate=[],
            conflicts_detected=[],
            migration_steps=[],
            estimated_time_minutes=5,
            recommendations=[],
        )

        # Test dataclass fields are accessible
        assert hasattr(plan, "success")
        assert hasattr(plan, "source_repository")
        assert hasattr(plan, "target_repository")
        assert hasattr(plan, "protocols_to_migrate")
        assert hasattr(plan, "conflicts_detected")
        assert hasattr(plan, "migration_steps")
        assert hasattr(plan, "estimated_time_minutes")
        assert hasattr(plan, "recommendations")

        # Test dataclass methods
        assert hasattr(plan, "has_conflicts")
        assert hasattr(plan, "can_proceed")
