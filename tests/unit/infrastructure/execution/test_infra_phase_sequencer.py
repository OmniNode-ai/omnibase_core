# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for infra_phase_sequencer.

This module tests the phase sequencer functions for converting execution profiles
and handler mappings into executable plans.

Test Categories:
1. Canonical phase order functions
2. Phase list validation
3. Handler grouping and ordering
4. Execution plan creation
5. Edge cases (empty inputs, invalid phases)
6. Determinism (same input -> same output)
7. Error handling

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.infrastructure.execution.infra_phase_sequencer import (
    create_default_execution_plan,
    create_empty_execution_plan,
    create_execution_plan,
    get_canonical_phase_order,
    get_phases_for_handlers,
    group_handlers_by_phase,
    order_handlers_in_phase,
    validate_phase_list,
    validate_phase_list_strict,
)
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.execution.model_execution_plan import (
    ModelExecutionPlan,
)

# =============================================================================
# Canonical Phase Order Tests
# =============================================================================


@pytest.mark.unit
class TestGetCanonicalPhaseOrder:
    """Tests for get_canonical_phase_order function."""

    def test_returns_all_phases(self) -> None:
        """Test that all six phases are returned."""
        phases = get_canonical_phase_order()
        assert len(phases) == 6

    def test_correct_order(self) -> None:
        """Test that phases are in correct canonical order."""
        phases = get_canonical_phase_order()
        expected = [
            EnumHandlerExecutionPhase.PREFLIGHT,
            EnumHandlerExecutionPhase.BEFORE,
            EnumHandlerExecutionPhase.EXECUTE,
            EnumHandlerExecutionPhase.AFTER,
            EnumHandlerExecutionPhase.EMIT,
            EnumHandlerExecutionPhase.FINALIZE,
        ]
        assert phases == expected

    def test_deterministic(self) -> None:
        """Test that multiple calls return the same result."""
        result1 = get_canonical_phase_order()
        result2 = get_canonical_phase_order()
        result3 = get_canonical_phase_order()
        assert result1 == result2 == result3

    def test_returns_enum_values(self) -> None:
        """Test that all returned values are EnumHandlerExecutionPhase."""
        phases = get_canonical_phase_order()
        for phase in phases:
            assert isinstance(phase, EnumHandlerExecutionPhase)


# =============================================================================
# Phase List Validation Tests
# =============================================================================


@pytest.mark.unit
class TestValidatePhaseList:
    """Tests for validate_phase_list function."""

    def test_empty_list_is_valid(self) -> None:
        """Test that an empty phase list is valid."""
        assert validate_phase_list([]) is True

    def test_default_phases_are_valid(self) -> None:
        """Test that DEFAULT_EXECUTION_PHASES is valid."""
        assert validate_phase_list(list(DEFAULT_EXECUTION_PHASES)) is True

    def test_single_phase_is_valid(self) -> None:
        """Test that a single valid phase is valid."""
        assert validate_phase_list(["preflight"]) is True
        assert validate_phase_list(["execute"]) is True
        assert validate_phase_list(["finalize"]) is True

    def test_contiguous_subsequence_is_valid(self) -> None:
        """Test that contiguous subsequences are valid."""
        assert validate_phase_list(["preflight", "before"]) is True
        assert validate_phase_list(["before", "execute", "after"]) is True
        assert validate_phase_list(["emit", "finalize"]) is True

    def test_non_contiguous_sequence_is_valid(self) -> None:
        """Test that non-contiguous (but ordered) sequences are valid."""
        assert validate_phase_list(["preflight", "execute"]) is True
        assert validate_phase_list(["before", "after", "finalize"]) is True

    def test_wrong_order_is_invalid(self) -> None:
        """Test that wrong ordering is invalid."""
        assert validate_phase_list(["execute", "before"]) is False
        assert validate_phase_list(["after", "preflight"]) is False
        assert validate_phase_list(["finalize", "emit"]) is False

    def test_invalid_phase_name_is_invalid(self) -> None:
        """Test that invalid phase names are rejected."""
        assert validate_phase_list(["invalid"]) is False
        assert validate_phase_list(["preflight", "invalid"]) is False
        assert validate_phase_list(["foo", "bar"]) is False

    def test_duplicate_phase_is_invalid(self) -> None:
        """Test that duplicate phases are invalid."""
        assert validate_phase_list(["execute", "execute"]) is False
        assert validate_phase_list(["preflight", "before", "preflight"]) is False

    def test_case_insensitive(self) -> None:
        """Test that phase names are case-insensitive."""
        assert validate_phase_list(["PREFLIGHT", "BEFORE"]) is True
        assert validate_phase_list(["Execute", "After"]) is True
        assert validate_phase_list(["PrEfLiGhT"]) is True


@pytest.mark.unit
class TestValidatePhaseListStrict:
    """Tests for validate_phase_list_strict function."""

    def test_valid_list_returns_true_and_none(self) -> None:
        """Test that valid lists return (True, None)."""
        is_valid, error = validate_phase_list_strict(list(DEFAULT_EXECUTION_PHASES))
        assert is_valid is True
        assert error is None

    def test_empty_list_is_valid(self) -> None:
        """Test that empty list returns (True, None)."""
        is_valid, error = validate_phase_list_strict([])
        assert is_valid is True
        assert error is None

    def test_invalid_phase_returns_error_message(self) -> None:
        """Test that invalid phase returns descriptive error."""
        is_valid, error = validate_phase_list_strict(["invalid_phase"])
        assert is_valid is False
        assert error is not None
        assert "Invalid phase" in error
        assert "invalid_phase" in error

    def test_wrong_order_returns_error_message(self) -> None:
        """Test that wrong order returns descriptive error."""
        is_valid, error = validate_phase_list_strict(["execute", "before"])
        assert is_valid is False
        assert error is not None
        assert "before" in error
        assert "execute" in error

    def test_duplicate_returns_error_message(self) -> None:
        """Test that duplicate phase returns descriptive error."""
        is_valid, error = validate_phase_list_strict(["execute", "execute"])
        assert is_valid is False
        assert error is not None
        assert "Duplicate" in error


# =============================================================================
# Handler Grouping Tests
# =============================================================================


@pytest.mark.unit
class TestGroupHandlersByPhase:
    """Tests for group_handlers_by_phase function."""

    def test_empty_mapping(self) -> None:
        """Test with empty handler mapping."""
        result = group_handlers_by_phase({})
        assert result == {}

    def test_single_handler(self) -> None:
        """Test with a single handler."""
        mapping = {"handler_a": EnumHandlerExecutionPhase.EXECUTE}
        result = group_handlers_by_phase(mapping)
        assert result == {EnumHandlerExecutionPhase.EXECUTE: ["handler_a"]}

    def test_multiple_handlers_same_phase(self) -> None:
        """Test multiple handlers in the same phase."""
        mapping = {
            "handler_a": EnumHandlerExecutionPhase.EXECUTE,
            "handler_b": EnumHandlerExecutionPhase.EXECUTE,
            "handler_c": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = group_handlers_by_phase(mapping)
        assert EnumHandlerExecutionPhase.EXECUTE in result
        assert sorted(result[EnumHandlerExecutionPhase.EXECUTE]) == [
            "handler_a",
            "handler_b",
            "handler_c",
        ]

    def test_handlers_across_phases(self) -> None:
        """Test handlers distributed across multiple phases."""
        mapping = {
            "validate": EnumHandlerExecutionPhase.PREFLIGHT,
            "setup": EnumHandlerExecutionPhase.BEFORE,
            "process": EnumHandlerExecutionPhase.EXECUTE,
            "cleanup": EnumHandlerExecutionPhase.AFTER,
        }
        result = group_handlers_by_phase(mapping)
        assert len(result) == 4
        assert result[EnumHandlerExecutionPhase.PREFLIGHT] == ["validate"]
        assert result[EnumHandlerExecutionPhase.BEFORE] == ["setup"]
        assert result[EnumHandlerExecutionPhase.EXECUTE] == ["process"]
        assert result[EnumHandlerExecutionPhase.AFTER] == ["cleanup"]

    def test_deterministic(self) -> None:
        """Test that grouping is deterministic."""
        mapping = {
            "h1": EnumHandlerExecutionPhase.EXECUTE,
            "h2": EnumHandlerExecutionPhase.BEFORE,
            "h3": EnumHandlerExecutionPhase.EXECUTE,
        }
        result1 = group_handlers_by_phase(mapping)
        result2 = group_handlers_by_phase(mapping)
        assert result1.keys() == result2.keys()


# =============================================================================
# Handler Ordering Tests
# =============================================================================


@pytest.mark.unit
class TestOrderHandlersInPhase:
    """Tests for order_handlers_in_phase function."""

    def test_empty_list(self) -> None:
        """Test with empty handler list."""
        result = order_handlers_in_phase([])
        assert result == []

    def test_single_handler(self) -> None:
        """Test with single handler."""
        result = order_handlers_in_phase(["handler_a"])
        assert result == ["handler_a"]

    def test_alphabetical_ordering_default(self) -> None:
        """Test that default ordering is alphabetical."""
        handlers = ["z_handler", "a_handler", "m_handler"]
        result = order_handlers_in_phase(handlers)
        assert result == ["a_handler", "m_handler", "z_handler"]

    def test_alphabetical_ordering_with_policy(self) -> None:
        """Test alphabetical ordering with explicit policy."""
        policy = ModelExecutionOrderingPolicy(tie_breakers=["alphabetical"])
        handlers = ["zebra", "alpha", "beta"]
        result = order_handlers_in_phase(handlers, policy)
        assert result == ["alpha", "beta", "zebra"]

    def test_does_not_mutate_input(self) -> None:
        """Test that input list is not mutated."""
        handlers = ["c", "b", "a"]
        original = handlers.copy()
        order_handlers_in_phase(handlers)
        assert handlers == original

    def test_deterministic(self) -> None:
        """Test that ordering is deterministic."""
        handlers = ["z", "m", "a", "n", "b"]
        result1 = order_handlers_in_phase(handlers)
        result2 = order_handlers_in_phase(handlers)
        result3 = order_handlers_in_phase(handlers)
        assert result1 == result2 == result3

    def test_preserves_all_handlers(self) -> None:
        """Test that all handlers are preserved."""
        handlers = ["h1", "h2", "h3", "h4", "h5"]
        result = order_handlers_in_phase(handlers)
        assert set(result) == set(handlers)
        assert len(result) == len(handlers)


# =============================================================================
# Execution Plan Creation Tests
# =============================================================================


@pytest.mark.unit
class TestCreateExecutionPlan:
    """Tests for create_execution_plan function."""

    def test_empty_handler_mapping(self) -> None:
        """Test with empty handler mapping."""
        profile = ModelExecutionProfile()
        result = create_execution_plan(profile, {})

        assert isinstance(result, ModelExecutionPlan)
        assert result.total_handlers() == 0

    def test_single_handler(self) -> None:
        """Test with a single handler."""
        profile = ModelExecutionProfile()
        mapping = {"handler_a": EnumHandlerExecutionPhase.EXECUTE}
        result = create_execution_plan(profile, mapping)

        assert result.total_handlers() == 1
        assert result.has_phase(EnumHandlerExecutionPhase.EXECUTE)
        execute_phase = result.get_phase(EnumHandlerExecutionPhase.EXECUTE)
        assert execute_phase is not None
        assert "handler_a" in execute_phase.handler_ids

    def test_multiple_handlers_multiple_phases(self) -> None:
        """Test with multiple handlers across phases."""
        profile = ModelExecutionProfile()
        mapping = {
            "validate_input": EnumHandlerExecutionPhase.PREFLIGHT,
            "setup_resources": EnumHandlerExecutionPhase.BEFORE,
            "process_data": EnumHandlerExecutionPhase.EXECUTE,
            "transform_output": EnumHandlerExecutionPhase.EXECUTE,
            "cleanup": EnumHandlerExecutionPhase.AFTER,
            "emit_events": EnumHandlerExecutionPhase.EMIT,
        }
        result = create_execution_plan(profile, mapping)

        assert result.total_handlers() == 6
        assert len(result.phases) == 6  # All default phases included

    def test_phases_in_canonical_order(self) -> None:
        """Test that phases appear in canonical order in the plan."""
        profile = ModelExecutionProfile()
        mapping = {
            "h_after": EnumHandlerExecutionPhase.AFTER,
            "h_before": EnumHandlerExecutionPhase.BEFORE,
            "h_execute": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = create_execution_plan(profile, mapping)

        # Get phases with handlers
        non_empty = result.get_non_empty_phases()
        phase_order = [p.phase for p in non_empty]

        expected_order = [
            EnumHandlerExecutionPhase.BEFORE,
            EnumHandlerExecutionPhase.EXECUTE,
            EnumHandlerExecutionPhase.AFTER,
        ]
        assert phase_order == expected_order

    def test_handlers_ordered_within_phase(self) -> None:
        """Test that handlers are ordered within each phase."""
        profile = ModelExecutionProfile()
        mapping = {
            "z_handler": EnumHandlerExecutionPhase.EXECUTE,
            "a_handler": EnumHandlerExecutionPhase.EXECUTE,
            "m_handler": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = create_execution_plan(profile, mapping)

        execute_phase = result.get_phase(EnumHandlerExecutionPhase.EXECUTE)
        assert execute_phase is not None
        assert execute_phase.handler_ids == ["a_handler", "m_handler", "z_handler"]

    def test_custom_ordering_policy(self) -> None:
        """Test with custom ordering policy."""
        profile = ModelExecutionProfile()
        custom_policy = ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["alphabetical"],
            deterministic_seed=True,
        )
        mapping = {
            "b": EnumHandlerExecutionPhase.EXECUTE,
            "a": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = create_execution_plan(profile, mapping, ordering_policy=custom_policy)

        assert result.ordering_policy == "topological_sort"

    def test_source_profile_recorded(self) -> None:
        """Test that source profile information is recorded."""
        profile = ModelExecutionProfile()
        result = create_execution_plan(profile, {})

        assert result.source_profile is not None
        assert "profile(" in result.source_profile

    def test_created_at_set(self) -> None:
        """Test that created_at timestamp is set."""
        profile = ModelExecutionProfile()
        result = create_execution_plan(profile, {})

        assert result.created_at is not None

    def test_deterministic_output(self) -> None:
        """Test that same input produces same output structure."""
        profile = ModelExecutionProfile()
        mapping = {
            "h1": EnumHandlerExecutionPhase.EXECUTE,
            "h2": EnumHandlerExecutionPhase.BEFORE,
            "h3": EnumHandlerExecutionPhase.EXECUTE,
        }

        result1 = create_execution_plan(profile, mapping)
        result2 = create_execution_plan(profile, mapping)

        # Structure should be identical (timestamps will differ)
        assert result1.total_handlers() == result2.total_handlers()
        assert len(result1.phases) == len(result2.phases)
        for p1, p2 in zip(result1.phases, result2.phases, strict=False):
            assert p1.phase == p2.phase
            assert p1.handler_ids == p2.handler_ids

    def test_invalid_phase_list_raises_error(self) -> None:
        """Test that invalid phase list raises ModelOnexError."""
        # Create profile with invalid phase order
        profile = ModelExecutionProfile(phases=("execute", "before"))  # Wrong order

        with pytest.raises(ModelOnexError) as exc_info:
            create_execution_plan(profile, {})

        assert "Invalid execution profile phase list" in str(exc_info.value.message)


@pytest.mark.unit
class TestCreateExecutionPlanEdgeCases:
    """Edge case tests for create_execution_plan."""

    def test_subset_of_phases(self) -> None:
        """Test with profile containing only subset of phases."""
        profile = ModelExecutionProfile(phases=("preflight", "execute", "finalize"))
        mapping = {
            "h1": EnumHandlerExecutionPhase.PREFLIGHT,
            "h2": EnumHandlerExecutionPhase.EXECUTE,
            "h3": EnumHandlerExecutionPhase.FINALIZE,
        }
        result = create_execution_plan(profile, mapping)

        # Should only have 3 phases
        assert len(result.phases) == 3
        phase_enums = [p.phase for p in result.phases]
        assert EnumHandlerExecutionPhase.BEFORE not in phase_enums
        assert EnumHandlerExecutionPhase.AFTER not in phase_enums
        assert EnumHandlerExecutionPhase.EMIT not in phase_enums

    def test_handlers_for_missing_phase(self) -> None:
        """Test that handlers for missing phases are ignored."""
        # Profile only has execute phase
        profile = ModelExecutionProfile(phases=("execute",))
        # But we map handlers to before and after too
        mapping = {
            "h_before": EnumHandlerExecutionPhase.BEFORE,
            "h_execute": EnumHandlerExecutionPhase.EXECUTE,
            "h_after": EnumHandlerExecutionPhase.AFTER,
        }
        result = create_execution_plan(profile, mapping)

        # Only execute phase should be in plan
        assert len(result.phases) == 1
        assert result.phases[0].phase == EnumHandlerExecutionPhase.EXECUTE
        assert result.total_handlers() == 1

    def test_all_phases_empty(self) -> None:
        """Test with all phases having no handlers."""
        profile = ModelExecutionProfile()
        result = create_execution_plan(profile, {})

        # All phases present but empty
        assert len(result.phases) == 6
        for phase_step in result.phases:
            assert phase_step.is_empty()


# =============================================================================
# Empty and Default Plan Tests
# =============================================================================


@pytest.mark.unit
class TestCreateEmptyExecutionPlan:
    """Tests for create_empty_execution_plan function."""

    def test_returns_empty_plan(self) -> None:
        """Test that returned plan is empty."""
        plan = create_empty_execution_plan()
        assert plan.is_empty()
        assert plan.total_handlers() == 0
        assert len(plan.phases) == 0

    def test_with_source_profile(self) -> None:
        """Test with custom source profile identifier."""
        plan = create_empty_execution_plan(source_profile="test_profile")
        assert plan.source_profile == "test_profile"

    def test_default_source_profile(self) -> None:
        """Test default source profile is 'empty'."""
        plan = create_empty_execution_plan()
        assert plan.source_profile == "empty"

    def test_ordering_policy_is_none(self) -> None:
        """Test that ordering policy is 'none'."""
        plan = create_empty_execution_plan()
        assert plan.ordering_policy == "none"


@pytest.mark.unit
class TestCreateDefaultExecutionPlan:
    """Tests for create_default_execution_plan function."""

    def test_uses_default_phases(self) -> None:
        """Test that default phases are used."""
        mapping = {"h1": EnumHandlerExecutionPhase.EXECUTE}
        plan = create_default_execution_plan(mapping)

        # Should have all default phases
        assert len(plan.phases) == len(DEFAULT_EXECUTION_PHASES)

    def test_empty_mapping(self) -> None:
        """Test with empty handler mapping."""
        plan = create_default_execution_plan({})
        assert plan.total_handlers() == 0

    def test_handlers_correctly_assigned(self) -> None:
        """Test that handlers are correctly assigned to phases."""
        mapping = {
            "h1": EnumHandlerExecutionPhase.PREFLIGHT,
            "h2": EnumHandlerExecutionPhase.EXECUTE,
        }
        plan = create_default_execution_plan(mapping)

        preflight = plan.get_phase(EnumHandlerExecutionPhase.PREFLIGHT)
        execute = plan.get_phase(EnumHandlerExecutionPhase.EXECUTE)

        assert preflight is not None
        assert "h1" in preflight.handler_ids
        assert execute is not None
        assert "h2" in execute.handler_ids


# =============================================================================
# Get Phases for Handlers Tests
# =============================================================================


@pytest.mark.unit
class TestGetPhasesForHandlers:
    """Tests for get_phases_for_handlers function."""

    def test_empty_mapping(self) -> None:
        """Test with empty mapping."""
        result = get_phases_for_handlers({})
        assert result == []

    def test_single_phase(self) -> None:
        """Test with handlers in single phase."""
        mapping = {
            "h1": EnumHandlerExecutionPhase.EXECUTE,
            "h2": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = get_phases_for_handlers(mapping)
        assert result == [EnumHandlerExecutionPhase.EXECUTE]

    def test_multiple_phases_in_order(self) -> None:
        """Test that phases are returned in canonical order."""
        mapping = {
            "h_after": EnumHandlerExecutionPhase.AFTER,
            "h_before": EnumHandlerExecutionPhase.BEFORE,
            "h_execute": EnumHandlerExecutionPhase.EXECUTE,
        }
        result = get_phases_for_handlers(mapping)
        expected = [
            EnumHandlerExecutionPhase.BEFORE,
            EnumHandlerExecutionPhase.EXECUTE,
            EnumHandlerExecutionPhase.AFTER,
        ]
        assert result == expected

    def test_all_phases(self) -> None:
        """Test with handlers in all phases."""
        mapping = {
            "h1": EnumHandlerExecutionPhase.PREFLIGHT,
            "h2": EnumHandlerExecutionPhase.BEFORE,
            "h3": EnumHandlerExecutionPhase.EXECUTE,
            "h4": EnumHandlerExecutionPhase.AFTER,
            "h5": EnumHandlerExecutionPhase.EMIT,
            "h6": EnumHandlerExecutionPhase.FINALIZE,
        }
        result = get_phases_for_handlers(mapping)
        assert result == get_canonical_phase_order()


# =============================================================================
# Determinism Tests
# =============================================================================


@pytest.mark.unit
class TestDeterminism:
    """Tests to verify deterministic behavior of pure functions."""

    def test_validate_phase_list_deterministic(self) -> None:
        """Test that validate_phase_list is deterministic."""
        phases = ["preflight", "execute", "finalize"]
        results = [validate_phase_list(phases) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_group_handlers_deterministic(self) -> None:
        """Test that group_handlers_by_phase is deterministic.

        Verifies both:
        1. The phase keys are consistent across invocations
        2. The handler lists within each phase are identical
        """
        mapping = {
            "h1": EnumHandlerExecutionPhase.EXECUTE,
            "h2": EnumHandlerExecutionPhase.BEFORE,
            "h3": EnumHandlerExecutionPhase.EXECUTE,
        }
        results = [group_handlers_by_phase(mapping) for _ in range(10)]
        first_result = results[0]

        for r in results:
            # Verify keys match
            assert r.keys() == first_result.keys()
            # Verify handler lists within each phase match
            for phase_key in first_result:
                assert r[phase_key] == first_result[phase_key], (
                    f"Handler list mismatch for phase {phase_key}: "
                    f"expected {first_result[phase_key]}, got {r[phase_key]}"
                )

    def test_order_handlers_deterministic(self) -> None:
        """Test that order_handlers_in_phase is deterministic."""
        handlers = ["z", "a", "m", "b", "n"]
        results = [order_handlers_in_phase(handlers) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_execution_plan_structure_deterministic(self) -> None:
        """Test that create_execution_plan structure is deterministic."""
        profile = ModelExecutionProfile()
        mapping = {
            "handler_c": EnumHandlerExecutionPhase.EXECUTE,
            "handler_a": EnumHandlerExecutionPhase.EXECUTE,
            "handler_b": EnumHandlerExecutionPhase.BEFORE,
        }

        results = [create_execution_plan(profile, mapping) for _ in range(5)]

        # All should have same structure
        for result in results:
            assert result.total_handlers() == 3
            execute = result.get_phase(EnumHandlerExecutionPhase.EXECUTE)
            assert execute is not None
            assert execute.handler_ids == ["handler_a", "handler_c"]


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling in phase sequencer."""

    def test_invalid_phase_in_profile(self) -> None:
        """Test that invalid phase in profile raises error."""
        profile = ModelExecutionProfile(phases=("invalid_phase",))

        with pytest.raises(ModelOnexError) as exc_info:
            create_execution_plan(profile, {})

        assert "Invalid phase" in str(exc_info.value.message)

    def test_error_contains_context(self) -> None:
        """Test that error contains useful context."""
        profile = ModelExecutionProfile(phases=("execute", "before"))  # Wrong order

        with pytest.raises(ModelOnexError) as exc_info:
            create_execution_plan(profile, {})

        error = exc_info.value
        assert error.context is not None
        # Context may be nested under additional_context
        if "additional_context" in error.context:
            inner_context = error.context["additional_context"].get("context", {})
            assert "phases" in inner_context
        else:
            assert "phases" in error.context

    def test_duplicate_phase_raises_error(self) -> None:
        """Test that duplicate phase raises error during model creation.

        ModelExecutionProfile has a Pydantic validator that prevents duplicate
        phases at model instantiation time, raising ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionProfile(phases=("execute", "execute"))

        # Verify the error message mentions uniqueness
        error_str = str(exc_info.value)
        assert "unique" in error_str.lower()
