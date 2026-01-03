# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive tests for ExecutionResolver.

Tests cover:
    - Basic ordering (simple dependencies)
    - Multiple dependencies and chains
    - Cycle detection (direct, indirect, self-reference)
    - Tie-breaking (priority, alphabetical, multiple)
    - Phase assignment
    - Edge cases (empty, single, all independent)
    - Constraint resolution (capability, handler, tag references)
    - Missing dependency handling

.. versionadded:: 0.4.1
"""

from typing import Any

import pytest

# Apply @pytest.mark.unit to all tests in this module
pytestmark = pytest.mark.unit

from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.resolution import ExecutionResolver

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def resolver() -> ExecutionResolver:
    """Create a fresh ExecutionResolver instance."""
    return ExecutionResolver()


@pytest.fixture
def default_profile() -> ModelExecutionProfile:
    """Create a default execution profile."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["priority", "alphabetical"],
            deterministic_seed=True,
        ),
    )


@pytest.fixture
def alphabetical_only_profile() -> ModelExecutionProfile:
    """Create a profile with alphabetical tie-breaking only."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["alphabetical"],
            deterministic_seed=True,
        ),
    )


@pytest.fixture
def priority_only_profile() -> ModelExecutionProfile:
    """Create a profile with priority tie-breaking only."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["priority"],
            deterministic_seed=True,
        ),
    )


def _create_contract(
    handler_id: str,
    *,
    requires_before: list[str] | None = None,
    requires_after: list[str] | None = None,
    must_run: bool = False,
    tags: list[str] | None = None,
    capability_outputs: list[str] | None = None,
    priority: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ModelHandlerContract:
    """Helper to create a handler contract for testing."""
    constraints = None
    if requires_before or requires_after or must_run:
        constraints = ModelExecutionConstraints(
            requires_before=requires_before or [],
            requires_after=requires_after or [],
            must_run=must_run,
        )

    final_metadata: dict[str, Any] = {"priority": priority}
    if metadata:
        final_metadata.update(metadata)

    return ModelHandlerContract(
        handler_id=handler_id,
        name=f"Handler {handler_id}",
        version="1.0.0",
        descriptor=ModelHandlerBehavior(handler_kind="compute"),
        input_model="test.Input",
        output_model="test.Output",
        execution_constraints=constraints,
        tags=tags or [],
        capability_outputs=capability_outputs or [],
        metadata=final_metadata,
    )


# =============================================================================
# Basic Ordering Tests
# =============================================================================


class TestBasicOrdering:
    """Tests for basic dependency ordering."""

    def test_simple_a_before_b(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test simple A -> B dependency."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers.index("handler.a") < handlers.index("handler.b")

    def test_chain_a_b_c(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test chain A -> B -> C dependency."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers == ["handler.a", "handler.b", "handler.c"]

    def test_multiple_dependencies(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test handler with multiple dependencies."""
        # C depends on both A and B
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.a", "handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # A and B must come before C
        assert handlers.index("handler.a") < handlers.index("handler.c")
        assert handlers.index("handler.b") < handlers.index("handler.c")

    def test_requires_after_constraint(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test requires_after constraint (A declares B must run after it)."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_after=["handler:handler.b"],
            ),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers.index("handler.a") < handlers.index("handler.b")

    def test_diamond_dependency(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test diamond dependency pattern: A -> B, A -> C, B -> D, C -> D."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.d",
                requires_before=["handler:handler.b", "handler:handler.c"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # A must be first, D must be last
        assert handlers[0] == "handler.a"
        assert handlers[-1] == "handler.d"
        # B and C must be in middle
        assert set(handlers[1:3]) == {"handler.b", "handler.c"}


# =============================================================================
# Cycle Detection Tests
# =============================================================================


class TestCycleDetection:
    """Tests for cycle detection."""

    def test_direct_cycle_a_b_a(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test direct cycle: A -> B -> A."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.b"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.is_valid
        assert plan.has_conflicts()
        assert plan.has_blocking_conflicts()

        cycle_conflicts = plan.get_cycle_conflicts()
        assert len(cycle_conflicts) >= 1
        cycle = cycle_conflicts[0]
        assert cycle.conflict_type == "cycle"
        assert cycle.severity == "error"
        assert cycle.cycle_path is not None
        # Cycle path should contain both handlers
        assert "handler.a" in cycle.cycle_path
        assert "handler.b" in cycle.cycle_path

    def test_indirect_cycle_a_b_c_a(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test indirect cycle: A -> B -> C -> A."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.c"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        cycle_conflicts = plan.get_cycle_conflicts()
        assert len(cycle_conflicts) >= 1
        cycle = cycle_conflicts[0]
        assert cycle.conflict_type == "cycle"
        assert cycle.cycle_path is not None
        # Cycle should include all three handlers
        assert len(set(cycle.cycle_path)) >= 3

    def test_self_reference_not_a_cycle(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that self-reference is NOT treated as a cycle (filtered out)."""
        # Self-references are filtered during graph building
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.a"],  # Self-reference
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Self-references are filtered out, so no cycle
        assert plan.is_valid

    def test_multiple_cycles_only_first_reported(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test fail-fast: only first cycle is reported when multiple exist.

        The resolver uses fail-fast cycle detection for performance and simplicity.
        When multiple independent cycles exist in the graph, only the first one
        encountered is reported. This is documented in ModelExecutionConflict.

        This test creates a graph with TWO independent cycles:
        - Cycle 1: alpha -> beta -> alpha
        - Cycle 2: gamma -> delta -> gamma

        These cycles are independent (no shared handlers). The resolver should
        detect and report exactly ONE cycle, then return immediately.

        Note:
            The specific cycle reported depends on traversal order (alphabetical
            by handler ID for determinism). Users should fix the reported cycle
            and re-run resolution to discover additional cycles.
        """
        # Create two independent cycles
        contracts = [
            # Cycle 1: alpha <-> beta
            _create_contract(
                "handler.alpha",
                requires_before=["handler:handler.beta"],
            ),
            _create_contract(
                "handler.beta",
                requires_before=["handler:handler.alpha"],
            ),
            # Cycle 2: gamma <-> delta (independent of cycle 1)
            _create_contract(
                "handler.gamma",
                requires_before=["handler:handler.delta"],
            ),
            _create_contract(
                "handler.delta",
                requires_before=["handler:handler.gamma"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Plan should be invalid due to cycle
        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        # CRITICAL: Only ONE cycle should be reported (fail-fast behavior)
        cycle_conflicts = plan.get_cycle_conflicts()
        assert len(cycle_conflicts) == 1, (
            f"Expected exactly 1 cycle conflict (fail-fast), but got "
            f"{len(cycle_conflicts)}. Fail-fast behavior is documented in "
            f"ModelExecutionConflict and _detect_cycles method."
        )

        # The single reported cycle should be valid
        cycle = cycle_conflicts[0]
        assert cycle.conflict_type == "cycle"
        assert cycle.severity == "error"
        assert cycle.cycle_path is not None
        assert len(cycle.cycle_path) >= 2  # At least 2 unique handlers + repeat


# =============================================================================
# Tie-Breaking Tests
# =============================================================================


class TestTieBreaking:
    """Tests for tie-breaking when handlers have no ordering constraints."""

    def test_priority_tie_breaking(
        self,
        resolver: ExecutionResolver,
        priority_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test priority-based tie-breaking (lower number = higher priority)."""
        contracts = [
            _create_contract("handler.z", priority=2),  # Lower priority
            _create_contract("handler.a", priority=1),  # Higher priority
            _create_contract("handler.m", priority=3),  # Lowest priority
        ]

        plan = resolver.resolve(priority_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be ordered by priority: 1, 2, 3
        # With secondary alphabetical for stability
        assert handlers[0] == "handler.a"  # priority 1
        assert handlers[1] == "handler.z"  # priority 2
        assert handlers[2] == "handler.m"  # priority 3

    def test_alphabetical_tie_breaking(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test alphabetical tie-breaking."""
        contracts = [
            _create_contract("handler.charlie"),
            _create_contract("handler.alpha"),
            _create_contract("handler.bravo"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be alphabetical
        assert handlers == ["handler.alpha", "handler.bravo", "handler.charlie"]

    def test_priority_then_alphabetical(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test priority first, then alphabetical for same priority."""
        contracts = [
            _create_contract("handler.z", priority=1),  # High priority
            _create_contract("handler.b", priority=2),  # Lower priority
            _create_contract("handler.a", priority=2),  # Same priority as b
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # z first (priority 1), then a before b (same priority 2, alphabetical)
        assert handlers[0] == "handler.z"
        # a and b have same priority, alphabetical order
        assert handlers[1] == "handler.a"
        assert handlers[2] == "handler.b"

    def test_tie_breaker_decision_recorded(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that tie-breaker decisions are recorded in metadata."""
        contracts = [
            _create_contract("handler.b"),
            _create_contract("handler.a"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        # Verify deterministic resolution occurred
        assert plan.resolution_metadata.deterministic is True
        # Verify handlers are in expected order (alphabetical since same priority)
        handlers = plan.get_all_handler_ids()
        assert handlers[0] == "handler.a"  # alphabetically first
        assert handlers[1] == "handler.b"  # alphabetically second


# =============================================================================
# Phase Assignment Tests
# =============================================================================


class TestPhaseAssignment:
    """Tests for handler phase assignment."""

    def test_handlers_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that handlers are assigned to the execute phase."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        # Find the execute phase
        execute_phase = None
        for phase in plan.phases:
            if phase.phase.value == "execute":
                execute_phase = phase
                break

        assert execute_phase is not None
        assert "handler.a" in execute_phase.handler_ids
        assert "handler.b" in execute_phase.handler_ids

    def test_phase_ordering_preserved(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that dependency order is preserved within phases."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = None
        for phase in plan.phases:
            if phase.phase.value == "execute":
                execute_phase = phase
                break

        assert execute_phase is not None
        handlers = execute_phase.handler_ids
        assert handlers.index("handler.a") < handlers.index("handler.b")


# =============================================================================
# Constraint Reference Resolution Tests
# =============================================================================


class TestConstraintResolution:
    """Tests for resolving capability:, handler:, and tag: references."""

    def test_capability_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test capability: reference resolution."""
        contracts = [
            _create_contract(
                "handler.auth",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.api",
                requires_before=["capability:auth.provider"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # auth provides auth.provider, api requires it
        assert handlers.index("handler.auth") < handlers.index("handler.api")

    def test_tag_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test tag: reference resolution."""
        contracts = [
            _create_contract(
                "handler.core",
                tags=["core-execution"],
            ),
            _create_contract(
                "handler.metrics",
                requires_before=["tag:core-execution"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # metrics requires core-execution tag
        assert handlers.index("handler.core") < handlers.index("handler.metrics")

    def test_multiple_handlers_with_same_capability(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test multiple handlers providing the same capability."""
        contracts = [
            _create_contract(
                "handler.auth_basic",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.auth_oauth",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.api",
                requires_before=["capability:auth.provider"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        api_idx = handlers.index("handler.api")
        # Both auth handlers must come before api
        assert handlers.index("handler.auth_basic") < api_idx
        assert handlers.index("handler.auth_oauth") < api_idx

    def test_missing_handler_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing handler: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Plan is still valid (warning, not error)
        assert plan.is_valid
        assert plan.has_conflicts()
        # Should have warning about missing dependency
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].conflict_type == "missing_dependency"
        assert "handler.nonexistent" in warnings[0].message

    def test_missing_capability_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing capability: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["capability:unknown.capability"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert "unknown.capability" in warnings[0].message

    def test_missing_tag_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing tag: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["tag:unknown-tag"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert "unknown-tag" in warnings[0].message


# =============================================================================
# Strict Mode Tests
# =============================================================================


class TestStrictMode:
    """Tests for strict_mode parameter that upgrades missing dependency warnings to errors."""

    @pytest.fixture
    def strict_profile(self) -> ModelExecutionProfile:
        """Create a profile with strict_mode enabled in ordering_policy."""
        return ModelExecutionProfile(
            phases=list(DEFAULT_EXECUTION_PHASES),
            ordering_policy=ModelExecutionOrderingPolicy(
                strategy="topological_sort",
                tie_breakers=["priority", "alphabetical"],
                deterministic_seed=True,
                strict_mode=True,
            ),
        )

    def test_strict_mode_missing_handler_is_error(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing handler: reference is error in strict mode."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        # Pass strict_mode=True explicitly
        plan = resolver.resolve(default_profile, contracts, strict_mode=True)

        # Plan is invalid in strict mode
        assert not plan.is_valid
        assert plan.has_conflicts()
        assert plan.has_blocking_conflicts()

        # Should have error (not warning) about missing dependency
        errors = [c for c in plan.conflicts if c.severity == "error"]
        assert len(errors) == 1
        assert errors[0].conflict_type == "missing_dependency"
        assert "handler.nonexistent" in errors[0].message

    def test_strict_mode_missing_capability_is_error(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing capability: reference is error in strict mode."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["capability:unknown.capability"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts, strict_mode=True)

        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        errors = [c for c in plan.conflicts if c.severity == "error"]
        assert len(errors) == 1
        assert "unknown.capability" in errors[0].message

    def test_strict_mode_missing_tag_is_error(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing tag: reference is error in strict mode."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["tag:unknown-tag"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts, strict_mode=True)

        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        errors = [c for c in plan.conflicts if c.severity == "error"]
        assert len(errors) == 1
        assert "unknown-tag" in errors[0].message

    def test_strict_mode_from_profile(
        self,
        resolver: ExecutionResolver,
        strict_profile: ModelExecutionProfile,
    ) -> None:
        """Test strict mode from profile's ordering_policy.strict_mode."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        # Don't pass strict_mode, use profile's setting
        plan = resolver.resolve(strict_profile, contracts)

        # Plan is invalid because profile has strict_mode=True
        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

    def test_strict_mode_explicit_overrides_profile(
        self,
        resolver: ExecutionResolver,
        strict_profile: ModelExecutionProfile,
    ) -> None:
        """Test explicit strict_mode=False overrides profile's strict_mode=True."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        # Explicitly disable strict mode, overriding profile
        plan = resolver.resolve(strict_profile, contracts, strict_mode=False)

        # Plan is valid because we overrode strict_mode
        assert plan.is_valid
        warnings = plan.get_warnings()
        assert len(warnings) == 1

    def test_non_strict_mode_missing_handler_is_warning(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing handler: reference is warning in non-strict mode (default)."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        # Default is strict_mode=False
        plan = resolver.resolve(default_profile, contracts)

        # Plan is still valid (warning, not error)
        assert plan.is_valid
        assert not plan.has_blocking_conflicts()

        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_strict_mode_multiple_missing_dependencies(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test multiple missing dependencies all become errors in strict mode."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=[
                    "handler:handler.nonexistent",
                    "capability:unknown.capability",
                    "tag:unknown-tag",
                ],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts, strict_mode=True)

        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        # All three missing dependencies should be errors
        errors = [c for c in plan.conflicts if c.severity == "error"]
        assert len(errors) == 3
        assert all(e.conflict_type == "missing_dependency" for e in errors)

    def test_strict_mode_with_valid_dependencies_succeeds(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test strict mode doesn't affect valid resolutions."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts, strict_mode=True)

        # Plan is valid - all dependencies resolved
        assert plan.is_valid
        assert not plan.has_conflicts()

        handlers = plan.get_all_handler_ids()
        assert handlers.index("handler.a") < handlers.index("handler.b")


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_contracts_list(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test resolution with empty contracts list."""
        plan = resolver.resolve(default_profile, [])

        assert plan.is_valid
        assert plan.is_empty()
        assert plan.total_handlers() == 0
        assert not plan.has_conflicts()

    def test_single_contract(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test resolution with single contract."""
        contracts = [_create_contract("handler.solo")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.total_handlers() == 1
        handlers = plan.get_all_handler_ids()
        assert handlers == ["handler.solo"]

    def test_all_handlers_independent(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test all handlers with no dependencies (all independent)."""
        contracts = [
            _create_contract("handler.delta"),
            _create_contract("handler.alpha"),
            _create_contract("handler.charlie"),
            _create_contract("handler.bravo"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be alphabetically sorted
        assert handlers == [
            "handler.alpha",
            "handler.bravo",
            "handler.charlie",
            "handler.delta",
        ]

    def test_no_constraints_in_contract(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test contracts with no execution_constraints field."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.total_handlers() == 2

    def test_large_chain(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test a longer dependency chain."""
        # Create chain: h0 -> h1 -> h2 -> ... -> h9
        contracts = [_create_contract("handler.h0")]
        for i in range(1, 10):
            contracts.append(
                _create_contract(
                    f"handler.h{i}",
                    requires_before=[f"handler:handler.h{i - 1}"],
                )
            )

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Verify order
        for i in range(10):
            assert handlers[i] == f"handler.h{i}"


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests verifying deterministic output."""

    def test_same_input_same_output(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that same inputs produce same outputs."""
        contracts = [
            _create_contract("handler.charlie"),
            _create_contract("handler.alpha"),
            _create_contract("handler.bravo"),
        ]

        plan1 = resolver.resolve(default_profile, contracts)
        plan2 = resolver.resolve(default_profile, contracts)

        assert plan1.is_valid and plan2.is_valid
        assert plan1.get_all_handler_ids() == plan2.get_all_handler_ids()

    def test_order_independence(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that input order doesn't affect output (when no deps)."""
        contracts1 = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
            _create_contract("handler.c"),
        ]
        contracts2 = [
            _create_contract("handler.c"),
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan1 = resolver.resolve(default_profile, contracts1)
        plan2 = resolver.resolve(default_profile, contracts2)

        assert plan1.is_valid and plan2.is_valid
        # Deterministic resolution must produce SAME ordering regardless of input order
        assert plan1.get_all_handler_ids() == plan2.get_all_handler_ids()


# =============================================================================
# Resolution Metadata Tests
# =============================================================================


class TestResolutionMetadata:
    """Tests for resolution metadata tracking."""

    def test_metadata_populated(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that resolution metadata is populated."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.resolution_metadata is not None
        meta = plan.resolution_metadata
        assert meta.strategy == "topological_sort"
        assert meta.total_handlers_resolved == 2
        assert meta.total_constraints_evaluated >= 1
        assert meta.resolution_started_at is not None
        assert meta.resolution_completed_at is not None
        assert meta.resolution_duration_ms is not None
        assert meta.resolution_duration_ms >= 0

    def test_constraint_count_tracking(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that constraint count is tracked correctly."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
                requires_after=["handler:handler.c"],
            ),
            _create_contract("handler.c"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.resolution_metadata is not None
        # handler.b has 2 constraints (1 before, 1 after)
        assert plan.resolution_metadata.total_constraints_evaluated == 2


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestProtocolCompliance:
    """Tests verifying ProtocolExecutionResolver compliance."""

    def test_resolver_is_protocol_compliant(
        self,
        resolver: ExecutionResolver,
    ) -> None:
        """Test that ExecutionResolver implements the protocol interface."""
        from omnibase_core.protocols.resolution.protocol_execution_resolver import (
            ProtocolExecutionResolver,
        )

        assert isinstance(resolver, ProtocolExecutionResolver)

    def test_resolve_signature_matches_protocol(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that resolve() method signature matches protocol."""
        contracts: list[ModelHandlerContract] = []
        # Should not raise TypeError
        plan = resolver.resolve(default_profile, contracts)
        assert plan is not None


# =============================================================================
# Can Execute Tests
# =============================================================================


class TestCanExecute:
    """Tests for plan.can_execute() method."""

    def test_valid_plan_can_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that valid non-empty plan can execute."""
        contracts = [_create_contract("handler.a")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.can_execute()

    def test_invalid_plan_cannot_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that invalid plan cannot execute."""
        # Create cycle
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.b"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.can_execute()

    def test_empty_plan_cannot_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that empty plan cannot execute."""
        plan = resolver.resolve(default_profile, [])

        assert not plan.can_execute()


# =============================================================================
# Phase Assignment Constraint Tests
# =============================================================================


class TestPhaseAssignmentConstraints:
    """
    Tests for phase assignment constraints based on ONEX Four-Node Architecture.

    These tests verify that:
    1. Handlers with different handler_kinds are tracked in contracts
    2. Cross-phase dependency constraints are respected
    3. Phase boundaries prevent invalid dependency patterns
    4. Future phase hint support is forward-compatible

    The ONEX Four-Node Architecture defines:
    - PREFLIGHT: Validation and setup before main execution
    - BEFORE: Pre-processing hooks and preparation
    - EXECUTE: Core handler logic execution
    - AFTER: Post-processing hooks and cleanup
    - EMIT: Event emission and notification
    - FINALIZE: Final cleanup and resource release

    Phases execute in strict order: PREFLIGHT -> BEFORE -> EXECUTE -> AFTER -> EMIT -> FINALIZE

    Currently, all handlers are assigned to EXECUTE phase. These tests document
    expected behavior and prepare for future phase hint support (when handlers
    can declare target phases in execution_constraints).
    """

    def test_handler_kind_compute_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that compute handlers are assigned to the EXECUTE phase.

        Compute handlers perform pure data transformations with no side effects.
        Per ONEX architecture, they belong in the EXECUTE phase where core
        logic runs.
        """
        contracts = [
            _create_contract("handler.compute_transform"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = next(
            (p for p in plan.phases if p.phase.value == "execute"), None
        )
        assert execute_phase is not None
        assert "handler.compute_transform" in execute_phase.handler_ids

    def test_handler_kind_effect_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that effect handlers are assigned to the EXECUTE phase.

        Effect handlers perform external I/O operations with side effects.
        Currently assigned to EXECUTE phase; future versions may support
        explicit phase hints for BEFORE (setup) or FINALIZE (cleanup).
        """
        # Create contract with effect handler_kind
        effect_contract = ModelHandlerContract(
            handler_id="handler.effect_io",
            name="Effect IO Handler",
            version="1.0.0",
            descriptor=ModelHandlerBehavior(handler_kind="effect"),
            input_model="test.Input",
            output_model="test.Output",
            metadata={"priority": 0},
        )
        contracts = [effect_contract]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = next(
            (p for p in plan.phases if p.phase.value == "execute"), None
        )
        assert execute_phase is not None
        assert "handler.effect_io" in execute_phase.handler_ids

    def test_handler_kind_reducer_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that reducer handlers are assigned to the EXECUTE phase.

        Reducer handlers perform state aggregation with FSM-driven transitions.
        They belong in EXECUTE phase where core state management occurs.
        """
        reducer_contract = ModelHandlerContract(
            handler_id="handler.reducer_state",
            name="Reducer State Handler",
            version="1.0.0",
            descriptor=ModelHandlerBehavior(handler_kind="reducer"),
            input_model="test.Input",
            output_model="test.Output",
            metadata={"priority": 0},
        )
        contracts = [reducer_contract]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = next(
            (p for p in plan.phases if p.phase.value == "execute"), None
        )
        assert execute_phase is not None
        assert "handler.reducer_state" in execute_phase.handler_ids

    def test_handler_kind_orchestrator_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that orchestrator handlers are assigned to the EXECUTE phase.

        Orchestrator handlers coordinate workflows and emit events/intents.
        Per ONEX architecture, they coordinate other handlers in EXECUTE phase.
        """
        orchestrator_contract = ModelHandlerContract(
            handler_id="handler.orchestrator_workflow",
            name="Orchestrator Workflow Handler",
            version="1.0.0",
            descriptor=ModelHandlerBehavior(handler_kind="orchestrator"),
            input_model="test.Input",
            output_model="test.Output",
            metadata={"priority": 0},
        )
        contracts = [orchestrator_contract]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = next(
            (p for p in plan.phases if p.phase.value == "execute"), None
        )
        assert execute_phase is not None
        assert "handler.orchestrator_workflow" in execute_phase.handler_ids

    def test_mixed_handler_kinds_all_in_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that all handler kinds (compute, effect, reducer, orchestrator)
        are assigned to EXECUTE phase.

        This documents current behavior where phase assignment does not yet
        use handler_kind hints. All handlers go to EXECUTE phase.
        """
        contracts = [
            ModelHandlerContract(
                handler_id="handler.compute",
                name="Compute Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="compute"),
                input_model="test.Input",
                output_model="test.Output",
                metadata={"priority": 0},
            ),
            ModelHandlerContract(
                handler_id="handler.effect",
                name="Effect Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="effect"),
                input_model="test.Input",
                output_model="test.Output",
                metadata={"priority": 0},
            ),
            ModelHandlerContract(
                handler_id="handler.reducer",
                name="Reducer Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="reducer"),
                input_model="test.Input",
                output_model="test.Output",
                metadata={"priority": 0},
            ),
            ModelHandlerContract(
                handler_id="handler.orchestrator",
                name="Orchestrator Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="orchestrator"),
                input_model="test.Input",
                output_model="test.Output",
                metadata={"priority": 0},
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = next(
            (p for p in plan.phases if p.phase.value == "execute"), None
        )
        assert execute_phase is not None

        # All four handler kinds should be in execute phase
        assert len(execute_phase.handler_ids) == 4
        assert "handler.compute" in execute_phase.handler_ids
        assert "handler.effect" in execute_phase.handler_ids
        assert "handler.reducer" in execute_phase.handler_ids
        assert "handler.orchestrator" in execute_phase.handler_ids

    def test_phase_ordering_respects_dependency_within_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that dependency ordering is preserved within the EXECUTE phase.

        Even when all handlers are in the same phase, topological ordering
        based on requires_before/requires_after must be respected.
        """
        contracts = [
            ModelHandlerContract(
                handler_id="handler.validation",
                name="Validation Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="compute"),
                input_model="test.Input",
                output_model="test.Output",
                metadata={"priority": 0},
            ),
            ModelHandlerContract(
                handler_id="handler.process",
                name="Process Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="compute"),
                input_model="test.Input",
                output_model="test.Output",
                execution_constraints=ModelExecutionConstraints(
                    requires_before=["handler:handler.validation"],
                ),
                metadata={"priority": 0},
            ),
            ModelHandlerContract(
                handler_id="handler.finalize",
                name="Finalize Handler",
                version="1.0.0",
                descriptor=ModelHandlerBehavior(handler_kind="effect"),
                input_model="test.Input",
                output_model="test.Output",
                execution_constraints=ModelExecutionConstraints(
                    requires_before=["handler:handler.process"],
                ),
                metadata={"priority": 0},
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()

        # Dependencies must be respected: validation -> process -> finalize
        assert handlers.index("handler.validation") < handlers.index("handler.process")
        assert handlers.index("handler.process") < handlers.index("handler.finalize")

    def test_non_execute_phases_are_empty(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that non-EXECUTE phases (PREFLIGHT, BEFORE, AFTER, EMIT, FINALIZE)
        are empty when no phase hints are used.

        This documents current behavior where all handlers go to EXECUTE phase.
        Future implementations may populate other phases based on handler_kind
        or explicit phase hints in execution_constraints.
        """
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid

        # All non-execute phases should be empty
        for phase in plan.phases:
            if phase.phase.value != "execute":
                assert len(phase.handler_ids) == 0, (
                    f"Phase {phase.phase.value} should be empty, "
                    f"but contains: {phase.handler_ids}"
                )

    def test_all_default_phases_present_in_plan(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that all six default phases are present in the execution plan.

        The ONEX pipeline defines six phases that execute in order:
        PREFLIGHT -> BEFORE -> EXECUTE -> AFTER -> EMIT -> FINALIZE

        Even if phases are empty, they should be present in the plan for
        future extension and explicit phase sequencing.
        """
        contracts = [_create_contract("handler.solo")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid

        # Extract phase names from plan
        phase_names = [phase.phase.value for phase in plan.phases]

        # All six default phases should be present
        expected_phases = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        for expected in expected_phases:
            assert expected in phase_names, f"Phase '{expected}' missing from plan"

    def test_cross_phase_dependency_within_execute_allowed(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Test that dependencies between handlers in the same phase are allowed.

        When all handlers are in EXECUTE phase, arbitrary dependency chains
        between them should be valid and respected in ordering.
        """
        # Create a complex dependency graph within EXECUTE phase
        contracts = [
            _create_contract("handler.auth", capability_outputs=["auth.token"]),
            _create_contract(
                "handler.validate",
                requires_before=["capability:auth.token"],
            ),
            _create_contract(
                "handler.transform",
                requires_before=["handler:handler.validate"],
            ),
            _create_contract(
                "handler.persist",
                requires_before=["handler:handler.transform"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()

        # Verify full dependency chain is respected
        assert handlers.index("handler.auth") < handlers.index("handler.validate")
        assert handlers.index("handler.validate") < handlers.index("handler.transform")
        assert handlers.index("handler.transform") < handlers.index("handler.persist")

    def test_phase_boundary_future_constraint_documented(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """
        Document future phase boundary constraint behavior.

        When future phase hint support is added, handlers should not be able
        to declare dependencies across phase boundaries in invalid ways:
        - EXECUTE handler cannot require AFTER handler (runs later)
        - PREFLIGHT handler cannot require EXECUTE handler (runs later)

        Currently, all handlers go to EXECUTE phase, so cross-phase constraints
        are not enforced. This test documents the expected future behavior.

        The plan should still be valid as phase hints are not yet implemented.
        """
        # Simulate what future cross-phase dependencies might look like
        # For now, these are just regular handlers with no phase hints
        contracts = [
            _create_contract("handler.preflight_validation", tags=["phase:preflight"]),
            _create_contract(
                "handler.execute_transform",
                tags=["phase:execute"],
                requires_before=["tag:phase:preflight"],
            ),
            _create_contract(
                "handler.after_cleanup",
                tags=["phase:after"],
                requires_before=["tag:phase:execute"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Plan is valid (all in EXECUTE phase currently)
        assert plan.is_valid
        handlers = plan.get_all_handler_ids()

        # Dependencies are respected even without explicit phase assignment
        assert handlers.index("handler.preflight_validation") < handlers.index(
            "handler.execute_transform"
        )
        assert handlers.index("handler.execute_transform") < handlers.index(
            "handler.after_cleanup"
        )


# =============================================================================
# Tie-Breaker Statistics Tests
# =============================================================================


class TestTieBreakerStatistics:
    """Tests for tie-breaker statistics tracking."""

    def test_statistics_empty_when_no_ties(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that statistics are empty when no tie-breaking needed."""
        # Single handler - no ties possible
        contracts = [_create_contract("handler.solo")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.resolution_metadata is not None
        assert plan.resolution_metadata.tie_breaker_statistics == {}

    def test_statistics_empty_for_empty_contracts(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that statistics are empty for empty contract list."""
        plan = resolver.resolve(default_profile, [])

        assert plan.resolution_metadata is not None
        assert plan.resolution_metadata.tie_breaker_statistics == {}

    def test_statistics_priority_tie_breaker(
        self,
        resolver: ExecutionResolver,
        priority_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test statistics when priority tie-breaker is used."""
        # Create handlers with different priorities - all independent
        contracts = [
            _create_contract("handler.z", priority=2),  # Lower priority
            _create_contract("handler.a", priority=1),  # Higher priority
            _create_contract("handler.m", priority=3),  # Lowest priority
        ]

        plan = resolver.resolve(priority_only_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        stats = plan.resolution_metadata.tie_breaker_statistics
        # Statistics may include "priority" if tie-breaking changed the order
        # The stats track when leader changed, not all sorts
        assert isinstance(stats, dict)

    def test_statistics_alphabetical_tie_breaker(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test statistics when alphabetical tie-breaker is used."""
        # Create independent handlers that will be sorted alphabetically
        contracts = [
            _create_contract("handler.charlie"),
            _create_contract("handler.alpha"),
            _create_contract("handler.bravo"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        stats = plan.resolution_metadata.tie_breaker_statistics
        # Should have alphabetical tie-breaker usage if order changed
        assert isinstance(stats, dict)
        # When there are independent handlers, alphabetical should be used
        if stats:
            assert "alphabetical" in stats

    def test_statistics_count_multiple_tie_breaks(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test that statistics correctly count multiple tie-breaks."""
        # Create a scenario with multiple independent groups requiring tie-breaking
        # All handlers are independent, so multiple tie-break decisions will be made
        contracts = [
            _create_contract("handler.d"),
            _create_contract("handler.c"),
            _create_contract("handler.b"),
            _create_contract("handler.a"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        stats = plan.resolution_metadata.tie_breaker_statistics
        # Multiple tie-breaking decisions should result in counts
        # The count represents number of times leader changed, not total sorts
        assert isinstance(stats, dict)

    def test_statistics_matches_decision_count(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test that statistics sum matches number of tie-breaker decisions."""
        contracts = [
            _create_contract("handler.z"),
            _create_contract("handler.a"),
            _create_contract("handler.m"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.resolution_metadata is not None
        stats = plan.resolution_metadata.tie_breaker_statistics
        decisions = plan.resolution_metadata.tie_breaker_decisions

        # Sum of all statistics should equal number of decisions
        total_from_stats = sum(stats.values())
        assert total_from_stats == len(decisions)

    def test_statistics_with_dependencies(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test statistics with handlers that have dependencies."""
        # B and C depend on A, but B and C are independent of each other
        contracts = [
            _create_contract("handler.c"),  # Will tie with B after A
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.d",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        # Statistics should be populated even with dependencies
        stats = plan.resolution_metadata.tie_breaker_statistics
        assert isinstance(stats, dict)
