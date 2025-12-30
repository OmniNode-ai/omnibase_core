# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for execution module exports.

This module verifies that all public APIs are correctly exported from both
the execution submodule and the parent infrastructure module.

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

import pytest


@pytest.mark.unit
class TestExecutionModuleExports:
    """Tests for imports from omnibase_core.infrastructure.execution."""

    def test_import_model_phase_step(self) -> None:
        """Test importing ModelPhaseStep from execution module."""
        from omnibase_core.infrastructure.execution import ModelPhaseStep

        assert ModelPhaseStep is not None

    def test_import_model_execution_plan(self) -> None:
        """Test importing ModelExecutionPlan from execution module."""
        from omnibase_core.infrastructure.execution import ModelExecutionPlan

        assert ModelExecutionPlan is not None

    def test_import_create_execution_plan(self) -> None:
        """Test importing create_execution_plan from execution module."""
        from omnibase_core.infrastructure.execution import create_execution_plan

        assert callable(create_execution_plan)

    def test_import_create_empty_execution_plan(self) -> None:
        """Test importing create_empty_execution_plan from execution module."""
        from omnibase_core.infrastructure.execution import create_empty_execution_plan

        assert callable(create_empty_execution_plan)

    def test_import_create_default_execution_plan(self) -> None:
        """Test importing create_default_execution_plan from execution module."""
        from omnibase_core.infrastructure.execution import create_default_execution_plan

        assert callable(create_default_execution_plan)

    def test_import_get_canonical_phase_order(self) -> None:
        """Test importing get_canonical_phase_order from execution module."""
        from omnibase_core.infrastructure.execution import get_canonical_phase_order

        assert callable(get_canonical_phase_order)

    def test_import_validate_phase_list(self) -> None:
        """Test importing validate_phase_list from execution module."""
        from omnibase_core.infrastructure.execution import validate_phase_list

        assert callable(validate_phase_list)

    def test_import_validate_phase_list_strict(self) -> None:
        """Test importing validate_phase_list_strict from execution module."""
        from omnibase_core.infrastructure.execution import validate_phase_list_strict

        assert callable(validate_phase_list_strict)

    def test_import_group_handlers_by_phase(self) -> None:
        """Test importing group_handlers_by_phase from execution module."""
        from omnibase_core.infrastructure.execution import group_handlers_by_phase

        assert callable(group_handlers_by_phase)

    def test_import_order_handlers_in_phase(self) -> None:
        """Test importing order_handlers_in_phase from execution module."""
        from omnibase_core.infrastructure.execution import order_handlers_in_phase

        assert callable(order_handlers_in_phase)

    def test_import_get_phases_for_handlers(self) -> None:
        """Test importing get_phases_for_handlers from execution module."""
        from omnibase_core.infrastructure.execution import get_phases_for_handlers

        assert callable(get_phases_for_handlers)

    def test_all_exports_are_accessible(self) -> None:
        """Test that all items in __all__ are accessible."""
        from omnibase_core.infrastructure import execution

        expected_exports = [
            "ModelPhaseStep",
            "ModelExecutionPlan",
            "create_execution_plan",
            "create_empty_execution_plan",
            "create_default_execution_plan",
            "validate_phase_list",
            "validate_phase_list_strict",
            "get_canonical_phase_order",
            "group_handlers_by_phase",
            "order_handlers_in_phase",
            "get_phases_for_handlers",
        ]

        for export_name in expected_exports:
            assert hasattr(execution, export_name), f"Missing export: {export_name}"

    def test_dunder_all_is_defined(self) -> None:
        """Test that __all__ is defined in the module."""
        from omnibase_core.infrastructure import execution

        assert hasattr(execution, "__all__")
        assert isinstance(execution.__all__, list)
        assert len(execution.__all__) > 0


@pytest.mark.unit
class TestInfrastructureModuleExports:
    """Tests for imports from omnibase_core.infrastructure."""

    def test_import_model_phase_step_from_infrastructure(self) -> None:
        """Test importing ModelPhaseStep from infrastructure module."""
        from omnibase_core.infrastructure import ModelPhaseStep

        assert ModelPhaseStep is not None

    def test_import_model_execution_plan_from_infrastructure(self) -> None:
        """Test importing ModelExecutionPlan from infrastructure module."""
        from omnibase_core.infrastructure import ModelExecutionPlan

        assert ModelExecutionPlan is not None

    def test_import_create_execution_plan_from_infrastructure(self) -> None:
        """Test importing create_execution_plan from infrastructure module."""
        from omnibase_core.infrastructure import create_execution_plan

        assert callable(create_execution_plan)

    def test_infrastructure_all_includes_execution_types(self) -> None:
        """Test that infrastructure __all__ includes execution types."""
        from omnibase_core import infrastructure

        assert "ModelPhaseStep" in infrastructure.__all__
        assert "ModelExecutionPlan" in infrastructure.__all__
        assert "create_execution_plan" in infrastructure.__all__


@pytest.mark.unit
class TestFunctionalExports:
    """Functional tests verifying exported items work correctly."""

    def test_create_empty_plan_works(self) -> None:
        """Test that create_empty_execution_plan can be called."""
        from omnibase_core.infrastructure.execution import create_empty_execution_plan

        plan = create_empty_execution_plan()
        assert plan.is_empty()
        assert plan.total_handlers() == 0

    def test_model_phase_step_instantiation(self) -> None:
        """Test that ModelPhaseStep can be instantiated."""
        from omnibase_core.enums import EnumHandlerExecutionPhase
        from omnibase_core.infrastructure.execution import ModelPhaseStep

        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler1", "handler2"],
        )
        assert step.phase == EnumHandlerExecutionPhase.EXECUTE
        assert step.handler_count() == 2

    def test_model_execution_plan_instantiation(self) -> None:
        """Test that ModelExecutionPlan can be instantiated."""
        from omnibase_core.enums import EnumHandlerExecutionPhase
        from omnibase_core.infrastructure.execution import (
            ModelExecutionPlan,
            ModelPhaseStep,
        )

        plan = ModelExecutionPlan(
            phases=[
                ModelPhaseStep(
                    phase=EnumHandlerExecutionPhase.EXECUTE,
                    handler_ids=["handler1"],
                )
            ],
            source_profile="test",
        )
        assert plan.total_handlers() == 1
        assert not plan.is_empty()

    def test_get_canonical_phase_order_returns_list(self) -> None:
        """Test that get_canonical_phase_order returns a list of phases."""
        from omnibase_core.enums import EnumHandlerExecutionPhase
        from omnibase_core.infrastructure.execution import get_canonical_phase_order

        phases = get_canonical_phase_order()
        assert isinstance(phases, list)
        assert len(phases) > 0
        assert all(isinstance(p, EnumHandlerExecutionPhase) for p in phases)

    def test_validate_phase_list_validates(self) -> None:
        """Test that validate_phase_list works correctly."""
        from omnibase_core.infrastructure.execution import validate_phase_list

        # Valid phase list
        assert validate_phase_list(["preflight", "execute"]) is True

        # Invalid order
        assert validate_phase_list(["execute", "preflight"]) is False

        # Empty is valid
        assert validate_phase_list([]) is True

    def test_create_execution_plan_integration(self) -> None:
        """Test full create_execution_plan integration."""
        from omnibase_core.enums import EnumHandlerExecutionPhase
        from omnibase_core.infrastructure.execution import create_execution_plan
        from omnibase_core.models.contracts import ModelExecutionProfile

        profile = ModelExecutionProfile()
        mapping = {
            "validate_handler": EnumHandlerExecutionPhase.PREFLIGHT,
            "process_handler": EnumHandlerExecutionPhase.EXECUTE,
            "emit_handler": EnumHandlerExecutionPhase.EMIT,
        }

        plan = create_execution_plan(profile, mapping)

        assert plan.total_handlers() == 3
        assert not plan.is_empty()
        assert plan.has_phase(EnumHandlerExecutionPhase.PREFLIGHT)
        assert plan.has_phase(EnumHandlerExecutionPhase.EXECUTE)
        assert plan.has_phase(EnumHandlerExecutionPhase.EMIT)
