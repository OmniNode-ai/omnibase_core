#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
ModelExecutionPlan Comprehensive Unit Tests.

This module provides comprehensive test coverage for ModelExecutionPlan,
the resolved phase ordering model for the Runtime Execution Sequencing system.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive validation scenarios
- Helper method testing

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.execution.model_execution_plan import (
    ModelExecutionPlan,
)
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep


@pytest.mark.unit
class TestModelExecutionPlan:
    """Comprehensive tests for ModelExecutionPlan with helper method coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.preflight_step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.PREFLIGHT,
            handler_ids=["validate_input", "check_permissions"],
        )
        self.execute_step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["process_data", "transform_output", "save_results"],
        )
        self.emit_step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EMIT,
            handler_ids=["emit_completion_event"],
        )
        self.empty_step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.AFTER,
            handler_ids=[],
        )

    # =================== VALID CONSTRUCTION TESTS ===================

    def test_valid_construction_minimal_fields(self) -> None:
        """Test valid construction with minimal fields (defaults)."""
        plan = ModelExecutionPlan()

        assert plan.phases == []
        assert plan.source_profile is None
        assert plan.ordering_policy is None
        assert plan.created_at is None
        assert plan.metadata is None

    def test_valid_construction_with_phases(self) -> None:
        """Test valid construction with phases."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        assert len(plan.phases) == 3
        assert plan.phases[0] == self.preflight_step
        assert plan.phases[1] == self.execute_step
        assert plan.phases[2] == self.emit_step

    def test_valid_construction_all_fields(self) -> None:
        """Test valid construction with all fields populated."""
        now = datetime.now(tz=UTC)
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step],
            source_profile="orchestrator_safe",
            ordering_policy="topological_sort with priority tie-breakers",
            created_at=now,
            metadata={"version": "1.0", "author": "test"},
        )

        assert len(plan.phases) == 2
        assert plan.source_profile == "orchestrator_safe"
        assert plan.ordering_policy == "topological_sort with priority tie-breakers"
        assert plan.created_at == now
        assert plan.metadata == {"version": "1.0", "author": "test"}

    # =================== GET_PHASE HELPER TESTS ===================

    def test_get_phase_returns_matching_phase(self) -> None:
        """Test get_phase returns the correct phase step."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = plan.get_phase(EnumHandlerExecutionPhase.EXECUTE)

        assert result is not None
        assert result == self.execute_step
        assert result.phase == EnumHandlerExecutionPhase.EXECUTE

    def test_get_phase_returns_first_phase(self) -> None:
        """Test get_phase returns the first phase."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = plan.get_phase(EnumHandlerExecutionPhase.PREFLIGHT)

        assert result is not None
        assert result == self.preflight_step

    def test_get_phase_returns_last_phase(self) -> None:
        """Test get_phase returns the last phase."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = plan.get_phase(EnumHandlerExecutionPhase.EMIT)

        assert result is not None
        assert result == self.emit_step

    def test_get_phase_returns_none_for_missing_phase(self) -> None:
        """Test get_phase returns None when phase not found."""
        plan = ModelExecutionPlan(phases=[self.preflight_step, self.execute_step])

        result = plan.get_phase(EnumHandlerExecutionPhase.FINALIZE)

        assert result is None

    def test_get_phase_returns_none_for_empty_plan(self) -> None:
        """Test get_phase returns None for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        result = plan.get_phase(EnumHandlerExecutionPhase.EXECUTE)

        assert result is None

    # =================== GET_ALL_HANDLER_IDS HELPER TESTS ===================

    def test_get_all_handler_ids_returns_all_handlers(self) -> None:
        """Test get_all_handler_ids returns all handlers in order."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = plan.get_all_handler_ids()

        assert result == [
            "validate_input",
            "check_permissions",
            "process_data",
            "transform_output",
            "save_results",
            "emit_completion_event",
        ]

    def test_get_all_handler_ids_preserves_phase_order(self) -> None:
        """Test get_all_handler_ids preserves the order of phases."""
        # Reverse the order
        plan = ModelExecutionPlan(
            phases=[self.emit_step, self.execute_step, self.preflight_step]
        )

        result = plan.get_all_handler_ids()

        # Handlers from emit_step come first now
        assert result[0] == "emit_completion_event"
        assert result[1] == "process_data"
        assert result[-1] == "check_permissions"

    def test_get_all_handler_ids_returns_empty_for_empty_plan(self) -> None:
        """Test get_all_handler_ids returns empty list for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        result = plan.get_all_handler_ids()

        assert result == []

    def test_get_all_handler_ids_skips_empty_phases(self) -> None:
        """Test get_all_handler_ids handles phases with no handlers."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.empty_step, self.execute_step]
        )

        result = plan.get_all_handler_ids()

        # Should only have handlers from preflight and execute
        assert result == [
            "validate_input",
            "check_permissions",
            "process_data",
            "transform_output",
            "save_results",
        ]

    # =================== TOTAL_HANDLERS HELPER TESTS ===================

    def test_total_handlers_returns_correct_count(self) -> None:
        """Test total_handlers returns the correct count."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = plan.total_handlers()

        assert result == 6  # 2 + 3 + 1

    def test_total_handlers_returns_zero_for_empty_plan(self) -> None:
        """Test total_handlers returns 0 for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        result = plan.total_handlers()

        assert result == 0

    def test_total_handlers_handles_empty_phases(self) -> None:
        """Test total_handlers counts correctly with empty phases."""
        plan = ModelExecutionPlan(phases=[self.preflight_step, self.empty_step])

        result = plan.total_handlers()

        assert result == 2  # Only from preflight_step

    def test_total_handlers_single_handler(self) -> None:
        """Test total_handlers with single handler."""
        plan = ModelExecutionPlan(phases=[self.emit_step])

        result = plan.total_handlers()

        assert result == 1

    # =================== IS_EMPTY HELPER TESTS ===================

    def test_is_empty_returns_true_for_no_phases(self) -> None:
        """Test is_empty returns True when phases list is empty."""
        plan = ModelExecutionPlan(phases=[])

        assert plan.is_empty() is True

    def test_is_empty_returns_true_for_all_empty_phases(self) -> None:
        """Test is_empty returns True when all phases have no handlers."""
        empty_phase_1 = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.PREFLIGHT,
            handler_ids=[],
        )
        empty_phase_2 = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=[],
        )
        plan = ModelExecutionPlan(phases=[empty_phase_1, empty_phase_2])

        assert plan.is_empty() is True

    def test_is_empty_returns_false_for_non_empty_plan(self) -> None:
        """Test is_empty returns False when handlers exist."""
        plan = ModelExecutionPlan(phases=[self.execute_step])

        assert plan.is_empty() is False

    def test_is_empty_returns_false_for_mixed_phases(self) -> None:
        """Test is_empty returns False when some phases have handlers."""
        plan = ModelExecutionPlan(phases=[self.empty_step, self.execute_step])

        assert plan.is_empty() is False

    # =================== HAS_PHASE HELPER TESTS ===================

    def test_has_phase_returns_true_when_present(self) -> None:
        """Test has_phase returns True when phase exists."""
        plan = ModelExecutionPlan(phases=[self.preflight_step, self.execute_step])

        assert plan.has_phase(EnumHandlerExecutionPhase.EXECUTE) is True
        assert plan.has_phase(EnumHandlerExecutionPhase.PREFLIGHT) is True

    def test_has_phase_returns_false_when_missing(self) -> None:
        """Test has_phase returns False when phase doesn't exist."""
        plan = ModelExecutionPlan(phases=[self.preflight_step])

        assert plan.has_phase(EnumHandlerExecutionPhase.EXECUTE) is False
        assert plan.has_phase(EnumHandlerExecutionPhase.FINALIZE) is False

    def test_has_phase_returns_false_for_empty_plan(self) -> None:
        """Test has_phase returns False for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        assert plan.has_phase(EnumHandlerExecutionPhase.EXECUTE) is False

    # =================== GET_PHASE_COUNT HELPER TESTS ===================

    def test_get_phase_count_returns_correct_count(self) -> None:
        """Test get_phase_count returns the number of phase steps."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        assert plan.get_phase_count() == 3

    def test_get_phase_count_returns_zero_for_empty_plan(self) -> None:
        """Test get_phase_count returns 0 for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        assert plan.get_phase_count() == 0

    def test_get_phase_count_includes_empty_phases(self) -> None:
        """Test get_phase_count includes phases even if they have no handlers."""
        plan = ModelExecutionPlan(phases=[self.preflight_step, self.empty_step])

        assert plan.get_phase_count() == 2

    # =================== GET_NON_EMPTY_PHASES HELPER TESTS ===================

    def test_get_non_empty_phases_returns_phases_with_handlers(self) -> None:
        """Test get_non_empty_phases returns only phases with handlers."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.empty_step, self.execute_step]
        )

        result = plan.get_non_empty_phases()

        assert len(result) == 2
        assert self.preflight_step in result
        assert self.execute_step in result
        assert self.empty_step not in result

    def test_get_non_empty_phases_returns_empty_for_all_empty_phases(self) -> None:
        """Test get_non_empty_phases returns empty list when all phases are empty."""
        empty_phase_1 = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.PREFLIGHT,
            handler_ids=[],
        )
        empty_phase_2 = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=[],
        )
        plan = ModelExecutionPlan(phases=[empty_phase_1, empty_phase_2])

        result = plan.get_non_empty_phases()

        assert result == []

    def test_get_non_empty_phases_returns_empty_for_empty_plan(self) -> None:
        """Test get_non_empty_phases returns empty list for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        result = plan.get_non_empty_phases()

        assert result == []

    # =================== SERIALIZATION TESTS ===================

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump returns proper dictionary."""
        now = datetime.now(tz=UTC)
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step],
            source_profile="test_profile",
            ordering_policy="topological_sort",
            created_at=now,
            metadata={"key": "value"},
        )

        result = plan.model_dump()

        assert isinstance(result, dict)
        assert len(result["phases"]) == 2
        assert result["source_profile"] == "test_profile"
        assert result["ordering_policy"] == "topological_sort"
        assert result["created_at"] == now
        assert result["metadata"] == {"key": "value"}

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json returns JSON string."""
        plan = ModelExecutionPlan(
            phases=[self.execute_step],
            source_profile="test_profile",
        )

        result = plan.model_dump_json()

        assert isinstance(result, str)
        assert "test_profile" in result
        assert "execute" in result

    def test_model_validate_from_dict(self) -> None:
        """Test model creation from dictionary."""
        data = {
            "phases": [
                {
                    "phase": "execute",
                    "handler_ids": ["handler_a", "handler_b"],
                }
            ],
            "source_profile": "from_dict_profile",
            "ordering_policy": "manual",
        }

        plan = ModelExecutionPlan.model_validate(data)

        assert len(plan.phases) == 1
        assert plan.phases[0].phase == EnumHandlerExecutionPhase.EXECUTE
        assert plan.source_profile == "from_dict_profile"

    def test_model_roundtrip_serialization(self) -> None:
        """Test model can be serialized and deserialized."""
        now = datetime.now(tz=UTC)
        original = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step],
            source_profile="roundtrip_profile",
            ordering_policy="topological_sort",
            created_at=now,
            metadata={"test": "data"},
        )

        serialized = original.model_dump()
        restored = ModelExecutionPlan.model_validate(serialized)

        assert restored.source_profile == original.source_profile
        assert restored.ordering_policy == original.ordering_policy
        assert restored.created_at == original.created_at
        assert restored.metadata == original.metadata
        assert len(restored.phases) == len(original.phases)

    # =================== STRING REPRESENTATION TESTS ===================

    def test_str_representation(self) -> None:
        """Test __str__ returns human-readable format."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step, self.execute_step, self.emit_step]
        )

        result = str(plan)

        assert "ExecutionPlan" in result
        assert "preflight" in result
        assert "execute" in result
        assert "emit" in result

    def test_str_representation_empty_plan(self) -> None:
        """Test __str__ for empty plan."""
        plan = ModelExecutionPlan(phases=[])

        result = str(plan)

        assert "(empty)" in result

    def test_repr_representation(self) -> None:
        """Test __repr__ returns detailed format."""
        plan = ModelExecutionPlan(
            phases=[self.preflight_step],
            source_profile="test_profile",
        )

        result = repr(plan)

        assert "ModelExecutionPlan" in result
        assert "phases=" in result
        assert "source_profile=" in result
        assert "test_profile" in result

    # =================== IMMUTABILITY TESTS ===================

    def test_frozen_model_rejects_assignment(self) -> None:
        """Test that frozen model rejects field assignment."""
        plan = ModelExecutionPlan(
            phases=[self.execute_step],
            source_profile="original",
        )

        with pytest.raises(Exception):  # Pydantic ValidationError for frozen model
            plan.source_profile = "modified"  # type: ignore[misc]

    def test_frozen_model_phases_list_is_immutable(self) -> None:
        """Test that phases list cannot be modified in place."""
        plan = ModelExecutionPlan(phases=[self.execute_step])

        # The list itself is a copy, but assignment to field is blocked
        with pytest.raises(Exception):
            plan.phases = []  # type: ignore[misc]

    # =================== EDGE CASE TESTS ===================

    def test_duplicate_phases_allowed(self) -> None:
        """Test that duplicate phases are allowed in ModelExecutionPlan.

        Duplicate phases are intentionally permitted for valid use cases:
        1. Multiple execution rounds (e.g., retry with different parameters)
        2. Composite workflows that merge multiple execution plans
        3. Staged processing where same phase type runs at different points

        Note: The get_phase() method returns the FIRST matching phase when
        duplicates exist. Use direct iteration over plan.phases if you need
        to access all instances of a duplicate phase.

        Behavior summary:
        - get_phase_count(): Counts ALL phases including duplicates
        - total_handlers(): Sums handlers from ALL phases including duplicates
        - get_phase(phase_type): Returns FIRST matching phase only
        - has_phase(phase_type): Returns True if ANY instance exists
        """
        # Same phase can appear multiple times (e.g., multiple EXECUTE phases)
        plan = ModelExecutionPlan(phases=[self.execute_step, self.execute_step])

        assert plan.get_phase_count() == 2
        assert plan.total_handlers() == 6  # 3 + 3

        # Verify get_phase returns the first occurrence
        first_phase = plan.get_phase(EnumHandlerExecutionPhase.EXECUTE)
        assert first_phase is not None
        assert first_phase is plan.phases[0]

    def test_metadata_accepts_basic_types(self) -> None:
        """Test that metadata accepts basic typed values only."""
        basic_metadata = {
            "string_val": "value",
            "number": 42,
            "float_val": 3.14,
            "boolean": True,
            "null_val": None,
        }
        plan = ModelExecutionPlan(phases=[], metadata=basic_metadata)

        assert plan.metadata == basic_metadata
        assert plan.metadata["string_val"] == "value"
        assert plan.metadata["number"] == 42

    def test_metadata_rejects_complex_types(self) -> None:
        """Test that metadata rejects nested dicts and lists (dict[str, Any] anti-pattern)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelExecutionPlan(
                phases=[],
                metadata={"nested": {"key": "value"}},  # type: ignore[dict-item]
            )

        with pytest.raises(ValidationError):
            ModelExecutionPlan(
                phases=[],
                metadata={"array": ["a", "b", "c"]},  # type: ignore[dict-item]
            )
